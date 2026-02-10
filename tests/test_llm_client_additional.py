from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

import httpx

from config.llm_request_config import LlmRequestConfig
from nlp.llm.llm_client import ChatRequest, JsonSchemaChatRequest, OpenAICompatChatClient


def _request_cfg() -> LlmRequestConfig:
    return LlmRequestConfig.from_values(
        max_tokens=128,
        temperature=0.2,
        top_p=0.95,
        top_k=40,
        repeat_penalty=1.1,
        seed=None,
        stop=None,
        response_format=None,
        stream=False,
    )


class _FakeStreamResponse:
    def __init__(self, error: Exception | None = None) -> None:
        self._error = error

    async def __aenter__(self):
        if self._error is not None:
            raise self._error
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def raise_for_status(self) -> None:
        return

    async def aiter_lines(self):
        if False:
            yield ""  # pragma: no cover


class _FakeAsyncClient:
    def __init__(self, stream_error: Exception | None = None) -> None:
        self._stream_error = stream_error

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    def stream(self, *args, **kwargs):
        _ = (args, kwargs)
        return _FakeStreamResponse(error=self._stream_error)


class LlmClientAdditionalTests(unittest.TestCase):
    def _build_client(self, model_family: str = "instruct") -> OpenAICompatChatClient:
        return OpenAICompatChatClient(
            server_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="demo-model",
            model_family=model_family,
            request_cfg=_request_cfg(),
        )

    def test_with_reasoning_mode_rejects_invalid_mode(self) -> None:
        client = self._build_client()
        with self.assertRaises(ValueError):
            client.with_reasoning_mode("bad")  # type: ignore[arg-type]

    def test_instruct_think_default_mode_raises_when_building_payload(self) -> None:
        client = self._build_client(model_family="instruct/think")
        with self.assertRaises(ValueError):
            client._build_payload(system="sys", user="u")

    def test_chat_many_raises_when_return_exceptions_false(self) -> None:
        client = self._build_client()
        client.chat_async = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            asyncio.run(
                client.chat_many(
                    [ChatRequest(system="sys", user="u")],
                    return_exceptions=False,
                )
            )

    def test_json_schema_chat_many_raises_when_return_exceptions_false(self) -> None:
        client = self._build_client()
        client.json_schema_chat_async = AsyncMock(side_effect=RuntimeError("boom"))  # type: ignore[method-assign]

        with self.assertRaises(RuntimeError):
            asyncio.run(
                client.json_schema_chat_many(
                    [JsonSchemaChatRequest(system="sys", user="u", schema={"type": "json_object"})],
                    return_exceptions=False,
                )
            )

    def test_chat_stream_async_wraps_httpx_error(self) -> None:
        client = self._build_client()
        err = httpx.RequestError("broken", request=httpx.Request("POST", "http://x"))
        fake_client = _FakeAsyncClient(stream_error=err)

        async def _collect() -> list:
            items = []
            async for event in client.chat_stream_async(system="sys", user="u"):
                items.append(event)
            return items

        with patch("nlp.llm.llm_client.httpx.AsyncClient", return_value=fake_client):
            with self.assertRaises(RuntimeError):
                asyncio.run(_collect())


if __name__ == "__main__":
    unittest.main()
