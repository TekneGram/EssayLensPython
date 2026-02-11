from __future__ import annotations

import asyncio
import unittest
from types import SimpleNamespace
from unittest.mock import AsyncMock, Mock

from nlp.llm.tasks.extract_metadata import (
    METADATA_RESPONSE_SCHEMA,
    SYSTEM_PROMPT,
    build_metadata_requests,
    run_parallel_metadata_extraction,
)


class ExtractMetadataTaskTests(unittest.TestCase):
    def test_build_metadata_requests_uses_shared_prompt_and_schema(self) -> None:
        requests_ = build_metadata_requests(["text one", "text two"])

        self.assertEqual(len(requests_), 2)
        self.assertEqual(requests_[0].system, SYSTEM_PROMPT)
        self.assertEqual(requests_[0].schema, METADATA_RESPONSE_SCHEMA)
        self.assertEqual(requests_[0].user, "text one")
        self.assertEqual(requests_[0].temperature, 0.0)

    def test_run_parallel_metadata_extraction_calls_json_schema_many(self) -> None:
        app_cfg = SimpleNamespace(llm_server=SimpleNamespace(llama_n_parallel=3))
        llm_service = Mock()
        llm_service.json_schema_chat_many = AsyncMock(
            return_value=[{"essay_title": "Demo"}, RuntimeError("bad")]
        )

        result = asyncio.run(
            run_parallel_metadata_extraction(
                llm_service=llm_service,
                app_cfg=app_cfg,
                text_tasks=["doc a", "doc b"],
            )
        )

        self.assertEqual(result["task_count"], 2)
        self.assertEqual(result["success_count"], 1)
        self.assertEqual(result["failure_count"], 1)
        llm_service.json_schema_chat_many.assert_called_once()


if __name__ == "__main__":
    unittest.main()
