from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from nlp.llm.llm_client import ChatResponse
from nlp.llm.tasks.test_parallel import SYSTEM_PROMPT, TASKS

if TYPE_CHECKING:
    from services.llm_service import LlmService


def run_sequential_stream_demo(llm_service: "LlmService") -> dict[str, Any]:
    started = time.perf_counter()
    outputs: list[ChatResponse | Exception] = []

    for idx, task in enumerate(TASKS, start=1):
        print(f"\n[Sequential Task {idx}] {task}")
        try:
            response = llm_service.chat_stream_to_terminal(
                system=SYSTEM_PROMPT,
                user=task,
            )
            outputs.append(response)
        except Exception as e:
            outputs.append(e)
            print(f"[Sequential Task {idx}] ERROR: {e}")

    elapsed_s = time.perf_counter() - started
    successful_responses = [res for res in outputs if isinstance(res, ChatResponse)]
    failed_tasks = [res for res in outputs if isinstance(res, Exception)]
    reasoning_count = sum(1 for res in successful_responses if res.reasoning_content)

    return {
        "mode": "sequential_stream",
        "task_count": len(TASKS),
        "success_count": len(successful_responses),
        "failure_count": len(failed_tasks),
        "elapsed_s": elapsed_s,
        "system_prompt_shared": True,
        "tasks": TASKS,
        "outputs": outputs,
        "reasoning_count": reasoning_count,
    }
