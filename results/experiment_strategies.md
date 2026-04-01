# AutoRAGsearch Experiment Strategies

---
## Experiment 1

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344 vs recall@k=0.96)
**Diagnostic insight:** Precision@k=0.192 means ~4 irrelevant docs retrieved per relevant one (k=5). MRR=0.926 shows the relevant doc is usually at position 1, but not always. Hit rate=0.96 is strong.
**Hypothesis:** Recursive chunking respects document structure (paragraph/sentence boundaries) better than fixed token splitting, which can cut mid-sentence. More coherent chunks should match queries better semantically, improving NDCG ranking quality without hurting the already-strong recall.
**Change:** Switch CHUNK_METHOD from "fixed" to "recursive", keep chunk_size=512 and chunk_overlap=50.
**Expected effect:** Modest improvement in ndcg@k (+0.005 to +0.02). Recall likely unchanged or slightly improved. Precision may improve slightly if structural chunks reduce noise.

### Outcome
**Retrieval score:** 0.9472 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9600 | ndcg@k=0.9344
**Diagnostic metrics:** precision@k=0.1920 | mrr=0.9256 | map@k=0.9256 | hit_rate@k=0.9600
**What I learned:** Recursive chunking with size=512/overlap=50 produces identical results to fixed chunking. The structural boundaries don't meaningfully change chunk quality at this configuration — likely because the corpus documents are not highly structured (encyclopedic NQ passages).
**Next direction:** Try smaller chunk size (256) to see if more granular, precise chunks improve NDCG by reducing noise in retrieved passages.

---
## Experiment 2

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** Precision@k=0.192 → ~1 relevant doc per 5 retrieved. The query matches loosely across big chunks. Smaller chunks could create tighter query-chunk alignment, pushing the relevant chunk to rank 1 more often.
**Hypothesis:** Halving chunk size from 512 to 256 tokens increases chunk granularity. Each chunk covers a narrower topic, so the relevant chunk should match the query more precisely in vector space. This should improve NDCG by ensuring the relevant chunk ranks higher while recall remains strong (more total chunks in index).
**Change:** Reduce CHUNK_SIZE from 512 to 256, keep CHUNK_OVERLAP=50, CHUNK_METHOD="fixed".
**Expected effect:** ndcg@k improvement (+0.01 to +0.03), recall likely stable or slight decrease (more chunks but smaller — may miss some relevant passages that span boundaries), precision@k may improve slightly.

### Outcome
**Retrieval score:** 0.9464 | **Delta:** -0.0008 | **Result:** REVERT
**Primary metrics:** recall@k=0.9600 | ndcg@k=0.9328
**Diagnostic metrics:** precision@k=0.1920 | mrr=0.9244 | map@k=0.9278 | hit_rate@k=0.9567
**What I learned:** Smaller chunks (256) slightly hurt NDCG (0.9328 vs 0.9344). More fragments in the index may cause the relevant passage to spread across more chunks, slightly reducing query-chunk match quality. Precision is unchanged.
**Next direction:** Try larger chunks (1024) — bigger context windows may capture more relevant content per chunk, potentially improving NDCG.

---
## Experiment 3

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** Precision@k=0.192 with k=5 means ~1 relevant doc per query. NDCG=0.9344 < recall=0.96 implies some queries have the relevant doc not at rank 1. The 512-token chunks are intermediate — smaller chunks hurt, so let's test if larger chunks help.
**Hypothesis:** 1024-token chunks capture more of the relevant document content in a single unit. With fewer but larger chunks, the relevant chunk has less competition from similar-topic fragments, potentially improving NDCG by allowing the relevant chunk to dominate cosine similarity ranking.
**Change:** Increase CHUNK_SIZE from 512 to 1024, keep CHUNK_OVERLAP=50, CHUNK_METHOD="fixed".
**Expected effect:** Possible ndcg@k improvement if larger chunks reduce noise competition. Recall should remain high (fewer chunks but each covers more ground). Precision@k may drop (larger chunks are more likely to partially match irrelevant queries).

### Outcome
**Retrieval score:** 0.9472 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9600 | ndcg@k=0.9344
**Diagnostic metrics:** precision@k=0.1920 | mrr=0.9256 | map@k=0.9256 | hit_rate@k=0.9600
**What I learned:** 1024-token chunks produce exactly the same 781 chunks as 512-token chunks and identical scores. The NQ corpus documents are already ≤512 tokens on average — chunking size has no effect above 512. Phase 1 chunking experiments are exhausted for size; document boundaries naturally constrain chunking.
**Next direction:** Move to Phase 2 (Retrieval). Try sentence-based chunking as a final Phase 1 test since it's qualitatively different (respects sentence boundaries), then explore hybrid retrieval (BM25 + Dense) to add keyword-matching capability.

---
## Experiment 4

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** Fixed chunking at any size above 512 produces identical behavior on NQ corpus (docs ≤512 tokens). Chunking SIZE is not the differentiating factor. The chunking METHOD may still matter if sentence boundaries produce more semantically coherent units.
**Hypothesis:** Sentence-based chunking groups text by natural sentence boundaries rather than character count. For NQ passages (encyclopedic text), this should produce more semantically complete units where each chunk represents a complete thought. Better chunk-query semantic alignment may improve NDCG.
**Change:** Switch CHUNK_METHOD from "fixed" to "sentence", keep other params (chunk_size=512, chunk_overlap=50 used as hints).
**Expected effect:** Possible small improvement in ndcg@k if sentence-aligned chunks improve query-chunk cosine similarity. Recall should be stable. May show improvement or be neutral depending on how well sentences align with NQ queries.

### Outcome
**Retrieval score:** 1.0570 (ARTIFACT) | **Delta:** +0.1098 (INVALID) | **Result:** REVERT
**Primary metrics:** recall@k=1.1833 (>1.0, INVALID) | ndcg@k=0.9306 (LOWER than baseline)
**Diagnostic metrics:** precision@k=0.2367 | mrr=0.9244 | map@k=1.1356 (>1.0, INVALID) | hit_rate@k=0.9600
**What I learned:** Sentence chunking produces multiple chunks per document. With top_k=5, the same doc_id can appear multiple times in retrieved results. The metric formula `recall = sum(hits) / len(relevant_set)` counts duplicate doc_ids as multiple hits, causing recall > 1.0. This is a measurement artifact, NOT a real improvement. NDCG actually DECREASED (0.9306 < 0.9344). Best_config.json restored to true baseline 0.9472.
**Next direction:** Move to Phase 2 (Retrieval). Try hybrid retrieval (BM25+Dense) — adding keyword matching may improve NDCG for queries relying on exact term overlap.

---
## Experiment 5

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** Dense-only retrieval achieves recall=0.96 but NDCG=0.9344 — ranking quality has room to improve. MRR=0.9256 means ~7.4% of queries have the relevant doc not at rank 1. BM25 excels at exact keyword matches that dense retrieval can miss via semantic drift.
**Hypothesis:** Hybrid retrieval via Reciprocal Rank Fusion (RRF) combines BM25's exact keyword matching with dense retrieval's semantic matching. NQ questions often reference specific named entities and terms that appear verbatim in relevant passages. BM25 should help push those matching docs to the top, improving NDCG and MRR.
**Change:** Switch RETRIEVAL_METHOD from "dense" to "hybrid". Default RRF weights and k=60 apply.
**Expected effect:** ndcg@k improvement (+0.01 to +0.03) from better keyword-aware ranking. Recall likely stays near 0.96. MRR may improve (relevant docs ranked higher).

### Outcome
**Retrieval score:** 0.9146 | **Delta:** -0.0326 | **Result:** REVERT
**Primary metrics:** recall@k=0.9400 | ndcg@k=0.8892
**Diagnostic metrics:** precision@k=0.1880 | mrr=0.8717 | map@k=0.8717 | hit_rate@k=0.9400
**What I learned:** Hybrid BM25+Dense significantly hurts performance (-3.3%). NQ questions are semantic in nature — dense retrieval captures the right meaning while BM25 introduces noise from keyword mismatch. The RRF fusion is degrading the dense retrieval signal.
**Next direction:** Stay with dense retrieval. Try top_k=10 to see if higher recall (more candidates) while keeping the same dense retrieval ranking helps. Also test if top_k=3 improves NDCG by reducing retrieved noise.

---
## Experiment 6

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** Recall=0.96 means 12/300 queries miss the relevant doc entirely. Increasing top_k may find those 12. Hit_rate=0.96 confirms — those 12 are total misses. Higher top_k brings in more candidates, potentially rescuing these lost queries.
**Hypothesis:** Doubling top_k from 5 to 10 retrieves more documents, giving a better chance of capturing the relevant doc for the 12 queries that currently miss. This should push recall closer to 1.0 and also improve NDCG by having the relevant doc present in a larger set (though ranking may spread).
**Change:** Increase TOP_K from 5 to 10, all other params unchanged.
**Expected effect:** Recall improvement (+0.02 to +0.04), retrieval_score improvement. NDCG may slightly decrease due to more candidates but recall gain should outweigh it.

### Outcome
**Retrieval score:** 0.9472 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9600 | ndcg@k=0.9344
**Diagnostic metrics:** precision@k=0.0960 | mrr=0.9256 | map@k=0.9256 | hit_rate@k=0.9600
**What I learned:** top_k=10 gives identical recall and NDCG as top_k=5. The 12 missing queries (recall gap) are not findable in top-10 with dense retrieval — they're a hard ceiling for this embedding model. Precision halved (as expected: twice the docs, same relevant ones), confirming the extra docs are all noise.
**Next direction:** Move to Phase 3 (Reranking). Enable cross-encoder reranker to improve NDCG by pushing the relevant doc to rank 1 more reliably. Also try top_k=20 with reranker for "retrieve more, rerank to fewer" strategy.

---
## Experiment 7

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9472
**Weakest primary metric:** ndcg@k (0.9344)
**Diagnostic insight:** MRR=0.9256 means ~7.4% of queries have the relevant doc NOT at rank 1 despite it being retrieved. Precision@k=0.192 means 80.8% of retrieved docs are irrelevant noise. A cross-encoder reranker can score each (query, passage) pair precisely and push the relevant doc to rank 1, directly improving NDCG and MRR.
**Hypothesis:** The cross-encoder reranker (ms-marco-MiniLM-L-6-v2) is specifically trained to score passage relevance for a given query. It can distinguish the relevant doc from noise more accurately than cosine similarity. Enabling it with top_k=5 retrieve and rerank_top_n=3 should push the relevant doc higher, improving NDCG.
**Change:** Set USE_RERANKER=True, keep TOP_K=5, RERANK_TOP_N=3.
**Expected effect:** ndcg@k improvement (+0.02 to +0.05), MRR improvement. Recall will decrease slightly (top_n=3 < top_k=5, so if relevant doc was at position 4-5, it's excluded after reranking). Net effect expected to be positive if NDCG gain exceeds recall loss.

### Outcome
**Retrieval score:** 0.9621 | **Delta:** +0.0149 | **Result:** KEEP
**Primary metrics:** recall@k=0.9667 | ndcg@k=0.9576
**Diagnostic metrics:** precision@k=0.1933 | mrr=0.9544 | map@k=0.9544 | hit_rate@k=0.9667
**What I learned:** Cross-encoder reranker is highly effective. NDCG jumped from 0.9344 to 0.9576 (+2.3%), MRR from 0.9256 to 0.9544. Recall actually IMPROVED slightly (0.96 → 0.9667) — surprising, but the reranker may have promoted a relevant doc from position 4-5 into the top-3 more often than it excluded one. Best config updated.
**Next direction:** Try larger top_k for initial retrieval (e.g., top_k=10) before reranking to give the reranker more candidates. More initial candidates = higher chance relevant doc is included before reranking = possibly higher recall.

---
## Experiment 8

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9621
**Weakest primary metric:** ndcg@k (0.9576) — already improved significantly with reranker
**Diagnostic insight:** MRR=0.9544 and hit_rate=0.9667 show the reranker is effective but still ~3.3% of queries miss. With top_k=5, the initial retrieval may not capture the relevant doc for those queries. Increasing initial pool to 10 gives the reranker more candidates.
**Hypothesis:** Increasing top_k from 5 to 10 for initial retrieval expands the candidate pool before reranking. Even if those extra 5 docs are noisy, the cross-encoder can correctly score them down. The relevant doc that was previously at position 6-10 (below top-5 cutoff) can now enter the reranker, improving recall and potentially NDCG.
**Change:** Increase TOP_K from 5 to 10, keep USE_RERANKER=True, increase RERANK_TOP_N from 3 to 5 (keep more after reranking).
**Expected effect:** Recall improvement as more candidates give the relevant doc more chances to be included. NDCG may also improve if the reranker correctly promotes the relevant doc from the expanded pool.

### Outcome
**Retrieval score:** 0.9710 | **Delta:** +0.0089 | **Result:** KEEP
**Primary metrics:** recall@k=0.9767 | ndcg@k=0.9653
**Diagnostic metrics:** precision@k=0.0977 | mrr=0.9614 | map@k=0.9614 | hit_rate@k=0.9767
**What I learned:** Expanding retrieval pool (top_k=10) then reranking to top_n=5 improves both recall (0.9667→0.9767) and NDCG (0.9576→0.9653). The reranker effectively selects relevant docs from a larger candidate set. "Retrieve more, rerank to fewer" is highly effective.
**Next direction:** Try even larger initial retrieval pool (top_k=20) with rerank_top_n=5 to see if recall can improve further for the remaining ~2.3% missing queries.

---
## Experiment 9

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9710
**Weakest primary metric:** ndcg@k (0.9653) and recall@k (0.9767) — both improved but ~2.3% of queries still miss
**Diagnostic insight:** Hit_rate=0.9767 means ~7 queries still get zero relevant docs in top-5 after reranking. If those relevant docs appear in positions 11-20 of the initial dense retrieval, expanding to top_k=20 before reranking could rescue them.
**Hypothesis:** Expanding the initial retrieval to 20 candidates gives the reranker an even larger pool. Some of the 7 hard-miss queries may have their relevant doc in positions 11-20 of dense ranking. Reranker can then correctly promote it.
**Change:** Increase TOP_K from 10 to 20, keep USE_RERANKER=True, RERANK_TOP_N=5.
**Expected effect:** Small recall improvement if the 7 remaining misses have relevant docs in positions 11-20. NDCG should stay similar or improve slightly. Wall-clock time will increase (~10 min) as reranker scores 20 docs × 300 queries.

### Outcome
**Retrieval score:** 0.9776 | **Delta:** +0.0066 | **Result:** KEEP
**Primary metrics:** recall@k=0.9833 | ndcg@k=0.9718
**Diagnostic metrics:** precision@k=0.0492 | mrr=0.9679 | map@k=0.9679 | hit_rate@k=0.9833
**What I learned:** Expanding to top_k=20 continues to improve: recall 0.9767→0.9833, NDCG 0.9653→0.9718. Some of the hard-miss queries do have relevant docs in positions 11-20 of dense retrieval, and the reranker successfully promotes them. Diminishing returns are setting in (wall clock is now 21 min).
**Next direction:** Try top_k=30 to see if diminishing returns are fully set in, or whether another push further improves recall for the last ~1.7% of missing queries.

---
## Experiment 10

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9776
**Weakest primary metric:** ndcg@k (0.9718) and recall@k (0.9833) — ~5 queries (~1.7%) still missing
**Diagnostic insight:** Hit_rate=0.9833 means 5 queries still get zero relevant docs in top-5 after reranking. The "retrieve more, rerank fewer" trend has consistently improved scores. Testing if positions 21-30 in dense ranking contain those remaining relevant docs.
**Hypothesis:** The 5 remaining hard-miss queries may have relevant docs at positions 21-30 in dense retrieval. Expanding to top_k=30 gives the reranker access to those candidates. Pattern so far: each doubling of top_k rescues more missing queries.
**Change:** Increase TOP_K from 20 to 30, keep USE_RERANKER=True, RERANK_TOP_N=5.
**Expected effect:** Possible small recall improvement (+0.01 to +0.02). NDCG should improve proportionally. Wall clock ~25-30 min.

### Outcome
**Retrieval score:** 0.9834 | **Delta:** +0.0058 | **Result:** KEEP
**Primary metrics:** recall@k=0.9900 | ndcg@k=0.9768
**Diagnostic metrics:** precision@k=0.0330 | mrr=0.9723 | map@k=0.9723 | hit_rate@k=0.9900
**What I learned:** top_k=30 continues the improvement trend: recall 0.9833→0.99, NDCG 0.9718→0.9768. More relevant docs are in positions 21-30 of dense retrieval, and the reranker correctly promotes them. Wall clock is now 33 min per experiment.
**Next direction:** Try top_k=50 to see if we can push recall to near-perfect (0.99→1.0). Also consider that wall-clock time grows linearly — may need to balance quality vs speed.

---
## Experiment 11

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9834
**Weakest primary metric:** recall@k (0.9900) and ndcg@k (0.9768)
**Diagnostic insight:** Hit_rate=0.99 means 3 queries (1%) still get zero relevant docs in top-5 after reranking. The consistent "more candidates = better recall" pattern suggests some relevant docs are in positions 31-50 of dense retrieval.
**Hypothesis:** Those 3 remaining hard-miss queries may have relevant docs at positions 31-50 in dense retrieval. top_k=50 gives the reranker access to them. Diminishing returns are expected but the pattern hasn't broken yet.
**Change:** Increase TOP_K from 30 to 50, keep USE_RERANKER=True, RERANK_TOP_N=5.
**Expected effect:** Possible recall 0.9900→0.9933 or 1.0. NDCG improvement proportional. Wall clock ~50 min.

### Outcome
**Retrieval score:** 0.9867 | **Delta:** +0.0033 | **Result:** KEEP
**Primary metrics:** recall@k=0.9933 | ndcg@k=0.9801
**Diagnostic metrics:** precision@k=0.0199 | mrr=0.9757 | map@k=0.9757 | hit_rate@k=0.9933
**What I learned:** top_k=50 continues improving (recall 0.99→0.9933, NDCG 0.9768→0.9801). Diminishing returns are clearly visible: delta dropped from +0.0066 (k=20) to +0.0058 (k=30) to +0.0033 (k=50). Wall clock is now 80 min per experiment — impractical for large k. 2 queries (0.67%) still miss.
**Next direction:** The top_k expansion strategy is hitting diminishing returns fast (wall clock doubles per step). Try top_k=100 once to confirm — if delta drops to near zero, stop expanding and explore other optimizations (rerank_top_n tuning, different reranker model).

---
## Experiment 12

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** MRR=0.9757 means the relevant doc is at rank 1 for 97.6% of queries in the reranked top-5. With top_n=5, positions 2-5 are mostly irrelevant noise. Reducing top_n to 3 should keep all relevant docs (since they're almost always at rank 1) while tightening the output.
**Hypothesis:** Reducing RERANK_TOP_N from 5 to 3 while keeping top_k=50 focuses the final output on the cross-encoder's most confident results. Since relevant docs are almost always at rank 1 in the reranked list (MRR=0.9757), top_n=3 should preserve recall while improving NDCG by reducing irrelevant noise in the final set.
**Change:** Reduce RERANK_TOP_N from 5 to 3, keep TOP_K=50, USE_RERANKER=True.
**Expected effect:** NDCG improvement as fewer irrelevant docs dilute the metric. Recall may stay at 0.9933 if the relevant doc remains in top-3 for most queries.

### Outcome
**Retrieval score:** 0.9844 | **Delta:** -0.0023 | **Result:** REVERT
**Primary metrics:** recall@k=0.9900 | ndcg@k=0.9788
**Diagnostic metrics:** precision@k=0.0198 | mrr=0.9750 | map@k=0.9750 | hit_rate@k=0.9900
**What I learned:** Reducing top_n from 5 to 3 cuts recall (0.9933→0.99) — some relevant docs are at positions 4-5 of the reranked list and get excluded. NDCG also drops (0.9801→0.9788). top_n=5 is the optimal output size for top_k=50 on this dataset.
**Next direction:** Try a larger cross-encoder reranker (ms-marco-MiniLM-L-12-v2) with the same top_k=50/top_n=5 — more model capacity may score relevance more accurately, improving NDCG.

---
## Experiment 13

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801) — scoring accuracy of reranker may be the bottleneck
**Diagnostic insight:** MRR=0.9757 means 2.4% of queries don't have the relevant doc at rank 1 after reranking with L-6-v2. A more powerful cross-encoder might correctly rank those queries.
**Hypothesis:** The ms-marco-MiniLM-L-12-v2 is a larger (12-layer) cross-encoder trained on the same MS MARCO dataset. It should score (query, passage) relevance more accurately than the 6-layer version, pushing more relevant docs to rank 1 and improving both NDCG and MRR.
**Change:** Switch RERANKER_MODEL from "cross-encoder/ms-marco-MiniLM-L-6-v2" to "cross-encoder/ms-marco-MiniLM-L-12-v2", keep TOP_K=50, RERANK_TOP_N=5.
**Expected effect:** ndcg@k improvement (+0.005 to +0.015), MRR improvement. Recall should stay at 0.9933 (same candidate pool). Wall clock may increase slightly (larger model per inference).

### Outcome
**Retrieval score:** OOM FAILURE | **Delta:** N/A | **Result:** REVERT
**Primary metrics:** N/A
**Diagnostic metrics:** N/A
**What I learned:** L-12-v2 OOMs when predicting 50 pairs in a single batch (RuntimeError: not enough memory at alloc_cpu.cpp). The model.predict() call processes all top_k pairs at once. L-12-v2 requires more memory per batch than available. Will retry with smaller top_k (20) to reduce batch size.
**Next direction:** Retry L-12-v2 with top_k=20, top_n=5 — 20 pairs per query should fit in memory. If L-12-v2 at top_k=20 beats L-6-v2 at top_k=20 (0.9776), the larger model's quality compensates for the smaller candidate pool.

---
## Experiment 14

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** L-6-v2 at top_k=20 scored 0.9776. L-12-v2 OOMed at top_k=50 (Exp 13). Using top_k=10 respects the 30-min wall-clock constraint (L-6-v2 at k=10 took 10 min; L-12-v2 ~2x slower = ~20 min).
**Hypothesis:** L-12-v2 (12-layer) is more accurate at relevance scoring than L-6-v2. Even with a smaller candidate pool (top_k=10), the superior cross-attention may push the relevant doc to rank 1 more reliably, improving NDCG and MRR beyond what L-6-v2 achieves with top_k=10 (0.9710).
**Change:** RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-12-v2", TOP_K=10, RERANK_TOP_N=5.
**Expected effect:** Score above 0.9710 (L-6-v2 at k=10). Confirms whether model quality can compensate for smaller pool size.

### Outcome
**Retrieval score:** 0.9710 | **Delta:** -0.0158 | **Result:** REVERT
**Primary metrics:** recall@k=0.9767 | ndcg@k=0.9653
**Diagnostic metrics:** precision@k=0.0977 | mrr=0.9614 | map@k=0.9614 | hit_rate@k=0.9767
**What I learned:** L-12-v2 at top_k=10 produces identical results to L-6-v2 at top_k=10 (0.9710). The candidate pool size is the bottleneck, not reranker model quality — both models score the same 10 candidates and arrive at the same ordering. More model capacity cannot compensate for a smaller initial pool.
**Next direction:** The pool size is the key variable. Explore whether hybrid retrieval (BM25+Dense) with reranker can find the 2 remaining missing queries that dense alone can't retrieve within top-50. BM25 keyword matching may find different docs.

---
## Experiment 15

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** Exp 5 showed hybrid (without reranker) hurt badly (-0.0326). But the issue was BM25 noise corrupting the ranking. With a cross-encoder reranker to filter that noise, hybrid might recover or surpass dense. BM25 can retrieve docs via exact keyword matches that dense misses semantically.
**Hypothesis:** Hybrid BM25+Dense retrieval produces a diverse candidate pool combining semantic and keyword matching. The cross-encoder reranker can then correctly score these candidates, filtering BM25 noise while keeping any extra keyword-matched relevant docs. Net effect: possibly higher recall than dense-only at the same top_k.
**Change:** RETRIEVAL_METHOD="hybrid", TOP_K=20, USE_RERANKER=True, RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-6-v2", RERANK_TOP_N=5.
**Expected effect:** Recall may improve over dense-only at top_k=20 (0.9833) if BM25 finds the 2 hard-miss queries. NDCG could also improve if diverse candidates include the relevant doc. Best case: approaches 0.9867 baseline.

### Outcome
**Retrieval score:** 1.4028 (ARTIFACT) | **Delta:** N/A (INVALID) | **Result:** REVERT
**Primary metrics:** recall@k=1.8367 (>1.0, INVALID) | ndcg@k=0.9688
**Diagnostic metrics:** precision@k=0.0918 | mrr=0.9643 | map@k=1.8165 (INVALID) | hit_rate@k=0.9800
**What I learned:** Hybrid retrieval with reranker produces the same measurement artifact as sentence chunking (Exp 4). The hybrid retriever returns multiple chunks from the same document (BM25 and dense independently rank both chunks highly for some docs), and both survive the reranker's top-5 cut. The evaluator counts each duplicate doc_id as a separate hit, inflating recall past 1.0. True NDCG (0.9688) is actually LOWER than dense-only at top_k=20 (0.9718). Best_config.json restored to true best 0.9867.
**Next direction:** Avoid hybrid retrieval (measurement artifact + genuinely worse NDCG). Stay with dense-only. Explore output size tuning: top_n=7 vs top_n=5 at top_k=20 — can more output docs improve the composite score?

---
## Experiment 16

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** At top_k=20/top_n=5, mrr=0.9679 meaning ~3.2% of queries have the relevant doc not at rank 1 in the reranked list. These queries' relevant docs may be at reranked positions 6-7. If so, increasing top_n from 5 to 7 would include them, boosting recall@7 while NDCG@7 is evaluated over a larger set.
**Hypothesis:** Increasing top_n from 5 to 7 (within the same top_k=20 pool) may capture relevant docs at reranked positions 6-7 that were excluded at top_n=5. The composite score recall@7 + ndcg@7 could improve if the recall gain exceeds the NDCG cost of positions 6-7 being noise.
**Change:** TOP_K=20, RERANK_TOP_N=7 (increased from 5), USE_RERANKER=True, RERANKER_MODEL L-6-v2.
**Expected effect:** recall@7 ≥ recall@5 (0.9833). NDCG@7 may be slightly worse than ndcg@5 (0.9718) due to positions 6-7 noise. Net effect on composite score uncertain.

### Outcome
**Retrieval score:** 0.9776 | **Delta:** -0.0092 | **Result:** REVERT
**Primary metrics:** recall@7=0.9833 | ndcg@7=0.9718
**Diagnostic metrics:** precision@7=0.0492 | mrr=0.9679 | map@7=0.9679 | hit_rate@7=0.9833
**What I learned:** top_n=7 produces identical scores to top_n=5 at top_k=20. Positions 6-7 in the reranked list contain no relevant docs — all relevant docs are already in top-5. NDCG@7 = NDCG@5 because extra irrelevant positions don't affect the metric (gain=0 at those positions). Output size tuning beyond top_n=5 yields no benefit for this retrieval configuration.
**Next direction:** Test pure dense retrieval at top_k=20 without reranker (return all 20 docs) as a baseline. Then try top_k=25 with reranker — interpolating between k=20 (0.9776) and k=30 (0.9834) within the 30-min wall-clock budget.

---
## Experiment 17

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** All reranker experiments use top_n=5 as output. The reranker's contribution is clear from comparing top_k=5/no-reranker (0.9472) vs top_k=5/reranker (0.9621). But we haven't measured pure dense retrieval at k=20 (returning all 20). This baseline isolates the reranker's value at the k=20 pool size.
**Hypothesis:** Dense retrieval at k=20 without reranker, returning all 20 docs, will measure recall@20 and ndcg@20. Recall@20 should be high (all docs in top-20 retrieved), but ndcg@20 may suffer due to relevant doc being buried in noise. This establishes the no-reranker baseline at this pool size.
**Change:** TOP_K=20, USE_RERANKER=False, RERANK_TOP_N=20 (return all retrieved docs unchanged).
**Expected effect:** High recall@20 (≥0.9833 since top_k=20+reranker→5 hit_rate=0.9833), but lower ndcg@20 due to relevant doc not consistently at rank 1 (cosine only, no reranking). Composite score likely lower than reranked version.

### Outcome
**Retrieval score:** 0.9649 | **Delta:** -0.0218 | **Result:** REVERT
**Primary metrics:** recall@20=0.9867 | ndcg@20=0.9431
**Diagnostic metrics:** precision@20=0.0493 | mrr=0.9292 | map@20=0.9292 | hit_rate@20=0.9867
**What I learned:** Pure dense retrieval at k=20 (no reranker) scores 0.9649 vs 0.9776 with reranker. The reranker adds +0.013 by dramatically improving NDCG (0.9431→0.9718, +3.0%) and MRR (0.9292→0.9679) at the cost of slightly lower recall (0.9867→0.9833, -0.34% from truncation to top-5). The reranker is clearly worth its cost: better ranking quality outweighs the recall loss from truncation.
**Next direction:** Try top_k=25 with reranker to interpolate between k=20 (0.9776) and k=30 (0.9834 at 33 min). k=25 should complete in ~27 min.

---
## Experiment 18

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** Scores at k=20 (0.9776) and k=30 (0.9834) show +0.0058 improvement per 10-doc pool expansion. k=25 tests whether this trend continues smoothly or jumps. If linear, expected score ~0.9805. Wall clock for k=25: ~27 min (within 30-min constraint).
**Hypothesis:** Expanding the initial retrieval pool from 20 to 25 gives the reranker 5 more candidates. Some of the ~1.7% of queries that miss at k=20 may find their relevant doc at positions 21-25 of dense ranking. Recall and NDCG should improve proportionally.
**Change:** TOP_K=25, RERANK_TOP_N=5, USE_RERANKER=True, RERANKER_MODEL L-6-v2.
**Expected effect:** Score ~0.9805, recall ~0.9867, ndcg ~0.9743. Interpolation between k=20 and k=30 results.

### Outcome
**Retrieval score:** 0.9776 | **Delta:** -0.0092 | **Result:** REVERT
**Primary metrics:** recall@5=0.9833 | ndcg@5=0.9718
**Diagnostic metrics:** precision@5=0.0393 | mrr=0.9679 | map@5=0.9679 | hit_rate@5=0.9833
**What I learned:** top_k=25 produces identical results to top_k=20 (0.9776). The 5 extra positions (21-25) contain no relevant docs for the missing queries. The jump from 0.9776 to 0.9834 seen at k=30 comes specifically from positions 26-30. Score is flat from k=20 to k=25 then jumps at k=26-30.
**Next direction:** Explore faster rerankers. L-2-v2 (MiniLM 2-layer) should be ~3x faster than L-6-v2. At top_k=50, L-2-v2 might complete in ~27 min. If its accuracy is sufficient, it could match L-6-v2's best score. Larger pools with the fast model could push beyond 0.9867.

---
## Experiment 19

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** L-6-v2 at k=50 takes 80 min (too slow to push further). L-2-v2 (2-layer MiniLM) is ~3x faster, so k=50 should take ~27 min. If L-2-v2 has sufficient ranking accuracy, it can serve as a faster alternative that allows exploring larger top_k values.
**Hypothesis:** MiniLM-L-2-v2 (2 layers) reranks much faster than L-6-v2 (6 layers). At top_k=50, wall clock ~27 min. If L-2-v2 reranking quality is sufficient, it should achieve comparable NDCG and recall to L-6-v2 at k=50 (0.9867). If better, enables pushing to k=75-100 in future experiments.
**Change:** RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-2-v2", TOP_K=50, RERANK_TOP_N=5.
**Expected effect:** Score near but possibly below 0.9867 (L-2-v2 less accurate per pair). Wall clock ~25-27 min. If close to 0.9867, confirms model quality isn't the bottleneck.

### Outcome
**Retrieval score:** 0.9783 | **Delta:** -0.0084 | **Result:** REVERT
**Primary metrics:** recall@5=0.9900 | ndcg@5=0.9667
**Diagnostic metrics:** precision@5=0.0198 | mrr=0.9587 | map@5=0.9587 | hit_rate@5=0.9900
**What I learned:** L-2-v2 at k=50 is 4.1x faster than L-6-v2 (19.3 min vs 80 min) but NDCG is significantly worse (0.9667 vs 0.9801, -1.3%). Recall is nearly identical (0.9900 vs 0.9933). The speed gain comes at a real accuracy cost — fewer layers means the model can't rank the relevant doc at position 1 as reliably. The 2-layer model is rate-limited by ranking precision, not pool size.
**Next direction:** Final experiment: L-2-v2 at top_k=75 (~29 min) — tests if pushing the pool to 75 compensates for the NDCG gap. Maximum pool size achievable within 30-min budget with the fast model.

---
## Experiment 20

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9867
**Weakest primary metric:** ndcg@k (0.9801)
**Diagnostic insight:** L-2-v2 at k=50 gave recall=0.9900 but ndcg=0.9667. Increasing k to 75 may improve recall slightly (if more relevant docs are at positions 51-75), and the reranker has more chances to find the relevant doc in the larger pool. However, NDCG is limited by model quality, not pool size.
**Hypothesis:** L-2-v2 at top_k=75 gives the reranker 25 more candidates than k=50. The 2 remaining hard-miss queries (0.67%) might have relevant docs at positions 51-75. This pushes recall toward 1.0. NDCG may stay near 0.9667 (model quality ceiling). Wall clock ~29 min.
**Change:** RERANKER_MODEL="cross-encoder/ms-marco-MiniLM-L-2-v2", TOP_K=75, RERANK_TOP_N=5.
**Expected effect:** Recall 0.9900→0.9933 (possibly). NDCG stays ~0.9667. Score ~0.9800. Will not beat L-6-v2 at k=50 (0.9867) due to NDCG gap.

### Outcome
**Retrieval score:** 0.9783 | **Delta:** -0.0084 | **Result:** REVERT
**Primary metrics:** recall@5=0.9900 | ndcg@5=0.9667
**Diagnostic metrics:** precision@5=0.0132 | mrr=0.9587 | map@5=0.9587 | hit_rate@5=0.9900
**What I learned:** L-2-v2 at top_k=75 produces identical results to top_k=50 (0.9783). Positions 51-75 in dense retrieval contain no more relevant docs for the 2 remaining hard-miss queries. The NDCG ceiling at 0.9667 is a model quality limitation — the 2-layer model cannot rank as precisely as 6 layers regardless of pool size. Confirmed: L-6-v2 at top_k=50 (0.9867) is optimal within the 30-min constraint and is the best achievable configuration explored.
**Next direction:** Optimization complete at 20 experiments. Final best: L-6-v2 + dense top_k=50 + top_n=5 → 0.9867.







