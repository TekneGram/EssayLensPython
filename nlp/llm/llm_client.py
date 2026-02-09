from __future__ import annotations
from dataclasses import dataclass, asdict
import asyncio
import json
from typing import Any, AsyncIterator, Iterable, Iterator, Literal, Sequence
import httpx
import requests

from typing import TYPE_CHECKING
if TYPE_CHECKING:
    from config.llm_request_config import LlmRequestConfig

JSONDict = dict[str, Any]


# ----- TYPES -----
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


@dataclass(frozen=True, slots=True)
class JsonSchemaChatRequest:
    system: str
    user: str
    schema: dict[str, Any]
    max_tokens: int | None = None
    temperature: float | None = None
    top_p: float | None = None
    top_k: int | None = None
    repeat_penalty: float | None = None
    seed: int | None = None
    stop: list[str] | None = None


@dataclass(frozen=True, slots=True)
class ChatResponse:
    content: str
    reasoning_content: str | None
    finish_reason: str | None
    model: str | None
    usage: dict[str, Any] | None


@dataclass(frozen=True, slots=True)
class ChatStreamEvent:
    channel: Literal["content", "reasoning", "meta"]
    text: str
    finish_reason: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None
    done: bool = False

# ----- Accumulator class for streaming -----
@dataclass
class ChatStreamAccumulator:
    content_parts: list[str]
    reasoning_parts: list[str]
    finish_reason: str | None = None
    model: str | None = None
    usage: dict[str, Any] | None = None

    @staticmethod
    def create() -> "ChatStreamAccumulator":
        return ChatStreamAccumulator(content_parts=[], reasoning_parts=[])

    def add(self, event: ChatStreamEvent) -> None:
        if event.channel == "content" and event.text:
            self.content_parts.append(event.text)
        elif event.channel == "reasoning" and event.text:
            self.reasoning_parts.append(event.text)

        if event.finish_reason is not None:
            self.finish_reason = event.finish_reason
        if event.model is not None:
            self.model = event.model
        if event.usage is not None:
            self.usage = event.usage

    def to_response(self) -> ChatResponse:
        content = "".join(self.content_parts).strip()
        reasoning = "".join(self.reasoning_parts).strip()
        return ChatResponse(
            content=content,
            reasoning_content=reasoning if reasoning else None,
            finish_reason=self.finish_reason,
            model=self.model,
            usage=self.usage,
        )

# ----- Main Client Implementation -----
@dataclass
class OpenAICompatChatClient:
    server_url: str
    model_name: str
    model_family: str
    request_cfg: LlmRequestConfig
    timeout_s: float = 120.0
    reasoning_mode: Literal["default", "think", "no_think"] = "default"

    def with_reasoning_mode(
        self,
        mode: Literal["default", "think", "no_think"],
    ) -> "OpenAICompatChatClient":
        allowed_modes = {"default", "think", "no_think"}
        if mode not in allowed_modes:
            raise ValueError(f"Unsupported reasoning mode: {mode}")
        return OpenAICompatChatClient(
            server_url=self.server_url,
            model_name=self.model_name,
            model_family=self.model_family,
            request_cfg=self.request_cfg,
            timeout_s=self.timeout_s,
            reasoning_mode=mode,
        )

    # ----- INTERNALS -----

    def _prepare_user_content(self, user: str) -> str:
        if self.model_family.strip().lower() != "instruct/think":
            return user

        if self.reasoning_mode == "think":
            return f"{user} /think"
        if self.reasoning_mode == "no_think":
            return f"{user} /no_think"
        raise ValueError(
            "reasoning_mode must be 'think' or 'no_think' for model_family='instruct/think'."
        )

    def _build_payload(
            self,
            system: str,
            user: str,
            **kwargs
    ) -> JSONDict:
        prompt_user = self._prepare_user_content(user)

        # Start with the core required fields
        payload: JSONDict = {
            "model": self.model_name,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": prompt_user}
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

    @staticmethod
    def _extract_str(value: Any) -> str | None:
        return value if isinstance(value, str) else None

    def _parse_chat_response(self, data: dict[str, Any]) -> ChatResponse:
        choices = data.get("choices")
        first_choice: dict[str, Any] = {}
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            first_choice = choices[0]

        message = first_choice.get("message")
        message_dict = message if isinstance(message, dict) else {}

        content = self._extract_str(message_dict.get("content")) or ""
        reasoning_content = self._extract_str(message_dict.get("reasoning_content"))
        finish_reason = self._extract_str(first_choice.get("finish_reason"))
        model = self._extract_str(data.get("model"))
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else None

        return ChatResponse(
            content=content.strip(),
            reasoning_content=reasoning_content.strip() if reasoning_content else None,
            finish_reason=finish_reason,
            model=model,
            usage=usage,
        )

    def _parse_json_schema_content(self, data: dict[str, Any]) -> Any:
        choices = data.get("choices")
        first_choice: dict[str, Any] = {}
        if isinstance(choices, list) and choices and isinstance(choices[0], dict):
            first_choice = choices[0]

        message = first_choice.get("message")
        message_dict = message if isinstance(message, dict) else {}
        content = (self._extract_str(message_dict.get("content")) or "").strip()
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Malformed JSON schema response: {content}") from exc
        
    def _events_from_stream_line(
        self,
        line: str,
        state: ChatStreamAccumulator,
    ) -> tuple[list[ChatStreamEvent], bool]:
        stripped = line.strip()
        if not stripped or not stripped.startswith("data:"):
            return [], False

        payload = stripped[len("data:"):].strip()
        if not payload:
            return [], False
        if payload == "[DONE]":
            return [
                ChatStreamEvent(
                    channel="meta",
                    text="",
                    finish_reason=state.finish_reason,
                    model=state.model,
                    usage=state.usage,
                    done=True,
                )
            ], True

        try:
            data = json.loads(payload)
        except json.JSONDecodeError as exc:
            raise RuntimeError(f"Malformed stream JSON chunk: {payload}") from exc

        if not isinstance(data, dict):
            return [], False

        events: list[ChatStreamEvent] = []

        model = self._extract_str(data.get("model"))
        usage = data.get("usage") if isinstance(data.get("usage"), dict) else None
        choices = data.get("choices")
        first_choice = choices[0] if isinstance(choices, list) and choices and isinstance(choices[0], dict) else {}
        finish_reason = self._extract_str(first_choice.get("finish_reason"))
        delta = first_choice.get("delta")
        delta_dict = delta if isinstance(delta, dict) else {}

        content_chunk = self._extract_str(delta_dict.get("content"))
        if content_chunk:
            events.append(ChatStreamEvent(channel="content", text=content_chunk))

        reasoning_chunk = self._extract_str(delta_dict.get("reasoning_content"))
        if reasoning_chunk:
            events.append(ChatStreamEvent(channel="reasoning", text=reasoning_chunk))

        if finish_reason is not None or model is not None or usage is not None:
            events.append(
                ChatStreamEvent(
                    channel="meta",
                    text="",
                    finish_reason=finish_reason,
                    model=model,
                    usage=usage,
                    done=False,
                )
            )

        for event in events:
            state.add(event)
        return events, False

    # ----- API: chat, chat_async, chat_many -----

    def chat(self, system: str, user: str, **kwargs) -> ChatResponse:
        payload = self._build_payload(system=system, user=user, **kwargs)

        try:
            response = requests.post(self.server_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM Server connection failed: {e}")
        
        data = response.json()
        return self._parse_chat_response(data)
    
    async def chat_async(self, system: str, user: str, **kwargs) -> ChatResponse:
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
                return self._parse_chat_response(data)
            except httpx.HTTPError as exc:
                raise RuntimeError(f"LLM Server Error: {exc}") from exc
    
    async def chat_many(
            self,
            requests_: Sequence[ChatRequest],
            *,
            max_concurrency: int | None = None,
            return_exceptions: bool = True
    ) -> list[ChatResponse | Exception]:
        if not requests_:
            return []
        
        # Local LLM servers usually handle 1 - 4 parallel requests well
        concurrency = max_concurrency or 2
        semaphor = asyncio.Semaphore(concurrency)

        async def _one(req: ChatRequest) -> ChatResponse | Exception:
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

    # ----- API: json_schema_chat, json_schema_chat_async, json_schema_chat_async_many -----

    def json_schema_chat(self, system: str, user: str, schema: dict[str, Any], **kwargs) -> Any:
        payload = self._build_payload(system=system, user=user, **kwargs)
        payload["response_format"] = schema

        try:
            response = requests.post(self.server_url, json=payload, timeout=self.timeout_s)
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM Server connection failed: {e}")

        data = response.json()
        return self._parse_json_schema_content(data)
    
    async def json_schema_chat_async(
        self,
        system: str,
        user: str,
        schema: dict[str, Any],
        **kwargs,
    ) -> Any:
        payload = self._build_payload(system=system, user=user, **kwargs)
        payload["response_format"] = schema

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                response = await client.post(
                    self.server_url,
                    json=payload
                )
                response.raise_for_status()

                data = response.json()
                return self._parse_json_schema_content(data)
            except httpx.HTTPError as exc:
                raise RuntimeError(f"LLM Server Error: {exc}") from exc

    async def json_schema_chat_many(
            self,
            requests_: Sequence[JsonSchemaChatRequest],
            *,
            max_concurrency: int | None = None,
            return_exceptions: bool = True
    ) -> list[Any | Exception]:
        if not requests_:
            return []

        concurrency = max_concurrency or 2
        semaphor = asyncio.Semaphore(concurrency)

        async def _one(req: JsonSchemaChatRequest) -> Any | Exception:
            async with semaphor:
                try:
                    req_data = asdict(req)
                    system = req_data.pop("system")
                    user = req_data.pop("user")
                    schema = req_data.pop("schema")

                    return await self.json_schema_chat_async(
                        system=system,
                        user=user,
                        schema=schema,
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
    
    # ----- API: chat_stream, chat_stream_async -----

    def chat_stream(self, system: str, user: str, **kwargs) -> Iterator[ChatStreamEvent]:
        payload = self._build_payload(system=system, user=user, **kwargs)
        payload["stream"] = True
        state = ChatStreamAccumulator.create()

        try:
            response = requests.post(
                self.server_url,
                json=payload,
                timeout=self.timeout_s,
                stream=True,
            )
            response.raise_for_status()
        except requests.exceptions.RequestException as e:
            raise RuntimeError(f"LLM Server connection failed: {e}")

        with response:
            for line in response.iter_lines(decode_unicode=True):
                if not isinstance(line, str):
                    continue
                events, done = self._events_from_stream_line(line, state)
                for event in events:
                    yield event
                if done:
                    return

    async def chat_stream_async(
        self,
        system: str,
        user: str,
        **kwargs,
    ) -> AsyncIterator[ChatStreamEvent]:
        payload = self._build_payload(system=system, user=user, **kwargs)
        payload["stream"] = True
        state = ChatStreamAccumulator.create()

        async with httpx.AsyncClient(timeout=self.timeout_s) as client:
            try:
                async with client.stream("POST", self.server_url, json=payload) as response:
                    response.raise_for_status()
                    async for line in response.aiter_lines():
                        if not isinstance(line, str):
                            continue
                        events, done = self._events_from_stream_line(line, state)
                        for event in events:
                            yield event
                        if done:
                            return
            except httpx.HTTPError as exc:
                raise RuntimeError(f"LLM Server Error: {exc}") from exc

    @staticmethod
    def aggregate_stream_events(events: Iterable[ChatStreamEvent]) -> ChatResponse:
        state = ChatStreamAccumulator.create()
        for event in events:
            state.add(event)
        return state.to_response()