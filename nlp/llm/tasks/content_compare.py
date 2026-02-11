from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "You are a reader who is interested in reading student work.\n"
    "You must compare two paragraphs.\n"
    "Which paragraph is more engaging for the reader?\n"
    "Explain your choice by comparing:\n"
    "-Use of examples\n"
    "-Clarity of main ideas.\n"
    "-Reader interest and flow.\n"
    "Output only plain text."
    "This is the first paragraph:\n"
    "AI is changing the world. I think AI will make us more useful in the future. Also, AI will help us to learn more things more quickly. AI is very interesting to use. But some people think AI is dangerous. I don't think so. Thank you.\n"
    "This is the second paragraph:\n"
)


def compare_paragraphs(text_tasks: Sequence[str]) -> list[ChatRequest]:
    return [
        ChatRequest(
            system=SYSTEM_PROMPT,
            user=text,
            temperature=0.0,
        )
        for text in text_tasks
    ]


async def run_parallel_hedging_analysis(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
    text_tasks: Sequence[str],
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    requests_ = compare_paragraphs(text_tasks)
    concurrency = max_concurrency or app_cfg.llm_server.llama_n_parallel

    started = time.perf_counter()
    outputs = await llm_service.chat_many(
        requests_,
        max_concurrency=concurrency,
    )
    elapsed_s = time.perf_counter() - started

    success_count = len([res for res in outputs if not isinstance(res, Exception)])
    failure_count = len([res for res in outputs if isinstance(res, Exception)])

    return {
        "mode": "parallel_json_schema",
        "task_count": len(requests_),
        "success_count": success_count,
        "failure_count": failure_count,
        "max_concurrency": concurrency,
        "elapsed_s": elapsed_s,
        "outputs": outputs,  # list[dict[str, Any] | Exception]
    }
