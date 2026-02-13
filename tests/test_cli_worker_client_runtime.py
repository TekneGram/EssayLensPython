from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, patch

from cli.worker_client import WorkerClient, WorkerClientError
from cli.worker_protocol import WorkerResponse, encode_response


class _DummyStdin:
    def __init__(self) -> None:
        self.writes: list[bytes] = []

    def write(self, data: bytes) -> None:
        self.writes.append(data)

    async def drain(self) -> None:
        return None


class _DummyStdout:
    def __init__(self, lines: list[bytes]) -> None:
        self._lines = lines

    async def readline(self) -> bytes:
        if not self._lines:
            return b""
        return self._lines.pop(0)


class _DummyProc:
    def __init__(self, lines: list[bytes]) -> None:
        self.stdin = _DummyStdin()
        self.stdout = _DummyStdout(lines)
        self.stderr = _DummyStdout([])
        self.returncode = None

    async def wait(self) -> int:
        self.returncode = 0
        return 0

    def terminate(self) -> None:
        self.returncode = 0

    def kill(self) -> None:
        self.returncode = -9


class CliWorkerClientRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_call_round_trip_success(self) -> None:
        resp = WorkerResponse(id=1, ok=True, result={"running": False})
        proc = _DummyProc([(encode_response(resp) + "\n").encode("utf-8")])

        client = WorkerClient(timeout_s=1.0)
        client._proc = proc  # type: ignore[assignment]

        result = await client.call("llm-status", {}, retry_once=False)

        self.assertEqual(result, {"running": False})
        self.assertTrue(proc.stdin.writes)

    async def test_timeout_raises_worker_client_error(self) -> None:
        class _SlowStdout:
            async def readline(self) -> bytes:
                await asyncio.sleep(0.05)
                return b""

        proc = _DummyProc([])
        proc.stdout = _SlowStdout()  # type: ignore[assignment]

        client = WorkerClient(timeout_s=0.01)
        client._proc = proc  # type: ignore[assignment]

        with self.assertRaises(WorkerClientError):
            await client.call("llm-status", {}, retry_once=False)

    async def test_call_restarts_and_retries_once(self) -> None:
        client = WorkerClient(timeout_s=1.0)

        with patch.object(
            client,
            "_call_once",
            new=AsyncMock(side_effect=[WorkerClientError("down"), {"ok": True}]),
        ), patch.object(client, "_restart", new=AsyncMock()) as restart_mock:
            result = await client.call("llm-status", {}, retry_once=True)

        self.assertEqual(result, {"ok": True})
        restart_mock.assert_awaited_once()

    async def test_call_skips_non_json_lines_until_valid_response(self) -> None:
        resp = WorkerResponse(id=1, ok=True, result={"running": True})
        proc = _DummyProc(
            [
                b"progress: loading model...\n",
                b"\n",
                (encode_response(resp) + "\n").encode("utf-8"),
            ]
        )
        client = WorkerClient(timeout_s=1.0)
        client._proc = proc  # type: ignore[assignment]

        result = await client.call("llm-status", {}, retry_once=False)

        self.assertEqual(result, {"running": True})


if __name__ == "__main__":
    unittest.main()
