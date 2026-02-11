from __future__ import annotations
import time
from typing import TYPE_CHECKING, Any

from nlp.llm.llm_client import ChatRequest, ChatResponse

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService

system = (
        "Extract the student_name, student_number, essay_title, essay and extraneous.\n"
        "Also extract anything that looks like word count data and extraneous part of writing like references or messages to the teacher.\n"
        "Do not edit any content you receive.\n"
        "Return ONLY valid JSON with double-quoted keys and string values.\n"
        "No extra text, no markdown, no trailing commas.\n"
        "Example:\n"
        "{"
        "\"student_name\":\"Daniel Parsons\","
        "\"student_number\":\"St29879.dfij9\","
        "\"essay_title\":\"Having Part Time Jobs\","
        "\"essay\":\"I disagree with...\","
        "If there is no student_name leave the property blank.\n"
        "If there is no student_number leave the property blank.\n"
        "If there is no essay_title leave the property blank.\n"
        "Example:\n"
        "{"
        "\"student_name\":\"\","
        "\"student_number\":\"\","
        "\"essay_title\":\"\","
        "\"essay\":\"I disagree with...\""
        "}\n"
    )

async def run_parallel_test(
        llm_service: "LlmService",
        app_cfg: "AppConfigShape"
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
    successful_responses = [res for res in outputs if isinstance(res, ChatResponse)]
    failed_tasks = [res for res in outputs if isinstance(res, Exception)]

    total_chars = sum(len(res.content or "") for res in successful_responses)
    chars_per_second = total_chars / elapsed_s if elapsed_s > 0 else 0.0

    return {
        "mode": "parallel",
        "task_count": len(TASKS),
        "success_count": len(successful_responses),
        "failure_count": len(failed_tasks),
        "max_concurrency": app_cfg.llm_server.llama_n_parallel,
        "elapsed_s": elapsed_s,
        "total_output_chars": total_chars,
        "chars_per_second": chars_per_second,
        "system_prompt_shared": True,
        "tasks": TASKS,
        "outputs": outputs,
    }