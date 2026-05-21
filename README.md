# AutoRAGsearch

An autonomous research agent that optimizes a RAG retrieval pipeline without any human in the loop — inspired by [Andrej Karpathy's Autoresearch](https://x.com/karpathy/status/1921368644069576888) concept. A single prompt launches Claude Code into a self-directed experiment loop that systematically searches for the best retrieval configuration, using **zero LLM API calls** during optimization.

---

## Concept

The idea is simple: give an AI coding agent a well-defined optimization objective, a structured experiment protocol, and complete freedom to explore the search space — then let it run.

**How it works:**

1. Claude Code is invoked with an initial prompt pointing it to `CLAUDE.md`
2. `CLAUDE.md` defines the optimization target, the search space, the experiment protocol, and the convergence criterion — the full loop the agent must execute
3. The agent autonomously runs experiments: forms a hypothesis, edits `rag_pipeline.py`, evaluates, interprets results, commits improvements, and decides what to try next
4. No human input is needed between experiments — the agent reads its own experiment history, diagnoses weaknesses in the current metrics, and navigates the search space accordingly
5. The loop terminates when the convergence criterion is met (no improvement in 10 consecutive experiments) or after a set number of experiments

Every evaluation is **purely local** — no LLM API calls, no external services. The optimization signal comes entirely from retrieval metrics computed against a fixed QA benchmark.

---

## What It Achieves

AutoRAGsearch treats RAG pipeline optimization as a structured search problem across three phases:

- **Phase 1 — Chunking:** How documents are split (fixed-size, recursive, sentence-based, overlap tuning)
- **Phase 2 — Retrieval:** How candidates are fetched (BM25, dense, hybrid BM25+Dense via RRF, top_k tuning)
- **Phase 3 — Reranking:** How candidates are re-scored (cross-encoder models, pool size, output size)

The optimization target is:

```
retrieval_score = 0.50 × Recall@k + 0.50 × NDCG@k
```

After **20 fully autonomous experiments on the NQ (Natural Questions) subset**, the agent improved retrieval quality from a baseline of **0.9472 → 0.9867** (+4.2%), with all gains coming from the reranking phase.

### Best Configuration Found

| Parameter | Value |
|---|---|
| Chunking | Fixed, 512 tokens, 50-token overlap |
| Embedding model | `all-MiniLM-L6-v2` (fixed) |
| Retrieval | Dense (ChromaDB cosine similarity) |
| Candidate pool | `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Final output | `top_n = 5` |

The agent discovered that a **"retrieve more, rerank fewer"** strategy — expanding the dense retrieval pool to 50 candidates, then using a cross-encoder to rerank down to 5 — consistently outperformed all alternatives. Full experiment narratives, strategies, and outcomes are in [`results/experiment_strategies.md`](results/experiment_strategies.md).

---

## Repository Structure

```
AutoRAGsearch/
├── CLAUDE.md                # Agent instructions: objective, protocol, search space, loop
├── rag_pipeline.py          # The only file the agent may edit — all pipeline parameters live here
├── evaluate.py              # Evaluation harness — DO NOT MODIFY
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
│   ├── results.tsv          # Full experiment log
│   ├── experiment_strategies.md  # Agent's hypothesis + outcome for every experiment
│   ├── best_config.json     # Winning configuration and its metrics
│   └── final_report.md      # Complete analysis and findings
└── chroma_db/               # Persisted ChromaDB vector index (auto-built)
```

The key design constraint: **`rag_pipeline.py` is the only file the agent may touch.** Everything else — evaluation harness, data, metrics, component implementations — is fixed. This gives the agent a well-bounded action space while keeping the evaluation signal honest.

---

## Running the Agent Yourself

### 1. Install dependencies

```bash
pip install -r requirements.txt
```

### 2. Launch Claude Code and point it at the instructions

```bash
claude
```

Then give it the initial prompt:

```
Read CLAUDE.md carefully and run the optimization loop from the beginning.
```

Claude Code will read `CLAUDE.md`, understand the experiment protocol, and begin autonomously running experiments — editing `rag_pipeline.py`, evaluating, logging results, committing improvements, and iterating until the convergence criterion is met.

### 3. Run the evaluation manually

To evaluate any configuration yourself:

```bash
python evaluate.py
```

To evaluate on HotpotQA:

```bash
python evaluate.py --data-dir data/hotpotqa_subset
```

### 4. Modify the pipeline configuration

Open `rag_pipeline.py` and edit the parameters at the top:

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

Re-run `python evaluate.py`. If chunking parameters change, the ChromaDB index is automatically rebuilt; retrieval-only and reranker-only changes reuse the cached index.

> **Fixed components:** The embedding model (`all-MiniLM-L6-v2`) and ChromaDB distance metric (cosine) cannot be changed — they are part of the evaluation contract defined in `CLAUDE.md`.

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

The agent ran 20 experiments across all three phases. Phase 1 (Chunking) and Phase 2 (Retrieval) contributed 0% of the total gain — the NQ corpus documents all fit within 512 tokens so chunking had no effect, and dense retrieval outperformed BM25/hybrid for semantic questions. All improvement came from Phase 3 (Reranking) through the progressive "retrieve more, rerank fewer" strategy.

Full per-experiment strategies and outcomes: [`results/experiment_strategies.md`](results/experiment_strategies.md)
Complete analysis: [`results/final_report.md`](results/final_report.md)

---

## Potential Improvements

The experiments were run on CPU, which constrained the candidate pool size (`top_k`) to ≤20 for sub-30-minute runs — preventing the agent from re-discovering the best config (top_k=50, committed from a prior longer run) within the session. The following directions were identified as most promising for further gains:

- **GPU acceleration** — Reranking 50 pairs × 300 queries took 80 minutes on CPU. On GPU, `top_k=100–200` becomes feasible in minutes, potentially recovering the 2 remaining hard-miss queries (0.67% of the benchmark).
- **Stronger embedding model** — The `all-MiniLM-L6-v2` model capped dense recall at 0.9933. Replacing it with `bge-base-en-v1.5` or `all-mpnet-base-v2` may raise this ceiling.
- **Larger cross-encoders** — `cross-encoder/ms-marco-MiniLM-L-12-v2` OOM'd at `top_k=50` on CPU but would be viable on GPU, likely pushing NDCG beyond 0.9801.
- **Query expansion (no LLM)** — Pseudo-relevance feedback using BM25 (augmenting queries with key terms from top-1 dense results) could help the 2 unfindable queries without any API calls.
- **Real chunking workloads** — The NQ corpus documents all fit within 512 tokens, so chunking strategy had zero effect here. On a corpus with longer documents, Phase 1 would become a meaningful optimization dimension.
- **Adapt the agent loop** — `CLAUDE.md` defines the convergence criterion, search space, and evaluation protocol. Changing these (e.g., different datasets, new retrieval components, alternative metrics) is all it takes to point the agent at a different optimization problem.

---

## Metrics Reference

| Metric | Role | Description |
|---|---|---|
| `Recall@k` | Primary (50%) | Fraction of relevant docs found in top-k |
| `NDCG@k` | Primary (50%) | Ranking quality — rewards relevant docs at higher positions |
| `Precision@k` | Diagnostic | Fraction of retrieved docs that are relevant |
| `MRR` | Diagnostic | How high is the first relevant doc ranked? |
| `MAP@k` | Diagnostic | Mean Average Precision across all relevant docs |
| `Hit Rate@k` | Diagnostic | Did retrieval find at least one relevant doc? |



## Official AutoRAG Baseline Comparison

To provide a reproducible retrieval baseline, the project-specific HotpotQA subset was also evaluated using the official [AutoRAG](https://github.com/Marker-Inc-Korea/AutoRAG) framework in a retrieval-only setting.

The original subset contained **200 QA examples** and **1992 corpus documents**. Since official AutoRAG expects retrieval ground truth as document IDs, the dataset was converted to the AutoRAG-compatible format. During this conversion, **12 QA examples were removed** because their ground-truth contexts could not be matched to document IDs in the corpus. The final comparable evaluation subset therefore contained **188 QA examples**.

Official AutoRAG was used as a controlled BM25 retrieval baseline, not as a full AutoRAG optimization run. Two BM25 configurations were evaluated:

- **BM25, top_k=5**: main retrieval-only baseline.
- **BM25, top_k=50**: controlled comparison with the proposed agentic RAG system, which also uses `top_k=50`.

The baseline configuration files, conversion script, extra metrics script, and summary results are available in:

```text
experiments/official_autorag_baseline/
Result Summary
1. Official AutoRAG Baseline — BM25, top_k=5
Setting:
  Method: BM25 lexical retrieval
  top_k: 5
  QA examples: 188
  Corpus documents: 1992

Core retrieval metrics:
  Precision:   0.1457
  Recall:      0.7287
  F1:          0.2429
  Full Recall: 72.87%

Ranking-aware metrics:
  MRR:         0.4629
  NDCG@k:      0.5291
  MAP@k:       0.4629
  Hit Rate:    0.7287
2. Official AutoRAG — BM25, top_k=50
Setting:
  Method: BM25 lexical retrieval
  top_k: 50
  QA examples: 188
  Corpus documents: 1992

Core retrieval metrics:
  Precision:   0.0191
  Recall:      0.9574
  F1:          0.0375
  Full Recall: 95.74%

Ranking-aware metrics:
  MRR:         0.4874
  NDCG@k:      0.5964
  MAP@k:       0.4874
  Hit Rate:    0.9574
3. Proposed Agentic RAG — Dense Retrieval + Cross-Encoder Reranker
Setting:
  Method: Dense retrieval + cross-encoder reranking
  Embedding model: all-MiniLM-L6-v2
  Reranker model: cross-encoder/ms-marco-MiniLM-L-6-v2
  top_k: 50
  rerank_top_n: 20
  Best experiment: 4
  Total experiments: 14

Core retrieval metrics:
  Precision@k:     0.0380
  Recall@k:        0.9500
  Retrieval score: 0.9257

Ranking-aware metrics:
  MRR:             0.9596
  NDCG@k:          0.9014
  MAP@k:           0.7765
  Hit Rate@k:      1.0000
Interpretation

The official AutoRAG BM25 baseline with top_k=5 provides a simple retrieval-only reference point. Increasing BM25 to top_k=50 significantly improves recall, from 0.7287 to 0.9574, but also greatly reduces precision, from 0.1457 to 0.0191. This is expected because returning more documents increases the chance of retrieving the correct supporting evidence, but also introduces more irrelevant documents.

Compared with the BM25 top_k=50 baseline, the proposed agentic RAG system achieves almost the same recall, 0.9500 compared to 0.9574, while improving precision from 0.0191 to 0.0380. More importantly, it achieves substantially stronger ranking-aware metrics: MRR = 0.9596, NDCG@k = 0.9014, MAP@k = 0.7765, and Hit Rate@k = 1.0000.

This suggests that the agent-guided refinement process identified a stronger retrieval configuration based on dense retrieval and cross-encoder reranking. The final system does not simply retrieve more documents; it ranks the relevant documents much closer to the top of the retrieved set.

Reproducibility Note

The official AutoRAG baseline results were produced locally on the same project-specific HotpotQA subset used by this project. They are not pre-existing benchmark results from the official AutoRAG repository.
