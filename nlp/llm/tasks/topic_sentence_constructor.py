from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "You are a writer of English.\n"
    "You write plain English.\n"
    "Read a paragraph that is missing the topic sentence\n"
    "Then write a topic sentence that introduces the topic of the paragraph.\n"
    "Write only one concise topic sentence that does not contain too many specific details from the paragraph.\n"
    "No comments. No analysis. No trailing text. No JSON.\n"
)


def build_topic_sentence_construction(text_tasks: Sequence[str]) -> list[ChatRequest]:
    return [
        ChatRequest(
            system=SYSTEM_PROMPT,
            user=text,
            temperature=0.0,
        )
        for text in text_tasks
    ]


async def run_parallel_topic_sentence_request(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
    text_tasks: Sequence[str],
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    requests_ = build_topic_sentence_construction(text_tasks)
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
