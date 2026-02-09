from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from config.llm_request_config import LlmRequestConfig
from nlp.llm.llm_client import ChatResponse, OpenAICompatChatClient


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


class OpenAICompatChatClientResponseTests(unittest.TestCase):
    def _build_client(self, model_family: str = "instruct/think") -> OpenAICompatChatClient:
        return OpenAICompatChatClient(
            server_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="demo-model",
            model_family=model_family,
            request_cfg=_request_cfg(),
        )

    def test_parse_chat_response_with_reasoning(self) -> None:
        client = self._build_client()
        parsed = client._parse_chat_response(
            {
                "model": "demo-model",
                "usage": {"prompt_tokens": 10},
                "choices": [
                    {
                        "finish_reason": "stop",
                        "message": {
                            "content": "  hello world  ",
                            "reasoning_content": "  chain  ",
                        },
                    }
                ],
            }
        )
        self.assertEqual(parsed.content, "hello world")
        self.assertEqual(parsed.reasoning_content, "chain")
        self.assertEqual(parsed.finish_reason, "stop")
        self.assertEqual(parsed.model, "demo-model")
        self.assertEqual(parsed.usage, {"prompt_tokens": 10})

    def test_parse_chat_response_without_optional_fields(self) -> None:
        client = self._build_client()
        parsed = client._parse_chat_response({"choices": [{"message": {"content": "ok"}}]})
        self.assertEqual(parsed.content, "ok")
        self.assertIsNone(parsed.reasoning_content)
        self.assertIsNone(parsed.finish_reason)
        self.assertIsNone(parsed.model)
        self.assertIsNone(parsed.usage)

    def test_parse_chat_response_malformed_payload_falls_back(self) -> None:
        client = self._build_client()
        parsed = client._parse_chat_response({"choices": "invalid"})
        self.assertEqual(parsed.content, "")
        self.assertIsNone(parsed.reasoning_content)
        self.assertIsNone(parsed.finish_reason)
        self.assertIsNone(parsed.model)
        self.assertIsNone(parsed.usage)

    def test_chat_returns_chat_response(self) -> None:
        client = self._build_client()
        mock_response = Mock()
        mock_response.json.return_value = {
            "model": "demo-model",
            "choices": [{"message": {"content": "done"}, "finish_reason": "stop"}],
        }
        mock_response.raise_for_status.return_value = None

        with patch("nlp.llm.llm_client.requests.post", return_value=mock_response):
            response = client.with_reasoning_mode("no_think").chat("sys", "usr")

        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.content, "done")

    def test_instruct_think_mode_appends_think_trigger(self) -> None:
        client = self._build_client().with_reasoning_mode("think")
        payload = client._build_payload(system="sys", user="task")
        self.assertEqual(payload["messages"][1]["content"], "task /think")

    def test_instruct_think_mode_appends_no_think_trigger(self) -> None:
        client = self._build_client().with_reasoning_mode("no_think")
        payload = client._build_payload(system="sys", user="task")
        self.assertEqual(payload["messages"][1]["content"], "task /no_think")

    def test_non_toggle_model_ignores_reasoning_mode_trigger(self) -> None:
        client = self._build_client(model_family="instruct").with_reasoning_mode("think")
        payload = client._build_payload(system="sys", user="task")
        self.assertEqual(payload["messages"][1]["content"], "task")


if __name__ == "__main__":
    unittest.main()
