from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Optional

import torch
from transformers import AutoTokenizer, AutoModelForTokenClassification

from nlp.ged.ged_types import GedSentenceResult


class GedBertDetector:
    """
    Fast sentence-level GED
    - Marks a sentence as error if ANY non-special token is predicted as ERROR
    - Avoids spaCy alignment
    """

    def __init__(
            self,
            model_name: str,
            device: Optional[str] = None,
    ) -> None:
        self.model_name = model_name

        if device is None:
            device = "cuda" if torch.cuda.is_available() else "cpu"
        self.device = torch.device(device)

        self.tokenizer = AutoTokenizer.from_pretrained(self.model_name)
        self.model = AutoModelForTokenClassification.from_pretrained(self.model_name)
        self.model.to(self.device)
        self.model.eval()

        self.ERROR_ID = 1

    @torch.no_grad()
    def score_sentences(self, sentences: List[str], batch_size: int = 8) -> List[GedSentenceResult]:

        results: List[GedSentenceResult] = []

        for i in range(0, len(sentences), batch_size):
            batch = sentences[i : i + batch_size]

            enc = self.tokenizer(
                batch,
                return_tensors="pt",
                padding=True,
                truncation=True
            )

            enc = {k: v.to(self.device) for k, v in enc.items()}
            outputs = self.model(**enc)
            preds = torch.argmax(outputs.logits, dim=-1)
            attn = enc["attention_mask"]
            input_ids = enc["input_ids"]
            special_ids = set(self.tokenizer.all_special_ids)

            for b_idx, sent in enumerate(batch):
                has_error = False
                error_tokens: List[str] = []
                for t_idx in range(preds.shape[1]):
                    if attn[b_idx, t_idx].item() == 0:
                        continue
                    token_id = int(input_ids[b_idx, t_idx].item())
                    if token_id in special_ids:
                        continue
                    if int(preds[b_idx, t_idx].item()) == self.ERROR_ID:
                        has_error = True
                        token = self.tokenizer.convert_ids_to_tokens([token_id])[0]
                        error_tokens.append(token)
                results.append(
                    GedSentenceResult(
                        sentence=sent,
                        has_error=has_error,
                        error_tokens=error_tokens,
                    )
                )
        return results
        
