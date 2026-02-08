from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True, slots=True)
class LlmRequestConfig:
    default_max_tokens: int
    default_temperature: float
    default_top_p: float | None
    default_top_k: int | None
    default_repeat_penalty: float | None
    default_seed: int | None
    default_stop: list[str] | None
    default_response_format: dict[str, Any] | None
    default_stream: bool | None

    @staticmethod
    def from_values(
        default_max_tokens: int,
        default_temperature: float,
        default_top_p: float | None,
        default_top_k: int | None,
        default_repeat_penalty: float | None,
        default_seed: int | None,
        default_stop: list[str] | None,
        default_response_format: dict[str, Any] | None,
        default_stream: bool | None,
    ) -> "LlmRequestConfig":
        return LlmRequestConfig(
            default_max_tokens=default_max_tokens,
            default_temperature=default_temperature,
            default_top_p=default_top_p,
            default_top_k=default_top_k,
            default_repeat_penalty=default_repeat_penalty,
            default_seed=default_seed,
            default_stop=default_stop,
            default_response_format=default_response_format,
            default_stream=default_stream,
        )

    def validate(self) -> None:
        if self.default_max_tokens <= 0:
            raise ValueError("default_max_tokens must be > 0")
        if self.default_temperature < 0:
            raise ValueError("default_temperature must be >= 0")
        if self.default_top_p is not None and not (0 < self.default_top_p <= 1):
            raise ValueError("default_top_p must be in (0, 1] when provided")
        if self.default_top_k is not None and self.default_top_k <= 0:
            raise ValueError("default_top_k must be > 0 when provided")
        if self.default_repeat_penalty is not None and self.default_repeat_penalty <= 0:
            raise ValueError("default_repeat_penalty must be > 0 when provided")

        if self.default_stop is not None:
            for token in self.default_stop:
                if not token or not token.strip():
                    raise ValueError("default_stop must only contain non-empty strings")
