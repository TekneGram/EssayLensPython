from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class OcrModelSpec:
    key: str
    display_name: str
    hf_repo_id: str
    hf_filename: str
    mmproj_filename: str
    backend: str
    model_family: str
    min_ram_gb: int
    min_vram_gb: int
    param_size_b: int
    notes: str


OCR_MODEL_SPECS: list[OcrModelSpec] = [
    OcrModelSpec(
        key="lightonocr_2_1b_q4_k_m",
        display_name="LightOnOCR 2 1B Q4_K_M",
        hf_repo_id="staghado/LightOnOCR-2-1B-Q4_K_M-GGUF",
        hf_filename="LightOnOCR-2-1B-Q4_K_M.gguf",
        mmproj_filename="mmproj-LightOnOCR-2-1B-Q8_0.gguf",
        backend="server",
        model_family="ocr/vision",
        min_ram_gb=4,
        min_vram_gb=4,
        param_size_b=1,
        notes="Multimodal OCR model for document text extraction.",
    ),
]
