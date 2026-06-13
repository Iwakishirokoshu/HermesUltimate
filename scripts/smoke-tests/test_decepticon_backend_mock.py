from __future__ import annotations

import pytest

from hermes_cli.backends.decepticon_backend import DecepticonBackend


class FakeResponse:
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        return None

    async def aiter_lines(self):
        for line in self._lines:
            yield line


class FakeStreamContext:
    def __init__(self, response: FakeResponse) -> None:
        self.response = response

    async def __aenter__(self) -> FakeResponse:
        return self.response

    async def __aexit__(self, exc_type, exc, tb) -> None:
        return None


class FakeClient:
    def __init__(self, lines: list[str]) -> None:
        self.lines = lines
        self.stream_calls: list[dict] = []
        self.post_calls: list[dict] = []
        self.closed = False

    def stream(self, method: str, url: str, json: dict):
        self.stream_calls.append({"method": method, "url": url, "json": json})
        return FakeStreamContext(FakeResponse(self.lines))

    async def post(self, url: str, json: dict):
        self.post_calls.append({"url": url, "json": json})
        return FakeResponse([])

    async def aclose(self) -> None:
        self.closed = True


@pytest.mark.asyncio
async def test_decepticon_backend_parses_sse_events() -> None:
    lines = [
        'data: {"event":"on_chat_model_stream","data":{"chunk":{"content":"Hi "}}}',
        "",
        'event: tool_call',
        'data: {"data":{"id":"tc-1","name":"nmap","args":{"target":"10.0.0.1"}}}',
        "",
        'data: {"event":"on_tool_end","data":{"id":"tc-1","name":"nmap","output":"done"}}',
        "",
        "data: [DONE]",
        "",
    ]
    client = FakeClient(lines)
    backend = DecepticonBackend(
        base_url="http://decepticon.test",
        client_factory=lambda: client,
    )

    events = [
        event
        async for event in backend.stream(
            messages=[{"role": "user", "content": "scan"}],
            tools=[],
            system_prompt="system",
        )
    ]

    assert [event.type for event in events] == ["token", "tool_call", "tool_result"]
    assert events[0].data == {"text": "Hi "}
    assert events[1].data["name"] == "nmap"
    assert events[1].data["args"] == {"target": "10.0.0.1"}
    assert events[2].data["output"] == "done"
    assert client.stream_calls == [
        {
            "method": "POST",
            "url": "http://decepticon.test/runs/stream",
            "json": {
                "input": {
                    "messages": [{"role": "user", "content": "scan"}],
                    "tools": [],
                    "system_prompt": "system",
                }
            },
        }
    ]
    assert client.post_calls == []
    assert client.closed is True


@pytest.mark.asyncio
async def test_decepticon_backend_resumes_after_hitl_request() -> None:
    lines = [
        (
            'data: {"event":"hitl_request","run_id":"run-1",'
            '"data":{"command":"net user","description":"operator approval","run_id":"run-1"}}'
        ),
        "",
        "data: [DONE]",
        "",
    ]
    client = FakeClient(lines)
    approvals: list[dict] = []

    async def approve_once(data: dict):
        approvals.append(data)
        return {"approved": True, "choice": "once"}

    backend = DecepticonBackend(
        base_url="http://decepticon.test",
        approval_handler=approve_once,
        client_factory=lambda: client,
    )

    events = [
        event
        async for event in backend.stream(
            messages=[{"role": "user", "content": "need approval"}],
            tools=[],
            system_prompt="system",
        )
    ]

    assert [event.type for event in events] == ["hitl_request"]
    assert approvals[0]["type"] == "command-approval-request"
    assert approvals[0]["command"] == "net user"
    assert client.post_calls == [
        {
            "url": "http://decepticon.test/runs/run-1/resume",
            "json": {
                "input": {
                    "approved": True,
                    "choice": "once",
                    "message": None,
                    "approval": approvals[0],
                }
            },
        }
    ]
