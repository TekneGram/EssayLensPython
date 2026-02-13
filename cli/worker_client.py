from __future__ import annotations

import asyncio
import sys
from typing import Any

from cli.worker_protocol import WorkerRequest, decode_response, encode_request


class WorkerClientError(RuntimeError):
    pass


class WorkerCommandError(WorkerClientError):
    def __init__(
        self,
        *,
        code: str,
        message: str,
        stage: str | None = None,
        traceback_text: str | None = None,
        diagnostics: list[dict[str, str]] | None = None,
    ) -> None:
        super().__init__(message)
        self.code = code
        self.stage = stage
        self.traceback_text = traceback_text
        self.diagnostics = diagnostics or []


class WorkerClient:
    def __init__(self, timeout_s: float = 240.0) -> None:
        self.timeout_s = timeout_s
        self._proc: asyncio.subprocess.Process | None = None
        self._next_id = 1
        self._lock = asyncio.Lock()

    async def start(self) -> None:
        if self._proc is not None and self._proc.returncode is None:
            return
        self._proc = await asyncio.create_subprocess_exec(
            sys.executable,
            "-m",
            "cli.worker_server",
            stdin=asyncio.subprocess.PIPE,
            stdout=asyncio.subprocess.PIPE,
            stderr=asyncio.subprocess.PIPE,
        )
        await self.call("health", {}, timeout_s=10.0, retry_once=False)

    async def shutdown(self) -> None:
        if self._proc is None:
            return
        if self._proc.returncode is None:
            try:
                await self.call("shutdown", {}, timeout_s=5.0, retry_once=False)
            except Exception:
                pass
            try:
                await asyncio.wait_for(self._proc.wait(), timeout=2.0)
            except Exception:
                self._proc.terminate()
                try:
                    await asyncio.wait_for(self._proc.wait(), timeout=2.0)
                except Exception:
                    self._proc.kill()
        self._proc = None

    async def call(
        self,
        method: str,
        params: dict[str, Any],
        *,
        timeout_s: float | None = None,
        retry_once: bool = True,
    ) -> dict[str, Any]:
        timeout = timeout_s if timeout_s is not None else self.timeout_s
        attempts = 2 if retry_once else 1

        last_exc: Exception | None = None
        for attempt in range(attempts):
            try:
                return await self._call_once(method, params, timeout=timeout)
            except WorkerClientError as exc:
                last_exc = exc
                if attempt + 1 >= attempts:
                    break
                await self._restart()
        if last_exc is not None:
            raise last_exc
        raise WorkerClientError("Worker call failed without exception.")

    async def _call_once(self, method: str, params: dict[str, Any], *, timeout: float) -> dict[str, Any]:
        async with self._lock:
            if self._proc is None or self._proc.returncode is not None:
                await self.start()
            assert self._proc is not None
            assert self._proc.stdin is not None
            assert self._proc.stdout is not None

            req = WorkerRequest(id=self._next_id, method=method, params=params)
            self._next_id += 1
            self._proc.stdin.write((encode_request(req) + "\n").encode("utf-8"))
            await self._proc.stdin.drain()

            loop = asyncio.get_running_loop()
            deadline = loop.time() + timeout
            non_protocol_lines: list[str] = []

            while True:
                remaining = deadline - loop.time()
                if remaining <= 0:
                    noise = "; ".join(non_protocol_lines[-3:])
                    suffix = f" Non-protocol output: {noise}" if noise else ""
                    raise WorkerClientError(f"Worker timeout for method {method}.{suffix}")
                try:
                    raw = await asyncio.wait_for(self._proc.stdout.readline(), timeout=remaining)
                except asyncio.TimeoutError as exc:
                    noise = "; ".join(non_protocol_lines[-3:])
                    suffix = f" Non-protocol output: {noise}" if noise else ""
                    raise WorkerClientError(f"Worker timeout for method {method}.{suffix}") from exc
                if not raw:
                    raise WorkerClientError("Worker process closed stdout.")

                line = raw.decode("utf-8", errors="replace").strip()
                if not line:
                    continue

                try:
                    resp = decode_response(line)
                except Exception:
                    non_protocol_lines.append(line)
                    continue

                if resp.id not in {req.id, -1}:
                    # With in-order lock semantics this should not happen,
                    # but ignore mismatched messages to keep protocol robust.
                    non_protocol_lines.append(line)
                    continue
                break

            if resp.ok:
                return resp.result or {}
            error = resp.error
            if error is None:
                raise WorkerClientError("Worker returned error without payload.")
            raise WorkerCommandError(
                code=error.code,
                message=error.message,
                stage=error.stage,
                traceback_text=error.traceback,
                diagnostics=resp.diagnostics or [],
            )

    async def _restart(self) -> None:
        await self.shutdown()
        await self.start()
