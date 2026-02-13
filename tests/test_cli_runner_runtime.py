from __future__ import annotations

import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch

from cli.runner import CliSession, RuntimeStageError


class CliRunnerRuntimeTests(unittest.TestCase):
    def test_configure_llm_selection_persists_without_starting_server(self) -> None:
        session = CliSession()
        fake_cfg = SimpleNamespace(llm_config=SimpleNamespace(llama_model_key="qwen3_4b_q8"))

        with patch.object(session, "_build_cfg", return_value=fake_cfg), patch(
            "cli.runner.llm_statuses",
            return_value=[SimpleNamespace(key="qwen3_4b_q8", display_name="Qwen", installed=True)],
        ):
            result = session.configure_llm_selection("qwen3_4b_q8")

        self.assertEqual(result["selected_llm_key"], "qwen3_4b_q8")
        self.assertTrue(result["installed"])
        self.assertIn("lazily", result["message"].lower())

    def test_switch_llm_stops_server_and_updates_selection(self) -> None:
        session = CliSession()
        with patch.object(session, "stop_llm", return_value=True), patch.object(
            session,
            "configure_llm_selection",
            return_value={"selected_llm_key": "qwen3_8b_q8", "message": "ok"},
        ):
            result = session.switch_llm("qwen3_8b_q8")

        self.assertTrue(result["was_running"])
        self.assertEqual(result["selected_llm_key"], "qwen3_8b_q8")

    def test_topic_sentence_runs_with_lazy_server_start(self) -> None:
        session = CliSession()

        with tempfile.TemporaryDirectory() as tmpdir:
            doc_path = Path(tmpdir) / "essay.docx"
            doc_path.write_text("placeholder", encoding="utf-8")
            out_root = Path(tmpdir) / "explained"

            server_proc = Mock()
            server_proc.is_running.return_value = False

            llm_task_service = Mock()
            llm_task_service.construct_topic_sentence_parallel.return_value = {
                "outputs": [SimpleNamespace(content="A tighter topic sentence.")]
            }
            llm_task_service.analyze_topic_sentence_parallel.return_value = {
                "outputs": [SimpleNamespace(content="The original sentence is too broad.")]
            }

            document_input_service = Mock()
            document_input_service.load.return_value = SimpleNamespace(
                blocks=["This is sentence one. This is sentence two."]
            )

            session.app_cfg = SimpleNamespace(
                assessment_paths=SimpleNamespace(explained_folder=out_root)
            )
            session.deps = {
                "server_proc": server_proc,
                "llm_task_service": llm_task_service,
                "document_input_service": document_input_service,
            }

            result = session.run_topic_sentence(doc_path)

            server_proc.start.assert_called_once()
            self.assertIn("tighter", result["suggested_topic_sentence"].lower())
            self.assertTrue(Path(result["json_out"]).exists())

    def test_ensure_runtime_raises_stage_error_with_context(self) -> None:
        session = CliSession()
        with patch.object(session, "_build_cfg", side_effect=RuntimeError("boom cfg")):
            with self.assertRaises(RuntimeStageError) as ctx:
                session.ensure_runtime_for_llm_task()
        self.assertEqual(ctx.exception.stage, "build_cfg")
        self.assertIn("boom cfg", ctx.exception.detail)

    def test_diagnostics_hook_receives_stage_details(self) -> None:
        captured: list[tuple[str, str]] = []

        def hook(stage: str, detail: str, _tb: str) -> None:
            captured.append((stage, detail))

        session = CliSession(diagnostics_hook=hook)
        with patch.object(session, "_build_cfg", side_effect=RuntimeError("cfg error")):
            with self.assertRaises(RuntimeStageError):
                session.ensure_runtime_for_llm_task()

        self.assertTrue(captured)
        self.assertEqual(captured[0][0], "build_cfg")
        self.assertIn("cfg error", captured[0][1])


if __name__ == "__main__":
    unittest.main()
