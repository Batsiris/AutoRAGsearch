"""Sentence-transformer embedder for dense retrieval."""

import numpy as np
from typing import List


class Embedder:
    """Wraps a sentence-transformers model for embedding texts."""

    def __init__(self, model_name: str = "all-MiniLM-L6-v2"):
        from sentence_transformers import SentenceTransformer
        self.model_name = model_name
        self.model = SentenceTransformer(model_name)

    def embed(self, texts: List[str]) -> np.ndarray:
        """Embed a list of texts, returning an (N, D) array."""
        return self.model.encode(texts, convert_to_numpy=True, show_progress_bar=False)

    def embed_query(self, query: str) -> np.ndarray:
        """Embed a single query string, returning a (D,) array."""
        return self.model.encode([query], convert_to_numpy=True, show_progress_bar=False)[0]
