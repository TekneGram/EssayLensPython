from __future__ import annotations

import unittest
from unittest.mock import Mock

from cli.shell import CliShell


class CliShellRuntimeTests(unittest.TestCase):
    def test_help_then_exit(self) -> None:
        inputs = iter(["/help", "/exit"])
        shell = CliShell(input_fn=lambda _prompt: next(inputs))
        shell.session = Mock()
        shell.session.stop_llm.return_value = False

        code = shell.run()

        self.assertEqual(code, 0)
        shell.session.stop_llm.assert_called()

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


if __name__ == "__main__":
    unittest.main()
