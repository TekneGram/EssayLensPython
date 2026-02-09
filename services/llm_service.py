from __future__ import annotations

from dataclasses import dataclass
from typing import Any, Sequence

from nlp.llm.llm_client import ChatRequest, OpenAICompatChatClient
from nlp.llm.tasks.test_parallel import run_parallel_test


@dataclass
class LlmService:
    client: OpenAICompatChatClient
    max_parallel: int | None = None

    def chat(
        self,
        system: str,
        user: str,
        *,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repeat_penalty: float | None = None,
        seed: int | None = None,
        stop: list[str] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> str:
        return self.client.chat(
            system=system,
            user=user,
            max_tokens=max_tokens,
            temperature=temperature,
            top_p=top_p,
            top_k=top_k,
            repeat_penalty=repeat_penalty,
            seed=seed,
            stop=stop,
            response_format=response_format,
        )

    async def chat_many(
        self,
        requests_: Sequence[ChatRequest],
        *,
        max_concurrency: int | None = None,
    ) -> list[str]:
        return await self.client.chat_many(
            requests_,
            max_concurrency=max_concurrency or self.max_parallel,
        )

    async def run_parallel_kv_cache_test(self, app_cfg: Any) -> dict[str, Any]:
        return await run_parallel_test(self, app_cfg)
