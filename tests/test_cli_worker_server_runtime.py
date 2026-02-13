from __future__ import annotations

import unittest
from unittest.mock import Mock

from cli.runner import RuntimeStageError
from cli.worker_protocol import WorkerRequest
from cli.worker_server import _handle_request


class CliWorkerServerRuntimeTests(unittest.TestCase):
    def _make_session(self) -> Mock:
        session = Mock()
        session.diagnostics_hook = None
        return session

    def test_llm_status_dispatch_success(self) -> None:
        session = self._make_session()
        session.status.return_value = {
            "selected_llm_key": "qwen3_4b_q8",
            "running": False,
            "endpoint": None,
        }

        resp, should_stop = _handle_request(session, WorkerRequest(id=1, method="llm-status", params={}))

        self.assertTrue(resp.ok)
        self.assertFalse(should_stop)
        self.assertEqual(resp.result, session.status.return_value)

    def test_topic_sentence_requires_file(self) -> None:
        session = self._make_session()

        resp, should_stop = _handle_request(session, WorkerRequest(id=2, method="topic-sentence", params={}))

        self.assertFalse(resp.ok)
        self.assertFalse(should_stop)
        assert resp.error is not None
        self.assertEqual(resp.error.code, "validation_error")

    def test_runtime_stage_error_is_forwarded(self) -> None:
        session = self._make_session()
        session.run_topic_sentence.side_effect = RuntimeStageError(
            stage="build_container",
            detail="bad value(s) in fds_to_keep",
            traceback_text="traceback",
        )

        resp, should_stop = _handle_request(
            session,
            WorkerRequest(id=3, method="topic-sentence", params={"file": "/tmp/essay.docx"}),
        )

        self.assertFalse(resp.ok)
        self.assertFalse(should_stop)
        assert resp.error is not None
        self.assertEqual(resp.error.code, "runtime_stage_error")
        self.assertEqual(resp.error.stage, "build_container")

    def test_shutdown_stops_session_and_requests_stop(self) -> None:
        session = self._make_session()

        resp, should_stop = _handle_request(session, WorkerRequest(id=4, method="shutdown", params={}))

        self.assertTrue(resp.ok)
        self.assertTrue(should_stop)
        session.stop_llm.assert_called_once()


if __name__ == "__main__":
    unittest.main()
