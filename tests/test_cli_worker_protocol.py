from __future__ import annotations

import unittest

from cli.worker_protocol import (
    WorkerErrorEnvelope,
    WorkerRequest,
    WorkerResponse,
    decode_request,
    decode_response,
    encode_request,
    encode_response,
)


class CliWorkerProtocolTests(unittest.TestCase):
    def test_request_round_trip(self) -> None:
        req = WorkerRequest(id=7, method="llm-status", params={"x": 1})
        decoded = decode_request(encode_request(req))
        self.assertEqual(decoded.id, 7)
        self.assertEqual(decoded.method, "llm-status")
        self.assertEqual(decoded.params, {"x": 1})

    def test_response_success_round_trip(self) -> None:
        resp = WorkerResponse(id=9, ok=True, result={"running": False}, diagnostics=[{"stage": "x", "detail": "ok"}])
        decoded = decode_response(encode_response(resp))
        self.assertTrue(decoded.ok)
        self.assertEqual(decoded.result, {"running": False})
        self.assertEqual(decoded.diagnostics, [{"stage": "x", "detail": "ok"}])

    def test_response_error_round_trip(self) -> None:
        resp = WorkerResponse(
            id=3,
            ok=False,
            error=WorkerErrorEnvelope(
                code="runtime_stage_error",
                message="bad value(s) in fds_to_keep",
                stage="build_container",
                traceback="tb",
            ),
        )
        decoded = decode_response(encode_response(resp))
        self.assertFalse(decoded.ok)
        assert decoded.error is not None
        self.assertEqual(decoded.error.code, "runtime_stage_error")
        self.assertEqual(decoded.error.stage, "build_container")

    def test_decode_request_rejects_invalid_payload(self) -> None:
        with self.assertRaises(ValueError):
            decode_request('{"id": "one", "method": "x", "params": {}}')


if __name__ == "__main__":
    unittest.main()
