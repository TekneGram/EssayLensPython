from __future__ import annotations
from dataclasses import dataclass



@dataclass(frozen=True)
class LlmModelSpec:
    key: str
    display_name: str
    hf_repo_id: str
    hf_filename: str
    mmproj_filename: str | None
    backend: str
    model_family: str
    min_ram_gb: int
    min_vram_gb: int
    param_size_b: int
    notes: str

MODEL_SPECS: list[LlmModelSpec] = [
    LlmModelSpec(
        key="qwen3_4b_instruct_q8",
        display_name="Qwen3 4B Q8_0 Instruct",
        hf_repo_id="unsloth/Qwen3-4B-Instruct-2507-GGUF",
        hf_filename="Qwen3-4B-Instruct-2507-Q8_0.gguf",
        mmproj_filename=None,
        backend="server",
        model_family="instruct",
        min_ram_gb=6,
        min_vram_gb=6,
        param_size_b=4,
        notes="CPU/GPU friendly; good quality for 4B.",
    ),
    LlmModelSpec(
        key="qwen3_4b_q8",
        display_name="Qwen3 4B Q8_0",
        hf_repo_id="Qwen/Qwen3-4B-GGUF",
        hf_filename="Qwen3-4B-Q8_0.gguf",
        mmproj_filename=None,
        backend="server",
        model_family="instruct/think",
        min_ram_gb=6,
        min_vram_gb=6,
        param_size_b=4,
        notes="CPU/GPU friendly; good quality for 4B.",
    ),
    LlmModelSpec(
        key="qwen3_8b_q8",
        display_name="Qwen3 8B Q8_0",
        hf_repo_id="Qwen/Qwen3-8B-GGUF",
        hf_filename="Qwen3-8B-Q8_0.gguf",
        mmproj_filename=None,
        backend="server",
        model_family="instruct/think",
        min_ram_gb=12,
        min_vram_gb=6,
        param_size_b=8,
        notes="Thinking and instruct variant."
    )
]
