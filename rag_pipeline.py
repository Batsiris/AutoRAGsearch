"""RAG pipeline — the ONLY file the optimization agent may edit.

Configuration variables at the top control all pipeline parameters.
The agent modifies these values between experiments.
"""

import hashlib
import json
import os
import sys

# === PIPELINE CONFIGURATION ===
# The agent will modify these values during optimization.
CHUNK_METHOD = "fixed"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
EMBEDDING_MODEL = "all-MiniLM-L6-v2"
RETRIEVAL_METHOD = "dense"   # "bm25", "dense", or "hybrid"
TOP_K = 50
USE_RERANKER = True
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 10

# Vector DB settings
CHROMA_PERSIST_DIR = "./chroma_db"
CHROMA_COLLECTION_NAME = "autoragsearch"
DISTANCE_METRIC = "cosine"  # fixed — do not change

# === END CONFIGURATION ===

def _get_data_dir_from_argv() -> str:
    """Mirror evaluate.py's --data-dir argument without editing the harness."""
    default_dir = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nq_subset")
    if "--data-dir" not in sys.argv:
        return default_dir

    idx = sys.argv.index("--data-dir")
    if idx + 1 >= len(sys.argv):
        return default_dir

    data_dir = sys.argv[idx + 1]
    if os.path.isabs(data_dir):
        return data_dir
    return os.path.abspath(os.path.join(os.getcwd(), data_dir))


DATA_DIR = _get_data_dir_from_argv()

_pipeline = None


def get_config() -> dict:
    """Return current pipeline configuration as a dict."""
    return {
        "chunk_method": CHUNK_METHOD,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "retrieval_method": RETRIEVAL_METHOD,
        "top_k": TOP_K,
        "use_reranker": USE_RERANKER,
        "reranker_model": RERANKER_MODEL,
        "rerank_top_n": RERANK_TOP_N,
        "chroma_persist_dir": CHROMA_PERSIST_DIR,
        "chroma_collection_name": CHROMA_COLLECTION_NAME,
        "distance_metric": DISTANCE_METRIC,
        "data_dir": DATA_DIR,
    }


def _needs_reindex(chunks, config_hash_path=".chroma_config_hash"):
    """Return True if chunking/embedding config has changed since last run."""
    config_str = json.dumps({
        "chunk_method": CHUNK_METHOD,
        "chunk_size": CHUNK_SIZE,
        "chunk_overlap": CHUNK_OVERLAP,
        "embedding_model": EMBEDDING_MODEL,
        "distance_metric": DISTANCE_METRIC,
        "data_dir": DATA_DIR,
        "num_chunks": len(chunks),
    }, sort_keys=True)
    new_hash = hashlib.md5(config_str.encode()).hexdigest()

    old_hash = None
    if os.path.exists(config_hash_path):
        with open(config_hash_path) as f:
            old_hash = f.read().strip()

    if new_hash != old_hash:
        with open(config_hash_path, "w") as f:
            f.write(new_hash)
        return True
    return False


def build_pipeline():
    """Build and return a pipeline closure over the corpus index."""
    from utils.data_loader import load_dataset
    from components.chunkers import chunk_documents
    from components.embedders import Embedder
    from components.retrievers import BM25Retriever, DenseRetriever, HybridRetriever
    from components.rerankers import Reranker, NoReranker

    _, corpus_df = load_dataset(DATA_DIR)
    documents = corpus_df.to_dict("records")

    # Chunk
    chunks = chunk_documents(
        documents,
        method=CHUNK_METHOD,
        chunk_size=CHUNK_SIZE,
        chunk_overlap=CHUNK_OVERLAP,
    )

    # Build retriever
    embedder = Embedder(EMBEDDING_MODEL)
    if RETRIEVAL_METHOD == "bm25":
        retriever = BM25Retriever()
        retriever.index(chunks)
    elif RETRIEVAL_METHOD == "dense":
        retriever = DenseRetriever(
            embedder,
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=CHROMA_COLLECTION_NAME,
            distance_metric=DISTANCE_METRIC,
        )
        if _needs_reindex(chunks):
            retriever.index(chunks)
        else:
            print("ChromaDB index up-to-date, skipping re-indexing.")
    elif RETRIEVAL_METHOD == "hybrid":
        retriever = HybridRetriever(
            embedder,
            persist_directory=CHROMA_PERSIST_DIR,
            collection_name=CHROMA_COLLECTION_NAME,
            distance_metric=DISTANCE_METRIC,
        )
        if _needs_reindex(chunks):
            retriever.index(chunks)
        else:
            print("ChromaDB index up-to-date, skipping re-indexing.")
    else:
        raise ValueError(f"Unknown retrieval method: {RETRIEVAL_METHOD}")

    # Build reranker
    if USE_RERANKER:
        reranker = Reranker(RERANKER_MODEL)
    else:
        reranker = NoReranker()

    def _run(question: str):
        retrieved = retriever.retrieve(question, top_k=TOP_K)
        final_chunks = reranker.rerank(question, retrieved, top_n=RERANK_TOP_N)
        contexts = [c["text"] for c in final_chunks]
        retrieved_doc_ids = [c["doc_id"] for c in final_chunks]
        return contexts, retrieved_doc_ids

    return _run


# Build pipeline once at import time
_pipeline = build_pipeline()


def run_pipeline(question: str):
    """Run the RAG pipeline for a single question.

    Returns:
        (contexts: list[str], retrieved_doc_ids: list[str])
    """
    return _pipeline(question)
