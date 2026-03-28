# AutoRAGsearch: Autonomous RAG Pipeline Optimization

## Objective
Find the optimal RAG pipeline configuration that maximizes the classical
composite score on the benchmark QA dataset. The composite score is:

  composite = 0.20 * recall_at_k
            + 0.15 * precision_at_k
            + 0.10 * mrr
            + 0.10 * ndcg_at_k
            + 0.20 * f1
            + 0.10 * exact_match
            + 0.05 * rouge_l
            + 0.10 * bertscore_f1

## Architecture
- `rag_pipeline.py` — the ONLY file you may edit. Contains all pipeline
  parameters and the end-to-end RAG function.
- `evaluate.py` — the evaluation harness. DO NOT MODIFY. Runs the pipeline
  on each query, computes all metrics (classical by default, RAGAS optional),
  and prints the composite score.
- `results/results.tsv` — append each experiment result here.

## LLM Usage
- The ONLY LLM call is for answer generation (Google Gemini 2.5 Flash, free tier).
- All evaluation metrics are computed locally — no LLM judge calls in default mode.
- This means: 300 samples = 300 API calls per experiment (~30 min at 10 RPM).
- Use `--mode ragas` on the final best config for deep RAGAS analysis.

## Rules

### Experiment Protocol
1. Make ONE meaningful change per experiment. Do not change multiple
   independent variables at once.
2. After editing `rag_pipeline.py`, run: `python evaluate.py`
3. Read the composite score from stdout. If it improves over the current
   best (stored in `results/best_config.json`), run `git add -A && git
   commit -m "improvement: <description> | score: <score>"`.
4. If the score does not improve, revert: `git checkout -- rag_pipeline.py`
5. Log every experiment (kept or reverted) to `results/results.tsv`.

### Convergence Criterion
The optimization loop ends when no improvement has been found in 10
consecutive experiments.

### Boundaries
- Never modify `evaluate.py`, `data/`, or `utils/`.
- Use only locally-runnable models (sentence-transformers, cross-encoders,
  BM25) for embeddings and retrieval. The only external API call is Gemini
  for answer generation.
- ChromaDB is used for vector storage. The index is persisted in
  `./chroma_db/` and only re-built when chunking or embedding config
  changes. This saves significant time on prompt-only experiments.

## Search Space — What to Explore

### Phase 1: Chunking Strategy
- Fixed-size token chunking (chunk size and overlap)
- Recursive character splitting
- Semantic / sentence-window chunking
- Paragraph-level chunking

### Phase 2: Embedding Model
- Lightweight models (faster, lower dimensionality)
- Mid-range / large models (higher quality, slower)

### Phase 3: Retrieval Method
- Lexical (BM25), Dense (cosine), Hybrid (RRF)
- Top-k value
- Fusion weights for hybrid

### Phase 3b: Vector Database Tuning
Explore ChromaDB-specific parameters:
- Distance metric: cosine similarity, L2 (euclidean), or inner product
- The interaction between distance metric and embedding model (some
  models are trained for cosine, others for dot product)

Think about: Cosine similarity is the default and works well for
normalized embeddings. Inner product can be faster and may work better
with models that produce non-normalized embeddings. L2 captures
absolute distances. Try switching and observe the retrieval metrics.

### Phase 4: Reranking
- No reranker vs cross-encoder reranker
- Rerank pool size and final top-n

### Phase 5: Generation Prompt Template
- Instruction style, context formatting, grounding instructions

## Strategy
- Start with a reasonable baseline and record all metrics.
- Analyze which metrics are weakest:
  - Low recall_at_k / precision_at_k → focus on retrieval (Phase 1-3)
  - Low f1 / exact_match / rouge_l → focus on generation (Phase 5)
  - Low bertscore_f1 → check answer relevance and prompt quality
- Proceed through phases but revisit earlier ones when later results reveal
  that a different choice would be better.
- After finding strong individual components, test interactions.

## Output Format
After each experiment, print exactly:
EXPERIMENT: <id>
DESCRIPTION: <what changed and why>
COMPOSITE_SCORE: <float>
RECALL@K: <float>
PRECISION@K: <float>
MRR: <float>
NDCG@K: <float>
F1: <float>
EXACT_MATCH: <float>
ROUGE_L: <float>
BERTSCORE_F1: <float>
RESULT: KEEP | REVERT
REASONING: <one sentence on what this result tells you about next steps>

## Final Deliverable
When convergence is met (10 consecutive experiments with no improvement):
1. Run `python evaluate.py --mode ragas` on the best config for deep analysis.
2. Produce `results/final_report.md` — summary of all experiments, best
   configuration, progression table, analysis of which dimensions mattered
   most, and recommendations.
3. Produce `results/best_config.json` — the winning configuration as JSON.
4. Commit everything: `git commit -m "autoragsearch complete: final score <X>"`.
