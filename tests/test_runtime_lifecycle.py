from __future__ import annotations

import unittest
from unittest.mock import Mock, patch

from app.runtime_lifecycle import RuntimeLifecycle


class RuntimeLifecycleTests(unittest.TestCase):
    def test_register_process_registers_once(self) -> None:
        lifecycle = RuntimeLifecycle()
        proc = Mock()

        with patch("app.runtime_lifecycle.atexit.register") as register_mock:
            lifecycle.register_process(proc)
            lifecycle.register_process(proc)

        register_mock.assert_called_once()

    def test_registered_shutdown_stops_running_process(self) -> None:
        lifecycle = RuntimeLifecycle()
        proc = Mock()
        proc.is_running.return_value = True

        with patch("app.runtime_lifecycle.atexit.register") as register_mock:
            lifecycle.register_process(proc)
            shutdown_cb = register_mock.call_args.args[0]

        shutdown_cb()
        proc.stop.assert_called_once_with()

    def test_registered_shutdown_skips_non_running_process(self) -> None:
        lifecycle = RuntimeLifecycle()
        proc = Mock()
        proc.is_running.return_value = False

        with patch("app.runtime_lifecycle.atexit.register") as register_mock:
            lifecycle.register_process(proc)
            shutdown_cb = register_mock.call_args.args[0]

        shutdown_cb()
        proc.stop.assert_not_called()


if __name__ == "__main__":
    unittest.main()
