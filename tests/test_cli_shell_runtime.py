from __future__ import annotations

import io
from contextlib import redirect_stdout
import unittest
from unittest.mock import Mock

from cli.shell import CliShell


class CliShellRuntimeTests(unittest.TestCase):
    def test_help_then_exit(self) -> None:
        inputs = iter(["/help", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.stop_llm.return_value = False

        buffer = io.StringIO()
        with redirect_stdout(buffer):
            code = shell.run()

        self.assertEqual(code, 0)
        shell.session.stop_llm.assert_called()
        self.assertIn("/metadata @path/to/file.docx", buffer.getvalue())
        self.assertIn("/prompt-test @path/to/file.docx", buffer.getvalue())

    def test_error_does_not_exit_loop(self) -> None:
        inputs = iter(["/unknown", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.stop_llm.return_value = False

        code = shell.run()

        self.assertEqual(code, 0)
        shell.session.stop_llm.assert_called()

    def test_llm_start_then_status_dispatches(self) -> None:
        inputs = iter(["/llm-start qwen3_4b_q8", "/llm-status", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.configure_llm_selection.return_value = {
            "selected_llm_key": "qwen3_4b_q8",
            "message": "Selection persisted.",
        }
        shell.session.status.return_value = {
            "selected_llm_key": "qwen3_4b_q8",
            "running": False,
            "endpoint": None,
        }

        code = shell.run()

        self.assertEqual(code, 0)
        shell.session.configure_llm_selection.assert_called_once_with("qwen3_4b_q8")
        shell.session.status.assert_called_once()

    def test_metadata_dispatches_to_session(self) -> None:
        inputs = iter(["/metadata @/tmp/essay.docx", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.run_metadata.return_value = {
            "file": "/tmp/essay.docx",
            "json_out": "/tmp/out.json",
            "metadata": {
                "student_name": "Ada",
                "student_number": "123",
                "essay_title": "Title",
            },
        }
        shell.session.stop_llm.return_value = False

        code = shell.run()

        self.assertEqual(code, 0)
        shell.session.run_metadata.assert_called_once_with("/tmp/essay.docx", json_out=None)
        shell.session.stop_llm.assert_called()

    def test_prompt_test_dispatches_to_session(self) -> None:
        inputs = iter(["/prompt-test @/tmp/essay.docx", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.run_prompt_test.return_value = {
            "file": "/tmp/essay.docx",
            "feedback": "Use more clear causal links.",
            "json_out": "/tmp/out.json",
        }
        shell.session.stop_llm.return_value = False

        code = shell.run()

        self.assertEqual(code, 0)
        shell.session.run_prompt_test.assert_called_once_with(
            "/tmp/essay.docx",
            max_concurrency=None,
            json_out=None,
        )
        shell.session.stop_llm.assert_called()


if __name__ == "__main__":
    unittest.main()
