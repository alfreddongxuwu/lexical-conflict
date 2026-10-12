import argparse
from pathlib import Path
import pandas as pd
from .paths import project_path

REQUIRED_COLUMNS = {
    "prompt_id",
    "baseline_type",
    "baseline_label",
    "source_freq_band",
    "source_category",
    "context_category",
    "source_word_zh",
    "standard_en",
    "response",
}
LABEL_ORDER = ["EXPECTED", "OTHER", "FAILED"]
FREQ_ORDER = ["high", "medium", "low"]


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create descriptive stats for one baseline run."
    )
    parser.add_argument("--run-dir", required=True)
    parser.add_argument("--input-name", default="responses_baseline_autocoded.csv")
    return parser.parse_args()


def validate_input(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Missing required columns: {sorted(missing)}")
    unexpected_labels = set(df["baseline_label"].dropna().unique()) - set(LABEL_ORDER)
    if unexpected_labels:
        raise ValueError(
            f"Unexpected baseline_label values: {sorted(unexpected_labels)}"
        )
    unexpected_types = set(df["baseline_type"].dropna().unique()) - {
        "normal_lexical",
        "anomalous_no_lexicon",
    }
    if unexpected_types:
        raise ValueError(f"Unexpected baseline_type values: {sorted(unexpected_types)}")
    if df["prompt_id"].duplicated().any():
        duplicated = df[df["prompt_id"].duplicated(keep=False)]
        raise ValueError(
            f"Duplicate prompt_id found. Examples:\n{duplicated[['prompt_id']].head(10)}"
        )


def add_ordering_columns(df: pd.DataFrame) -> pd.DataFrame:
    df = df.copy()
    df["baseline_label"] = pd.Categorical(
        df["baseline_label"], categories=LABEL_ORDER, ordered=True
    )
    df["source_freq_band"] = pd.Categorical(
        df["source_freq_band"], categories=FREQ_ORDER, ordered=True
    )
    return df


def count_with_percent(
    df: pd.DataFrame,
    group_cols: list[str],
    label_col: str = "baseline_label",
    percent_name: str | None = None,
) -> pd.DataFrame:
    if percent_name is None:
        percent_name = f"percent_within_{'_'.join(group_cols)}"
    count_cols = group_cols + [label_col]
    counts = df.groupby(count_cols, observed=False).size().reset_index(name="n")
    totals = counts.groupby(group_cols, observed=False)["n"].transform("sum")
    counts[percent_name] = (counts["n"] / totals * 100).round(2)
    return counts


def make_overall_counts(df: pd.DataFrame) -> pd.DataFrame:
    counts = df.groupby(["baseline_label"], observed=False).size().reset_index(name="n")
    counts["percent"] = (counts["n"] / counts["n"].sum() * 100).round(2)
    return counts


def make_other_examples(df: pd.DataFrame) -> pd.DataFrame:
    desired_cols = [
        "prompt_id",
        "baseline_type",
        "source_category",
        "context_category",
        "source_freq_band",
        "source_word_zh",
        "standard_en",
        "source_sentence_zh",
        "literal_expected_en",
        "response",
        "contains_expected",
        "expected_forms",
        "expected_matched_forms",
        "prompt",
    ]
    available_cols = [col for col in desired_cols if col in df.columns]
    other = df[df["baseline_label"] == "OTHER"].copy()
    other = other[available_cols]
    sort_cols = [
        col
        for col in [
            "baseline_type",
            "source_category",
            "context_category",
            "source_freq_band",
            "source_word_zh",
        ]
        if col in other.columns
    ]
    if sort_cols:
        other = other.sort_values(sort_cols)
    return other


def save_table(output_dir: Path, table: pd.DataFrame, filename: str) -> None:
    output_path = output_dir / filename
    table.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved: {output_path}")


def main() -> None:
    args = parse_args()
    run_dir = project_path(args.run_dir)
    input_path = run_dir / args.input_name
    output_dir = run_dir / "stats"
    if not input_path.exists():
        raise FileNotFoundError(f"Cannot find input file: {input_path}")
    output_dir.mkdir(parents=True, exist_ok=True)
    df = pd.read_csv(input_path)
    validate_input(df)
    df = add_ordering_columns(df)
    tables = {
        "01_overall_label_counts.csv": make_overall_counts(df),
        "02_by_baseline_type.csv": count_with_percent(
            df, ["baseline_type"], percent_name="percent_within_baseline_type"
        ),
        "03_by_source_freq.csv": count_with_percent(
            df, ["source_freq_band"], percent_name="percent_within_source_freq_band"
        ),
        "04_by_baseline_type_source_freq.csv": count_with_percent(
            df,
            ["baseline_type", "source_freq_band"],
            percent_name="percent_within_baseline_type_source_freq",
        ),
        "05_by_source_category.csv": count_with_percent(
            df, ["source_category"], percent_name="percent_within_source_category"
        ),
        "06_by_context_category.csv": count_with_percent(
            df, ["context_category"], percent_name="percent_within_context_category"
        ),
        "07_by_baseline_type_context_category.csv": count_with_percent(
            df,
            ["baseline_type", "context_category"],
            percent_name="percent_within_baseline_type_context_category",
        ),
        "08_other_examples.csv": make_other_examples(df),
    }
    for filename, table in tables.items():
        save_table(output_dir, table, filename)
    print("Overall baseline_label counts:")
    print(tables["01_overall_label_counts.csv"].to_string(index=False))
    print(f"OTHER examples saved: {len(tables['08_other_examples.csv'])} rows")


if __name__ == "__main__":
    main()
