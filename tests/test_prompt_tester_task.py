from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from nlp.llm.tasks.prompt_tester import (
    SYSTEM_PROMPT,
    build_prompt_tester,
    run_parallel_prompt_tester,
)


class PromptTesterTaskTests(unittest.TestCase):
    def test_build_prompt_tester_builds_chat_requests(self) -> None:
        requests_ = build_prompt_tester(["text one", "text two"])

        self.assertEqual(len(requests_), 2)
        self.assertEqual(requests_[0].system, SYSTEM_PROMPT)
        self.assertEqual(requests_[0].user, "text one")
        self.assertEqual(requests_[0].temperature, 0.0)

    def test_run_parallel_prompt_tester_calls_chat_many(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=3))
        llm_service = Mock()
        llm_service.chat_many = AsyncMock(return_value=[Mock(content="ok"), RuntimeError("bad")])

        result = asyncio.run(
            run_parallel_prompt_tester(
                llm_service=llm_service,
                app_cfg=app_cfg,
                text_tasks=["doc a", "doc b"],
                max_concurrency=2,
            )
        )

        self.assertEqual(result["mode"], "parallel_chat")
        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        self.assertEqual(result["max_concurrency"], 2)
        llm_service.chat_many.assert_called_once()


if __name__ == "__main__":
    unittest.main()
