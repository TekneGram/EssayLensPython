from __future__ import annotations

# Standard library imports
from dataclasses import dataclass
from pathlib import Path
import asyncio
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from services.llm_service import LlmService

from nlp.llm.llm_types import ChatRequest, ChatResponse
from nlp.llm.tasks.test_parallel_2 import build_feedback_tasks, SYSTEM_PROMPT

# Interfaces and protocols
from interfaces.config.app_config import AppConfigShape


@dataclass
class TestPipeline():
    """
    End to end pipeline to run a quick sanity check test.
    Responsibilities
    - Apply LLM chat
    """

    # Injected dependencies
    llm: "LlmService"

    def run_test_again(self, app_cfg: "AppConfigShape") -> dict[str, Any]:
        llm_no_think = self.llm.with_mode("no_think")
        tasks = build_feedback_tasks()
        requests_ = [
            ChatRequest(
                system=SYSTEM_PROMPT,
                user=t.user_prompt
            )
            for t in tasks
        ]
        outputs = asyncio.run(
            llm_no_think.chat_many(requests_, max_concurrency = app_cfg.llm_server.llama_n_parallel)
        )

        return {
            "tasks": [t.name for t in tasks],
            "outputs": outputs, # list[ChatResponse | Exception]
        }
        

    def run_test(self, app_cfg:AppConfigShape):
        llm_no_think = self.llm.with_mode("no_think")
        return asyncio.run(llm_no_think.run_parallel_kv_cache_test(app_cfg))
