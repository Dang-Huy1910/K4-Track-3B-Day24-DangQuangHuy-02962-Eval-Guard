"""M3: Cross-Encoder Reranker."""
from __future__ import annotations

from types import SimpleNamespace


class CrossEncoderReranker:
    def __init__(self):
        pass

    def rerank(self, question: str, docs: list[dict], top_k: int = 3) -> list:
        """Rerank search documents and return top_k."""
        return [SimpleNamespace(text=d["text"]) for d in docs[:top_k]]

