"""Minimal semantic search over the ingested corpus.

This is a *verification* harness, not a product feature (retrieval is out of
scope — see PROJECT.md). It embeds a query with the same provider used at ingest
and ranks corpus chunks by cosine similarity, resolving each hit back to its
source document's title (provenance). Useful to confirm the corpus is real and
queryable, and to demo "trace an answer back to the source".
"""

from __future__ import annotations

from dataclasses import dataclass

from .orchestrator import Deps
from .providers import bytes_to_vector, get_embedder


@dataclass
class Hit:
    score: float
    path: str
    title: str
    region: str
    snippet: str


def _cosine(mat, q):
    import numpy as np

    m = np.asarray(mat, dtype=np.float32)
    v = np.asarray(q, dtype=np.float32)
    m /= (np.linalg.norm(m, axis=1, keepdims=True) + 1e-9)
    v /= (np.linalg.norm(v) + 1e-9)
    return m @ v


def search(deps: Deps, query: str, k: int = 5) -> list[Hit]:
    chunks = [c for c in deps.corpus.all_chunks() if c.embedding]
    if not chunks:
        return []
    import numpy as np

    sims = _cosine([bytes_to_vector(c.embedding) for c in chunks],
                   get_embedder().embed([query])[0])
    order = np.argsort(-sims)[:k]

    titles: dict[str, str] = {}
    hits: list[Hit] = []
    for i in order:
        c = chunks[int(i)]
        if c.path not in titles:
            doc = deps.documents.get(c.path)
            titles[c.path] = (doc.meta.get("title") if doc and doc.meta else None) or c.path
        hits.append(Hit(score=float(sims[int(i)]), path=c.path, title=titles[c.path],
                        region=c.region, snippet=" ".join(c.content.split())[:200]))
    return hits
