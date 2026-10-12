"""M2: Hybrid Search."""
from __future__ import annotations

import re
from types import SimpleNamespace
from rank_bm25 import BM25Okapi


class HybridSearch:
    def __init__(self):
        self.chunks = []
        self.bm25 = None

    def _tokenize(self, text: str) -> list[str]:
        return [w.lower() for w in re.findall(r"\w+", text)]

    def index(self, chunks: list[dict]):
        self.chunks = list(chunks)
        tokenized_corpus = [self._tokenize(c["text"]) for c in self.chunks]
        if tokenized_corpus:
            self.bm25 = BM25Okapi(tokenized_corpus)

    def search(self, question: str) -> list:
        if not self.chunks or self.bm25 is None:
            return []
        tokenized_query = self._tokenize(question)
        scores = self.bm25.get_scores(tokenized_query)
        ranked_indices = sorted(range(len(scores)), key=lambda i: scores[i], reverse=True)
        results = []
        for idx in ranked_indices[:20]:
            chunk = self.chunks[idx]
            results.append(SimpleNamespace(
                text=chunk["text"],
                score=float(scores[idx]),
                metadata=chunk["metadata"],
            ))
        return results

