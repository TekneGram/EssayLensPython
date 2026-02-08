from __future__ import annotations
from dataclasses import dataclass
import asyncio
from typing import Any, Sequence

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from config.llm_request_config import LlmRequestConfig

try:
    import requests  # type: ignore
except ImportError:
    class _RequestsFallback:
        @staticmethod
        def post(*args, **kwargs):
            raise RuntimeError("requests is not installed.")

    requests = _RequestsFallback()


JSONDict = dict[str, Any]


@dataclass(frozen=True, slots=True)
class ChatRequest:
    system: str
    user: str
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    repeat_penalty: float | None = None
    seed: int | None = None
    stop: list[str] | None = None
    response_format: dict[str, Any] | None = None


@dataclass
class OpenAICompatChatClient:
    server_url: str
    model_name: str
    request_cfg: LlmRequestConfig
    timeout_s: float = 120.0

    def _build_payload(
        self,
        *,
        system: str,
        user: str,
        max_tokens: int | None = None,
        temperature: float | None = None,
        top_p: float | None = None,
        top_k: int | None = None,
        repeat_penalty: float | None = None,
        seed: int | None = None,
        stop: list[str] | None = None,
        response_format: dict[str, Any] | None = None,
    ) -> JSONDict:
        payload: JSONDict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "max_tokens": self.request_cfg.default_max_tokens if max_tokens is None else max_tokens,
            "temperature": self.request_cfg.default_temperature if temperature is None else temperature,
            # Explicitly set cache_prompt per request; server must also be started with --cache-prompt.
            "cache_prompt": True,
        }

        effective_top_p = self.request_cfg.default_top_p if top_p is None else top_p
        effective_top_k = self.request_cfg.default_top_k if top_k is None else top_k
        effective_repeat_penalty = (
            self.request_cfg.default_repeat_penalty if repeat_penalty is None else repeat_penalty
        )
        effective_seed = self.request_cfg.default_seed if seed is None else seed
        effective_stop = self.request_cfg.default_stop if stop is None else stop
        effective_response_format = (
            self.request_cfg.default_response_format if response_format is None else response_format
        )

        if effective_top_p is not None:
            payload["top_p"] = effective_top_p
        if effective_top_k is not None:
            payload["top_k"] = effective_top_k
        if effective_repeat_penalty is not None:
            payload["repeat_penalty"] = effective_repeat_penalty
        if effective_seed is not None:
            payload["seed"] = effective_seed
        if effective_stop is not None:
            payload["stop"] = effective_stop
        if effective_response_format is not None:
            payload["response_format"] = effective_response_format
        return payload

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
        payload = self._build_payload(
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
        response = requests.post(self.server_url, json=payload, timeout=self.timeout_s)
        if response.status_code != 200:
            raise RuntimeError(f"llm server HTTP {response.status_code}: {response.text[:1000]}")
        data = response.json()
        return ((data.get("choices") or [{}])[0].get("message", {}).get("content") or "").strip()

    async def chat_async(
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
        return await asyncio.to_thread(
            self.chat,
            system,
            user,
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
        if not requests_:
            return []
        concurrency = max(1, max_concurrency or len(requests_))
        semaphore = asyncio.Semaphore(concurrency)

        async def _one(req: ChatRequest) -> str:
            async with semaphore:
                return await self.chat_async(
                    system=req.system,
                    user=req.user,
                    max_tokens=req.max_tokens,
                    temperature=req.temperature,
                    top_p=req.top_p,
                    top_k=req.top_k,
                    repeat_penalty=req.repeat_penalty,
                    seed=req.seed,
                    stop=req.stop,
                    response_format=req.response_format,
                )

        return await asyncio.gather(*(_one(req) for req in requests_))
