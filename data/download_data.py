"""Download and preprocess benchmark datasets for AutoRAGsearch.

Produces:
  data/nq_subset/qa.parquet        — 300 QA pairs from SQuAD (NQ-style)
  data/nq_subset/corpus.parquet    — all context passages (distractors included)
  data/hotpotqa_subset/qa.parquet  — 200 QA pairs from HotpotQA
  data/hotpotqa_subset/corpus.parquet
"""

import os
import random
import hashlib
import pandas as pd
from datasets import load_dataset

RANDOM_SEED = 42
NQ_SUBSET_SIZE = 300
HOTPOT_SUBSET_SIZE = 200

BASE_DIR = os.path.dirname(os.path.abspath(__file__))
NQ_DIR = os.path.join(BASE_DIR, "nq_subset")
HOTPOT_DIR = os.path.join(BASE_DIR, "hotpotqa_subset")


# ---------------------------------------------------------------------------
# SQuAD as NQ substitute (Wikipedia-based Q&A with passage context)
# ---------------------------------------------------------------------------

def download_nq_subset():
    print("Downloading SQuAD (NQ-style Wikipedia QA)...")
    ds = load_dataset("rajpurkar/squad", split="train")

    random.seed(RANDOM_SEED)
    indices = random.sample(range(len(ds)), min(NQ_SUBSET_SIZE * 5, len(ds)))
    subset = ds.select(indices)

    qa_rows = []
    corpus_map = {}  # doc_id -> text

    seen_questions = set()
    for sample in subset:
        if len(qa_rows) >= NQ_SUBSET_SIZE:
            break

        question = sample["question"].strip()
        if question in seen_questions:
            continue
        seen_questions.add(question)

        context = sample["context"].strip()
        answers = sample["answers"]["text"]
        if not answers:
            continue
        answer = answers[0].strip()

        # Use a stable doc_id based on context hash
        doc_id = "nq_" + hashlib.md5(context.encode()).hexdigest()[:12]
        corpus_map[doc_id] = context

        qid = f"nq_{len(qa_rows):04d}"
        qa_rows.append({
            "qid": qid,
            "question": question,
            "ground_truth_answer": answer,
            "ground_truth_contexts": [context],
        })

    # Add distractor passages from the rest of the dataset
    all_indices = set(range(len(ds))) - set(indices)
    distractor_indices = random.sample(list(all_indices), min(500, len(all_indices)))
    for idx in distractor_indices:
        sample = ds[idx]
        context = sample["context"].strip()
        doc_id = "nq_" + hashlib.md5(context.encode()).hexdigest()[:12]
        if doc_id not in corpus_map:
            corpus_map[doc_id] = context

    corpus_rows = [
        {"doc_id": doc_id, "text": text, "metadata": {"source": "squad"}}
        for doc_id, text in corpus_map.items()
    ]

    qa_df = pd.DataFrame(qa_rows)
    corpus_df = pd.DataFrame(corpus_rows)

    os.makedirs(NQ_DIR, exist_ok=True)
    qa_df.to_parquet(os.path.join(NQ_DIR, "qa.parquet"), index=False)
    corpus_df.to_parquet(os.path.join(NQ_DIR, "corpus.parquet"), index=False)
    print(f"  NQ subset: {len(qa_df)} QA pairs, {len(corpus_df)} corpus docs")


# ---------------------------------------------------------------------------
# HotpotQA (distractor split)
# ---------------------------------------------------------------------------

def download_hotpotqa_subset():
    print("Downloading HotpotQA (distractor split)...")
    ds = load_dataset("hotpot_qa", "distractor", split="train", trust_remote_code=True)

    random.seed(RANDOM_SEED)
    indices = random.sample(range(len(ds)), min(HOTPOT_SUBSET_SIZE * 3, len(ds)))
    subset = ds.select(indices)

    qa_rows = []
    corpus_map = {}  # doc_id -> text

    for sample in subset:
        if len(qa_rows) >= HOTPOT_SUBSET_SIZE:
            break

        question = sample["question"].strip()
        answer = sample["answer"].strip()
        if not answer or answer.lower() in ("yes", "no"):
            # Skip yes/no questions for cleaner RAGAS evaluation
            continue

        # Context is a list of [title, [sentence1, sentence2, ...]] pairs
        context_titles = sample["context"]["title"]
        context_sentences = sample["context"]["sentences"]

        # Supporting facts: {'title': [...], 'sent_id': [...]}
        sf_titles = set(sample["supporting_facts"]["title"])

        ground_truth_contexts = []
        for title, sents in zip(context_titles, context_sentences):
            doc_text = " ".join(sents).strip()
            doc_id = "hotpot_" + hashlib.md5((title + doc_text[:50]).encode()).hexdigest()[:12]
            corpus_map[doc_id] = doc_text
            if title in sf_titles:
                ground_truth_contexts.append(doc_text)

        if not ground_truth_contexts:
            continue

        qid = f"hotpot_{len(qa_rows):04d}"
        qa_rows.append({
            "qid": qid,
            "question": question,
            "ground_truth_answer": answer,
            "ground_truth_contexts": ground_truth_contexts,
        })

    corpus_rows = [
        {"doc_id": doc_id, "text": text, "metadata": {"source": "hotpotqa"}}
        for doc_id, text in corpus_map.items()
    ]

    qa_df = pd.DataFrame(qa_rows)
    corpus_df = pd.DataFrame(corpus_rows)

    os.makedirs(HOTPOT_DIR, exist_ok=True)
    qa_df.to_parquet(os.path.join(HOTPOT_DIR, "qa.parquet"), index=False)
    corpus_df.to_parquet(os.path.join(HOTPOT_DIR, "corpus.parquet"), index=False)
    print(f"  HotpotQA subset: {len(qa_df)} QA pairs, {len(corpus_df)} corpus docs")


if __name__ == "__main__":
    download_nq_subset()
    download_hotpotqa_subset()
    print("Done.")
