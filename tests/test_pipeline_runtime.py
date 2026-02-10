from __future__ import annotations

import unittest
from dataclasses import dataclass
from types import SimpleNamespace
from unittest.mock import patch

from app.pipeline import TestPipeline
from nlp.llm.llm_types import ChatResponse


@dataclass(frozen=True)
class _Task:
    name: str
    user_prompt: str


class _FakeLlm:
    def __init__(self, outputs):
        self._outputs = outputs
        self.calls: list[dict] = []

    def with_mode(self, mode: str):
        self.calls.append({"mode": mode})
        return self

    async def chat_many(self, requests_, max_concurrency=None):
        self.calls.append(
            {
                "requests": requests_,
                "max_concurrency": max_concurrency,
            }
        )
        return self._outputs


class PipelineRuntimeTests(unittest.TestCase):
    def test_run_test_again_builds_requests_and_returns_task_names(self) -> None:
        outputs = [
            ChatResponse(
                content="ok",
                reasoning_content=None,
                finish_reason="stop",
                model="demo",
                usage=None,
            )
        ]
        llm = _FakeLlm(outputs)
        pipeline = TestPipeline(llm=llm)
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=4))
        tasks = [_Task(name="Task A", user_prompt="Prompt A")]

        with patch("app.pipeline.build_feedback_tasks", return_value=tasks):
            result = pipeline.run_test_again(app_cfg)

        self.assertEqual(result["tasks"], ["Task A"])
        self.assertEqual(result["outputs"], outputs)
        self.assertEqual(llm.calls[0]["mode"], "no_think")
        self.assertEqual(llm.calls[1]["max_concurrency"], 4)
        self.assertEqual(llm.calls[1]["requests"][0].user, "Prompt A")

    def test_run_test_again_keeps_exception_outputs(self) -> None:
        err = RuntimeError("boom")
        llm = _FakeLlm([err])
        pipeline = TestPipeline(llm=llm)
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=2))
        tasks = [_Task(name="Task B", user_prompt="Prompt B")]

        with patch("app.pipeline.build_feedback_tasks", return_value=tasks):
            result = pipeline.run_test_again(app_cfg)

        self.assertIs(result["outputs"][0], err)


if __name__ == "__main__":
    unittest.main()
