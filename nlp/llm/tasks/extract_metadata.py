from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import JsonSchemaChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


SYSTEM_PROMPT = (
    "Extract the student_name, student_number, essay_title, and essay from the text.\n"
    "Return ONLY JSON that follows the requested schema.\n"
    "Do not rewrite or correct content.\n"
    "If a field is missing, return an empty string.\n"
    "The extraneous field should include references, salutations, "
    "word-count notes, and content not part of the essay body."
)

METADATA_RESPONSE_SCHEMA: dict[str, Any] = {
    "type": "json_schema",
    "json_schema": {
        "name": "essay_metadata",
        "schema": {
            "type": "object",
            "properties": {
                "student_name": {"type": "string"},
                "student_number": {"type": "string"},
                "essay_title": {"type": "string"},
                "essay": {"type": "string"},
                "extraneous": {"type": "string"},
            },
            "required": [
                "student_name",
                "student_number",
                "essay_title",
                "essay",
                "extraneous",
            ],
            "additionalProperties": False,
        },
    },
}


def build_metadata_requests(text_tasks: Sequence[str]) -> list[JsonSchemaChatRequest]:
    return [
        JsonSchemaChatRequest(
            system=SYSTEM_PROMPT,
            user=text,
            schema=METADATA_RESPONSE_SCHEMA,
            temperature=0.0,
        )
        for text in text_tasks
    ]


async def run_parallel_metadata_extraction(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
    text_tasks: Sequence[str],
) -> dict[str, Any]:
    requests_ = build_metadata_requests(text_tasks)

    started = time.perf_counter()
    outputs = await llm_service.json_schema_chat_many(
        requests_,
        max_concurrency=app_cfg.llm_server.llama_n_parallel,
    )
    elapsed_s = time.perf_counter() - started

    success_count = len([res for res in outputs if not isinstance(res, Exception)])
    failure_count = len([res for res in outputs if isinstance(res, Exception)])

    return {
        "mode": "parallel_json_schema",
        "task_count": len(requests_),
        "success_count": success_count,
        "failure_count": failure_count,
        "max_concurrency": app_cfg.llm_server.llama_n_parallel,
        "elapsed_s": elapsed_s,
        "outputs": outputs,  # list[dict[str, Any] | Exception]
    }
