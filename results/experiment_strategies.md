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

---
## Experiment 2

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.8903
**Weakest primary metric:** recall@k
**Diagnostic insight:** Hit rate is almost perfect and MRR is very high, so most questions have at least one relevant document ranked near the top. Recall is lower because HotpotQA often needs multiple supporting documents and top_n=5 may filter out the second one.
**Hypothesis:** Returning more reranked documents will improve recall more than it hurts NDCG, because the cross-encoder already puts at least one relevant document near the front.
**Change:** Increase RERANK_TOP_N from 5 to 10 while keeping dense TOP_K=50.
**Expected effect:** recall@k should rise by 0.03-0.08; ndcg@k may fall slightly if lower-ranked noise enters the final list, but the composite should improve if recall gains dominate.

### Outcome
**Retrieval score:** 0.9156 | **Delta:** +0.0253 | **Result:** KEEP
**Primary metrics:** recall@k=0.9125 | ndcg@k=0.9187
**Diagnostic metrics:** precision@k=0.0365 | mrr=0.9596 | map@k=0.7710 | hit_rate@k=1.0000
**What I learned:** HotpotQA benefits strongly from returning more reranked documents; the recall gain outweighed the expected NDCG drop. The perfect hit rate confirms the first-stage pool nearly always contains at least one supporting document.
**Next direction:** Continue increasing rerank output size to find where extra recall stops compensating for lower ranking concentration.
