import math
import pandas as pd
from pathlib import Path

RUNS = {
    "autorag_bm25_top5": Path(r".\my_hotpotqa_subset_autorag_result\0\retrieval_only\lexical_retrieval\best_0.parquet"),
    "autorag_bm25_top50": Path(r".\my_hotpotqa_subset_autorag_top50_result\0\retrieval_only\lexical_retrieval\best_0.parquet"),
}

def flatten_ids(x):
    """
    Recursively flatten nested lists / tuples / numpy arrays / pandas objects
    into a simple list of string document IDs.
    """
    if x is None:
        return []

    if hasattr(x, "tolist"):
        x = x.tolist()

    if isinstance(x, (list, tuple, set)):
        result = []
        for item in x:
            result.extend(flatten_ids(item))
        return result

    return [str(x)]

def reciprocal_rank(gt, pred):
    gt = set(flatten_ids(gt))
    pred = flatten_ids(pred)

    for rank, doc_id in enumerate(pred, start=1):
        if doc_id in gt:
            return 1.0 / rank

    return 0.0

def hit_rate(gt, pred):
    gt = set(flatten_ids(gt))
    pred = flatten_ids(pred)

    return 1.0 if any(doc_id in gt for doc_id in pred) else 0.0

def average_precision(gt, pred):
    gt = set(flatten_ids(gt))
    pred = flatten_ids(pred)

    if not gt:
        return 0.0

    hits = 0
    score = 0.0

    for rank, doc_id in enumerate(pred, start=1):
        if doc_id in gt:
            hits += 1
            score += hits / rank

    return score / len(gt)

def ndcg(gt, pred):
    gt = set(flatten_ids(gt))
    pred = flatten_ids(pred)

    if not gt:
        return 0.0

    dcg = 0.0

    for rank, doc_id in enumerate(pred, start=1):
        if doc_id in gt:
            dcg += 1.0 / math.log2(rank + 1)

    ideal_hits = min(len(gt), len(pred))
    idcg = sum(1.0 / math.log2(rank + 1) for rank in range(1, ideal_hits + 1))

    return dcg / idcg if idcg > 0 else 0.0

def compute_metrics(name, path):
    print("=" * 80)
    print(name)
    print("File:", path)

    df = pd.read_parquet(path)
    pred_col = "retrieved_ids_lexical"

    native = df[["retrieval_precision", "retrieval_recall", "retrieval_f1"]].mean()

    mrr = df.apply(lambda r: reciprocal_rank(r["retrieval_gt"], r[pred_col]), axis=1).mean()
    hit = df.apply(lambda r: hit_rate(r["retrieval_gt"], r[pred_col]), axis=1).mean()
    map_k = df.apply(lambda r: average_precision(r["retrieval_gt"], r[pred_col]), axis=1).mean()
    ndcg_k = df.apply(lambda r: ndcg(r["retrieval_gt"], r[pred_col]), axis=1).mean()

    full_recall_count = int((df["retrieval_recall"] == 1.0).sum())
    full_recall_percent = round((df["retrieval_recall"] == 1.0).mean() * 100, 2)

    result = {
        "system": name,
        "questions": len(df),
        "retrieval_precision": native["retrieval_precision"],
        "retrieval_recall": native["retrieval_recall"],
        "retrieval_f1": native["retrieval_f1"],
        "mrr": mrr,
        "ndcg_at_k": ndcg_k,
        "map_at_k": map_k,
        "hit_rate_at_k": hit,
        "full_recall_count": full_recall_count,
        "full_recall_percent": full_recall_percent,
    }

    for k, v in result.items():
        print(f"{k}: {v}")

    return result

all_results = []

for name, path in RUNS.items():
    all_results.append(compute_metrics(name, path))

out_df = pd.DataFrame(all_results)
out_path = Path(r".\autorag_extra_metrics_summary.csv")
out_df.to_csv(out_path, index=False)

print("=" * 80)
print("Saved summary to:", out_path)
print(out_df.to_string(index=False))