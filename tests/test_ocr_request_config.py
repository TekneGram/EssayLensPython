from __future__ import annotations

import unittest

from config.ocr_request_config import OcrRequestConfig


class OcrRequestConfigTests(unittest.TestCase):
    def test_validate_accepts_defaults(self) -> None:
        cfg = OcrRequestConfig.from_values()
        cfg.validate()

    def test_validate_rejects_non_positive_max_tokens(self) -> None:
        cfg = OcrRequestConfig.from_values(max_tokens=0)
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_invalid_top_p(self) -> None:
        cfg = OcrRequestConfig.from_values(top_p=1.5)
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_negative_top_k(self) -> None:
        cfg = OcrRequestConfig.from_values(top_k=-1)
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_blank_image_mime(self) -> None:
        cfg = OcrRequestConfig.from_values(image_mime="   ")
        with self.assertRaises(ValueError):
            cfg.validate()

    def test_validate_rejects_blank_prompt(self) -> None:
        cfg = OcrRequestConfig.from_values(prompt="   ")
        with self.assertRaises(ValueError):
            cfg.validate()


if __name__ == "__main__":
    unittest.main()
