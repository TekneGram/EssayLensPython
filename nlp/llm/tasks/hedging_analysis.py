from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "Hedging language refers to language that softens and strengthens claims.\n"
    "It involves words like probably, could be, maybe, perhaps and it could be said that.\n"
    "It also involves words like definitely, certainly, there is no doubt that, should and must\n"
    "The writer should use some in their writing because it helps to give nuance to their writing.\n"
    "Comment on the quality of their hedging. Be concise\n"
    "If there is no hedging language, encourage them to use more and give *one* example sentence.\n"
)


def build_hedging_anaylsis(text_tasks: Sequence[str]) -> list[ChatRequest]:
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
    requests_ = build_hedging_anaylsis(text_tasks)
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
