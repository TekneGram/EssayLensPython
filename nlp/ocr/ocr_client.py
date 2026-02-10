from __future__ import annotations

from dataclasses import dataclass
import base64
from typing import Any

import httpx
import requests

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from config.ocr_request_config import OcrRequestConfig

JSONDict = dict[str, Any]


@dataclass
class OcrClient:
    server_url: str
    model_name: str
    request_cfg: OcrRequestConfig
    timeout_s: float = 120.0

    @staticmethod
    def _extract_str(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    @staticmethod
    def _image_to_base64(image_bytes: bytes) -> str:
        if not image_bytes:
            raise ValueError("image_bytes must be non-empty")
        return base64.b64encode(image_bytes).decode("ascii")

    def _build_payload(
        self,
        image_bytes: bytes,
        prompt: str | None = None,
        **kwargs: Any,
    ) -> JSONDict:
        image_mime = kwargs.get("image_mime")
        if image_mime is None:
            image_mime = self.request_cfg.image_mime

        input_prompt = prompt if prompt is not None else self.request_cfg.prompt
        image_b64 = self._image_to_base64(image_bytes)
        image_url = f"data:{image_mime};base64,{image_b64}"

        content: list[dict[str, Any]] = []
        if input_prompt is not None:
            content.append({"type": "text", "text": input_prompt})
        content.append({"type": "image_url", "image_url": {"url": image_url}})

        payload: JSONDict = {
            "model": self.model_name,
            "messages": [
                {
                    "role": "user",
                    "content": content,
                }
            ],
        }

        for field in ["max_tokens", "temperature", "top_p", "top_k", "stream"]:
            val = kwargs.get(field)
            if val is None:
                val = getattr(self.request_cfg, field, None)
            if val is not None:
                payload[field] = val
        return payload

    def _parse_text_response(self, data: dict[str, Any]) -> str:
        choices = data.get("choices")
        first_choice: dict[str, Any] = {}
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            first_choice = choices[0]

        message = first_choice.get("message")
        message_dict = message if isinstance(message, dict) else {}
        content = message_dict.get("content")

        direct_text = self._extract_str(content)
        if direct_text is not None:
            return direct_text.strip()

        if isinstance(content, list):
            text_parts: list[str] = []
            for item in content:
                if not isinstance(item, dict):
                    continue
                if item.get("type") == "text":
                    text = self._extract_str(item.get("text"))
                    if text:
                        text_parts.append(text)
            return "\n".join(text_parts).strip()

        return ""

    def extract_text(self, image_bytes: bytes, prompt: str | None = None, **kwargs: Any) -> str:
        payload = self._build_payload(image_bytes=image_bytes, prompt=prompt, **kwargs)

        try:
            response = requests.post(self.server_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.exceptions.RequestException as exc:
            raise RuntimeError(f"OCR server connection failed: {exc}") from exc

        return self._parse_text_response(response.json())

    async def extract_text_async(
        self,
        image_bytes: bytes,
        prompt: str | None = None,
        **kwargs: Any,
    ) -> str:
        payload = self._build_payload(image_bytes=image_bytes, prompt=prompt, **kwargs)

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(self.server_url, json=payload)
                response.raise_for_status()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"OCR server error: {exc}") from exc

        return self._parse_text_response(response.json())
