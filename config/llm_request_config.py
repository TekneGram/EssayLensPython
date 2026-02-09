from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LlmRequestConfig:
    max_tokens: int
    temperature: float
    top_p: float | None
    top_k: int | None
    repeat_penalty: float | None
    seed: int | None
    stop: list[str] | None
    response_format: dict[str, Any] | None
    stream: bool | None

    @staticmethod
    def from_values(
        max_tokens: int,
        temperature: float,
        top_p: float | None,
        top_k: int | None,
        repeat_penalty: float | None,
        seed: int | None,
        stop: list[str] | None,
        response_format: dict[str, Any] | None,
        stream: bool | None,
    ) -> "LlmRequestConfig":
        return LlmRequestConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            seed=seed,
            stop=stop,
            response_format=response_format,
            stream=stream,
        )

    def validate(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.temperature < 0:
            raise ValueError("temperature must be >= 0")
        if self.top_p is not None and not (0 < self.top_p <= 1):
            raise ValueError("top_p must be in (0, 1] when provided")
        if self.top_k is not None and self.top_k <= 0:
            raise ValueError("top_k must be > 0 when provided")
        if self.repeat_penalty is not None and self.repeat_penalty <= 0:
            raise ValueError("repeat_penalty must be > 0 when provided")

        if self.stop is not None:
            for token in self.stop:
                if not token or not token.strip():
                    raise ValueError("stop must only contain non-empty strings")
