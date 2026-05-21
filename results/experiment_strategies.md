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

---
## Experiment 3

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9156
**Weakest primary metric:** recall@k
**Diagnostic insight:** Increasing top_n to 10 gave perfect hit rate and much higher recall while preserving MRR, so the reranker is ranking first evidence well but still may be excluding second supporting documents.
**Hypothesis:** Increasing top_n to 15 will capture additional relevant HotpotQA supports, and the recall gain may still exceed any NDCG loss from including more lower-ranked items.
**Change:** Increase RERANK_TOP_N from 10 to 15 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** recall@k should improve by 0.01-0.04; ndcg@k may decline by 0.01-0.03, with a possible small net gain if missing supports are recovered.

### Outcome
**Retrieval score:** 0.9218 | **Delta:** +0.0062 | **Result:** KEEP
**Primary metrics:** recall@k=0.9350 | ndcg@k=0.9086
**Diagnostic metrics:** precision@k=0.0374 | mrr=0.9596 | map@k=0.7747 | hit_rate@k=1.0000
**What I learned:** Top_n=15 recovers more supporting documents and still beats the NDCG loss. The smaller delta suggests the output-size curve is approaching its optimum.
**Next direction:** Test top_n=20 to see whether the remaining recall headroom is still worth the ranking dilution.

---
## Experiment 4

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9218
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Recall improved to 0.9350 at top_n=15, while NDCG fell to 0.9086 and became the weaker primary metric. MRR stayed high, so the first relevant document remains near the top.
**Hypothesis:** Increasing top_n to 20 may recover a few more second supporting documents, but the score will only improve if that recall gain is larger than the additional NDCG dilution.
**Change:** Increase RERANK_TOP_N from 15 to 20 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** recall@k may improve by 0.005-0.025; ndcg@k may drop by 0.01-0.03, so this is likely near the tradeoff boundary.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** +0.0039 | **Result:** KEEP
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9014
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7765 | hit_rate@k=1.0000
**What I learned:** Top_n=20 still improves the composite by adding enough supporting-document recall to offset lower NDCG. The diminishing delta suggests the next larger output may be the turning point.
**Next direction:** Test top_n=25; if it fails, bracket the optimum between 15 and 25 with smaller steps.

---
## Experiment 5

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Top_n=20 pushed recall to 0.9500 but ndcg@k is now near 0.90. MRR is unchanged, so the main risk is lower-ranked noise rather than losing top-hit quality.
**Hypothesis:** Top_n=25 may recover a small amount of remaining recall, but the NDCG penalty may now exceed the benefit.
**Change:** Increase RERANK_TOP_N from 20 to 25 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** recall@k may rise slightly toward the first-stage ceiling; ndcg@k likely falls enough that this may be a REVERT.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9014
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7765 | hit_rate@k=1.0000
**What I learned:** Top_n=25 returns the same relevant document set as top_n=20 on this benchmark, so it does not improve the objective. The best output size remains 20.
**Next direction:** Keep top_n=20 and test whether a larger dense candidate pool can surface missing supporting documents before reranking.

---
## Experiment 6

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Top_n=20 appears to saturate output recall for the top-50 dense pool. Remaining recall failures may be first-stage misses rather than reranker filtering.
**Hypothesis:** Increasing dense TOP_K from 50 to 75 will expose additional supporting documents to the reranker, potentially improving recall while the cross-encoder preserves good ordering in the top 20.
**Change:** Increase TOP_K from 50 to 75 while keeping RERANK_TOP_N=20 and the same dense retriever/reranker.
**Expected effect:** recall@k may improve by 0.005-0.02 if missing supports are in ranks 51-75; ndcg@k could stay similar or fall if new distractors are promoted.

### Outcome
**Retrieval score:** 0.9254 | **Delta:** -0.0004 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9007
**Diagnostic metrics:** precision@k=0.0253 | mrr=0.9596 | map@k=0.7752 | hit_rate@k=1.0000
**What I learned:** A larger dense pool did not recover additional relevant documents in the final top 20 and slightly degraded ranking. The remaining misses are not solved by simply expanding dense top_k to 75.
**Next direction:** Return to TOP_K=50 and probe nearby output-size or retrieval-method alternatives.

---
## Experiment 7

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Top_n=20 is best so far, while top_n=25 tied it exactly and TOP_K=75 did not help. A nearby smaller top_n might preserve recall while improving NDCG.
**Hypothesis:** Setting top_n=18 may remove a little tail noise and improve NDCG without losing many relevant supporting docs, potentially beating top_n=20.
**Change:** Decrease RERANK_TOP_N from 20 to 18 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** ndcg@k may improve by 0.002-0.01; recall@k may drop by 0.000-0.01, with a possible small net gain.

### Outcome
**Retrieval score:** 0.9251 | **Delta:** -0.0006 | **Result:** REVERT
**Primary metrics:** recall@k=0.9475 | ndcg@k=0.9027
**Diagnostic metrics:** precision@k=0.0379 | mrr=0.9596 | map@k=0.7762 | hit_rate@k=1.0000
**What I learned:** Top_n=18 recovers a little NDCG but loses enough recall to fall below top_n=20. The current best sits at the recall-heavy edge of the reranked output-size curve.
**Next direction:** Evaluate retrieval-method or chunking alternatives; corpus length inspection shows most documents are short, so retrieval method is more likely than chunk size to matter.

---
## Experiment 8

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Dense retrieval with reranking has perfect hit rate, but recall tops out at 0.9500 in the final 20. HotpotQA questions often contain exact entity names where lexical retrieval may surface different supporting documents.
**Hypothesis:** BM25 may retrieve entity-matched supporting documents that dense retrieval ranks lower or misses, and the cross-encoder can then reorder them into a useful top 20.
**Change:** Change RETRIEVAL_METHOD from dense to bm25 while keeping TOP_K=50, RERANK_TOP_N=20, and the same cross-encoder.
**Expected effect:** Recall may improve for exact-match questions but NDCG may fall if BM25 brings more lexical distractors; this is exploratory.

### Outcome
**Retrieval score:** 0.8905 | **Delta:** -0.0353 | **Result:** REVERT
**Primary metrics:** recall@k=0.8725 | ndcg@k=0.9084
**Diagnostic metrics:** precision@k=0.0349 | mrr=0.9477 | map@k=0.7321 | hit_rate@k=0.9950
**What I learned:** BM25 loses too many supporting documents compared with dense retrieval, even after reranking. HotpotQA's entity matches are not enough to compensate for dense semantic recall on this subset.
**Next direction:** Keep dense retrieval and probe candidate-depth or reranker variants rather than pure lexical retrieval.

---
## Experiment 9

**Phase:** 2-Retrieval
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** TOP_K=75 did not help, but it may have introduced too much tail noise. A smaller increase could recover a few missing supports with less reranking distraction.
**Hypothesis:** TOP_K=60 may expose useful candidates just beyond rank 50 while avoiding the extra noise seen at 75.
**Change:** Increase TOP_K from 50 to 60 while keeping dense retrieval, RERANK_TOP_N=20, and the same cross-encoder.
**Expected effect:** recall@k may improve slightly if missing supports are in ranks 51-60; ndcg@k should be less affected than TOP_K=75.

### Outcome
**Retrieval score:** 0.9250 | **Delta:** -0.0008 | **Result:** REVERT
**Primary metrics:** recall@k=0.9475 | ndcg@k=0.9024
**Diagnostic metrics:** precision@k=0.0316 | mrr=0.9596 | map@k=0.7759 | hit_rate@k=1.0000
**What I learned:** TOP_K=60 also fails to improve, and recall falls relative to TOP_K=50. The best candidate depth remains 50 for this reranker/output-size setting.
**Next direction:** Test whether the reranker is essential, then probe tight top_n and chunking alternatives.

---
## Experiment 10

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** The cross-encoder has preserved high MRR across top_n settings. A no-reranker ablation will show whether dense order alone can support top_n=20 or whether reranking is essential.
**Hypothesis:** Removing the reranker will reduce NDCG and MAP because dense retrieval order is less precise, even if recall stays acceptable.
**Change:** Set USE_RERANKER from True to False while keeping dense TOP_K=50 and RERANK_TOP_N=20.
**Expected effect:** ndcg@k and mrr should drop; recall may stay moderate if dense top-20 contains supports, but the composite should be worse.

### Outcome
**Retrieval score:** 0.8861 | **Delta:** -0.0397 | **Result:** REVERT
**Primary metrics:** recall@k=0.9225 | ndcg@k=0.8496
**Diagnostic metrics:** precision@k=0.0369 | mrr=0.8933 | map@k=0.6906 | hit_rate@k=0.9950
**What I learned:** The reranker is essential for ranking quality on HotpotQA; dense order alone loses substantial NDCG, MRR, and MAP. The best configuration should keep cross-encoder reranking.
**Next direction:** Keep the reranker and test nearby top_n or chunking settings.

---
## Experiment 11

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Top_n=25 tied top_n=20, while top_n=18 was slightly worse. Testing the immediate upper neighbor checks whether there is any useful support exactly at rank 21.
**Hypothesis:** Top_n=21 will likely tie top_n=20; if it improves, the optimum is just above 20.
**Change:** Increase RERANK_TOP_N from 20 to 21 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** Metrics should be identical or nearly identical to top_n=20; any extra relevant document at rank 21 would slightly raise recall.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9014
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7765 | hit_rate@k=1.0000
**What I learned:** Top_n=21 ties top_n=20 exactly, so rank 21 adds no relevant documents in this evaluation. The smallest equivalent best output remains top_n=20.
**Next direction:** Test the immediate lower neighbor, then move to chunking alternatives if it does not improve.

---
## Experiment 12

**Phase:** 3-Reranking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Top_n=18 was slightly worse, top_n=21 tied top_n=20, and top_n=20 remains the smallest known best. Rank 20 may contain a relevant support that rank 18 excludes.
**Hypothesis:** Top_n=19 may either match top_n=20 if rank 20 is not relevant, or trail slightly if rank 20 contains one needed support.
**Change:** Decrease RERANK_TOP_N from 20 to 19 while keeping dense TOP_K=50 and the same cross-encoder.
**Expected effect:** Metrics may tie top_n=20 or fall by a very small recall amount; a tie would prefer top_n=19 as the smaller output.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9014
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7765 | hit_rate@k=1.0000
**What I learned:** Top_n=19 ties top_n=20 exactly, so the metric plateau begins below 20. The protocol still keeps the existing best because this is not a strict score improvement.
**Next direction:** Move to chunking experiments; most documents are short, but smaller chunks may affect the long tail.

---
## Experiment 13

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Corpus inspection shows most HotpotQA documents are short, but the longest documents exceed 512 tokens. Smaller chunks may sharpen dense retrieval and reranking for that long tail.
**Hypothesis:** Reducing chunk size to 256 can improve ranking focus for long documents while leaving most documents unchanged, potentially increasing NDCG without sacrificing recall.
**Change:** Decrease CHUNK_SIZE from 512 to 256 while keeping fixed chunking, overlap 50, dense TOP_K=50, and RERANK_TOP_N=20.
**Expected effect:** Slight NDCG improvement is possible for long documents; recall may remain similar because most documents are shorter than both chunk sizes.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** -0.0001 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9013
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7763 | hit_rate@k=1.0000
**What I learned:** Smaller chunks barely changed the outcome and slightly reduced NDCG/MAP. Because most documents are already short, chunk-size reduction does not materially alter the retrieval problem.
**Next direction:** Test larger chunks to confirm chunking is not an active improvement axis for this HotpotQA subset.

---
## Experiment 14

**Phase:** 1-Chunking
**Current best retrieval_score:** 0.9257
**Weakest primary metric:** ndcg@k
**Diagnostic insight:** Reducing chunk size to 256 had negligible impact. Since 95% of documents are under roughly 178 tokens, larger chunks should mostly leave the corpus unchanged except for a few long documents.
**Hypothesis:** Increasing chunk size to 1024 will not improve the score because most documents already fit in the baseline chunk size, and larger long-document chunks may add noise.
**Change:** Increase CHUNK_SIZE from 512 to 1024 while keeping fixed chunking, overlap 50, dense TOP_K=50, and RERANK_TOP_N=20.
**Expected effect:** Metrics should tie or slightly trail the current best; a non-improvement would confirm chunking convergence for this subset.

### Outcome
**Retrieval score:** 0.9257 | **Delta:** +0.0000 | **Result:** REVERT
**Primary metrics:** recall@k=0.9500 | ndcg@k=0.9014
**Diagnostic metrics:** precision@k=0.0380 | mrr=0.9596 | map@k=0.7765 | hit_rate@k=1.0000
**What I learned:** Larger chunks tie the current best because nearly all documents already fit inside the baseline 512-token chunks. Chunking is not a meaningful improvement axis for this HotpotQA subset.
**Next direction:** Stop the loop: this is the 10th consecutive non-improvement after Experiment 4, satisfying the convergence criterion.
