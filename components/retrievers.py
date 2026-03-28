"""Retriever classes: BM25, Dense (cosine), and Hybrid (RRF)."""

import numpy as np
from typing import List, Dict, Any


class BM25Retriever:
    """Lexical BM25 retriever using rank_bm25."""

    def __init__(self):
        self.chunks = []
        self.bm25 = None

    def index(self, chunks: List[Dict[str, Any]]):
        from rank_bm25 import BM25Okapi
        self.chunks = chunks
        tokenized = [chunk["text"].lower().split() for chunk in chunks]
        self.bm25 = BM25Okapi(tokenized)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        tokens = query.lower().split()
        scores = self.bm25.get_scores(tokens)
        top_indices = np.argsort(scores)[::-1][:top_k]
        results = []
        for idx in top_indices:
            chunk = dict(self.chunks[idx])
            chunk["score"] = float(scores[idx])
            results.append(chunk)
        return results


class DenseRetriever:
    """Dense retriever backed by a ChromaDB persistent vector database."""

    def __init__(self, embedder=None, persist_directory="./chroma_db",
                 collection_name="autoragsearch", distance_metric="cosine"):
        from components.embedders import Embedder
        import chromadb
        self.embedder = embedder or Embedder()
        self.persist_directory = persist_directory
        self.collection_name = collection_name
        self.distance_metric = distance_metric
        self.client = chromadb.PersistentClient(path=persist_directory)
        self.collection = self._get_or_create_collection()

    def _get_or_create_collection(self):
        import chromadb
        return self.client.get_or_create_collection(
            name=self.collection_name,
            metadata={"hnsw:space": self.distance_metric},
        )

    def index(self, chunks: List[Dict[str, Any]]):
        try:
            self.client.delete_collection(self.collection_name)
        except Exception:
            pass
        self.collection = self._get_or_create_collection()

        batch_size = 500
        total = len(chunks)
        print(f"Indexing {total} chunks into ChromaDB...")

        for i in range(0, total, batch_size):
            batch = chunks[i:i + batch_size]
            texts = [c["text"] for c in batch]
            ids = [c["chunk_id"] for c in batch]
            metadatas = [{"doc_id": c["doc_id"], **c.get("metadata", {})} for c in batch]
            embeddings = self.embedder.embed(texts).tolist()
            self.collection.add(
                ids=ids,
                embeddings=embeddings,
                documents=texts,
                metadatas=metadatas,
            )
            print(f"  Indexed {min(i + batch_size, total)}/{total}")

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        query_embedding = self.embedder.embed_query(query).tolist()
        results = self.collection.query(
            query_embeddings=[query_embedding],
            n_results=min(top_k, self.collection.count()),
            include=["documents", "metadatas", "distances"],
        )
        retrieved = []
        for j in range(len(results["ids"][0])):
            score = (1 - results["distances"][0][j]
                     if self.distance_metric == "cosine"
                     else results["distances"][0][j])
            retrieved.append({
                "chunk_id": results["ids"][0][j],
                "text": results["documents"][0][j],
                "doc_id": results["metadatas"][0][j].get("doc_id", ""),
                "score": score,
                "metadata": results["metadatas"][0][j],
            })
        return retrieved


class HybridRetriever:
    """Hybrid BM25 + Dense retriever using Reciprocal Rank Fusion."""

    def __init__(self, embedder=None, bm25_weight: float = 0.5, rrf_k: int = 60,
                 persist_directory="./chroma_db", collection_name="autoragsearch",
                 distance_metric="cosine"):
        from components.embedders import Embedder
        self.bm25 = BM25Retriever()
        self.dense = DenseRetriever(
            embedder or Embedder(),
            persist_directory=persist_directory,
            collection_name=collection_name,
            distance_metric=distance_metric,
        )
        self.bm25_weight = bm25_weight
        self.dense_weight = 1.0 - bm25_weight
        self.rrf_k = rrf_k
        self.chunks = []

    def index(self, chunks: List[Dict[str, Any]]):
        self.chunks = chunks
        self.bm25.index(chunks)
        self.dense.index(chunks)

    def retrieve(self, query: str, top_k: int = 5) -> List[Dict[str, Any]]:
        # Retrieve more candidates for fusion
        fetch_k = min(top_k * 4, len(self.chunks))
        bm25_results = self.bm25.retrieve(query, top_k=fetch_k)
        dense_results = self.dense.retrieve(query, top_k=fetch_k)

        # Build chunk_id -> chunk map
        chunk_map: Dict[str, Dict] = {}
        for r in bm25_results + dense_results:
            chunk_map[r["chunk_id"]] = r

        # RRF scoring
        rrf_scores: Dict[str, float] = {}
        for rank, r in enumerate(bm25_results):
            cid = r["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + self.bm25_weight / (self.rrf_k + rank + 1)
        for rank, r in enumerate(dense_results):
            cid = r["chunk_id"]
            rrf_scores[cid] = rrf_scores.get(cid, 0) + self.dense_weight / (self.rrf_k + rank + 1)

        sorted_ids = sorted(rrf_scores, key=lambda x: rrf_scores[x], reverse=True)[:top_k]
        results = []
        for cid in sorted_ids:
            chunk = dict(chunk_map[cid])
            chunk["score"] = rrf_scores[cid]
            results.append(chunk)
        return results
