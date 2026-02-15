from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any, Sequence

from nlp.llm.llm_types import ChatRequest

if TYPE_CHECKING:
    from interfaces.config.app_config import AppConfigShape
    from services.llm_service import LlmService


# --- RUBRIC DESCRIPTORS ONLY ----
SYSTEM_PROMPT_NICE_WITH_QWEN_8B = (
    "Write a detailed evaluation of the learner's paragraph.\n"
    "Refer to the following rubric. If a student did something well, say explicitly what they did. If a student needs to improve, say explicitly what is weak about the writing.\n"
    "Organization: Clear topic sentence, well developed points in the body support the topic sentence, clear conclusion sentence.\n"
    "Coherence: Ideas flow naturally and the organization is logical and easy for the reader.\n"
    "Language: Language is accurate, with natural expressions that are appropriate for the topic.\n"
    "Content: Content is original and engaging for the reader; ideas feel like the students' own ideas.\n"
)

# --- ONE CATEGORY RUBRIC WITH SCORING / DETAILED ---
SYSTEM_PROMPT_NICE_WITH_QWEN_8B = (
    "Write a detailed evaluation of the learner's paragraph. Use examples from the writing to support your evaluation.\n"
    "Refer to the following rubric.\n"
    "Coherence: 5 points: The student uses advanced techniques to connect ideas in the paragraph.\n"
    "Coherence: 4 points: The student uses general techniques to connect ideas in the paragraph.\n"
    "Coherence: 3 points: The student uses some basic techniques to connect ideas but there could be improvements.\n"
    "Coherence: 2 points: The student rarely demonstrates coherence. Improvements are necessary.\n"
    "Coherence: 1 point: There is little coherence between the sentences. The student needs to learn the basics of coherence.\n"
)

# --- ONE CATEGORY RUBRIC WITH SCORING / BRIEF ---
SYSTEM_PROMPT_REASONABLE_WITH_QWEN_8B = (
    "Write a brief evaluation of the learner's paragraph. Use one or two examples from the writing to support your evaluation.\n"
    "Refer to the following rubric.\n"
    "Coherence: 5 points: The student uses advanced techniques to connect ideas in the paragraph.\n"
    "Coherence: 4 points: The student uses general techniques to connect ideas in the paragraph.\n"
    "Coherence: 3 points: The student uses some basic techniques to connect ideas but there could be improvements.\n"
    "Coherence: 2 points: The student rarely demonstrates coherence. Improvements are necessary.\n"
    "Coherence: 1 point: There is little coherence between the sentences. The student needs to learn the basics of coherence.\n"
)

# --- ONE CATEGORY RUBRIC WITH SCORING / BRIEF ---
SYSTEM_PROMPT_NICE_WITH_QWEN_8B = (
    "Write a brief evaluation of the learner's paragraph. Use one or two examples from the writing to support your evaluation.\n"
    "Refer to the following rubric.\n"
    "Content: 5 points: The ideas are original and thoroughly explored and evaluated\n"
    "Content: 4 points: The ideas are original and explored in some depth.\n"
    "Content: 3 points: The ideas are interesting for the reader but there is not much exploration or evaluation.\n"
    "Content: 2 points: The ideas are stated, but they lack insight and there is no exploration or evaluation.\n"
    "Content: 1 point: There is nothing original in the student's writing. It is quite boring to read and shows no insight, no depth and no evaluation.\n"
)

# --- CAN-DO STATEMENTS / BRIEF ---
SYSTEM_PROMPT_REASONABLE_WITH_QWEN_8B = (
    "Write a brief evaluation of the learners achievement on the criteria below.\n"
    "For each criteria, decide whether the learner 'can do well', 'still learning', 'cannot do'"
    "For each decision, explain with an example from the text."
    "Topic sentence: The learner can write an effective topic sentence that introduces the issues discussed in the writing.\n"
    "Supporting details: The learner can provide explanations and reasons that develop and support the topic sentence.\n"
    "Analytical insight: The learner can explore and evaluate each point in detail.\n"
    "Language: The learner uses compare / contrast language like 'However', 'In contrast', 'more than ~ ', '~er', '~est' and others to develop the discussion accurately and coherently.\n"
)

SYSTEM_PROMPT = (
    "Say hello for now."
)


def build_prompt_tester(text_tasks: Sequence[str]) -> list[ChatRequest]:
    return [
        ChatRequest(
            system=SYSTEM_PROMPT,
            user=text,
            temperature=0.0,
        )
        for text in text_tasks
    ]


async def run_parallel_prompt_tester(
    llm_service: "LlmService",
    app_cfg: "AppConfigShape",
    text_tasks: Sequence[str],
    max_concurrency: int | None = None,
) -> dict[str, Any]:
    requests_ = build_prompt_tester(text_tasks)
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
        "mode": "parallel_chat",
        "task_count": len(requests_),
        "success_count": success_count,
        "failure_count": failure_count,
        "max_concurrency": concurrency,
        "elapsed_s": elapsed_s,
        "outputs": outputs,  # list[dict[str, Any] | Exception]
    }
