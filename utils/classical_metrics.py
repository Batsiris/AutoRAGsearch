"""Classical evaluation metrics — computed locally, no LLM calls.

Retrieval metrics: Recall@k, Precision@k, MRR, NDCG@k
Generation metrics: F1, Exact Match, ROUGE-L, BERTScore F1

Composite score:
  composite = 0.20 * recall_at_k
            + 0.15 * precision_at_k
            + 0.10 * mrr
            + 0.10 * ndcg_at_k
            + 0.20 * f1
            + 0.10 * exact_match
            + 0.05 * rouge_l
            + 0.10 * bertscore_f1
"""

import math
import re
import string
import logging
from typing import List, Dict

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Retrieval Metrics
# ---------------------------------------------------------------------------

def compute_retrieval_metrics(
    retrieved_doc_ids: List[List[str]],
    ground_truth_doc_ids: List[List[str]],
    k: int,
) -> Dict[str, float]:
    """Compute retrieval metrics by comparing retrieved doc IDs against ground-truth.

    Args:
        retrieved_doc_ids: For each query, doc IDs returned by retriever in ranked order.
        ground_truth_doc_ids: For each query, the ground-truth relevant doc IDs.
        k: Top-k cutoff used for retrieval.

    Returns:
        dict with keys: recall_at_k, precision_at_k, mrr, ndcg_at_k
    """
    recalls, precisions, mrrs, ndcgs = [], [], [], []

    for retrieved, relevant in zip(retrieved_doc_ids, ground_truth_doc_ids):
        if not relevant:
            continue

        relevant_set = set(relevant)
        top_k = retrieved[:k]
        hits = [1 if doc_id in relevant_set else 0 for doc_id in top_k]

        # Recall@k
        recall = sum(hits) / len(relevant_set)
        recalls.append(recall)

        # Precision@k
        precision = sum(hits) / k if k > 0 else 0.0
        precisions.append(precision)

        # MRR
        mrr = 0.0
        for rank, doc_id in enumerate(retrieved, start=1):
            if doc_id in relevant_set:
                mrr = 1.0 / rank
                break
        mrrs.append(mrr)

        # NDCG@k
        dcg = sum(hits[i] / math.log2(i + 2) for i in range(len(hits)))
        ideal_hits = sorted(hits, reverse=True)
        idcg = sum(ideal_hits[i] / math.log2(i + 2) for i in range(len(ideal_hits)))
        ndcg = dcg / idcg if idcg > 0 else 0.0
        ndcgs.append(ndcg)

    maps, hit_rates = [], []

    for retrieved, relevant in zip(retrieved_doc_ids, ground_truth_doc_ids):
        if not relevant:
            continue

        relevant_set = set(relevant)
        top_k = retrieved[:k]

        # MAP@k
        num_hits = 0
        sum_precision = 0.0
        for i, doc_id in enumerate(top_k, start=1):
            if doc_id in relevant_set:
                num_hits += 1
                sum_precision += num_hits / i
        map_k = sum_precision / len(relevant_set)
        maps.append(map_k)

        # Hit Rate@k
        hit = 1.0 if any(doc_id in relevant_set for doc_id in top_k) else 0.0
        hit_rates.append(hit)

    def _mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    return {
        "recall_at_k": _mean(recalls),
        "precision_at_k": _mean(precisions),
        "mrr": _mean(mrrs),
        "ndcg_at_k": _mean(ndcgs),
        "map_at_k": _mean(maps),
        "hit_rate_at_k": _mean(hit_rates),
    }


# ---------------------------------------------------------------------------
# Generation Metrics
# ---------------------------------------------------------------------------

def _normalize(text: str) -> str:
    """Lowercase, strip punctuation and extra whitespace."""
    text = text.lower()
    text = text.translate(str.maketrans("", "", string.punctuation))
    text = re.sub(r"\s+", " ", text).strip()
    return text


def _token_f1(prediction: str, reference: str) -> float:
    pred_tokens = _normalize(prediction).split()
    ref_tokens = _normalize(reference).split()
    if not pred_tokens or not ref_tokens:
        return 0.0
    pred_set = set(pred_tokens)
    ref_set = set(ref_tokens)
    common = pred_set & ref_set
    if not common:
        return 0.0
    precision = len(common) / len(pred_set)
    recall = len(common) / len(ref_set)
    return 2 * precision * recall / (precision + recall)


def compute_generation_metrics(
    predictions: List[str],
    references: List[str],
) -> Dict[str, float]:
    """Compute generation quality metrics.

    Args:
        predictions: Generated answers.
        references: Ground-truth answers.

    Returns:
        dict with keys: f1, exact_match, rouge_l, bertscore_f1
    """
    from rouge_score import rouge_scorer

    f1_scores, em_scores, rouge_scores = [], [], []

    scorer = rouge_scorer.RougeScorer(["rougeL"], use_stemmer=True)

    for pred, ref in zip(predictions, references):
        if not pred:
            pred = ""
        if not ref:
            ref = ""

        f1_scores.append(_token_f1(pred, ref))
        em_scores.append(1.0 if _normalize(pred) == _normalize(ref) else 0.0)
        rouge_result = scorer.score(ref, pred)
        rouge_scores.append(rouge_result["rougeL"].fmeasure)

    # BERTScore
    try:
        from bert_score import score as bert_score_fn
        P, R, F = bert_score_fn(
            predictions,
            references,
            model_type="distilbert-base-uncased",
            verbose=False,
        )
        bertscore_f1 = float(F.mean())
    except Exception as e:
        logger.warning("BERTScore failed (%s), substituting 0.0", e)
        bertscore_f1 = 0.0

    def _mean(lst):
        return sum(lst) / len(lst) if lst else 0.0

    return {
        "f1": _mean(f1_scores),
        "exact_match": _mean(em_scores),
        "rouge_l": _mean(rouge_scores),
        "bertscore_f1": bertscore_f1,
    }


# ---------------------------------------------------------------------------
# Composite Score
# ---------------------------------------------------------------------------

def compute_composite_score(
    retrieval_metrics: Dict[str, float],
    generation_metrics: Dict[str, float],
) -> float:
    """Combine retrieval and generation metrics into a single scalar."""
    return (
        0.20 * retrieval_metrics["recall_at_k"] +
        0.15 * retrieval_metrics["precision_at_k"] +
        0.10 * retrieval_metrics["mrr"] +
        0.10 * retrieval_metrics["ndcg_at_k"] +
        0.20 * generation_metrics["f1"] +
        0.10 * generation_metrics["exact_match"] +
        0.05 * generation_metrics["rouge_l"] +
        0.10 * generation_metrics["bertscore_f1"]
    )
