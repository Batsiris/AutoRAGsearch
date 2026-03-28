"""RAGAS evaluation wrapper — optional deep-analysis mode (--mode ragas).

Uses Google Gemini as the LLM judge and local HuggingFace embeddings.
Includes rate-limit handling with a 7-second delay between samples.

Composite score formula (RAGAS):
  composite = 0.25 * faithfulness
            + 0.20 * answer_correctness
            + 0.20 * context_recall
            + 0.15 * context_precision
            + 0.10 * answer_relevancy
            + 0.10 * answer_similarity
"""

import logging
import time
import warnings
from typing import List, Dict, Any

logger = logging.getLogger(__name__)

RAGAS_WEIGHTS = {
    "faithfulness": 0.25,
    "answer_correctness": 0.20,
    "context_recall": 0.20,
    "context_precision": 0.15,
    "answer_relevancy": 0.10,
    "answer_similarity": 0.10,
}


def evaluate_ragas(samples: List[Dict[str, Any]]) -> Dict[str, float]:
    """Run RAGAS evaluation on a list of samples using Gemini as judge.

    Each sample must have:
        - question (str)
        - answer (str)
        - contexts (list of str)
        - ground_truth (str)

    Returns a dict with individual metric scores and 'composite'.
    """
    import os
    from datasets import Dataset

    try:
        from ragas.metrics import (
            faithfulness,
            answer_correctness,
            context_recall,
            context_precision,
            answer_relevancy,
        )
        try:
            from ragas.metrics import answer_similarity
        except ImportError:
            from ragas.metrics import SemanticSimilarity as answer_similarity
        metrics = [
            faithfulness,
            answer_correctness,
            context_recall,
            context_precision,
            answer_relevancy,
            answer_similarity,
        ]
    except ImportError as e:
        raise ImportError(f"RAGAS not installed. Run: pip install ragas\n{e}")

    from ragas import evaluate

    # Configure Gemini as LLM judge
    try:
        from langchain_google_genai import ChatGoogleGenerativeAI
        from ragas.llms import LangchainLLMWrapper
        llm = LangchainLLMWrapper(
            ChatGoogleGenerativeAI(
                model="gemini-2.5-flash",
                temperature=0.0,
                google_api_key=os.environ.get("GOOGLE_API_KEY"),
            )
        )
        for metric in metrics:
            if hasattr(metric, "llm"):
                metric.llm = llm
    except Exception as e:
        logger.warning("Could not configure Gemini for RAGAS: %s. Using default LLM.", e)

    # Configure local embeddings for metrics that need them
    try:
        from langchain_community.embeddings import HuggingFaceEmbeddings
        from ragas.embeddings import LangchainEmbeddingsWrapper
        embeddings = LangchainEmbeddingsWrapper(
            HuggingFaceEmbeddings(model_name="all-MiniLM-L6-v2")
        )
        for metric in metrics:
            if hasattr(metric, "embeddings"):
                metric.embeddings = embeddings
    except Exception as e:
        logger.warning("Could not configure local embeddings for RAGAS: %s", e)

    print(f"Running RAGAS evaluation on {len(samples)} samples...")
    print("(7-second delay between batches for rate limiting)")

    data = {
        "question": [s["question"] for s in samples],
        "answer": [s["answer"] for s in samples],
        "contexts": [s["contexts"] for s in samples],
        "ground_truth": [s["ground_truth"] for s in samples],
    }
    dataset = Dataset.from_dict(data)

    # Run in small batches with rate-limit delay
    batch_size = 10
    all_results = []

    for i in range(0, len(samples), batch_size):
        batch = dataset.select(range(i, min(i + batch_size, len(samples))))
        print(f"  Evaluating samples {i+1}-{min(i+batch_size, len(samples))}...")
        with warnings.catch_warnings():
            warnings.simplefilter("ignore")
            result = evaluate(batch, metrics=metrics)
        all_results.append(dict(result))
        if i + batch_size < len(samples):
            time.sleep(7)

    # Aggregate results across batches
    metric_names_map = {
        "faithfulness": "faithfulness",
        "answer_correctness": "answer_correctness",
        "context_recall": "context_recall",
        "context_precision": "context_precision",
        "answer_relevancy": "answer_relevancy",
        "answer_similarity": "answer_similarity",
        "semantic_similarity": "answer_similarity",
    }

    scores: Dict[str, float] = {}
    for raw_name, canonical in metric_names_map.items():
        vals = []
        for batch_result in all_results:
            if raw_name in batch_result:
                val = batch_result[raw_name]
                if val is not None and not (isinstance(val, float) and val != val):
                    vals.append(float(val))
        if vals:
            scores[canonical] = sum(vals) / len(vals)

    for metric_name in RAGAS_WEIGHTS:
        if metric_name not in scores:
            logger.warning("Metric %s missing, substituting 0.0", metric_name)
            scores[metric_name] = 0.0

    composite = sum(RAGAS_WEIGHTS[m] * scores[m] for m in RAGAS_WEIGHTS)
    scores["composite"] = composite
    return scores
