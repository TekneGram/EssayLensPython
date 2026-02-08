from __future__ import annotations
from dataclasses import dataclass

@dataclass(frozen=True, slots=True)
class GedConfig:
    model_name: str
    batch_size: int = 16

    def validate(self) -> None:
        if not isinstance(self.model_name, str) or not self.model_name.strip():
            raise ValueError("GedConfig.model_name must be a non-empty string.")
        
        if not isinstance(self.batch_size, int):
            raise ValueError("GedConfig.batch_size must be an int.")
        
        # Choose safe bounds
        if self.batch_size < 1:
            raise ValueError("GedConfig.batch_size must be >= 1")
        if self.batch_size > 256:
            raise ValueError("GedConfig.batch_size is unusually large (>256)")
        
    @staticmethod
    def from_strings(
        model_name: str,
        batch_size: str | int = 16
    ) -> "GedConfig":
        bs = int(batch_size)
        cfg = GedConfig(model_name=model_name, batch_size=bs)
        cfg.validate()
        return cfg