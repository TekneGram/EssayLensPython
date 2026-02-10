from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class OcrRequestConfig:
    max_tokens: int
    temperature: float
    top_p: float | None
    top_k: int | None
    stream: bool | None
    image_mime: str
    prompt: str | None

    @staticmethod
    def from_values(
        max_tokens: int = 1024,
        temperature: float = 0.2,
        top_p: float | None = 0.9,
        top_k: int | None = 0,
        stream: bool | None = None,
        image_mime: str = "image/png",
        prompt: str | None = None,
    ) -> "OcrRequestConfig":
        return OcrRequestConfig(
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            stream=stream,
            image_mime=image_mime,
            prompt=prompt,
        )

    def validate(self) -> None:
        if self.max_tokens <= 0:
            raise ValueError("max_tokens must be > 0")
        if self.temperature < 0:
            raise ValueError("temperature must be >= 0")
        if self.top_p is not None and not (0 < self.top_p <= 1):
            raise ValueError("top_p must be in (0, 1] when provided")
        if self.top_k is not None and self.top_k < 0:
            raise ValueError("top_k must be >= 0 when provided")
        if not self.image_mime or not self.image_mime.strip():
            raise ValueError("image_mime must be a non-empty string")
        if self.prompt is not None and not self.prompt.strip():
            raise ValueError("prompt must be non-empty when provided")
