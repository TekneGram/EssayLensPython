from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path


@dataclass(frozen=True, slots=True)
class LlmServerConfig:
    llama_backend: str
    llama_server_path: Path
    llama_server_url: str
    llama_n_ctx: int
    llama_host: str
    llama_port: int
    llama_n_threads: int | None
    llama_n_gpu_layers: int | None
    llama_n_batch: int | None
    llama_n_parallel: int | None
    llama_seed: int | None
    llama_rope_freq_base: float | None
    llama_rope_freq_scale: float | None
    llama_use_jinja: bool
    llama_cache_prompt: bool
    llama_flash_attn: bool

    @staticmethod
    def from_strings(
        llama_backend: str,
        llama_server_path: str | Path,
        llama_server_url: str,
        llama_n_ctx: int,
        llama_host: str,
        llama_port: int,
        llama_n_threads: int | None,
        llama_n_gpu_layers: int | None,
        llama_n_batch: int | None,
        llama_n_parallel: int | None,
        llama_seed: int | None,
        llama_rope_freq_base: float | None,
        llama_rope_freq_scale: float | None,
        llama_use_jinja: bool,
        llama_cache_prompt: bool,
        llama_flash_attn: bool,
    ) -> "LlmServerConfig":
        return LlmServerConfig(
            llama_backend=llama_backend,
            llama_server_path=LlmServerConfig._norm(llama_server_path),
            llama_server_url=llama_server_url,
            llama_n_ctx=llama_n_ctx,
            llama_host=llama_host,
            llama_port=llama_port,
            llama_n_threads=llama_n_threads,
            llama_n_gpu_layers=llama_n_gpu_layers,
            llama_n_batch=llama_n_batch,
            llama_n_parallel=llama_n_parallel,
            llama_seed=llama_seed,
            llama_rope_freq_base=llama_rope_freq_base,
            llama_rope_freq_scale=llama_rope_freq_scale,
            llama_use_jinja=llama_use_jinja,
            llama_cache_prompt=llama_cache_prompt,
            llama_flash_attn=llama_flash_attn,
        )

    def validate(self) -> None:
        required_strings: list[tuple[str, str]] = [
            ("llama_backend", self.llama_backend),
            ("llama_server_url", self.llama_server_url),
            ("llama_host", self.llama_host),
        ]
        for field_name, value in required_strings:
            if not value or not value.strip():
                raise ValueError(f"{field_name} must be a non-empty string")

        if self.llama_backend != "server":
            raise ValueError(f"llama_backend must be 'server', got: {self.llama_backend}")

        if not self.llama_server_path.exists():
            raise ValueError(f"llama_server_path does not exist: {self.llama_server_path}")
        if not self.llama_server_path.is_file():
            raise ValueError(f"llama_server_path is not a file: {self.llama_server_path}")

        if self.llama_n_ctx <= 0:
            raise ValueError("llama_n_ctx must be > 0")

        if not (1 <= self.llama_port <= 65535):
            raise ValueError("llama_port must be between 1 and 65535")

        if self.llama_n_threads is not None and self.llama_n_threads <= 0:
            raise ValueError("llama_n_threads must be > 0 when provided")
        if self.llama_n_gpu_layers is not None and self.llama_n_gpu_layers < 0:
            raise ValueError("llama_n_gpu_layers must be >= 0 when provided")
        if self.llama_n_batch is not None and self.llama_n_batch <= 0:
            raise ValueError("llama_n_batch must be > 0 when provided")
        if self.llama_n_parallel is not None and self.llama_n_parallel <= 0:
            raise ValueError("llama_n_parallel must be > 0 when provided")
        if self.llama_rope_freq_base is not None and self.llama_rope_freq_base <= 0:
            raise ValueError("llama_rope_freq_base must be > 0 when provided")
        if self.llama_rope_freq_scale is not None and self.llama_rope_freq_scale <= 0:
            raise ValueError("llama_rope_freq_scale must be > 0 when provided")

    @staticmethod
    def _norm(p: str | Path) -> Path:
        return Path(p).expanduser().resolve()
