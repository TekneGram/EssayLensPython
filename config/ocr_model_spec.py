from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrModelSpec:
    key: str
    display_name: str
    hf_repo_id: str
    hf_filename: str
    mmproj_filename: str
    notes: str


OCR_MODEL_SPECS: list[OcrModelSpec] = [
    OcrModelSpec(
        key="lightonocr_2_1b_q4_k_m",
        display_name="LightOnOCR 2 1B Q4_K_M",
        hf_repo_id="staghado/LightOnOCR-2-1B-Q4_K_M-GGUF",
        hf_filename="LightOnOCR-2-1B-Q4_K_M.gguf",
        mmproj_filename="mmproj-LightOnOCR-2-1B-Q8_0.gguf",
        notes="Default OCR model for multimodal text extraction.",
    ),
]
