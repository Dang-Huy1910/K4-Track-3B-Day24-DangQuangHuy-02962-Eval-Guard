"""M5: Chunk enrichment."""
from __future__ import annotations

from types import SimpleNamespace


def enrich_chunks(chunks: list[dict]) -> list:
    """Enrich chunks or return empty list as fallback to use raw chunks."""
    return [
        SimpleNamespace(
            enriched_text=chunk["text"],
            auto_metadata={"enriched": True},
        )
        for chunk in chunks
    ]

