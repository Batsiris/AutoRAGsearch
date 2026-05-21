import pandas as pd
import re
from pathlib import Path

SOURCE_DIR = Path(r"C:\Users\user\Downloads\AutoRagSearch\AutoRAGsearch\data\hotpotqa_subset")
OUTPUT_DIR = Path(r".\data\my_hotpotqa_subset_autorag")
OUTPUT_DIR.mkdir(parents=True, exist_ok=True)

qa_path = SOURCE_DIR / "qa.parquet"
corpus_path = SOURCE_DIR / "corpus.parquet"

qa = pd.read_parquet(qa_path)
corpus = pd.read_parquet(corpus_path)

print("Original QA rows:", len(qa))
print("Original QA columns:", qa.columns.tolist())
print("Original corpus rows:", len(corpus))
print("Original corpus columns:", corpus.columns.tolist())

def normalize_text(x):
    if x is None:
        return ""
    return re.sub(r"\s+", " ", str(x)).strip()

# Convert corpus format: text -> contents
corpus_autorag = corpus.copy()
corpus_autorag = corpus_autorag.rename(columns={"text": "contents"})
corpus_autorag["doc_id"] = corpus_autorag["doc_id"].astype(str)
corpus_autorag["contents"] = corpus_autorag["contents"].astype(str)

# Build lookup from normalized corpus text to doc_id
text_to_doc_id = {}
for _, row in corpus_autorag.iterrows():
    norm = normalize_text(row["contents"])
    if norm not in text_to_doc_id:
        text_to_doc_id[norm] = row["doc_id"]

def parse_contexts(value):
    if value is None:
        return []

    if isinstance(value, list):
        return value

    if isinstance(value, (tuple, set)):
        return list(value)

    return [value]

def find_doc_id_for_context(context):
    norm_ctx = normalize_text(context)

    # Exact match
    if norm_ctx in text_to_doc_id:
        return text_to_doc_id[norm_ctx]

    # Fallback: containment match
    for _, row in corpus_autorag.iterrows():
        norm_doc = normalize_text(row["contents"])
        if norm_ctx and (norm_ctx in norm_doc or norm_doc in norm_ctx):
            return row["doc_id"]

    return None

qa_rows = []
bad_rows = []

for idx, row in qa.iterrows():
    contexts = parse_contexts(row["ground_truth_contexts"])
    retrieval_gt = []

    for ctx in contexts:
        doc_id = find_doc_id_for_context(ctx)
        if doc_id is not None:
            retrieval_gt.append(doc_id)

    # Remove duplicates while keeping order
    retrieval_gt = list(dict.fromkeys(retrieval_gt))

    if len(retrieval_gt) == 0:
        bad_rows.append(idx)
        continue

    qa_rows.append({
        "qid": str(row["qid"]),
        "query": row["question"],
        "generation_gt": row["ground_truth_answer"],
        "retrieval_gt": retrieval_gt
    })

qa_autorag = pd.DataFrame(qa_rows)

print("Converted QA rows:", len(qa_autorag))
print("Rows without matched retrieval_gt:", len(bad_rows))

if bad_rows:
    print("First bad row indices:", bad_rows[:10])

# Verify all retrieval_gt doc_ids exist in corpus
corpus_doc_ids = set(corpus_autorag["doc_id"].astype(str))
missing_rows = []

for idx, row in qa_autorag.iterrows():
    missing = [doc_id for doc_id in row["retrieval_gt"] if doc_id not in corpus_doc_ids]
    if missing:
        missing_rows.append((idx, missing))

print("Rows with missing doc_ids after conversion:", len(missing_rows))

qa_out = OUTPUT_DIR / "qa_validation.parquet"
corpus_out = OUTPUT_DIR / "corpus.parquet"

qa_autorag.to_parquet(qa_out, index=False)
corpus_autorag[["doc_id", "contents", "metadata"]].to_parquet(corpus_out, index=False)

print("Saved QA:", qa_out)
print("Saved corpus:", corpus_out)
print("Final QA columns:", qa_autorag.columns.tolist())
print("Final corpus columns:", corpus_autorag[["doc_id", "contents", "metadata"]].columns.tolist())