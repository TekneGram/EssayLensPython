from __future__ import annotations

import asyncio
import unittest
from unittest.mock import Mock, patch

import httpx
import requests

from config.ocr_request_config import OcrRequestConfig
from nlp.ocr.ocr_client import OcrClient


def _request_cfg() -> OcrRequestConfig:
    return OcrRequestConfig.from_values(
        max_tokens=128,
        temperature=0.1,
        top_p=0.95,
        top_k=20,
        stream=False,
        image_mime="image/png",
        prompt="Read this image.",
    )


class _FakeAsyncResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload: dict | None = None, error: Exception | None = None) -> None:
        self._payload = payload or {}
        self._error = error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        if self._error is not None:
            raise self._error
        return _FakeAsyncResponse(self._payload)


class OcrClientTests(unittest.TestCase):
    def _build_client(self) -> OcrClient:
        return OcrClient(
            server_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="ocr-model",
            request_cfg=_request_cfg(),
        )

    def test_image_to_base64_rejects_empty_bytes(self) -> None:
        with self.assertRaises(ValueError):
            OcrClient._image_to_base64(b"")

    def test_build_payload_includes_text_and_image(self) -> None:
        client = self._build_client()
        payload = client._build_payload(image_bytes=b"\x89PNG", prompt="Extract all text")

        self.assertEqual(payload["model"], "ocr-model")
        self.assertEqual(payload["messages"][0]["role"], "user")
        content = payload["messages"][0]["content"]
        self.assertEqual(content[0]["type"], "text")
        self.assertEqual(content[0]["text"], "Extract all text")
        self.assertEqual(content[1]["type"], "image_url")
        self.assertTrue(content[1]["image_url"]["url"].startswith("data:image/png;base64,"))
        self.assertEqual(payload["max_tokens"], 128)
        self.assertEqual(payload["top_k"], 20)

    def test_parse_text_response_supports_direct_string_and_list(self) -> None:
        client = self._build_client()
        direct = client._parse_text_response(
            {"choices": [{"message": {"content": "  direct text  "}}]}
        )
        self.assertEqual(direct, "direct text")

        list_content = client._parse_text_response(
            {
                "choices": [
                    {
                        "message": {
                            "content": [
                                {"type": "text", "text": "line 1"},
                                {"type": "ignored", "text": "x"},
                                {"type": "text", "text": "line 2"},
                            ]
                        }
                    }
                ]
            }
        )
        self.assertEqual(list_content, "line 1\nline 2")

    def test_extract_text_wraps_requests_errors(self) -> None:
        client = self._build_client()
        with patch(
            "nlp.ocr.ocr_client.requests.post",
            side_effect=requests.exceptions.RequestException("network down"),
        ):
            with self.assertRaises(RuntimeError):
                client.extract_text(image_bytes=b"img")

    def test_extract_text_returns_parsed_text(self) -> None:
        client = self._build_client()
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {"choices": [{"message": {"content": "ok"}}]}
        with patch("nlp.ocr.ocr_client.requests.post", return_value=mock_response):
            result = client.extract_text(image_bytes=b"img")
        self.assertEqual(result, "ok")

    def test_extract_text_async_wraps_httpx_errors(self) -> None:
        client = self._build_client()
        fake_client = _FakeAsyncClient(
            error=httpx.RequestError("bad", request=httpx.Request("POST", "http://x"))
        )
        with patch("nlp.ocr.ocr_client.httpx.AsyncClient", return_value=fake_client):
            with self.assertRaises(RuntimeError):
                asyncio.run(client.extract_text_async(image_bytes=b"img"))

    def test_extract_text_async_returns_parsed_text(self) -> None:
        client = self._build_client()
        fake_client = _FakeAsyncClient(payload={"choices": [{"message": {"content": "async ok"}}]})
        with patch("nlp.ocr.ocr_client.httpx.AsyncClient", return_value=fake_client):
            result = asyncio.run(client.extract_text_async(image_bytes=b"img"))
        self.assertEqual(result, "async ok")


if __name__ == "__main__":
    unittest.main()
