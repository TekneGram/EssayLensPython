from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from nlp.llm.llm_client import ChatRequest, ChatResponse
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


if __name__ == "__main__":
    unittest.main()
