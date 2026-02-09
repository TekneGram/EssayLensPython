from __future__ import annotations
from dataclasses import dataclass

SYSTEM_PROMPT = (
    "Here is some writing: I went to Tokyo once. It was lovely. "
    "I really want to go there again. I wish my friends had come with me. "
    "I was lonely. I don't like being lonely. So I wanted to die. "
    "But I didn't. I was relieved. Thank you for reading. I had a lovely time."
)

@dataclass(frozen=True)
class TestTaskAgain:
    name: str
    user_prompt: str

def build_feedback_tasks() -> list[TestTaskAgain]:
    return[
        TestTaskAgain(
            name="Wildly optimistic person",
            user_prompt="Give feedback as a wildly optimistic person."
        ),
        TestTaskAgain(
            name="Unbelievably pesimistic person",
            user_prompt="Give feedback as an unbelievably pessimistic person."
        ),
        TestTaskAgain(
            name="Slightly risque person",
            user_prompt="Give feedback as a priest."
        ),
    ]