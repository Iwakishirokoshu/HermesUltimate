"""
cdp_humanize_shim.py
CDP HTTP+WS man-in-the-middle. Перехватывает Input.dispatchMouseEvent type=mousePressed
и инжектит траекторию по Безье из последней известной позиции мыши до точки клика.

Схема: Agent -> http://127.0.0.1:9223 -> [shim] -> http://127.0.0.1:9222 -> CloakBrowser

Установка зависимостей:
  pip install aiohttp

Запуск (рядом с cloakbrowser_cdp.py):
  # Терминал 1: CloakBrowser
  DISPLAY=:1 python3 cloakbrowser_cdp.py acc_01

  # Терминал 2: shim
  python3 cdp_humanize_shim.py --listen 9223 --upstream-port 9222 -v

  # Подключить агента:
  hermes config set browser.cdp_url http://127.0.0.1:9223
  hermes config set browser.auto_local_for_private_urls false

  # Проверить:
  curl -s http://127.0.0.1:9223/json/version | python3 -m json.tool

Что делает shim:
  - mousePressed → инжектирует N mouseMoved по кривой Безье перед кликом
  - mouseReleased → небольшая задержка (имитация удержания)
  - mouseMoved → запоминает текущую позицию (для следующего клика)
  - Ответы на инжектированные ID фильтрует (не отдаёт клиенту)
  - /json/* → проксирует с заменой ws-порта на listen-порт
"""
import argparse, asyncio, json, logging, math, random, re
from typing import Dict, Tuple
import aiohttp
from aiohttp import web, WSMsgType

log = logging.getLogger("humanize")
INJECTED_BASE = 0x40000000  # ID-пространство для инжектов, не пересекается с клиентским

def bezier(p0, p1, p2, p3, t):
    u = 1 - t
    return (
        u*u*u*p0[0] + 3*u*u*t*p1[0] + 3*u*t*t*p2[0] + t*t*t*p3[0],
        u*u*u*p0[1] + 3*u*u*t*p1[1] + 3*u*t*t*p2[1] + t*t*t*p3[1],
    )

def make_curve(start, end, steps):
    sx, sy = start; ex, ey = end
    dx, dy = ex - sx, ey - sy
    d = max(1.0, math.hypot(dx, dy))
    px, py = -dy / d, dx / d  # перпендикуляр
    amp = min(d * 0.35, 220) * random.uniform(0.3, 1.0)
    c1 = (sx + dx*0.25 + px*amp*random.uniform(-1, 1),
          sy + dy*0.25 + py*amp*random.uniform(-1, 1))
    c2 = (sx + dx*0.75 + px*amp*random.uniform(-1, 1),
          sy + dy*0.75 + py*amp*random.uniform(-1, 1))
    pts = []
    for i in range(1, steps + 1):
        t = i / steps
        t = 3*t*t - 2*t*t*t  # smoothstep ease in-out
        pts.append(bezier(start, c1, c2, end, t))
    return pts


class WSSession:
    def __init__(self):
        self.mouse: Dict[str, Tuple[float, float]] = {}
        self.injected_ids: set = set()
        self.next_id = INJECTED_BASE

    def _new_id(self):
        self.next_id += 1
        self.injected_ids.add(self.next_id)
        return self.next_id

    async def humanize_click(self, params, session_id, up_ws):
        x = float(params.get("x", 0))
        y = float(params.get("y", 0))
        start = self.mouse.get(session_id)
        if start is None:
            start = (x + random.uniform(-180, 180), y + random.uniform(-140, 140))
        end = (x, y)
        dist = math.hypot(end[0]-start[0], end[1]-start[1])
        steps = max(8, min(45, int(dist / 12)))
        for cx, cy in make_curve(start, end, steps):
            inj = {
                "id": self._new_id(),
                "method": "Input.dispatchMouseEvent",
                "params": {
                    "type": "mouseMoved",
                    "x": cx + random.uniform(-0.4, 0.4),
                    "y": cy + random.uniform(-0.4, 0.4),
                    "button": "none", "buttons": 0,
                    "modifiers": params.get("modifiers", 0),
                },
            }
            if session_id:
                inj["sessionId"] = session_id
            await up_ws.send_str(json.dumps(inj))
            if random.random() < 0.08:
                await asyncio.sleep(random.uniform(0.04, 0.09))
            else:
                await asyncio.sleep(random.uniform(0.008, 0.022))
        await asyncio.sleep(random.uniform(0.05, 0.13))
        self.mouse[session_id] = end


async def ws_handler(request: web.Request):
    upstream_url = request.app["upstream_ws"] + request.rel_url.path_qs
    client = web.WebSocketResponse(max_msg_size=0)
    await client.prepare(request)
    log.info("WS open -> %s", upstream_url)
    sess = WSSession()
    timeout = aiohttp.ClientTimeout(total=None)
    async with aiohttp.ClientSession(timeout=timeout) as http:
        async with http.ws_connect(upstream_url, max_msg_size=0,
                                   autoclose=False, heartbeat=None) as up:
            async def c2u():
                async for m in client:
                    if m.type == WSMsgType.BINARY:
                        await up.send_bytes(m.data); continue
                    if m.type != WSMsgType.TEXT:
                        continue
                    try:
                        msg = json.loads(m.data)
                    except Exception:
                        await up.send_str(m.data); continue
                    if msg.get("method") == "Input.dispatchMouseEvent":
                        p = msg.get("params") or {}
                        sid = msg.get("sessionId", "")
                        t = p.get("type")
                        if t == "mouseMoved":
                            sess.mouse[sid] = (float(p.get("x", 0)), float(p.get("y", 0)))
                        elif t == "mousePressed":
                            await sess.humanize_click(p, sid, up)
                        elif t == "mouseReleased":
                            await asyncio.sleep(random.uniform(0.04, 0.13))
                    await up.send_str(m.data)

            async def u2c():
                async for m in up:
                    if m.type == WSMsgType.BINARY:
                        await client.send_bytes(m.data); continue
                    if m.type != WSMsgType.TEXT:
                        continue
                    try:
                        msg = json.loads(m.data)
                        mid = msg.get("id")
                        if isinstance(mid, int) and mid in sess.injected_ids:
                            sess.injected_ids.discard(mid); continue
                    except Exception:
                        pass
                    await client.send_str(m.data)

            await asyncio.gather(c2u(), u2c(), return_exceptions=True)
    log.info("WS closed")
    return client


async def http_handler(request: web.Request):
    """Прокси /json/* + переписывание webSocketDebuggerUrl на наш порт."""
    upstream = request.app["upstream_http"] + request.rel_url.path_qs
    headers = {k: v for k, v in request.headers.items() if k.lower() != "host"}
    data = await request.read() if request.can_read_body else None
    async with aiohttp.ClientSession() as http:
        async with http.request(request.method, upstream, headers=headers,
                                data=data, allow_redirects=False) as up:
            body = await up.read()
            if "json" in up.headers.get("Content-Type", ""):
                try:
                    text = body.decode("utf-8", "replace")
                    listen = request.app["listen"]
                    text = re.sub(r"ws://127\.0\.0\.1:\d+",
                                  f"ws://127.0.0.1:{listen}", text)
                    body = text.encode("utf-8")
                except Exception:
                    pass
            resp_headers = {k: v for k, v in up.headers.items()
                            if k.lower() not in ("content-length",
                                                 "transfer-encoding",
                                                 "content-encoding")}
            return web.Response(status=up.status, body=body, headers=resp_headers)


async def router(request: web.Request):
    if request.headers.get("Upgrade", "").lower() == "websocket":
        return await ws_handler(request)
    return await http_handler(request)


def main():
    p = argparse.ArgumentParser()
    p.add_argument("--listen", type=int, default=9223)
    p.add_argument("--upstream-host", default="127.0.0.1")
    p.add_argument("--upstream-port", type=int, default=9222)
    p.add_argument("-v", "--verbose", action="store_true")
    a = p.parse_args()
    logging.basicConfig(
        level=logging.DEBUG if a.verbose else logging.INFO,
        format="%(asctime)s %(levelname)s: %(message)s",
    )
    app = web.Application(client_max_size=1024**3)
    app["upstream_http"] = f"http://{a.upstream_host}:{a.upstream_port}"
    app["upstream_ws"]   = f"ws://{a.upstream_host}:{a.upstream_port}"
    app["listen"] = a.listen
    app.router.add_route("*", "/{tail:.*}", router)
    log.info("CDP humanize shim: 127.0.0.1:%d -> %s:%d",
             a.listen, a.upstream_host, a.upstream_port)
    web.run_app(app, host="127.0.0.1", port=a.listen, print=None)


if __name__ == "__main__":
    main()
