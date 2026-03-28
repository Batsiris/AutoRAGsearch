"""Reranker classes for second-stage retrieval refinement."""

from typing import List, Dict, Any


class Reranker:
    """Cross-encoder reranker using sentence-transformers."""

    def __init__(self, model_name: str = "cross-encoder/ms-marco-MiniLM-L-6-v2"):
        from sentence_transformers import CrossEncoder
        self.model_name = model_name
        self.model = CrossEncoder(model_name)

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        """Rerank chunks using cross-encoder scores, returning top_n."""
        if not chunks:
            return chunks
        pairs = [(query, chunk["text"]) for chunk in chunks]
        scores = self.model.predict(pairs)
        scored = sorted(zip(scores, chunks), key=lambda x: x[0], reverse=True)
        return [chunk for _, chunk in scored[:top_n]]


class NoReranker:
    """Passthrough reranker — returns chunks unchanged (truncated to top_n)."""

    def rerank(self, query: str, chunks: List[Dict[str, Any]], top_n: int = 3) -> List[Dict[str, Any]]:
        return chunks[:top_n]
