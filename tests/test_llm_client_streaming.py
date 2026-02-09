from __future__ import annotations

import unittest
from unittest.mock import patch

from config.llm_request_config import LlmRequestConfig
from nlp.llm.llm_client import (
    ChatResponse,
    ChatStreamAccumulator,
    ChatStreamEvent,
    OpenAICompatChatClient,
)


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
    def __init__(self, lines: list[str]) -> None:
        self._lines = lines

    def raise_for_status(self) -> None:
        return

    def iter_lines(self, decode_unicode: bool = True):
        for line in self._lines:
            yield line

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


class OpenAICompatChatClientStreamingTests(unittest.TestCase):
    def _build_client(self, model_family: str = "instruct/think") -> OpenAICompatChatClient:
        return OpenAICompatChatClient(
            server_url="http://127.0.0.1:8080/v1/chat/completions",
            model_name="demo-model",
            model_family=model_family,
            request_cfg=_request_cfg(),
        )

    def test_chat_stream_emits_content_reasoning_and_done(self) -> None:
        client = self._build_client().with_reasoning_mode("think")
        lines = [
            'data: {"model":"demo-model","choices":[{"delta":{"reasoning_content":"think "}}]}',
            'data: {"choices":[{"delta":{"content":"Hello"}}]}',
            'data: {"choices":[{"delta":{"content":" world"},"finish_reason":"stop"}],"usage":{"prompt_tokens":5}}',
            "data: [DONE]",
        ]

        with patch("nlp.llm.llm_client.requests.post", return_value=_FakeStreamResponse(lines)) as post_mock:
            events = list(client.chat_stream(system="sys", user="task"))

        self.assertGreaterEqual(len(events), 4)
        reasoning_events = [e for e in events if e.channel == "reasoning"]
        content_events = [e for e in events if e.channel == "content"]
        self.assertEqual(reasoning_events[0].text, "think ")
        self.assertEqual(content_events[0].text, "Hello")
        self.assertTrue(events[-1].done)
        payload = post_mock.call_args.kwargs["json"]
        self.assertTrue(payload["stream"])
        self.assertEqual(payload["messages"][1]["content"], "task /think")

    def test_aggregate_stream_events_builds_chat_response(self) -> None:
        events = [
            ChatStreamEvent(channel="content", text="Hello"),
            ChatStreamEvent(channel="reasoning", text="chain"),
            ChatStreamEvent(channel="content", text=" world"),
            ChatStreamEvent(channel="meta", text="", finish_reason="stop", model="demo"),
        ]
        response = OpenAICompatChatClient.aggregate_stream_events(events)
        self.assertIsInstance(response, ChatResponse)
        self.assertEqual(response.content, "Hello world")
        self.assertEqual(response.reasoning_content, "chain")
        self.assertEqual(response.finish_reason, "stop")
        self.assertEqual(response.model, "demo")

    def test_stream_malformed_json_raises_runtime_error(self) -> None:
        client = self._build_client().with_reasoning_mode("no_think")
        lines = ['data: {"choices":[{"delta":{"content":"ok"}}]}', "data: {bad json}"]

        with patch("nlp.llm.llm_client.requests.post", return_value=_FakeStreamResponse(lines)):
            with self.assertRaises(RuntimeError):
                list(client.chat_stream(system="sys", user="task"))

    def test_stream_accumulator_collects_response(self) -> None:
        state = ChatStreamAccumulator.create()
        state.add(ChatStreamEvent(channel="content", text="A"))
        state.add(ChatStreamEvent(channel="reasoning", text="B"))
        state.add(ChatStreamEvent(channel="meta", text="", usage={"prompt_tokens": 1}))

        response = state.to_response()
        self.assertEqual(response.content, "A")
        self.assertEqual(response.reasoning_content, "B")
        self.assertEqual(response.usage, {"prompt_tokens": 1})


if __name__ == "__main__":
    unittest.main()
