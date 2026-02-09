from __future__ import annotations

from dataclasses import dataclass
import sys
from typing import Any, AsyncIterator, Iterator, Literal, Sequence

from nlp.llm.llm_client import (
    ChatRequest,
    ChatResponse,
    ChatStreamAccumulator,
    ChatStreamEvent,
    JsonSchemaChatRequest,
    OpenAICompatChatClient,
)
from nlp.llm.tasks.test_parallel import run_parallel_test


@dataclass
class LlmService:
    client: OpenAICompatChatClient
    max_parallel: int | None = None

    def with_mode(self, mode: Literal["default", "think", "no_think"]) -> "LlmService":
        return LlmService(
            client=self.client.with_reasoning_mode(mode),
            max_parallel=self.max_parallel,
        )

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
    ) -> ChatResponse:
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
    ) -> list[ChatResponse | Exception]:
        return await self.client.chat_many(
            requests_,
            max_concurrency=max_concurrency or self.max_parallel,
        )

    def json_schema_chat(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        return self.client.json_schema_chat(
            system=system,
            user=user,
            schema=schema,
            **kwargs,
        )

    async def json_schema_chat_async(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        **kwargs: Any,
    ) -> Any:
        return await self.client.json_schema_chat_async(
            system=system,
            user=user,
            schema=schema,
            **kwargs,
        )

    async def json_schema_chat_many(
        self,
        requests_: Sequence[JsonSchemaChatRequest],
        *,
        max_concurrency: int | None = None,
        return_exceptions: bool = True,
    ) -> list[Any | Exception]:
        return await self.client.json_schema_chat_many(
            requests_,
            max_concurrency=max_concurrency or self.max_parallel,
            return_exceptions=return_exceptions,
        )

    def chat_stream(
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
    ) -> Iterator[ChatStreamEvent]:
        return self.client.chat_stream(
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

    async def chat_stream_async(
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
    ) -> AsyncIterator[ChatStreamEvent]:
        async for event in self.client.chat_stream_async(
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
        ):
            yield event

    def chat_stream_to_terminal(
        self,
        system: str,
        user: str,
        *,
        show_reasoning_prefix: str = "\n[reasoning] ",
        **kwargs: Any,
    ) -> ChatResponse:
        state = ChatStreamAccumulator.create()
        showed_reasoning_prefix = False

        for event in self.chat_stream(system=system, user=user, **kwargs):
            state.add(event)
            if event.channel == "content" and event.text:
                sys.stdout.write(event.text)
                sys.stdout.flush()
            elif event.channel == "reasoning" and event.text:
                if not showed_reasoning_prefix:
                    sys.stdout.write(show_reasoning_prefix)
                    showed_reasoning_prefix = True
                sys.stdout.write(event.text)
                sys.stdout.flush()

        sys.stdout.write("\n")
        sys.stdout.flush()
        return state.to_response()

    async def run_parallel_kv_cache_test(self, app_cfg: Any) -> dict[str, Any]:
        return await run_parallel_test(self, app_cfg)
