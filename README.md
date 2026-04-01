# AutoRAGsearch

An autonomous RAG retrieval pipeline optimizer that systematically searches for the best retrieval configuration using **zero LLM API calls**. It maximizes retrieval quality on a QA benchmark through a structured experiment loop — every evaluation runs locally and is completely free.

---

## What It Does

AutoRAGsearch treats RAG pipeline optimization as a search problem. It runs experiments across three phases — chunking strategy, retrieval method, and reranking — measuring each configuration against a composite retrieval score:

```
retrieval_score = 0.50 × Recall@k + 0.50 × NDCG@k
```

After **20 experiments on the NQ (Natural Questions) subset**, the pipeline improved from a baseline of **0.9472 → 0.9867** (+4.2%), with all improvement coming from the reranking phase.

### Best Configuration Found

| Parameter | Value |
|---|---|
| Chunking | Fixed, 512 tokens, 50-token overlap |
| Embedding model | `all-MiniLM-L6-v2` |
| Retrieval | Dense (ChromaDB cosine similarity) |
| Candidate pool | `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Final output | `top_n = 5` |

The key finding: a **"retrieve more, rerank fewer"** strategy — expand the dense retrieval pool to 50 candidates, then use a cross-encoder to rerank down to the final 5 — consistently outperforms all alternatives.

---

## Repository Structure

```
AutoRAGsearch/
├── rag_pipeline.py          # The only file modified during optimization
├── evaluate.py              # Evaluation harness (do not modify)
├── components/
│   ├── chunkers.py          # Fixed, recursive, sentence chunking
│   ├── embedders.py         # sentence-transformers wrapper
│   ├── retrievers.py        # BM25, Dense (ChromaDB), Hybrid (RRF)
│   └── rerankers.py         # Cross-encoder reranker + passthrough
├── utils/
│   ├── data_loader.py       # Loads QA + corpus parquet files
│   └── classical_metrics.py # Recall@k, NDCG@k, MRR, MAP, Precision, Hit Rate
├── data/
│   ├── nq_subset/           # Natural Questions: qa.parquet + corpus.parquet
│   └── hotpotqa_subset/     # HotpotQA: qa.parquet + corpus.parquet
├── results/
│   ├── results.tsv          # Full experiment log (all 20 runs)
│   ├── experiment_strategies.md  # Strategy + outcome for every experiment
│   ├── best_config.json     # Winning configuration and its metrics
│   └── final_report.md      # Full analysis and findings
└── chroma_db/               # Persisted ChromaDB vector index (auto-built)
```

---

## How to Run

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Run the evaluation

```bash
python evaluate.py
```

This loads the NQ subset, runs the pipeline configured in `rag_pipeline.py`, and prints a full metrics report. The ChromaDB index is built on first run and cached — subsequent runs with the same chunking config skip re-indexing.

To evaluate on HotpotQA instead:

```bash
python evaluate.py --data-dir data/hotpotqa_subset
```

### 3. Change the pipeline configuration

Open `rag_pipeline.py` and modify the parameters at the top:

```python
CHUNK_METHOD = "fixed"       # "fixed", "recursive", "sentence"
CHUNK_SIZE = 512
CHUNK_OVERLAP = 50
RETRIEVAL_METHOD = "dense"   # "bm25", "dense", "hybrid"
TOP_K = 50
USE_RERANKER = True
RERANKER_MODEL = "cross-encoder/ms-marco-MiniLM-L-6-v2"
RERANK_TOP_N = 5
```

Then re-run `python evaluate.py`. If chunking parameters change, the index is automatically rebuilt.

> **Note:** The embedding model (`all-MiniLM-L6-v2`) and ChromaDB distance metric (cosine) are fixed and should not be changed.

### 4. Run the optimization loop manually

Follow the protocol in `CLAUDE.md`:
1. Write your hypothesis in `results/experiment_strategies.md`
2. Edit `rag_pipeline.py`
3. Run `python evaluate.py`
4. If score improves: `git add -A && git commit -m "improvement: <description> | score: <score>"`
5. If not: `git checkout -- rag_pipeline.py`
6. Log the result in `results/results.tsv`

---

## Results Summary

| Experiment | Change | Score | Delta |
|---|---|---|---|
| Baseline | Dense, top_k=5, no reranker | 0.9472 | — |
| Exp 7 | Added cross-encoder reranker | 0.9621 | +0.0149 |
| Exp 8 | top_k=10 → rerank to top_n=5 | 0.9710 | +0.0089 |
| Exp 9 | top_k=20 → rerank to top_n=5 | 0.9776 | +0.0066 |
| Exp 10 | top_k=30 → rerank to top_n=5 | 0.9834 | +0.0058 |
| **Exp 11** | **top_k=50 → rerank to top_n=5** | **0.9867** | **+0.0033** |

All 20 experiments and their full strategies are documented in [`results/experiment_strategies.md`](results/experiment_strategies.md). A complete analysis is in [`results/final_report.md`](results/final_report.md).

---

## Potential Improvements

The experiments were run on CPU, which limited how far the pool size (`top_k`) could be pushed within a 30-minute wall-clock budget. The following directions were identified as most promising:

- **GPU acceleration** — L-6-v2 reranking 50 pairs × 300 queries took 80 minutes on CPU. On GPU, `top_k=100–200` becomes feasible, potentially recovering the 2 remaining hard-miss queries (0.67%).
- **Stronger embedding model** — Replacing `all-MiniLM-L6-v2` with `bge-base-en-v1.5` or `all-mpnet-base-v2` may shift the dense retrieval ceiling, which capped recall at 0.9933.
- **Larger cross-encoders** — `cross-encoder/ms-marco-MiniLM-L-12-v2` OOM'd at `top_k=50` on CPU but would be viable on GPU, potentially improving NDCG beyond 0.9801.
- **Query expansion (no LLM)** — Pseudo-relevance feedback using BM25 (augmenting the query with key terms from the top-1 dense result) could help the 2 unfindable queries without any API calls.
- **Longer documents / real chunking** — The NQ corpus documents all fit within 512 tokens, so chunking had zero effect. On a corpus with longer documents, chunking strategy would become a meaningful optimization dimension.

---

## Metrics

| Metric | Role | Description |
|---|---|---|
| `Recall@k` | Primary (50%) | Fraction of relevant docs found in top-k |
| `NDCG@k` | Primary (50%) | Ranking quality — rewards relevant docs at higher positions |
| `Precision@k` | Diagnostic | Fraction of retrieved docs that are relevant |
| `MRR` | Diagnostic | How high is the first relevant doc ranked? |
| `MAP@k` | Diagnostic | Mean Average Precision across all relevant docs |
| `Hit Rate@k` | Diagnostic | Did retrieval find at least one relevant doc? |
