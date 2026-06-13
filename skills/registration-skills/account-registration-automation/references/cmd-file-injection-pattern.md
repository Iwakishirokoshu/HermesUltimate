# Паттерн: Cmd-file injection для живого браузера

## Проблема

Playwright sync API в одном Python процессе. Нельзя параллельно:
- Ждать email (polling loop с time.sleep)
- Принимать команды извне

## Решение: cmd-file injection

Основной скрипт в конце (или в polling loop) проверяет файл-команд:

```python
CMD_FILE = "/tmp/chatgpt_next_cmd.py"
STATUS_FILE = "/tmp/chatgpt_status.txt"

def write_status(msg):
    with open(STATUS_FILE, "w") as f:
        f.write(msg + "\n")
    print(f"[STATUS] {msg}", flush=True)

# В конце основного flow — cmd loop
while True:
    if os.path.exists(CMD_FILE):
        cmd = open(CMD_FILE).read()
        os.remove(CMD_FILE)
        write_status(f"CMD: {cmd[:60]}...")
        try:
            exec(cmd, {"page": page, "ctx": ctx, "time": time,
                       "write_status": write_status})
            write_status("CMD_DONE")
        except Exception as e:
            write_status(f"CMD_ERROR: {e}")
    time.sleep(2)
```

Агент пишет Python-код в `/tmp/chatgpt_next_cmd.py`, браузер-процесс его подбирает и исполняет с доступом к `page` и `ctx`.

## КРИТИЧЕСКИЙ PITFALL: cmd-loop не работает во время основного polling

Если основной flow застрял в email-polling loop (`while elapsed < timeout: time.sleep(5)`),
cmd-файл не подхватывается. Решение — встраивать проверку cmd **внутрь** каждого polling loop:

```python
for attempt in range(retries):
    # Проверить cmd-файл в начале каждой итерации
    if os.path.exists(CMD_FILE):
        cmd = open(CMD_FILE).read(); os.remove(CMD_FILE)
        exec(cmd, {"page": page, "write_status": write_status})

    time.sleep(delay)
    # ... polling logic ...
```

## Паттерн: статус-файл для мониторинга

Агент читает `/tmp/chatgpt_status.txt` и tail лог-файла чтобы следить за прогрессом
фонового браузерного процесса без его прерывания.

```bash
# Мониторинг прогресса
cat /tmp/chatgpt_status.txt
tail -20 /tmp/browser_session.log
```

## Полный шаблон запуска

```python
# Запуск фонового скрипта
import subprocess, os
env = os.environ.copy()
env["CLOAKBROWSER_BINARY_PATH"] = os.path.expanduser(
    "~/.cloakbrowser/chromium-146.0.7680.177.5/chrome"
)
proc = subprocess.Popen(
    ["/home/hermes/.venv/bin/python3", "/tmp/browser_script.py"],
    stdout=open("/tmp/browser_script.log", "w"),
    stderr=subprocess.STDOUT,
    env=env
)
```

Или через terminal(background=True) с watch_patterns для ключевых событий.
