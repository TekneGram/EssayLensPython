from __future__ import annotations

import asyncio
import io
import unittest
from contextlib import redirect_stdout
from unittest.mock import AsyncMock, Mock

from nlp.llm.llm_client import ChatRequest, ChatResponse, ChatStreamEvent, JsonSchemaChatRequest
from services.llm_service import LlmService


class LlmServiceResponseTests(unittest.TestCase):
    def test_chat_returns_chat_response_from_client(self) -> None:
        expected = ChatResponse(
            content="answer",
            reasoning_content=None,
            finish_reason="stop",
            model="demo",
            usage={"prompt_tokens": 1},
        )
        mock_client = Mock()
        mock_client.chat.return_value = expected

        service = LlmService(client=mock_client)
        result = service.chat(system="sys", user="usr")

        self.assertIs(result, expected)
        mock_client.chat.assert_called_once()

    def test_chat_many_returns_response_or_exception(self) -> None:
        expected_response = ChatResponse(
            content="ok",
            reasoning_content=None,
            finish_reason=None,
            model=None,
            usage=None,
        )
        expected_error = RuntimeError("boom")
        mock_client = Mock()
        mock_client.chat_many = AsyncMock(return_value=[expected_response, expected_error])

        service = LlmService(client=mock_client, max_parallel=2)
        result = asyncio.run(
            service.chat_many(
                [ChatRequest(system="sys", user="a"), ChatRequest(system="sys", user="b")]
            )
        )

        self.assertEqual(result, [expected_response, expected_error])
        mock_client.chat_many.assert_called_once()

    def test_chat_stream_passthrough(self) -> None:
        stream_events = [
            ChatStreamEvent(channel="content", text="Hi"),
            ChatStreamEvent(channel="reasoning", text="think"),
            ChatStreamEvent(channel="meta", text="", done=True),
        ]
        mock_client = Mock()
        mock_client.chat_stream.return_value = iter(stream_events)

        service = LlmService(client=mock_client, max_parallel=2)
        result = list(service.chat_stream(system="sys", user="u"))

        self.assertEqual(result, stream_events)
        mock_client.chat_stream.assert_called_once()

    def test_chat_stream_to_terminal_prints_and_returns_response(self) -> None:
        stream_events = [
            ChatStreamEvent(channel="reasoning", text="R"),
            ChatStreamEvent(channel="content", text="A"),
            ChatStreamEvent(channel="content", text="B"),
            ChatStreamEvent(channel="meta", text="", finish_reason="stop", done=True),
        ]
        mock_client = Mock()
        mock_client.chat_stream.return_value = iter(stream_events)
        service = LlmService(client=mock_client)

        capture = io.StringIO()
        with redirect_stdout(capture):
            response = service.chat_stream_to_terminal(system="sys", user="u")

        self.assertEqual(response.content, "AB")
        self.assertEqual(response.reasoning_content, "R")
        self.assertEqual(response.finish_reason, "stop")
        self.assertIn("[reasoning] RAB", capture.getvalue())

    def test_chat_stream_async_passthrough(self) -> None:
        async def _event_source():
            for event in [
                ChatStreamEvent(channel="content", text="X"),
                ChatStreamEvent(channel="meta", text="", done=True),
            ]:
                yield event

        mock_client = Mock()
        mock_client.chat_stream_async = Mock(return_value=_event_source())
        service = LlmService(client=mock_client)

        async def _collect():
            items: list[ChatStreamEvent] = []
            async for event in service.chat_stream_async(system="sys", user="u"):
                items.append(event)
            return items

        result = asyncio.run(_collect())
        self.assertEqual(len(result), 2)
        self.assertEqual(result[0].text, "X")

    def test_json_schema_chat_passthrough(self) -> None:
        mock_client = Mock()
        mock_client.json_schema_chat.return_value = {"ok": True}
        service = LlmService(client=mock_client)

        result = service.json_schema_chat(
            system="sys",
            user="u",
            schema={"type": "json_object"},
            max_tokens=200,
        )

        self.assertEqual(result, {"ok": True})
        mock_client.json_schema_chat.assert_called_once()

    def test_json_schema_chat_async_passthrough(self) -> None:
        mock_client = Mock()
        mock_client.json_schema_chat_async = AsyncMock(return_value={"score": 100})
        service = LlmService(client=mock_client)

        result = asyncio.run(
            service.json_schema_chat_async(
                system="sys",
                user="u",
                schema={"type": "json_object"},
            )
        )

        self.assertEqual(result, {"score": 100})
        mock_client.json_schema_chat_async.assert_called_once()

    def test_json_schema_chat_many_passthrough(self) -> None:
        requests_ = [
            JsonSchemaChatRequest(system="sys", user="u1", schema={"type": "json_object"}),
            JsonSchemaChatRequest(system="sys", user="u2", schema={"type": "json_object"}),
        ]
        mock_client = Mock()
        mock_client.json_schema_chat_many = AsyncMock(return_value=[{"id": 1}, RuntimeError("x")])
        service = LlmService(client=mock_client, max_parallel=4)

        result = asyncio.run(service.json_schema_chat_many(requests_))

        self.assertEqual(result[0], {"id": 1})
        self.assertIsInstance(result[1], Exception)
        mock_client.json_schema_chat_many.assert_called_once()


if __name__ == "__main__":
    unittest.main()
