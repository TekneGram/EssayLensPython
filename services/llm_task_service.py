from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence
from utils.terminal_ui import type_print, Color

from nlp.llm.tasks.extract_metadata import run_parallel_metadata_extraction
from nlp.llm.tasks.grammar_error_correction import run_parallel_grammar_correction

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


@dataclass
class LlmTaskService:
    """
    Application-facing LLM task orchestration.

    This service groups domain tasks while delegating transport concerns to
    LlmService and prompt/schema composition to nlp.llm.tasks.* modules.
    """

    llm_service: "LlmService"

    def extract_metadata_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
    ) -> dict[str, Any]:
        type_print("Setting up LLM in no_think mode: may need to change for future instruct versions.", color=Color.YELLOW)
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_metadata_extraction(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
            )
        )

    def correct_grammar_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_grammar_correction(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )
