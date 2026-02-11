from __future__ import annotations

import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from services.llm_task_service import LlmTaskService


class LlmTaskServiceRuntimeTests(unittest.TestCase):
    def test_extract_metadata_parallel_uses_no_think_and_returns_result(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=2))

        llm_no_think = Mock()
        llm_no_think.json_schema_chat_many = AsyncMock(
            return_value=[
                {
                    "student_name": "A",
                    "student_number": "",
                    "essay_title": "",
                    "essay": "essay",
                    "extraneous": "",
                }
            ]
        )
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.extract_metadata_parallel(
            app_cfg=app_cfg,
            text_tasks=["essay text"],
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)

    def test_correct_grammar_parallel_uses_no_think_and_max_concurrency(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="fixed sentence.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.correct_grammar_parallel(
            app_cfg=app_cfg,
            text_tasks=["bad sentence."],
            max_concurrency=3,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 3)


if __name__ == "__main__":
    unittest.main()
