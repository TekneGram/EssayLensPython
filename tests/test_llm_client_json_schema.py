from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock, patch

from config.llm_request_config import LlmRequestConfig
from nlp.llm.llm_client import JsonSchemaChatRequest, OpenAICompatChatClient


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


class _FakeAsyncResponse:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    def raise_for_status(self) -> None:
        return

    def json(self) -> dict:
        return self._payload


class _FakeAsyncClient:
    def __init__(self, payload: dict) -> None:
        self._payload = payload

    async def __aenter__(self):
        return self

    async def __aexit__(self, exc_type, exc, tb):
        return False

    async def post(self, *args, **kwargs):
        return _FakeAsyncResponse(self._payload)


class OpenAICompatJsonSchemaTests(unittest.TestCase):
    def _build_client(self, model_family: str = "instruct/think") -> OpenAICompatChatClient:
        return OpenAICompatChatClient(
            server_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="demo-model",
            model_family=model_family,
            request_cfg=_request_cfg(),
        )

    def test_json_schema_chat_returns_parsed_json(self) -> None:
        client = self._build_client().with_reasoning_mode("no_think")
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": '{"grade":"A","score":95}'}}]
        }
        schema = {"type": "json_object"}

        with patch("nlp.llm.llm_client.requests.post", return_value=mock_response) as post_mock:
            result = client.json_schema_chat(system="sys", user="task", schema=schema)

        self.assertEqual(result, {"grade": "A", "score": 95})
        payload = post_mock.call_args.kwargs["json"]
        self.assertEqual(payload["response_format"], schema)
        self.assertEqual(payload["messages"][1]["content"], "task /no_think")

    def test_json_schema_chat_raises_on_malformed_json(self) -> None:
        client = self._build_client().with_reasoning_mode("no_think")
        mock_response = Mock()
        mock_response.raise_for_status.return_value = None
        mock_response.json.return_value = {
            "choices": [{"message": {"content": "{bad json}"}}]
        }

        with patch("nlp.llm.llm_client.requests.post", return_value=mock_response):
            with self.assertRaises(RuntimeError):
                client.json_schema_chat(system="sys", user="task", schema={"type": "json_object"})

    def test_json_schema_chat_async_returns_parsed_json(self) -> None:
        client = self._build_client().with_reasoning_mode("think")
        payload = {"choices": [{"message": {"content": '{"ok":true}'}}]}
        fake_client = _FakeAsyncClient(payload)

        with patch("nlp.llm.llm_client.httpx.AsyncClient", return_value=fake_client):
            result = asyncio.run(
                client.json_schema_chat_async(
                    system="sys",
                    user="task",
                    schema={"type": "json_object"},
                )
            )

        self.assertEqual(result, {"ok": True})

    def test_json_schema_chat_many_uses_dedicated_request_shape(self) -> None:
        client = self._build_client(model_family="instruct")

        async def _fake_call(system: str, user: str, schema: dict, **kwargs):
            if user == "bad":
                raise RuntimeError("broken")
            return {"user": user, "schema_type": schema.get("type")}

        client.json_schema_chat_async = AsyncMock(side_effect=_fake_call)  # type: ignore[method-assign]

        requests_ = [
            JsonSchemaChatRequest(system="sys", user="ok", schema={"type": "json_object"}),
            JsonSchemaChatRequest(system="sys", user="bad", schema={"type": "json_object"}),
        ]
        result = asyncio.run(client.json_schema_chat_many(requests_))

        self.assertEqual(result[0], {"user": "ok", "schema_type": "json_object"})
        self.assertIsInstance(result[1], Exception)


if __name__ == "__main__":
    unittest.main()
