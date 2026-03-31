"""AutoRAGsearch evaluation harness. DO NOT MODIFY.

Usage:
    python evaluate.py
    python evaluate.py --data-dir data/hotpotqa_subset
    python evaluate.py --experiment-id 1 --phase 1-Chunking --description "baseline"
"""

import argparse
import json
import os
import time

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nq_subset")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
BEST_CONFIG_PATH = os.path.join(RESULTS_DIR, "best_config.json")


def main():
    parser = argparse.ArgumentParser(description="AutoRAGsearch evaluator")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                        help="Path to directory containing qa.parquet and corpus.parquet")
    parser.add_argument("--experiment-id", type=int, default=0,
                        help="Sequential experiment ID")
    parser.add_argument("--phase", default="1-Chunking",
                        help="Experiment phase label")
    parser.add_argument("--description", default="(no description)",
                        help="What changed and why")
    args = parser.parse_args()

    from utils.data_loader import load_dataset
    from rag_pipeline import run_pipeline, get_config, TOP_K

    qa_df, corpus_df = load_dataset(args.data_dir)
    # Evaluate ALL samples — no head() truncation

    # Build ground-truth doc ID map: corpus text → doc_id
    corpus_text_to_id = {row["text"]: row["doc_id"] for _, row in corpus_df.iterrows()}

    start_time = time.time()
    all_retrieved_doc_ids = []
    all_ground_truth_doc_ids = []

    for _, row in qa_df.iterrows():
        question = row["question"]
        gt_contexts = row["ground_truth_contexts"]
        if not isinstance(gt_contexts, (list, tuple)):
            if hasattr(gt_contexts, "__iter__") and not isinstance(gt_contexts, str):
                gt_contexts = list(gt_contexts)
            else:
                gt_contexts = [str(gt_contexts)]

        gt_doc_ids = []
        for ctx_text in gt_contexts:
            doc_id = corpus_text_to_id.get(ctx_text)
            if doc_id:
                gt_doc_ids.append(doc_id)

        contexts, retrieved_doc_ids = run_pipeline(question)
        all_retrieved_doc_ids.append(retrieved_doc_ids)
        all_ground_truth_doc_ids.append(gt_doc_ids)

    wall_clock = time.time() - start_time
    num_samples = len(qa_df)

    from utils.classical_metrics import compute_retrieval_metrics

    metrics = compute_retrieval_metrics(all_retrieved_doc_ids, all_ground_truth_doc_ids, k=TOP_K)
    retrieval_score = 0.50 * metrics["recall_at_k"] + 0.50 * metrics["ndcg_at_k"]

    # Load current best
    best_score = -1.0
    if os.path.exists(BEST_CONFIG_PATH):
        try:
            with open(BEST_CONFIG_PATH) as f:
                best_data = json.load(f)
            best_score = best_data.get("retrieval_score", -1.0)
        except Exception:
            pass

    delta = retrieval_score - best_score if best_score >= 0.0 else retrieval_score
    delta_str = f"{delta:+.4f}" if best_score >= 0.0 else "N/A (first run)"

    print("===== AUTORAGSEARCH EXPERIMENT =====")
    print(f"EXPERIMENT_ID:       {args.experiment_id}")
    print(f"PHASE:               {args.phase}")
    print(f"DESCRIPTION:         {args.description}")
    print(f"RETRIEVAL_SCORE:     {retrieval_score:.4f}")
    print("--- Primary Metrics (in optimization target) ---")
    print(f"RECALL@K:            {metrics['recall_at_k']:.4f}")
    print(f"NDCG@K:              {metrics['ndcg_at_k']:.4f}")
    print("--- Diagnostic Metrics (not in optimization target) ---")
    print(f"PRECISION@K:         {metrics['precision_at_k']:.4f}")
    print(f"MRR:                 {metrics['mrr']:.4f}")
    print(f"MAP@K:               {metrics['map_at_k']:.4f}")
    print(f"HIT_RATE@K:          {metrics['hit_rate_at_k']:.4f}")
    print("--- Experiment Info ---")
    print(f"NUM_EVAL_SAMPLES:    {num_samples}")
    print(f"LLM_CALLS:           0")
    print(f"WALL_CLOCK_SECONDS:  {wall_clock:.1f}")
    print(f"DELTA_VS_BEST:       {delta_str}")
    print(f"RESULT:              {'KEEP' if retrieval_score > best_score else 'REVERT'}")
    print(f"REASONING:           (fill in after reviewing metrics)")
    print("====================================")

    # Save best config if improved
    os.makedirs(RESULTS_DIR, exist_ok=True)
    if retrieval_score > best_score:
        config = get_config()
        config["retrieval_score"] = retrieval_score
        config.update(metrics)
        with open(BEST_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"[INFO] New best config saved (retrieval_score: {retrieval_score:.4f})")


if __name__ == "__main__":
    main()
