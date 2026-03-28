import pandas as pd
import os


def load_dataset(data_dir: str):
    """Load qa.parquet and corpus.parquet from data_dir.

    Returns:
        (qa_df, corpus_df) as pandas DataFrames.
    """
    qa_path = os.path.join(data_dir, "qa.parquet")
    corpus_path = os.path.join(data_dir, "corpus.parquet")
    qa_df = pd.read_parquet(qa_path)
    corpus_df = pd.read_parquet(corpus_path)
    return qa_df, corpus_df
