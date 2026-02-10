from __future__ import annotations

import asyncio
import unittest
from unittest.mock import AsyncMock, Mock

from services.ocr_service import OcrService


class OcrServiceTests(unittest.TestCase):
    def test_extract_text_passthrough(self) -> None:
        mock_client = Mock()
        mock_client.extract_text.return_value = "hello"

        service = OcrService(client=mock_client)
        result = service.extract_text(b"image", prompt="read", max_tokens=77)

        self.assertEqual(result, "hello")
        mock_client.extract_text.assert_called_once_with(
            image_bytes=b"image",
            prompt="read",
            max_tokens=77,
        )

    def test_extract_text_async_passthrough(self) -> None:
        mock_client = Mock()
        mock_client.extract_text_async = AsyncMock(return_value="async text")
        service = OcrService(client=mock_client)

        result = asyncio.run(service.extract_text_async(b"image", prompt="read"))

        self.assertEqual(result, "async text")
        mock_client.extract_text_async.assert_called_once_with(
            image_bytes=b"image",
            prompt="read",
        )


if __name__ == "__main__":
    unittest.main()
