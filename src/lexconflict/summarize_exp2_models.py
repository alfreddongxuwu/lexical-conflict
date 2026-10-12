import argparse
from pathlib import Path
import pandas as pd
from .paths import project_path
from .result_validity import row_is_valid

LABELS = ["PK", "CK", "BOTH", "OTHER"]
BASELINE_LABELS = ["EXPECTED", "OTHER"]
FREQ_ORDER = ["high", "medium", "low"]
EXP2_REQUIRED_COLUMNS = {
    "prompt_id",
    "mapping_id",
    "frame_id",
    "frame_name",
    "context_type",
    "source_item_id",
    "source_category",
    "target_category",
    "source_freq_band",
    "target_freq_band",
    "pairing_round",
    "source_sentence_zh",
    "auto_label",
    "response",
}
BASELINE_REQUIRED_COLUMNS = {
    "prompt_id",
    "baseline_type",
    "source_item_id",
    "source_sentence_zh",
    "baseline_label",
    "response",
}


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Create unfiltered, normal-lexical-baseline-filtered, and baseline-stratified cross-model summaries for Exp2."
    )
    parser.add_argument("--runs-root", default="outputs/runs")
    parser.add_argument("--output-dir", default="outputs/summary/exp2")
    parser.add_argument("--experiment", default="exp2")
    parser.add_argument("--baseline-experiment", default="baseline")
    parser.add_argument("--input-name", default="responses_autocoded.csv")
    parser.add_argument("--expected-rows", type=int, default=3000)
    parser.add_argument("--expected-model-count", type=int, default=0)
    parser.add_argument("--models", nargs="*", default=None)
    return parser.parse_args()


def discover_models(
    runs_root: Path,
    experiment: str,
    baseline_experiment: str,
    requested_models: list[str] | None,
    expected_model_count: int,
) -> list[str]:
    experiment_root = runs_root / experiment
    baseline_root = runs_root / baseline_experiment
    if not experiment_root.is_dir():
        raise FileNotFoundError(f"Cannot find Exp2 directory: {experiment_root}")
    if not baseline_root.is_dir():
        raise FileNotFoundError(f"Cannot find baseline directory: {baseline_root}")
    if requested_models:
        models = sorted(dict.fromkeys(requested_models))
    else:
        experiment_models = {
            path.name for path in experiment_root.iterdir() if path.is_dir()
        }
        baseline_models = {
            path.name for path in baseline_root.iterdir() if path.is_dir()
        }
        models = sorted(experiment_models & baseline_models)
    if not models:
        raise ValueError("No Exp2 models with matching baseline data were found.")
    if expected_model_count and len(models) != expected_model_count:
        raise ValueError(
            f"Expected {expected_model_count} Exp2 models, found {len(models)}: {models}"
        )
    return models


def read_csv(path: Path, required: set[str], label: str) -> pd.DataFrame:
    if not path.is_file():
        raise FileNotFoundError(f"Cannot find {label}: {path}")
    df = pd.read_csv(path, keep_default_na=False)
    missing = required - set(df.columns)
    if missing:
        raise ValueError(f"{label} is missing columns {sorted(missing)}: {path}")
    duplicates = int(df["prompt_id"].duplicated().sum())
    if duplicates:
        raise ValueError(
            f"Found {duplicates} duplicate prompt_id rows in {label}: {path}"
        )
    return df


def validate_exp2(df: pd.DataFrame, model_id: str, expected_rows: int) -> None:
    if expected_rows and len(df) != expected_rows:
        raise ValueError(
            f"Expected {expected_rows} Exp2 rows for {model_id}, found {len(df)}"
        )
    unexpected_labels = set(df["auto_label"].unique()) - set(LABELS)
    if unexpected_labels:
        raise ValueError(
            f"Unexpected auto_label values for {model_id}: {sorted(unexpected_labels)}"
        )
    context_types = set(df["context_type"].unique())
    if context_types != {"within_category_context"}:
        raise ValueError(
            f"Unexpected Exp2 context_type values for {model_id}: {sorted(context_types)}"
        )
    cross_category = df["source_category"].ne(df["target_category"])
    if cross_category.any():
        examples = df.loc[
            cross_category, ["prompt_id", "source_category", "target_category"]
        ].head(10)
        raise ValueError(f"Exp2 contains cross-category rows for {model_id}:\n{examples}")
    same_frequency = df["source_freq_band"].eq(df["target_freq_band"])
    if same_frequency.any():
        examples = df.loc[
            same_frequency, ["prompt_id", "source_freq_band", "target_freq_band"]
        ].head(10)
        raise ValueError(
            f"Exp2 contains same-frequency rows for {model_id}:\n{examples}"
        )
    unexpected_frequencies = (
        set(df["source_freq_band"].unique()) | set(df["target_freq_band"].unique())
    ) - set(FREQ_ORDER)
    if unexpected_frequencies:
        raise ValueError(
            f"Unexpected frequency bands for {model_id}: {sorted(unexpected_frequencies)}"
        )


def validate_baseline(df: pd.DataFrame, model_id: str) -> None:
    unexpected_labels = set(df["baseline_label"].unique()) - set(BASELINE_LABELS)
    if unexpected_labels:
        raise ValueError(
            f"Unexpected baseline_label values for {model_id}: {sorted(unexpected_labels)}"
        )


def ensure_valid_rows(df: pd.DataFrame, label: str) -> None:
    valid = df.apply(row_is_valid, axis=1)
    invalid_count = int((~valid).sum())
    if invalid_count:
        raise ValueError(f"Found {invalid_count} invalid rows in {label}")


def add_model_id(df: pd.DataFrame, model_id: str) -> pd.DataFrame:
    result = df.copy()
    if "model_id" in result.columns:
        result = result.drop(columns=["model_id"])
    result.insert(0, "model_id", model_id)
    return result


def attach_normal_lexical_baseline(
    exp2: pd.DataFrame, baseline: pd.DataFrame, model_id: str
) -> pd.DataFrame:
    normal = baseline[baseline["baseline_type"].eq("normal_lexical")].copy()
    if normal.empty:
        raise ValueError(f"No normal_lexical baseline rows found for {model_id}")
    duplicate_items = normal.duplicated(["source_item_id"], keep=False)
    if duplicate_items.any():
        examples = normal.loc[duplicate_items, ["prompt_id", "source_item_id"]].head(20)
        raise ValueError(
            f"Duplicate normal_lexical baseline source_item_id values for {model_id}:\n{examples}"
        )
    baseline_by_item = {
        str(row.source_item_id): row for row in normal.itertuples(index=False)
    }
    missing_items = sorted(
        set(exp2["source_item_id"].astype(str)) - set(baseline_by_item)
    )
    if missing_items:
        raise ValueError(
            f"Missing normal_lexical baseline matches for {model_id}: {missing_items[:20]}"
        )
    baseline_prompt_ids: list[str] = []
    baseline_labels: list[str] = []
    baseline_statuses: list[str] = []
    sentence_mismatches: list[str] = []
    for row in exp2.itertuples(index=False):
        baseline_row = baseline_by_item[str(row.source_item_id)]
        if str(row.source_sentence_zh) != str(baseline_row.source_sentence_zh):
            sentence_mismatches.append(str(row.source_item_id))
        baseline_prompt_ids.append(str(baseline_row.prompt_id))
        baseline_labels.append(str(baseline_row.baseline_label))
        baseline_statuses.append(str(getattr(baseline_row, "status", "")))
    if sentence_mismatches:
        raise ValueError(
            f"Exp2/baseline source sentence mismatches for {model_id}: {sorted(set(sentence_mismatches))[:20]}"
        )
    enriched = exp2.copy()
    enriched["matched_baseline_type"] = "normal_lexical"
    enriched["matched_baseline_prompt_id"] = baseline_prompt_ids
    enriched["matched_baseline_label"] = baseline_labels
    enriched["matched_baseline_status"] = baseline_statuses
    return enriched


def percent(numerator: pd.Series, denominator: pd.Series) -> pd.Series:
    return (numerator / denominator.replace(0, pd.NA) * 100).round(2).fillna(0)


def distribution_table(df: pd.DataFrame, group_cols: list[str]) -> pd.DataFrame:
    grouped = (
        df.groupby(group_cols + ["auto_label"], observed=True, dropna=False)
        .size()
        .unstack("auto_label", fill_value=0)
    )
    for label in LABELS:
        if label not in grouped.columns:
            grouped[label] = 0
    grouped = grouped[LABELS].reset_index()
    grouped["n"] = grouped[LABELS].sum(axis=1)
    ordered_columns = list(group_cols) + ["n"]
    for label in LABELS:
        lower = label.lower()
        grouped[f"n_{lower}"] = grouped[label].astype(int)
        grouped[f"percent_{lower}"] = percent(grouped[label], grouped["n"])
        ordered_columns.extend([f"n_{lower}", f"percent_{lower}"])
    return grouped[ordered_columns].sort_values(group_cols).reset_index(drop=True)


def experiment_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "01_by_model.csv": distribution_table(df, ["model_id"]),
        "02_by_frame.csv": distribution_table(
            df, ["model_id", "frame_id", "frame_name"]
        ),
        "03_by_source_frequency.csv": distribution_table(
            df, ["model_id", "source_freq_band"]
        ),
        "04_by_target_frequency.csv": distribution_table(
            df, ["model_id", "target_freq_band"]
        ),
        "05_by_frequency_transition.csv": distribution_table(
            df, ["model_id", "source_freq_band", "target_freq_band"]
        ),
        "06_by_category.csv": distribution_table(df, ["model_id", "source_category"]),
        "07_by_pairing_round.csv": distribution_table(
            df, ["model_id", "pairing_round"]
        ),
    }


def stratified_tables(df: pd.DataFrame) -> dict[str, pd.DataFrame]:
    return {
        "01_by_model_and_baseline_label.csv": distribution_table(
            df, ["model_id", "matched_baseline_label"]
        ),
        "02_by_frame_and_baseline_label.csv": distribution_table(
            df, ["model_id", "frame_id", "frame_name", "matched_baseline_label"]
        ),
        "03_by_source_frequency_and_baseline_label.csv": distribution_table(
            df, ["model_id", "source_freq_band", "matched_baseline_label"]
        ),
        "04_by_target_frequency_and_baseline_label.csv": distribution_table(
            df, ["model_id", "target_freq_band", "matched_baseline_label"]
        ),
        "05_by_frequency_transition_and_baseline_label.csv": distribution_table(
            df,
            [
                "model_id",
                "source_freq_band",
                "target_freq_band",
                "matched_baseline_label",
            ],
        ),
        "06_by_category_and_baseline_label.csv": distribution_table(
            df, ["model_id", "source_category", "matched_baseline_label"]
        ),
        "07_by_pairing_round_and_baseline_label.csv": distribution_table(
            df, ["model_id", "pairing_round", "matched_baseline_label"]
        ),
    }


def inventory_row(
    model_id: str, enriched: pd.DataFrame, baseline: pd.DataFrame
) -> dict[str, int | float | str]:
    matched_counts = enriched["matched_baseline_label"].value_counts().to_dict()
    filtered_rows = int(matched_counts.get("EXPECTED", 0))
    excluded_rows = int(matched_counts.get("OTHER", 0))
    if filtered_rows + excluded_rows != len(enriched):
        raise ValueError(
            f"Baseline filter counts do not cover every Exp2 row for {model_id}"
        )
    normal = baseline[baseline["baseline_type"].eq("normal_lexical")]
    normal_counts = normal["baseline_label"].value_counts().to_dict()
    return {
        "model_id": model_id,
        "unfiltered_rows": len(enriched),
        "baseline_filtered_rows": filtered_rows,
        "excluded_rows": excluded_rows,
        "retained_percent": round(filtered_rows / len(enriched) * 100, 2),
        "unique_source_items": int(enriched["source_item_id"].nunique()),
        "normal_baseline_expected_items": int(normal_counts.get("EXPECTED", 0)),
        "normal_baseline_other_items": int(normal_counts.get("OTHER", 0)),
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


def write_summary(
    path: Path,
    inventory: pd.DataFrame,
    unfiltered_by_model: pd.DataFrame,
    filtered_by_model: pd.DataFrame,
) -> None:
    lines = [
        "# Exp2 Cross-Model Summary",
        "",
        "Three analysis views are retained:",
        "",
        "- `unfiltered/`: all Exp2 rows.",
        "- `baseline_filtered/`: rows whose source item has an `EXPECTED`",
        "  `normal_lexical` baseline response for the same model.",
        "- `baseline_stratified/`: all rows, grouped by matched normal-lexical",
        "  baseline label.",
        "",
        "The Exp2 source item and baseline source sentence are required to match exactly.",
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


def main() -> None:
    args = parse_args()
    runs_root = project_path(args.runs_root)
    output_dir = project_path(args.output_dir)
    models = discover_models(
        runs_root,
        args.experiment,
        args.baseline_experiment,
        args.models,
        args.expected_model_count,
    )
    frames = []
    filtered_frames = []
    inventory_rows = []
    for model_id in models:
        run_path = runs_root / args.experiment / model_id / args.input_name
        baseline_path = (
            runs_root
            / args.baseline_experiment
            / model_id
            / "responses_baseline_autocoded.csv"
        )
        exp2 = read_csv(run_path, EXP2_REQUIRED_COLUMNS, f"Exp2 run for {model_id}")
        baseline = read_csv(
            baseline_path, BASELINE_REQUIRED_COLUMNS, f"baseline run for {model_id}"
        )
        validate_exp2(exp2, model_id, args.expected_rows)
        validate_baseline(baseline, model_id)
        ensure_valid_rows(exp2, f"Exp2 run for {model_id}")
        ensure_valid_rows(baseline, f"baseline run for {model_id}")
        enriched = attach_normal_lexical_baseline(exp2, baseline, model_id)
        inventory_rows.append(inventory_row(model_id, enriched, baseline))
        enriched = add_model_id(enriched, model_id)
        filtered = enriched[enriched["matched_baseline_label"].eq("EXPECTED")].copy()
        frames.append(enriched)
        filtered_frames.append(filtered)
    all_rows = pd.concat(frames, ignore_index=True)
    all_filtered = pd.concat(filtered_frames, ignore_index=True)
    inventory = (
        pd.DataFrame(inventory_rows).sort_values("model_id").reset_index(drop=True)
    )
    unfiltered_tables = experiment_tables(all_rows)
    filtered_tables = experiment_tables(all_filtered)
    baseline_stratified_tables = stratified_tables(all_rows)
    save_table(output_dir / "00_filter_inventory.csv", inventory)
    save_tables(output_dir / "unfiltered", unfiltered_tables)
    save_tables(output_dir / "baseline_filtered", filtered_tables)
    save_tables(output_dir / "baseline_stratified", baseline_stratified_tables)
    write_summary(
        output_dir / "summary.md",
        inventory,
        unfiltered_tables["01_by_model.csv"],
        filtered_tables["01_by_model.csv"],
    )


if __name__ == "__main__":
    main()
