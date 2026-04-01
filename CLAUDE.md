# AutoRAGsearch: Autonomous RAG Pipeline Optimization

## Objective
Find the optimal RAG retrieval pipeline configuration that maximizes
retrieval quality on the benchmark QA dataset, using ZERO LLM API calls
during the optimization loop.

The evaluation is purely retrieval-based. The optimization target is:

  retrieval_score = 0.50 * recall@k + 0.50 * ndcg@k

This formula captures the two things that matter most for RAG:
- **Recall@k** — Did you find the relevant documents?
- **NDCG@k** — Are they ranked well?

### Why This Formula
The IR and RAG literature typically uses a single primary metric (usually
NDCG@k or Recall@k) for optimization. A weighted composite of many metrics
introduces redundancy — NDCG@k already incorporates ranking quality (like
MRR) and penalizes irrelevant documents (like Precision@k). By focusing on
just Recall and NDCG with equal weight, the agent gets a clean optimization
signal: improve coverage or improve ranking.

### Diagnostic Metrics
The following metrics are computed and logged for every experiment but
are NOT part of the optimization target. Use them to diagnose issues:
- **Precision@k** — What fraction of retrieved docs are relevant? High
  recall + low precision means too much noise; consider a reranker.
- **MRR** — How high is the first relevant doc ranked? Low MRR with
  decent NDCG means relevant docs exist but the top-1 slot is wrong.
- **MAP@k** — Mean Average Precision across all relevant docs. A holistic
  measure of both precision and ranking; useful as a sanity check.
- **Hit Rate@k** — Binary: did retrieval find at least one relevant doc?
  A floor check; if this is low, recall is catastrophically broken.

These metrics compare retrieved doc IDs against ground-truth relevant
doc IDs. No answer generation is needed. No LLM calls are made.
Every experiment evaluates on ALL QA samples in the dataset (e.g., 300).
Experiments are unlimited — there is no API cost.

## Architecture
- `rag_pipeline.py` — the ONLY file you may edit. Contains all pipeline
  parameters and the retrieval pipeline function.
- `evaluate.py` — the evaluation harness. DO NOT MODIFY. It loads all
  QA samples, runs retrieval, computes retrieval metrics, and prints
  the retrieval_score.
- `results/results.tsv` — append each experiment result here.
- `results/experiment_strategies.md` — append your strategy BEFORE each
  experiment here (see Strategy Log section below).

## Fixed Components (DO NOT CHANGE)
These components are locked and must not be modified by the agent:
- **Embedding model**: `all-MiniLM-L6-v2` (sentence-transformers)
- **Vector DB distance metric**: cosine similarity (ChromaDB)
- **Evaluation set**: all QA samples in the dataset
- **Evaluation harness**: `evaluate.py` and all files in `utils/`
- **Generation prompt template**: not part of the optimization loop

## Rules

### Experiment Protocol
1. BEFORE making any change, write your strategy in
   `results/experiment_strategies.md` (see format below).
2. Make ONE meaningful change per experiment. Do not change multiple
   independent variables at once.
3. After editing `rag_pipeline.py`, run: `python evaluate.py`
4. Read the retrieval_score from stdout. If it improves over the current
   best (stored in `results/best_config.json`), run `git add -A && git
   commit -m "improvement: <description> | score: <score>"`.
5. If the score does not improve, revert: `git checkout -- rag_pipeline.py`
6. Log every experiment (kept or reverted) to `results/results.tsv`.
7. Update the strategy entry in `experiment_strategies.md` with the
   outcome and what you learned.

### Strategy Log
Before EVERY experiment, append a new entry to
`results/experiment_strategies.md` in this exact format:

```
---
## Experiment <id>

**Phase:** <1-Chunking / 2-Retrieval / 3-Reranking>
**Current best retrieval_score:** <float>
**Weakest primary metric:** <recall@k or ndcg@k — whichever is lower>
**Diagnostic insight:** <what precision, mrr, map, hit_rate tell you>
**Hypothesis:** <what you think will improve the score and why>
**Change:** <specific change you will make to rag_pipeline.py>
**Expected effect:** <which metrics you expect to improve and by how much>

### Outcome
**Retrieval score:** <float> | **Delta:** <+/- float> | **Result:** KEEP / REVERT
**Primary metrics:** recall@k=<f> | ndcg@k=<f>
**Diagnostic metrics:** precision@k=<f> | mrr=<f> | map@k=<f> | hit_rate@k=<f>
**What I learned:** <1-2 sentences on what the result means>
**Next direction:** <what this tells you to try next>
```

Fill in everything above "### Outcome" BEFORE running the experiment.
Fill in the Outcome section AFTER seeing the results.

### Convergence Criterion
The optimization loop ends when no improvement has been found in 10
consecutive experiments. This is the stopping condition — not a time
limit.

### Boundaries
- Never modify `evaluate.py`, `data/`, or `utils/`.
- Never change the embedding model — it is fixed to `all-MiniLM-L6-v2`.
- Never change the ChromaDB distance metric — it is fixed to cosine.
- This optimization loop makes ZERO LLM API calls. All evaluation is
  local. Do not add any LLM calls to the evaluation or pipeline during
  the optimization loop.
- ChromaDB is used as the vector store for dense retrieval. The index
  is persisted in `./chroma_db/` and only re-built when the chunking
  configuration changes. This saves significant time on retrieval-only
  or reranker-only experiments.

## Search Space — What to Explore

You have full freedom to choose specific parameter values. The dimensions
below describe WHAT to explore, not specific grid values. Use your
reasoning to choose good starting points, adjust based on results, and
explore the space intelligently — not exhaustively.

Since every experiment is FREE (zero API calls), you can afford to
explore broadly. Take advantage of this.

### Phase 1: Chunking Strategy
Explore different ways to split documents into chunks:
- Fixed-size token chunking (you choose the chunk size and overlap)
- Recursive character splitting (LangChain-style hierarchical splitting)
- Semantic chunking (split on topic or meaning boundaries)
- Sentence-window chunking (retrieve a sentence, expand to surrounding
  window at query time)
- Paragraph-level chunking (respect document structure)

Think about: What chunk size captures enough context without introducing
noise? How much overlap prevents information from being cut at boundaries?
Smaller chunks improve precision but may hurt recall. Larger chunks
improve recall but add noise. Let the metrics guide you.

### Phase 2: Retrieval Method
Explore how documents are retrieved:
- Lexical retrieval (BM25 — keyword-based)
- Dense retrieval (cosine similarity via ChromaDB vector store)
- Hybrid retrieval (BM25 + Dense combined via Reciprocal Rank Fusion)
- The number of documents to retrieve (top-k)
- The fusion weight between lexical and dense scores

Think about: Dense retrieval captures semantics but misses exact keyword
matches. BM25 is the opposite. Hybrid methods try to get both — but the
weighting matters. Use diagnostic metrics to guide you: if recall@k is
high but precision@k is low, you're retrieving too many irrelevant docs.
If precision@k is high but recall@k is low, you're missing relevant docs.

### Phase 3: Reranking
Explore whether a second-stage reranker improves the retrieved set:
- No reranker (baseline)
- Cross-encoder rerankers (various sizes and training data)
- How many documents to rerank and how many to keep after reranking

Think about: Reranking can dramatically improve NDCG@k by pushing
irrelevant docs down. If precision@k (diagnostic) is already high,
reranking may not help. If recall@k is high but precision@k is low,
a reranker could filter noise effectively. Watch the MRR diagnostic —
rerankers often improve MRR by pushing the first relevant doc to
position 1, which also boosts NDCG@k.

## Strategy
- Start with a reasonable baseline. Run the first evaluation and record
  both primary metrics (recall@k, ndcg@k) and all diagnostic metrics.
- Identify the weaker primary metric. This tells you what to fix:
  - Low recall@k → retrieval is missing relevant docs. Try larger
    chunks, more overlap, higher top-k, or hybrid retrieval.
  - Low ndcg@k → ranking quality is poor. Try a different retrieval
    method, adjust fusion weights, or add a reranker.
- Use diagnostic metrics to refine your understanding:
  - Low precision@k with high recall@k → too much noise. Consider a
    reranker or lower top-k.
  - Low MRR with decent NDCG@k → the top-1 slot is wrong but overall
    ranking is okay. A reranker may help.
  - Low hit_rate@k → catastrophic recall failure. Fix chunking or
    retrieval method first.
- ALWAYS write your strategy in `results/experiment_strategies.md`
  before running an experiment. This is not optional.
- Proceed through phases sequentially. Within each phase, iterate
  until you stop finding improvements.
- After completing all phases, revisit earlier phases. The best
  chunking strategy may change once you've added a reranker.
  Since experiments are free, revisiting costs nothing.
- When improvements plateau across all phases after revisiting,
  the loop is complete.

## Output Format
After each experiment, print exactly this block to stdout:
```
===== AUTORAGSEARCH EXPERIMENT =====
EXPERIMENT_ID:       <int, sequential starting from 1>
PHASE:               <1-Chunking / 2-Retrieval / 3-Reranking>
DESCRIPTION:         <what changed and why you tried it>
RETRIEVAL_SCORE:     <float, 4 decimal places>
--- Primary Metrics (in optimization target) ---
RECALL@K:            <float, 4 decimal places>
NDCG@K:              <float, 4 decimal places>
--- Diagnostic Metrics (not in optimization target) ---
PRECISION@K:         <float, 4 decimal places>
MRR:                 <float, 4 decimal places>
MAP@K:               <float, 4 decimal places>
HIT_RATE@K:          <float, 4 decimal places>
--- Experiment Info ---
NUM_EVAL_SAMPLES:    <int — all samples in dataset>
LLM_CALLS:           0
WALL_CLOCK_SECONDS:  <float, 1 decimal place>
DELTA_VS_BEST:       <+/- float vs best retrieval_score, 4 decimal places>
RESULT:              KEEP | REVERT
REASONING:           <1-2 sentences: what this tells you, what to try next>
====================================
```

Also append a row to `results/results.tsv` with tab-separated columns:
```
experiment_id	phase	description	retrieval_score	recall_at_k	ndcg_at_k	precision_at_k	mrr	map_at_k	hit_rate_at_k	num_eval_samples	wall_clock_seconds	delta_vs_best	result	reasoning	timestamp
```

Create this TSV with a header row before the first experiment.

## Final Deliverable
When the convergence criterion is met (10 consecutive experiments with
no improvement across all phases), produce:

1. `results/final_report.md` — summary including:
   - Total experiments run (all free — zero LLM calls)
   - Breakdown of experiments per phase
   - Baseline retrieval_score vs final retrieval_score
   - The best configuration as a table
   - Progression of retrieval_score across all kept improvements
   - Per-metric analysis: how both primary metrics (recall@k, ndcg@k)
     evolved, plus insights from diagnostic metrics
   - Analysis of which phase contributed the most improvement
   - Top 3 most impactful individual experiments
   - Recommendations for further optimization
2. `results/best_config.json` — the winning configuration as JSON.
3. `results/experiment_strategies.md` should already be complete with
   the full research narrative of every experiment.
4. Commit everything with message
   "autoragsearch complete: retrieval_score <baseline> → <final> in <N> experiments (0 LLM calls)"
