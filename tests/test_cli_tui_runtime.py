from __future__ import annotations

import asyncio
from pathlib import Path
import unittest
from unittest.mock import AsyncMock, Mock, patch

import cli.tui_app as tui_app


@unittest.skipUnless(tui_app.TEXTUAL_AVAILABLE, "textual is not installed")
class CliTuiRuntimeTests(unittest.IsolatedAsyncioTestCase):
    async def test_llm_start_dispatch(self) -> None:
        session = Mock()
        session.configure_llm_selection.return_value = {
            "message": "Selection persisted.",
            "selected_llm_key": "qwen3_4b_q8",
        }
        session.status.return_value = {
            "selected_llm_key": "qwen3_4b_q8",
            "running": False,
            "endpoint": None,
        }

        app = tui_app.EssayLensTuiApp(session=session)
        app._log = Mock()  # type: ignore[method-assign]
        app._refresh_status = Mock()  # type: ignore[method-assign]

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await app._dispatch("llm-start", {"model_key": "qwen3_4b_q8"})

        session.configure_llm_selection.assert_called_once_with("qwen3_4b_q8")

    async def test_topic_sentence_dispatch_uses_worker_path(self) -> None:
        session = Mock()
        session.run_topic_sentence.return_value = {
            "file": "/tmp/essay.docx",
            "suggested_topic_sentence": "Better sentence.",
            "feedback": "Feedback.",
            "json_out": "/tmp/out.json",
        }
        session.status.return_value = {
            "selected_llm_key": "qwen3_4b_q8",
            "running": True,
            "endpoint": "http://127.0.0.1:8080/v1/chat/completions",
        }

        app = tui_app.EssayLensTuiApp(session=session)
        app._log = Mock()  # type: ignore[method-assign]
        app._refresh_status = Mock()  # type: ignore[method-assign]

        with patch("asyncio.to_thread", new=AsyncMock(side_effect=lambda fn, *a, **kw: fn(*a, **kw))):
            await app._dispatch(
                "topic-sentence",
                {"file": "/tmp/essay.docx", "max_concurrency": None, "json_out": None},
            )

        session.run_topic_sentence.assert_called_once_with(
            "/tmp/essay.docx",
            max_concurrency=None,
            json_out=None,
        )

    async def test_shutdown_calls_stop_llm(self) -> None:
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
        await app.on_unmount()
        session.stop_llm.assert_called_once()

    async def test_completion_activates_after_four_chars(self) -> None:
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
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
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
        app._render_completion = Mock()  # type: ignore[method-assign]
        app.state.completion_active = True
        app.state.completion_items = ["Assessment/in/sample.docx"]

        text = "/topic-sentence @ass"
        app._schedule_completion(text, len(text))
        await asyncio.sleep(0)

        self.assertFalse(app.state.completion_active)
        self.assertEqual(app.state.completion_items, [])

    async def test_completion_apply_replaces_full_token(self) -> None:
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
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
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
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
        session = Mock()
        session.status.return_value = {"selected_llm_key": None, "running": False, "endpoint": None}
        app = tui_app.EssayLensTuiApp(session=session)
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


if __name__ == "__main__":
    unittest.main()
