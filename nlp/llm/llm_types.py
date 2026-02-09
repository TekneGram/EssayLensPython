from __future__ import annotations
from dataclasses import dataclass
from typing import Any, Literal

@dataclass(frozen=True, slots=True)
class ChatRequest:
    system: str
    user: str
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    repeat_penalty: float | None = None
    seed: int | None = None
    stop: list[str] | None = None
    response_format: dict[str, Any] | None = None


@dataclass(frozen=True, slots=True)
class JsonSchemaChatRequest:
    system: str
    user: str
    schema: dict[str, Any]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    repeat_penalty: float | None = None
    seed: int | None = None
    stop: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ChatResponse:
    content: str
    reasoning_content: str | None
    finish_reason: str | None
    model: str | None
    usage: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    channel: Literal["content", "reasoning", "meta"]
    text: str
    finish_reason: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None
    done: bool = False