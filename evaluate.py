"""AutoRAGsearch evaluation harness. DO NOT MODIFY.

Usage:
    python evaluate.py                                   # classical metrics (default)
    python evaluate.py --mode classical                  # explicit classical
    python evaluate.py --mode ragas                      # RAGAS + classical
    python evaluate.py --data-dir data/hotpotqa_subset   # different dataset
"""

import argparse
import json
import os
import sys
import time

# Check for GOOGLE_API_KEY before anything else
if not os.environ.get("GOOGLE_API_KEY"):
    print("ERROR: GOOGLE_API_KEY not set. Get a free key at https://aistudio.google.com/")
    print("Then: export GOOGLE_API_KEY='your-key-here'")
    sys.exit(1)

DEFAULT_DATA_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "data", "nq_subset")
RESULTS_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "results")
BEST_CONFIG_PATH = os.path.join(RESULTS_DIR, "best_config.json")


def main():
    parser = argparse.ArgumentParser(description="AutoRAGsearch evaluator")
    parser.add_argument("--data-dir", default=DEFAULT_DATA_DIR,
                        help="Path to directory containing qa.parquet and corpus.parquet")
    parser.add_argument("--mode", default="classical", choices=["classical", "ragas"],
                        help="Evaluation mode: 'classical' (default) or 'ragas'")
    args = parser.parse_args()

    from utils.data_loader import load_dataset
    from rag_pipeline import run_pipeline, get_config

    qa_df, corpus_df = load_dataset(args.data_dir)

    # Build ground-truth doc ID map: for each question, what doc_ids are relevant?
    # We match ground_truth_contexts text against corpus to find doc_ids
    corpus_text_to_id = {row["text"]: row["doc_id"] for _, row in corpus_df.iterrows()}

    start_time = time.time()
    samples = []
    all_retrieved_doc_ids = []
    all_ground_truth_doc_ids = []
    llm_calls = 0

    for _, row in qa_df.iterrows():
        question = row["question"]
        ground_truth_answer = row["ground_truth_answer"]
        gt_contexts = row["ground_truth_contexts"]
        if not isinstance(gt_contexts, list):
            gt_contexts = [str(gt_contexts)]

        # Map ground-truth context texts to doc IDs
        gt_doc_ids = []
        for ctx_text in gt_contexts:
            doc_id = corpus_text_to_id.get(ctx_text)
            if doc_id:
                gt_doc_ids.append(doc_id)

        answer, contexts, retrieved_doc_ids = run_pipeline(question)
        llm_calls += 1

        samples.append({
            "question": question,
            "answer": answer,
            "contexts": contexts,
            "ground_truth": ground_truth_answer,
        })
        all_retrieved_doc_ids.append(retrieved_doc_ids)
        all_ground_truth_doc_ids.append(gt_doc_ids)

    wall_clock = time.time() - start_time

    # Classical metrics
    from utils.classical_metrics import (
        compute_retrieval_metrics,
        compute_generation_metrics,
        compute_composite_score,
    )
    from rag_pipeline import TOP_K

    retrieval_metrics = compute_retrieval_metrics(
        all_retrieved_doc_ids, all_ground_truth_doc_ids, k=TOP_K
    )
    generation_metrics = compute_generation_metrics(
        [s["answer"] for s in samples],
        [s["ground_truth"] for s in samples],
    )
    composite = compute_composite_score(retrieval_metrics, generation_metrics)

    # Print output
    print("===== AUTORAGSEARCH EVALUATION =====")
    print(f"MODE:                {args.mode}")
    print(f"COMPOSITE_SCORE:     {composite:.4f}")
    print("--- Retrieval Metrics ---")
    print(f"RECALL@K:            {retrieval_metrics['recall_at_k']:.4f}")
    print(f"PRECISION@K:         {retrieval_metrics['precision_at_k']:.4f}")
    print(f"MRR:                 {retrieval_metrics['mrr']:.4f}")
    print(f"NDCG@K:              {retrieval_metrics['ndcg_at_k']:.4f}")
    print("--- Generation Metrics ---")
    print(f"F1:                  {generation_metrics['f1']:.4f}")
    print(f"EXACT_MATCH:         {generation_metrics['exact_match']:.4f}")
    print(f"ROUGE_L:             {generation_metrics['rouge_l']:.4f}")
    print(f"BERTSCORE_F1:        {generation_metrics['bertscore_f1']:.4f}")

    ragas_scores = None
    if args.mode == "ragas":
        from utils.ragas_eval import evaluate_ragas
        ragas_scores = evaluate_ragas(samples)
        print("--- RAGAS Metrics ---")
        print(f"FAITHFULNESS:        {ragas_scores.get('faithfulness', 0.0):.4f}")
        print(f"ANSWER_CORRECTNESS:  {ragas_scores.get('answer_correctness', 0.0):.4f}")
        print(f"CONTEXT_RECALL:      {ragas_scores.get('context_recall', 0.0):.4f}")
        print(f"CONTEXT_PRECISION:   {ragas_scores.get('context_precision', 0.0):.4f}")
        print(f"ANSWER_RELEVANCY:    {ragas_scores.get('answer_relevancy', 0.0):.4f}")
        print(f"ANSWER_SIMILARITY:   {ragas_scores.get('answer_similarity', 0.0):.4f}")

    print("--- Meta ---")
    print(f"WALL_CLOCK_SECONDS:  {wall_clock:.1f}")
    print(f"NUM_SAMPLES:         {len(samples)}")
    print(f"LLM_CALLS:           {llm_calls}")
    print("====================================")

    # Save best config if improved
    os.makedirs(RESULTS_DIR, exist_ok=True)
    best_score = -1.0
    if os.path.exists(BEST_CONFIG_PATH):
        try:
            with open(BEST_CONFIG_PATH) as f:
                best_data = json.load(f)
            best_score = best_data.get("composite_score", -1.0)
        except Exception:
            pass

    if composite > best_score:
        config = get_config()
        config["composite_score"] = composite
        config.update(retrieval_metrics)
        config.update(generation_metrics)
        with open(BEST_CONFIG_PATH, "w") as f:
            json.dump(config, f, indent=2)
        print(f"[INFO] New best config saved (score: {composite:.4f})")


if __name__ == "__main__":
    main()
