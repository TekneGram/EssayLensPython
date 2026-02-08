from __future__ import annotations

import unittest

from config.llm_model_spec import MODEL_SPECS


class LlmModelSpecTests(unittest.TestCase):
    def test_model_specs_schema_constraints(self) -> None:
        self.assertGreater(len(MODEL_SPECS), 0)
        for spec in MODEL_SPECS:
            self.assertTrue(spec.key.strip())
            self.assertTrue(spec.display_name.strip())
            self.assertTrue(spec.hf_repo_id.strip())
            self.assertTrue(spec.hf_filename.strip())
            self.assertTrue(spec.backend.strip())
            self.assertTrue(spec.model_family.strip())
            self.assertGreater(spec.min_ram_gb, 0)
            self.assertGreater(spec.min_vram_gb, 0)
            self.assertGreater(spec.param_size_b, 0)
            self.assertTrue(spec.notes.strip())
            self.assertTrue(
                spec.mmproj_filename is None or bool(spec.mmproj_filename.strip())
            )


if __name__ == "__main__":
    unittest.main()
