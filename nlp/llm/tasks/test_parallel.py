from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from nlp.llm.llm_client import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "Here is some writing: I went to Tokyo once. It was lovely. "
    "I really want to go there again. I wish my friends had come with me. "
    "I was lonely. I don't like being lonely. So I wanted to die. "
    "But I didn't. I was relieved. Thank you for reading. I had a lovely time."
)

TASKS = [
    "As a kind teacher, give feedback on how interesting the writing above is. Be very brief.",
    "As a critical reviewer, say what is wrong with the writing. Be super brief.",
    "As someone curious about language choice, ask questions about the writing. Be crazy brief.",
]


async def run_parallel_test(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
) -> dict[str, Any]:
    requests_ = [ChatRequest(system=SYSTEM_PROMPT, user=task) for task in TASKS]

    started = time.perf_counter()
    outputs = await llm_service.chat_many(
        requests_,
        max_concurrency=app_cfg.llm_server.llama_n_parallel,
    )
    for i, res in enumerate(outputs):
        if isinstance(res, Exception):
            print(f"Task {i} failed with: {res}")
    elapsed_s = time.perf_counter() - started

    # Separate successes from failure
    successful_texts = [res for res in outputs if isinstance(res, str)]
    failed_tasks = [res for res in outputs if isinstance(res, Exception)]

    total_chars = sum(len(text or "") for text in outputs)
    chars_per_second = total_chars / elapsed_s if elapsed_s > 0 else 0.0

    return {
        "mode": "parallel",
        "task_count": len(TASKS),
        "success_count": len(successful_texts),
        "failure_count": len(failed_tasks),
        "max_concurrency": app_cfg.llm_server.llama_n_parallel,
        "elapsed_s": elapsed_s,
        "total_output_chars": total_chars,
        "chars_per_second": chars_per_second,
        "system_prompt_shared": True,
        "tasks": TASKS,
        "outputs": outputs,
    }
