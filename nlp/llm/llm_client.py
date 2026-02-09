from __future__ import annotations
from dataclasses import dataclass, asdict
import asyncio
from typing import Any, Sequence
import httpx

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
            system: str,
            user: str,
            **kwargs
    ) -> JSONDict:
        # Start with the core required fields
        payload: JSONDict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user}
            ],
        }

        # List the keys to process
        fields = [
            "max_tokens", "temperature", "top_p", "top_k",
            "repeat_penalty", "seed", "stop", "response_format"
        ]

        for field in fields:
            val = kwargs.get(field)
            if val is None:
                val = getattr(self.request_cfg, field, None)
            
            if val is not None:
                payload[field] = val
        return payload

    def chat(self, system: str, user: str, **kwargs) -> str:
        payload = self._build_payload(system=system, user=user, **kwargs)

        try:
            response = requests.post(self.server_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM Server connection failed: {e}")
        
        data = response.json()
        return data["choices"][0]["message"]["content"].strip()
    
    async def chat_async(self, system: str, user: str, **kwargs) -> str:
        payload = self._build_payload(system=system, user=user, **kwargs)
        print("Payload:", payload)

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(
                    self.server_url,
                    json=payload
                )
                # Raises httpx.HTTPStatusError if response is 4xx or 5xx
                response.raise_for_status()

                data = response.json()
                return data["choices"][0]["message"]["content"].strip()
            except httpx.HTTPError as exc:
                raise RuntimeError(f"LLM Server Error: {exc}") from exc

    async def chat_many(
            self,
            requests_: Sequence[ChatRequest],
            *,
            max_concurrency: int | None = None,
            return_exceptions: bool = True
    ) -> list[str | Exception]:
        if not requests_:
            return []
        
        # Local LLM servers usually handle 1 - 4 parallel requests well
        concurrency = max_concurrency or 2
        semaphor = asyncio.Semaphore(concurrency)

        async def _one(req: ChatRequest) -> str:
            async with semaphor:
                try:
                    # Prepare the data
                    req_data = asdict(req)
                    system = req_data.pop("system")
                    user = req_data.pop("user")

                    # Execute call
                    return await self.chat_async(
                        system=system,
                        user=user,
                        **req_data
                    )
                except Exception as e:
                    if return_exceptions:
                        return e
                    raise e
        return await asyncio.gather(
            *(_one(req) for req in requests_),
            return_exceptions=return_exceptions
        )
