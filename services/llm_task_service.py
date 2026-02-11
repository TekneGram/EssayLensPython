from __future__ import annotations

import asyncio
from dataclasses import dataclass
from typing import TYPE_CHECKING, Any, Sequence
from utils.terminal_ui import type_print, Color

from nlp.llm.tasks.extract_metadata import run_parallel_metadata_extraction
from nlp.llm.tasks.grammar_error_correction import run_parallel_grammar_correction
from nlp.llm.tasks.conclusion_sentence_analyzer import run_parallel_conclusion_sentence_analysis
from nlp.llm.tasks.hedging_analysis import run_parallel_hedging_analysis
from nlp.llm.tasks.cause_effect_analysis import run_parallel_cause_effect_analysis
from nlp.llm.tasks.compare_contrast_analysis import run_parallel_compare_contrast_analysis
from nlp.llm.tasks.topic_sentence_analyzer import run_parallel_topic_sentence_analysis
from nlp.llm.tasks.topic_sentence_constructor import run_parallel_topic_sentence_request

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

    def construct_topic_sentence_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_topic_sentence_request(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )

    def analyze_topic_sentence_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_topic_sentence_analysis(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )

    def analyze_conclusion_sentence_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_conclusion_sentence_analysis(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )

    def analyze_hedging_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_hedging_analysis(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )

    def analyze_cause_effect_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_cause_effect_analysis(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )

    def analyze_compare_contrast_parallel(
        self,
        *,
        app_cfg: "AppConfigShape",
        text_tasks: Sequence[str],
        max_concurrency: int | None = None,
    ) -> dict[str, Any]:
        llm_no_think = self.llm_service.with_mode("no_think")
        return asyncio.run(
            run_parallel_compare_contrast_analysis(
                llm_service=llm_no_think,
                app_cfg=app_cfg,
                text_tasks=text_tasks,
                max_concurrency=max_concurrency,
            )
        )
