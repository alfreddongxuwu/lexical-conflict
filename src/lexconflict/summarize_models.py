import argparse
from pathlib import Path
import pandas as pd
from .paths import project_path
from .result_validity import row_is_valid

MAIN_LABELS = ["PK", "CK", "BOTH", "OTHER"]
BASELINE_LABELS = ["EXPECTED", "OTHER"]
CONTEXT_TO_BASELINE_TYPE = {
    "PK_context": "normal_lexical",
    "CK_context": "anomalous_no_lexicon",
}
MAIN_REQUIRED_COLUMNS = {
    "prompt_id",
    "context_type",
    "context_category",
    "source_item_id",
    "source_category",
    "target_category",
    "source_freq_band",
    "target_freq_band",
    "auto_label",
    "response",
    "frame_id",
    "frame_name",
}
BASELINE_REQUIRED_COLUMNS = {
    "prompt_id",
    "baseline_type",
    "source_item_id",
    "context_category",
    "source_freq_band",
    "baseline_label",
    "response",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create unfiltered, baseline-filtered, and baseline-stratified cross-model summaries for a main-style experiment. PK-context rows match normal-lexical baseline rows; CK-context rows match anomalous-no-lexicon rows."
    )
    parser.add_argument("--runs-root", default="outputs/runs")
    parser.add_argument("--output-dir", default="outputs/summary/exp1")
    parser.add_argument("--baseline-output-dir", default=None)
    parser.add_argument("--main-experiment", default="main")
    parser.add_argument("--baseline-experiment", default="baseline")
    parser.add_argument("--expected-rows", type=int, default=6000)
    parser.add_argument("--expected-model-count", type=int, default=0)
    parser.add_argument("--models", nargs="*", default=None)
    return parser.parse_args()


def require_columns(
    df: pd.DataFrame, columns: set[str], label: str, path: Path
) -> None:
    missing = columns - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing columns {sorted(missing)}: {path}")


def read_csv(
    path: Path, required_columns: set[str], label: str, expected_rows: int | None = None
) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Cannot find {label}: {path}")
    df = pd.read_csv(path, keep_default_na=False)
    require_columns(df, required_columns, label, path)
    if expected_rows and len(df) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} rows for {label}, found {len(df)}: {path}"
        )
    duplicates = int(df["prompt_id"].duplicated().sum())
    if duplicates:
        raise ValueError(
            f"Found {duplicates} duplicate prompt_id rows in {label}: {path}"
        )
    return df


def discover_models(
    runs_root: Path,
    main_experiment: str,
    baseline_experiment: str,
    requested_models: list[str] | None,
    expected_model_count: int,
) -> list[str]:
    main_root = runs_root / main_experiment
    baseline_root = runs_root / baseline_experiment
    if not main_root.is_dir():
        raise FileNotFoundError(f"Cannot find experiment directory: {main_root}")
    if not baseline_root.is_dir():
        raise FileNotFoundError(f"Cannot find baseline directory: {baseline_root}")
    if requested_models:
        models = sorted(dict.fromkeys(requested_models))
    else:
        main_models = {path.name for path in main_root.iterdir() if path.is_dir()}
        baseline_models = {
            path.name for path in baseline_root.iterdir() if path.is_dir()
        }
        models = sorted(main_models & baseline_models)
    if not models:
        raise ValueError(f"No models found for {main_experiment} with baseline data.")
    if expected_model_count and len(models) != expected_model_count:
        raise ValueError(
            f"Expected {expected_model_count} models for {main_experiment}, found {len(models)}: {models}"
        )
    return models


def expected_baseline_context_category(row: pd.Series) -> str:
    if row["context_type"] == "PK_context":
        return str(row["source_category"])
    if row["context_type"] == "CK_context":
        return str(row["target_category"])
    raise ValueError(f"Unexpected context_type: {row['context_type']}")


def baseline_lookup_key(row: pd.Series) -> tuple[str, str, str]:
    return (
        str(row["source_item_id"]),
        str(row["matched_baseline_context_category"]),
        str(row["matched_baseline_type"]),
    )


def attach_baseline_labels(main: pd.DataFrame, baseline: pd.DataFrame) -> pd.DataFrame:
    unexpected_contexts = set(main["context_type"].unique()) - set(
        CONTEXT_TO_BASELINE_TYPE
    )
    if unexpected_contexts:
        raise ValueError(
            f"Unexpected context_type values: {sorted(unexpected_contexts)}"
        )
    duplicate_keys = baseline.duplicated(
        ["source_item_id", "context_category", "baseline_type"], keep=False
    )
    if duplicate_keys.any():
        examples = baseline.loc[
            duplicate_keys,
            ["prompt_id", "source_item_id", "context_category", "baseline_type"],
        ].head(20)
        raise ValueError(f"Duplicate baseline matching keys found:\n{examples}")
    baseline_by_key = {
        (str(row.source_item_id), str(row.context_category), str(row.baseline_type)): row
        for row in baseline.itertuples(index=False)
    }
    enriched = main.copy()
    enriched["matched_baseline_type"] = enriched["context_type"].map(
        CONTEXT_TO_BASELINE_TYPE
    )
    enriched["matched_baseline_context_category"] = enriched.apply(
        expected_baseline_context_category, axis=1
    )
    baseline_prompt_ids: list[str] = []
    baseline_labels: list[str] = []
    baseline_statuses: list[str] = []
    missing_keys: list[tuple[str, str, str]] = []
    for _, row in enriched.iterrows():
        key = baseline_lookup_key(row)
        baseline_row = baseline_by_key.get(key)
        if baseline_row is None:
            missing_keys.append(key)
            baseline_prompt_ids.append("")
            baseline_labels.append("MISSING")
            baseline_statuses.append("")
            continue
        baseline_prompt_ids.append(str(baseline_row.prompt_id))
        baseline_labels.append(str(baseline_row.baseline_label))
        baseline_statuses.append(str(getattr(baseline_row, "status", "")))
    if missing_keys:
        examples = "\n".join(map(str, missing_keys[:20]))
        raise ValueError(f"Missing baseline matches for experiment rows:\n{examples}")
    enriched["matched_baseline_prompt_id"] = baseline_prompt_ids
    enriched["matched_baseline_label"] = baseline_labels
    enriched["matched_baseline_status"] = baseline_statuses
    return enriched


def add_model_id(df: pd.DataFrame, model_id: str) -> pd.DataFrame:
    result = df.copy()
    if "model_id" in result.columns:
        result = result.drop(columns=["model_id"])
    result.insert(0, "model_id", model_id)
    return result


def validate_labels(
    df: pd.DataFrame, column: str, allowed: list[str], label: str
) -> None:
    unexpected = set(df[column].unique()) - set(allowed)
    if unexpected:
        raise ValueError(f"Unexpected {label} values: {sorted(unexpected)}")


def ensure_valid_rows(df: pd.DataFrame, label: str) -> None:
    valid = df.apply(row_is_valid, axis=1)
    invalid_count = int((~valid).sum())
    if invalid_count:
        raise ValueError(f"Found {invalid_count} invalid rows in {label}")


def percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.replace(0, pd.NA) * 100).round(2).fillna(0)


def distribution_table(
    df: pd.DataFrame, group_cols: list[str], label_col: str, labels: list[str]
) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols + [label_col], observed=True, dropna=False)
        .size()
        .unstack(label_col, fill_value=0)
    )
    for label in labels:
        if label not in grouped.columns:
            grouped[label] = 0
    grouped = grouped[labels].reset_index()
    grouped["n"] = grouped[labels].sum(axis=1)
    ordered_columns = list(group_cols) + ["n"]
    for label in labels:
        lower = label.lower()
        grouped[f"n_{lower}"] = grouped[label].astype(int)
        grouped[f"percent_{lower}"] = percent(grouped[label], grouped["n"])
        ordered_columns.extend([f"n_{lower}", f"percent_{lower}"])
    return grouped[ordered_columns].sort_values(group_cols).reset_index(drop=True)


def experiment_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "01_by_model.csv": distribution_table(
            df, ["model_id"], "auto_label", MAIN_LABELS
        ),
        "02_by_context_type.csv": distribution_table(
            df, ["model_id", "context_type"], "auto_label", MAIN_LABELS
        ),
        "03_by_frame.csv": distribution_table(
            df, ["model_id", "frame_id", "frame_name"], "auto_label", MAIN_LABELS
        ),
        "04_by_source_frequency.csv": distribution_table(
            df, ["model_id", "source_freq_band"], "auto_label", MAIN_LABELS
        ),
        "05_by_target_frequency.csv": distribution_table(
            df, ["model_id", "target_freq_band"], "auto_label", MAIN_LABELS
        ),
    }


def stratified_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "01_by_model_and_baseline_label.csv": distribution_table(
            df, ["model_id", "matched_baseline_label"], "auto_label", MAIN_LABELS
        ),
        "02_by_context_type_and_baseline_label.csv": distribution_table(
            df,
            ["model_id", "context_type", "matched_baseline_label"],
            "auto_label",
            MAIN_LABELS,
        ),
        "03_by_frame_and_baseline_label.csv": distribution_table(
            df,
            ["model_id", "frame_id", "frame_name", "matched_baseline_label"],
            "auto_label",
            MAIN_LABELS,
        ),
        "04_by_source_frequency_and_baseline_label.csv": distribution_table(
            df,
            ["model_id", "source_freq_band", "matched_baseline_label"],
            "auto_label",
            MAIN_LABELS,
        ),
        "05_by_target_frequency_and_baseline_label.csv": distribution_table(
            df,
            ["model_id", "target_freq_band", "matched_baseline_label"],
            "auto_label",
            MAIN_LABELS,
        ),
    }


def baseline_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "01_overall_by_model.csv": distribution_table(
            df, ["model_id"], "baseline_label", BASELINE_LABELS
        ),
        "02_by_model_baseline_type.csv": distribution_table(
            df, ["model_id", "baseline_type"], "baseline_label", BASELINE_LABELS
        ),
        "03_by_model_source_freq.csv": distribution_table(
            df, ["model_id", "source_freq_band"], "baseline_label", BASELINE_LABELS
        ),
        "04_by_model_context_category.csv": distribution_table(
            df, ["model_id", "context_category"], "baseline_label", BASELINE_LABELS
        ),
    }


def inventory_row(
    model_id: str, main: pd.DataFrame, baseline: pd.DataFrame, enriched: pd.DataFrame
) -> dict[str, int | float | str]:
    matched_counts = enriched["matched_baseline_label"].value_counts().to_dict()
    filtered_rows = int(matched_counts.get("EXPECTED", 0))
    excluded_rows = int(matched_counts.get("OTHER", 0))
    if filtered_rows + excluded_rows != len(main):
        raise ValueError(
            f"Baseline filter counts do not cover every row for {model_id}"
        )
    return {
        "model_id": model_id,
        "unfiltered_rows": len(main),
        "baseline_filtered_rows": filtered_rows,
        "excluded_rows": excluded_rows,
        "retained_percent": round(filtered_rows / len(main) * 100, 2),
        "baseline_rows": len(baseline),
    }


def save_table(path: Path, table: pd.DataFrame) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    table.to_csv(path, index=False, encoding="utf-8-sig")
    print(f"Saved: {path}")


def save_tables(output_dir: Path, tables: dict[str, pd.DataFrame]) -> None:
    for filename, table in tables.items():
        save_table(output_dir / filename, table)


def markdown_table(df: pd.DataFrame) -> str:
    if df.empty:
        return "_No rows._"
    columns = list(df.columns)
    lines = [
        "| " + " | ".join(columns) + " |",
        "| " + " | ".join(["---"] * len(columns)) + " |",
    ]
    for _, row in df.iterrows():
        values = [str(row[column]).replace("|", "\\|") for column in columns]
        lines.append("| " + " | ".join(values) + " |")
    return "\n".join(lines)


def write_experiment_summary(
    path: Path,
    experiment: str,
    inventory: pd.DataFrame,
    unfiltered_by_model: pd.DataFrame,
    filtered_by_model: pd.DataFrame,
) -> None:
    lines = [
        f"# {experiment} Cross-Model Summary",
        "",
        "Three analysis views are retained:",
        "",
        "- `unfiltered/`: all experiment rows.",
        "- `baseline_filtered/`: only rows whose matched baseline label is `EXPECTED`.",
        "- `baseline_stratified/`: all rows, grouped by matched baseline label.",
        "",
        "Matching rule:",
        "",
        "- `PK_context` rows match `normal_lexical` baseline rows.",
        "- `CK_context` rows match `anomalous_no_lexicon` baseline rows.",
        "",
        "## Filter Inventory",
        "",
        markdown_table(inventory),
        "",
        "## Unfiltered By Model",
        "",
        markdown_table(unfiltered_by_model),
        "",
        "## Baseline-Filtered By Model",
        "",
        markdown_table(filtered_by_model),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {path}")


def write_baseline_summary(path: Path, by_model: pd.DataFrame) -> None:
    lines = [
        "# Baseline Cross-Model Summary",
        "",
        "This directory summarizes baseline performance across models. It is the",
        "screening source for the baseline-filtered experiment summaries.",
        "",
        "## Overall By Model",
        "",
        markdown_table(by_model),
        "",
    ]
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("\n".join(lines), encoding="utf-8")
    print(f"Saved: {path}")


def main() -> None:
    args = parse_args()
    runs_root = project_path(args.runs_root)
    output_dir = project_path(args.output_dir)
    baseline_output_dir = (
        project_path(args.baseline_output_dir) if args.baseline_output_dir else None
    )
    models = discover_models(
        runs_root,
        args.main_experiment,
        args.baseline_experiment,
        args.models,
        args.expected_model_count,
    )
    inventory_rows = []
    main_frames = []
    filtered_frames = []
    baseline_frames = []
    for model_id in models:
        main_path = (
            runs_root / args.main_experiment / model_id / "responses_autocoded.csv"
        )
        baseline_path = (
            runs_root
            / args.baseline_experiment
            / model_id
            / "responses_baseline_autocoded.csv"
        )
        main_df = read_csv(
            main_path,
            MAIN_REQUIRED_COLUMNS,
            f"{args.main_experiment} run for {model_id}",
            args.expected_rows,
        )
        baseline_df = read_csv(
            baseline_path, BASELINE_REQUIRED_COLUMNS, f"baseline run for {model_id}"
        )
        validate_labels(main_df, "auto_label", MAIN_LABELS, "auto_label")
        validate_labels(
            baseline_df, "baseline_label", BASELINE_LABELS, "baseline_label"
        )
        ensure_valid_rows(main_df, f"{args.main_experiment} run for {model_id}")
        ensure_valid_rows(baseline_df, f"baseline run for {model_id}")
        enriched = attach_baseline_labels(main_df, baseline_df)
        inventory_rows.append(inventory_row(model_id, main_df, baseline_df, enriched))
        enriched = add_model_id(enriched, model_id)
        filtered = enriched[enriched["matched_baseline_label"].eq("EXPECTED")].copy()
        baseline_df = add_model_id(baseline_df, model_id)
        main_frames.append(enriched)
        filtered_frames.append(filtered)
        baseline_frames.append(baseline_df)
    all_main = pd.concat(main_frames, ignore_index=True)
    all_filtered = pd.concat(filtered_frames, ignore_index=True)
    all_baseline = pd.concat(baseline_frames, ignore_index=True)
    inventory = (
        pd.DataFrame(inventory_rows).sort_values("model_id").reset_index(drop=True)
    )
    unfiltered_tables = experiment_tables(all_main)
    filtered_tables = experiment_tables(all_filtered)
    baseline_stratified_tables = stratified_tables(all_main)
    save_table(output_dir / "00_filter_inventory.csv", inventory)
    save_tables(output_dir / "unfiltered", unfiltered_tables)
    save_tables(output_dir / "baseline_filtered", filtered_tables)
    save_tables(output_dir / "baseline_stratified", baseline_stratified_tables)
    write_experiment_summary(
        output_dir / "summary.md",
        args.main_experiment,
        inventory,
        unfiltered_tables["01_by_model.csv"],
        filtered_tables["01_by_model.csv"],
    )
    if baseline_output_dir is not None:
        baseline_summary_tables = baseline_tables(all_baseline)
        save_tables(baseline_output_dir, baseline_summary_tables)
        write_baseline_summary(
            baseline_output_dir / "summary.md",
            baseline_summary_tables["01_overall_by_model.csv"],
        )


if __name__ == "__main__":
    main()
