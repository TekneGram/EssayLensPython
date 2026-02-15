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

    def test_construct_topic_sentence_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Good topic sentence.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.construct_topic_sentence_parallel(
            app_cfg=app_cfg,
            text_tasks=["Supporting details without the original topic sentence."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_analyze_topic_sentence_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="The learner topic sentence is too general.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.analyze_topic_sentence_parallel(
            app_cfg=app_cfg,
            text_tasks=['{"learner_text":"x","learner_topic_sentence":"y","good_topic_sentence":"z"}'],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_analyze_conclusion_sentence_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Conclusion feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.analyze_conclusion_sentence_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content to evaluate conclusion sentence quality."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_analyze_hedging_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Hedging feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.analyze_hedging_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for hedging analysis."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_prompt_tester_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Cause/effect feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.prompt_tester_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for cause/effect analysis."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_analyze_cause_effect_parallel_delegates_to_prompt_tester(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))
        llm_service = Mock()
        task_service = LlmTaskService(llm_service=llm_service)
        expected = {
            "task_count": 1,
            "success_count": 1,
            "failure_count": 0,
            "max_concurrency": 2,
            "outputs": [Mock(content="Cause/effect feedback.")],
        }
        task_service.prompt_tester_parallel = Mock(return_value=expected)  # type: ignore[method-assign]

        result = task_service.analyze_cause_effect_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for cause/effect analysis."],
            max_concurrency=2,
        )

        task_service.prompt_tester_parallel.assert_called_once_with(  # type: ignore[union-attr]
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for cause/effect analysis."],
            max_concurrency=2,
        )
        self.assertEqual(result, expected)

    def test_analyze_compare_contrast_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Compare/contrast feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.analyze_compare_contrast_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for compare/contrast analysis."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_analyze_content_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Content analysis feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.analyze_content_parallel(
            app_cfg=app_cfg,
            text_tasks=["Paragraph content for content analysis."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_filter_content_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Filtered content feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.filter_content_parallel(
            app_cfg=app_cfg,
            text_tasks=["Comparison feedback to filter."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)

    def test_summarize_personalize_parallel_uses_no_think(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))

        llm_no_think = Mock()
        llm_no_think.chat_many = AsyncMock(return_value=[Mock(content="Final summary feedback.")])
        llm_service = Mock()
        llm_service.with_mode.return_value = llm_no_think

        task_service = LlmTaskService(llm_service=llm_service)
        result = task_service.summarize_personalize_parallel(
            app_cfg=app_cfg,
            text_tasks=["Long feedback text to summarize and personalize."],
            max_concurrency=2,
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)
        self.assertEqual(result["max_concurrency"], 2)


    def test_extract_essay_parallel_uses_no_think_and_returns_result(self) -> None:
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
        result = task_service.extract_essay_parallel(
            app_cfg=app_cfg,
            text_tasks=["essay text"],
        )

        llm_service.with_mode.assert_called_once_with("no_think")
        self.assertEqual(result["task_count"], 1)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 0)


if __name__ == "__main__":
    unittest.main()
