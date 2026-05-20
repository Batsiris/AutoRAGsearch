---
## Experiment 1

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.0000
**Weakest primary metric:** unknown before HotpotQA baseline
**Diagnostic insight:** No HotpotQA retrieval diagnostics have been collected yet; this run establishes the local baseline on all HotpotQA samples.
**Hypothesis:** The existing NQ-winning configuration may be a strong starting point for HotpotQA because it retrieves a broad dense candidate pool and uses a cross-encoder to prioritize likely supporting documents.
**Change:** Establish the HotpotQA baseline with fixed chunking at 512 tokens / 50 overlap, dense top_k=50, and cross-encoder reranking to top_n=5.
**Expected effect:** Produce the initial recall@k and ndcg@k measurements for HotpotQA; no improvement estimate is available before the baseline.

### Outcome
**Retrieval score:** 0.8903 | **Delta:** N/A | **Result:** KEEP
**Primary metrics:** recall@k=0.8400 | ndcg@k=0.9405
**Diagnostic metrics:** precision@k=0.0336 | mrr=0.9588 | map@k=0.7525 | hit_rate@k=0.9950
**What I learned:** The current dense + reranker pipeline ranks found evidence very well, but recall is the weaker primary metric. HotpotQA likely needs a larger candidate pool or better first-stage recall because multi-hop questions can require two supporting documents.
**Next direction:** Increase dense candidate depth before reranking to test whether recall can rise while keeping top-ranked output compact.
