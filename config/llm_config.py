from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LlmConfig:
    hf_repo_id: str | None = None
    hf_filename: str | None = None
    hf_revision: str | None = None
    hf_mmproj_filename: str | None = None
    llama_gguf_path: Path | None = None
    llama_mmproj_path: Path | None = None
    llama_server_model: str = ""
    llama_model_key: str = ""
    llama_model_display_name: str = ""
    llama_model_alias: str = ""
    llama_model_family: str = ""

    @staticmethod
    def from_strings(
        hf_repo_id: str | None = None,
        hf_filename: str | None = None,
        hf_revision: str | None = None,
        hf_mmproj_filename: str | None = None,
        llama_gguf_path: str | Path | None = None,
        llama_mmproj_path: str | Path | None = None,
        llama_server_model: str = "",
        llama_model_key: str = "",
        llama_model_display_name: str = "",
        llama_model_alias: str = "",
        llama_model_family: str = "",
    ) -> "LlmConfig":
        return LlmConfig(
            hf_repo_id=LlmConfig._norm_optional_text(hf_repo_id),
            hf_filename=LlmConfig._norm_optional_text(hf_filename),
            hf_revision=LlmConfig._norm_optional_text(hf_revision),
            hf_mmproj_filename=LlmConfig._norm_optional_text(hf_mmproj_filename),
            llama_gguf_path=LlmConfig._norm_optional_path(llama_gguf_path),
            llama_mmproj_path=LlmConfig._norm_optional_path(llama_mmproj_path),
            llama_server_model=llama_server_model,
            llama_model_key=llama_model_key,
            llama_model_display_name=llama_model_display_name,
            llama_model_alias=llama_model_alias,
            llama_model_family=llama_model_family,
        )

    def validate(self, allow_unresolved_model_paths: bool = False) -> None:
        required_strings: list[tuple[str, str]] = [
            ("llama_server_model", self.llama_server_model),
            ("llama_model_key", self.llama_model_key),
            ("llama_model_display_name", self.llama_model_display_name),
            ("llama_model_alias", self.llama_model_alias),
            ("llama_model_family", self.llama_model_family),
        ]
        for field_name, value in required_strings:
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        for field_name, value in [
            ("hf_repo_id", self.hf_repo_id),
            ("hf_filename", self.hf_filename),
            ("hf_revision", self.hf_revision),
            ("hf_mmproj_filename", self.hf_mmproj_filename),
        ]:
            if value is not None and not value.strip():
                raise ValueError(f"{field_name} must be non-empty when provided")

        hf_source = self.hf_repo_id is not None and self.hf_filename is not None
        local_source = self.llama_gguf_path is not None
        if not allow_unresolved_model_paths and not (hf_source or local_source):
            raise ValueError(
                "Model source is required: provide llama_gguf_path or both hf_repo_id and hf_filename"
            )

        if self.llama_gguf_path is not None:
            if not self.llama_gguf_path.exists():
                raise ValueError(f"llama_gguf_path does not exist: {self.llama_gguf_path}")
            if not self.llama_gguf_path.is_file():
                raise ValueError(f"llama_gguf_path is not a file: {self.llama_gguf_path}")

        if self.llama_mmproj_path is not None:
            if not self.llama_mmproj_path.exists():
                raise ValueError(f"llama_mmproj_path does not exist: {self.llama_mmproj_path}")
            if not self.llama_mmproj_path.is_file():
                raise ValueError(f"llama_mmproj_path is not a file: {self.llama_mmproj_path}")

    @staticmethod
    def _norm_optional_path(p: str | Path | None) -> Path | None:
        if p is None:
            return None
        if isinstance(p, str) and not p.strip():
            return None
        return Path(p).expanduser().resolve()

    @staticmethod
    def _norm_optional_text(value: str | None) -> str | None:
        if value is None:
            return None
        if not value.strip():
            return None
        return value
