from __future__ import annotations

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


if __name__ == "__main__":
    unittest.main()

