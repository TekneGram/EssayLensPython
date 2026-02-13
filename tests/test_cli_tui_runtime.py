from __future__ import annotations

import asyncio
from pathlib import Path
from types import SimpleNamespace
import unittest
from unittest.mock import AsyncMock, Mock, patch

import cli.tui_app as tui_app
from cli.worker_client import WorkerClientError, WorkerCommandError


@unittest.skipUnless(tui_app.TEXTUAL_AVAILABLE, "textual is not installed")
class CliTuiRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_start_dispatch_uses_worker(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(
            return_value={
                "message": "Selection persisted.",
                "selected_llm_key": "qwen3_4b_q8",
            }
        )

        app = tui_app.EssayLensTuiApp(worker=worker)
        app._log = Mock()  # type: ignore[method-assign]

        await app._dispatch("llm-start", {"model_key": "qwen3_4b_q8"})

        worker.call.assert_awaited_once_with("llm-start", {"model_key": "qwen3_4b_q8"})

    async def test_topic_sentence_dispatch_uses_worker(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(
            return_value={
                "file": "/tmp/essay.docx",
                "suggested_topic_sentence": "Better sentence.",
                "feedback": "Feedback.",
                "json_out": "/tmp/out.json",
            }
        )

        app = tui_app.EssayLensTuiApp(worker=worker)
        app._log = Mock()  # type: ignore[method-assign]

        await app._dispatch(
            "topic-sentence",
            {"file": "/tmp/essay.docx", "max_concurrency": None, "json_out": None},
        )

        worker.call.assert_awaited_once_with(
            "topic-sentence",
            {
                "file": "/tmp/essay.docx",
                "max_concurrency": None,
                "json_out": None,
            },
        )

    async def test_shutdown_calls_worker_shutdown(self) -> None:
        worker = Mock()
        worker.shutdown = AsyncMock()
        app = tui_app.EssayLensTuiApp(worker=worker)
        await app.on_unmount()
        worker.shutdown.assert_awaited_once()

    async def test_completion_activates_after_four_chars(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._render_completion = Mock()  # type: ignore[method-assign]

        with patch("asyncio.sleep", new=AsyncMock(return_value=None)), patch(
            "asyncio.to_thread",
            new=AsyncMock(return_value=["/tmp/Assessment/in/sample.docx"]),
        ):
            text = "/topic-sentence @asse"
            app._schedule_completion(text, len(text))
            assert app._completion_task is not None
            await app._completion_task

        self.assertTrue(app.state.completion_active)
        self.assertEqual(app.state.completion_items[0], "/tmp/Assessment/in/sample.docx")

    async def test_completion_clears_below_threshold(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._render_completion = Mock()  # type: ignore[method-assign]
        app.state.completion_active = True
        app.state.completion_items = ["Assessment/in/sample.docx"]

        text = "/topic-sentence @ass"
        app._schedule_completion(text, len(text))
        await asyncio.sleep(0)

        self.assertFalse(app.state.completion_active)
        self.assertEqual(app.state.completion_items, [])

    async def test_completion_apply_replaces_full_token(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._clear_completion = Mock()  # type: ignore[method-assign]
        app._log = Mock()  # type: ignore[method-assign]

        cmd_input = Mock()
        cmd_input.value = "/topic-sentence @Assessment/in/sample.docx trailing"
        cmd_input.cursor_position = cmd_input.value.index("@Assessment") + len("@Assess")

        app.state.completion_active = True
        app.state.completion_items = ["/tmp/full/path/file.docx"]
        app.state.completion_index = 0
        app.state.completion_start = cmd_input.value.index("@Assessment")
        app.state.completion_end = cmd_input.value.index(" trailing")
        app.state.completion_query = "Assess"
        app.state.completion_source_text = cmd_input.value
        app.state.completion_source_cursor = cmd_input.cursor_position

        with patch.object(app, "query_one", return_value=cmd_input):
            app.action_completion_apply()

        expected_path = str(Path("/tmp/full/path/file.docx").resolve())
        self.assertEqual(cmd_input.value, f"/topic-sentence @{expected_path} trailing")

    async def test_completion_apply_stale_state_retriggers_search(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._clear_completion = Mock()  # type: ignore[method-assign]
        app._log = Mock()  # type: ignore[method-assign]
        app._schedule_completion = Mock()  # type: ignore[method-assign]

        cmd_input = Mock()
        cmd_input.value = "/topic-sentence trailing"
        cmd_input.cursor_position = len(cmd_input.value)

        app.state.completion_active = True
        app.state.completion_items = ["/tmp/full/path/file.docx"]
        app.state.completion_index = 0
        app.state.completion_start = 16
        app.state.completion_end = 22
        app.state.completion_query = "Assess"
        app.state.completion_source_text = "/topic-sentence @asse"
        app.state.completion_source_cursor = len("/topic-sentence @asse")

        with patch.object(app, "query_one", return_value=cmd_input):
            app.action_completion_apply()

        app._schedule_completion.assert_called_once_with(cmd_input.value, cmd_input.cursor_position)

    async def test_enter_applies_completion_instead_of_submitting(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app.action_completion_apply = Mock()  # type: ignore[method-assign]
        app._log = Mock()  # type: ignore[method-assign]

        app.state.completion_active = True
        app.state.completion_items = ["/tmp/path/file.docx"]
        event = Mock()
        event.value = "/topic-sentence @asse"
        event.input = Mock()
        event.input.value = event.value

        with patch("cli.tui_app.parse_shell_command") as parse_mock:
            await app.on_input_submitted(event)

        app.action_completion_apply.assert_called_once()
        parse_mock.assert_not_called()

    async def test_busy_guard_blocks_submit(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(return_value={"selected_llm_key": None, "running": False, "endpoint": None})
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._log = Mock()  # type: ignore[method-assign]
        app._busy = True

        event = Mock()
        event.value = "/llm-status"
        event.input = Mock()
        event.input.value = event.value

        with patch("cli.tui_app.parse_shell_command") as parse_mock:
            await app.on_input_submitted(event)

        parse_mock.assert_not_called()
        app._log.assert_called_with("Busy: previous command still running.")

    async def test_worker_stage_error_is_surfaced(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(
            side_effect=WorkerCommandError(
                code="runtime_stage_error",
                message="bad value(s) in fds_to_keep",
                stage="build_container",
                traceback_text="traceback",
            )
        )
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._log = Mock()  # type: ignore[method-assign]
        app._refresh_status = AsyncMock()  # type: ignore[method-assign]
        app._clear_completion = Mock()  # type: ignore[method-assign]

        parsed = SimpleNamespace(name="topic-sentence", args={"file": "/tmp/essay.docx"})
        event = Mock()
        event.value = "/topic-sentence @/tmp/essay.docx"
        event.input = Mock()
        event.input.value = event.value
        with patch("cli.tui_app.parse_shell_command", return_value=parsed):
            await app.on_input_submitted(event)

        log_calls = [str(call.args[0]) for call in app._log.call_args_list]
        self.assertTrue(any("Error at stage build_container" in msg for msg in log_calls))

    async def test_worker_transport_error_is_surfaced(self) -> None:
        worker = Mock()
        worker.call = AsyncMock(side_effect=WorkerClientError("transport down"))
        app = tui_app.EssayLensTuiApp(worker=worker)
        app._log = Mock()  # type: ignore[method-assign]
        app._refresh_status = AsyncMock()  # type: ignore[method-assign]
        app._clear_completion = Mock()  # type: ignore[method-assign]

        parsed = SimpleNamespace(name="llm-status", args={})
        event = Mock()
        event.value = "/llm-status"
        event.input = Mock()
        event.input.value = event.value

        with patch("cli.tui_app.parse_shell_command", return_value=parsed):
            await app.on_input_submitted(event)

        log_calls = [str(call.args[0]) for call in app._log.call_args_list]
        self.assertTrue(any("Worker transport error" in msg for msg in log_calls))


if __name__ == "__main__":
    unittest.main()
