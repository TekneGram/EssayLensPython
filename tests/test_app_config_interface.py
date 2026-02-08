from __future__ import annotations

import unittest

from app.settings import AppConfig
from interfaces.config.app_config import AppConfigShape


class AppConfigInterfaceTests(unittest.TestCase):
    def test_app_config_shape_matches_runtime_field_names(self) -> None:
        runtime_fields = set(AppConfig.__dataclass_fields__.keys())
        interface_fields = set(AppConfigShape.__dataclass_fields__.keys())
        self.assertEqual(interface_fields, runtime_fields)


if __name__ == "__main__":
    unittest.main()
