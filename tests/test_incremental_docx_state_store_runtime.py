from __future__ import annotations

import json
import tempfile
import unittest
from pathlib import Path

from services.incremental_docx_state_store import IncrementalDocxStateStore, StateStoreError


class IncrementalDocxStateStoreRuntimeTests(unittest.TestCase):
    def test_load_new_state_when_sidecar_missing(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            store = IncrementalDocxStateStore(output_path=output)

            state = store.load()

            self.assertEqual(state["version"], 1)
            self.assertEqual(state["sections_written"], [])
            self.assertEqual(state["feedback_append_count"], 0)

    def test_save_then_load_roundtrip(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            store = IncrementalDocxStateStore(output_path=output)
            state = store.load()

            store.ensure_section(state, "header_edited")
            store.record_edited_hash(state, "edited text")
            store.save(state)

            loaded = store.load()

            self.assertIn("header_edited", loaded["sections_written"])
            self.assertIsInstance(loaded["edited_text_hash"], str)

    def test_corrupt_sidecar_raises_actionable_error(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            store = IncrementalDocxStateStore(output_path=output)
            store.sidecar_path.write_text("not json", encoding="utf-8")

            with self.assertRaises(StateStoreError):
                store.load()

    def test_invalid_schema_raises(self) -> None:
        with tempfile.TemporaryDirectory() as tmp:
            output = Path(tmp) / "report.docx"
            store = IncrementalDocxStateStore(output_path=output)
            store.sidecar_path.write_text(json.dumps({"version": 1}), encoding="utf-8")

            with self.assertRaises(StateStoreError):
                store.load()


if __name__ == "__main__":
    unittest.main()
