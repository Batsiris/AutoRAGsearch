# AutoRAGsearch Final Report: HotpotQA Subset

## Summary

- Dataset: `data/hotpotqa_subset`
- Total experiments run: 14
- LLM calls during optimization: 0
- Convergence: reached after 10 consecutive non-improvements, Experiments 5-14
- Baseline retrieval_score: 0.8903
- Final retrieval_score: 0.9257
- Absolute improvement: +0.0354
- Relative improvement: +4.0%

## Experiments by Phase

| Phase | Experiments | Count | Best contribution |
|---|---:|---:|---:|
| 1-Chunking | 1, 13, 14 | 3 | +0.0000 after baseline |
| 2-Retrieval | 6, 8, 9 | 3 | +0.0000 |
| 3-Reranking | 2, 3, 4, 5, 7, 10, 11, 12 | 8 | +0.0354 |

## Best Configuration

| Parameter | Value |
|---|---|
| Dataset | `data/hotpotqa_subset` |
| Chunking | Fixed |
| Chunk size | 512 tokens |
| Chunk overlap | 50 tokens |
| Embedding model | `all-MiniLM-L6-v2` |
| Retrieval method | Dense ChromaDB cosine |
| Candidate pool | `top_k = 50` |
| Reranker | `cross-encoder/ms-marco-MiniLM-L-6-v2` |
| Final output | `rerank_top_n = 20` |

## Kept Improvements

| Experiment | Change | retrieval_score | Delta |
|---:|---|---:|---:|
| 1 | HotpotQA baseline: fixed 512/50, dense top_k=50, rerank top_n=5 | 0.8903 | N/A |
| 2 | Increase rerank output top_n from 5 to 10 | 0.9156 | +0.0253 |
| 3 | Increase rerank output top_n from 10 to 15 | 0.9218 | +0.0062 |
| 4 | Increase rerank output top_n from 15 to 20 | 0.9257 | +0.0039 |

## Metric Analysis

The baseline already ranked the first relevant document very well: MRR was 0.9588 and hit_rate@k was 0.9950. The weakness was recall@k at 0.8400, which is expected for HotpotQA because most questions need multiple supporting documents.

The winning pattern was to keep a broad dense candidate pool and return more reranked documents. Increasing `rerank_top_n` from 5 to 20 improved recall@k from 0.8400 to 0.9500. NDCG@k declined from 0.9405 to 0.9014, but the recall gain dominated the objective. Final diagnostic metrics stayed strong: MRR 0.9596, MAP@k 0.7765, and hit_rate@k 1.0000.

## Phase Impact

Reranking contributed all measured improvement. Chunking changes had negligible effect because the HotpotQA subset corpus is mostly short documents: median length was 81 tokens and the 95th percentile was about 178 tokens. Retrieval-method changes did not help: BM25 reduced recall substantially, and larger dense candidate pools of 60 and 75 did not surface better final evidence after reranking.

## Top 3 Individual Experiments

| Rank | Experiment | Impact | Interpretation |
|---:|---:|---:|---|
| 1 | 2 | +0.0253 | Moving from top_n=5 to 10 recovered many second supporting documents. |
| 2 | 3 | +0.0062 | top_n=15 added more recall while the NDCG penalty was still modest. |
| 3 | 4 | +0.0039 | top_n=20 reached the best recall/NDCG tradeoff. |

## Recommendations

- Keep the final HotpotQA configuration at dense top_k=50 with cross-encoder rerank_top_n=20.
- If further optimization is allowed, test a stronger cross-encoder on GPU; CPU reranking was the runtime bottleneck.
- Consider a deduplication-aware metric or pipeline option if repeated chunks from the same document become an issue on longer corpora.
- For this subset, do not spend more time on chunk-size tuning unless the corpus changes to include longer source documents.
