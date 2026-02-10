from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from nlp.ocr.ocr_client import OcrClient


@dataclass
class OcrService:
    client: OcrClient

    def extract_text(self, image_bytes: bytes, prompt: str | None = None, **kwargs: Any) -> str:
        return self.client.extract_text(image_bytes=image_bytes, prompt=prompt, **kwargs)

    async def extract_text_async(
        self,
        image_bytes: bytes,
        prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        return await self.client.extract_text_async(
            image_bytes=image_bytes,
            prompt=prompt,
            **kwargs,
        )
