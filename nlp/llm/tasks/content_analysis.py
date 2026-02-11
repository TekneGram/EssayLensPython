from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "You are a reader who compares two paragraphs.\n"
    "Determine whether the second paragraph is engaging for the reader.\n"
    "Explain your decision by checking examples, clarity, and reader flow.\n"
    "If the second paragraph is weaker, suggest improvements.\n"
    "Output only plain text.\n"
    "Keep your analysis concise.\n"
    "This is the first paragraph:\n"
    "AI is changing the world. I think AI will make us more useful in the future. "
    "Also, AI will help us to learn more things more quickly. AI is very "
    "interesting to use. But some people think AI is dangerous. I don't think so. "
    "Thank you.\n"
    "This is the second paragraph:\n"
)


def build_content_analysis(text_tasks: Sequence[str]) -> list[ChatRequest]:
    return [
        ChatRequest(
            system=SYSTEM_PROMPT,
            user=text,
            temperature=0.0,
        )
        for text in text_tasks
    ]


async def run_parallel_content_analysis(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
    text_tasks: Sequence[str],
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    requests_ = build_content_analysis(text_tasks)
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
        "outputs": outputs,
    }
