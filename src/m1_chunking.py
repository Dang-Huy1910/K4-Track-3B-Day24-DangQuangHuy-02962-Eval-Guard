"""M1: Document loading and hierarchical chunking."""
from __future__ import annotations

import os
from pathlib import Path
from types import SimpleNamespace

from config import DATA_DIR, HIERARCHICAL_PARENT_SIZE, HIERARCHICAL_CHILD_SIZE


def load_documents() -> list[dict]:
    """Load text documents from DATA_DIR."""
    data_path = Path(DATA_DIR)
    docs = []
    if not data_path.exists():
        return docs

    for file_path in sorted(data_path.glob("*")):
        if file_path.suffix.lower() == ".md":
            try:
                content = file_path.read_text(encoding="utf-8")
                docs.append({
                    "text": content,
                    "metadata": {"source": file_path.name, "file_path": str(file_path)},
                })
            except Exception:
                pass
        elif file_path.suffix.lower() == ".pdf":
            try:
                import pypdf
                reader = pypdf.PdfReader(str(file_path))
                text_parts = [page.extract_text() or "" for page in reader.pages]
                full_text = "\n\n".join(text_parts).strip()
                if full_text:
                    docs.append({
                        "text": full_text,
                        "metadata": {"source": file_path.name, "file_path": str(file_path)},
                    })
            except Exception:
                pass
    return docs


def chunk_hierarchical(text: str, metadata: dict | None = None) -> tuple[list, list]:
    """Chunk text into parent and child chunks."""
    meta = dict(metadata or {})
    parent_size = HIERARCHICAL_PARENT_SIZE
    child_size = HIERARCHICAL_CHILD_SIZE

    parents = []
    children = []

    step_parent = parent_size
    step_child = child_size

    parent_idx = 0
    for p_start in range(0, max(1, len(text)), step_parent):
        p_text = text[p_start : p_start + parent_size].strip()
        if not p_text:
            continue
        p_id = f"p_{meta.get('source', 'doc')}_{parent_idx}"
        parents.append(SimpleNamespace(id=p_id, text=p_text, metadata=meta))

        # Create child chunks
        for c_start in range(0, max(1, len(p_text)), step_child):
            c_text = p_text[c_start : c_start + child_size].strip()
            if not c_text:
                continue
            children.append(SimpleNamespace(
                text=c_text,
                metadata=meta,
                parent_id=p_id,
            ))
        parent_idx += 1

    return parents, children

