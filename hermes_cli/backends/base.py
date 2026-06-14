from __future__ import annotations

from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from typing import Any, AsyncIterator


@dataclass(frozen=True)
class StreamEvent:
    type: str
    data: dict[str, Any] = field(default_factory=dict)


class AgentBackend(ABC):
    @abstractmethod
    async def stream(
        self,
        messages: list[dict[str, Any]],
        tools: list[dict[str, Any]],
        system_prompt: str,
    ) -> AsyncIterator[StreamEvent]:
        raise NotImplementedError
