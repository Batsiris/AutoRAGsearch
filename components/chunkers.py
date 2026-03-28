"""Chunking strategies for RAG pipeline documents."""

import re
import uuid
from typing import List, Dict, Any


def chunk_documents(documents: List[Dict[str, Any]], method: str, **kwargs) -> List[Dict[str, Any]]:
    """Chunk a list of documents using the specified method.

    Args:
        documents: List of dicts with keys: doc_id, text, metadata.
        method: One of "fixed", "recursive", "sentence".
        **kwargs: Method-specific parameters.

    Returns:
        List of chunk dicts with keys: chunk_id, text, doc_id, metadata.
    """
    if method == "fixed":
        return _fixed_chunking(documents, **kwargs)
    elif method == "recursive":
        return _recursive_chunking(documents, **kwargs)
    elif method == "sentence":
        return _sentence_chunking(documents, **kwargs)
    else:
        raise ValueError(f"Unknown chunking method: {method}")


def _fixed_chunking(documents: List[Dict], chunk_size: int = 512, chunk_overlap: int = 50) -> List[Dict]:
    """Fixed-size token-approximate chunking (splits on whitespace tokens)."""
    chunks = []
    for doc in documents:
        tokens = doc["text"].split()
        start = 0
        while start < len(tokens):
            end = min(start + chunk_size, len(tokens))
            chunk_text = " ".join(tokens[start:end])
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "text": chunk_text,
                "doc_id": doc["doc_id"],
                "metadata": dict(doc.get("metadata", {})),
            })
            if end == len(tokens):
                break
            start += chunk_size - chunk_overlap
    return chunks


def _recursive_chunking(documents: List[Dict], chunk_size: int = 512, chunk_overlap: int = 50) -> List[Dict]:
    """Recursive character splitting (LangChain-style hierarchical splitting)."""
    try:
        from langchain.text_splitter import RecursiveCharacterTextSplitter
    except ImportError:
        from langchain_text_splitters import RecursiveCharacterTextSplitter

    splitter = RecursiveCharacterTextSplitter(
        chunk_size=chunk_size * 5,  # approximate chars from tokens
        chunk_overlap=chunk_overlap * 5,
        separators=["\n\n", "\n", ". ", " ", ""],
    )
    chunks = []
    for doc in documents:
        texts = splitter.split_text(doc["text"])
        for text in texts:
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "text": text,
                "doc_id": doc["doc_id"],
                "metadata": dict(doc.get("metadata", {})),
            })
    return chunks


def _sentence_chunking(documents: List[Dict], sentences_per_chunk: int = 5, overlap_sentences: int = 1) -> List[Dict]:
    """Split on sentence boundaries, grouping N sentences per chunk."""
    sentence_pattern = re.compile(r'(?<=[.!?])\s+')
    chunks = []
    for doc in documents:
        sentences = sentence_pattern.split(doc["text"].strip())
        sentences = [s.strip() for s in sentences if s.strip()]
        start = 0
        while start < len(sentences):
            end = min(start + sentences_per_chunk, len(sentences))
            chunk_text = " ".join(sentences[start:end])
            chunks.append({
                "chunk_id": str(uuid.uuid4()),
                "text": chunk_text,
                "doc_id": doc["doc_id"],
                "metadata": dict(doc.get("metadata", {})),
            })
            if end == len(sentences):
                break
            start += sentences_per_chunk - overlap_sentences
    return chunks
