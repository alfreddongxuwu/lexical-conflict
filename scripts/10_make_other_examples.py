import argparse
import csv
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[1]
KEEP_COLUMNS = [
    "source_word_zh",
    "standard_en",
    "prompted_en",
    "source_sentence_zh",
    "response",
]
OPTIONAL_EMPTY_COLUMNS = {"prompted_en"}
DEFAULT_INPUT_CANDIDATES = [
    "responses_autocoded.csv",
    "responses_baseline_autocoded.csv",
    "stats/10_other_examples.csv",
    "stats/08_other_examples.csv",
]
DEFAULT_LABEL_COLUMNS = ["auto_label", "baseline_label"]


def project_path(path: str | Path) -> Path:
    path = Path(path)
    if path.is_absolute():
        return path
    return PROJECT_ROOT / path


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Write a compact 10_other_examples.csv for manual inspection. By default, this reads an auto-coded run file, filters OTHER rows, and writes directly into outputs/runs/<experiment_id>/<model_id>/."
    )
    parser.add_argument(
        "--run-dir",
        default=None,
        help="Run directory, for example outputs/runs/main/qwen3_8b.",
    )
    parser.add_argument(
        "--experiment-id",
        default="main",
        help="Experiment id used when --run-dir is not provided.",
    )
    parser.add_argument(
        "--model-id",
        default="qwen3_8b",
        help="Model id used when --run-dir is not provided.",
    )
    parser.add_argument(
        "--input-name",
        default=None,
        help="Input CSV path or name relative to the run directory. Defaults to responses_autocoded.csv, then responses_baseline_autocoded.csv.",
    )
    parser.add_argument(
        "--output-name",
        default="10_other_examples.csv",
        help="Output CSV path or name relative to the run directory.",
    )
    parser.add_argument(
        "--label",
        default="OTHER",
        help="Label value to keep when the input has auto_label or baseline_label.",
    )
    return parser.parse_args()


def resolve_run_dir(args: argparse.Namespace) -> Path:
    if args.run_dir is not None:
        return project_path(args.run_dir)
    return project_path(Path("outputs/runs") / args.experiment_id / args.model_id)


def resolve_input_path(run_dir: Path, input_name: str | None) -> Path:
    if input_name is not None:
        input_path = Path(input_name)
        if input_path.is_absolute():
            return input_path
        return run_dir / input_path
    for candidate in DEFAULT_INPUT_CANDIDATES:
        input_path = run_dir / candidate
        if input_path.exists():
            return input_path
    return run_dir / DEFAULT_INPUT_CANDIDATES[0]


def resolve_output_path(run_dir: Path, output_name: str) -> Path:
    output_path = Path(output_name)
    if output_path.is_absolute():
        return output_path
    return run_dir / output_path


def find_label_column(fieldnames: list[str]) -> str | None:
    for label_column in DEFAULT_LABEL_COLUMNS:
        if label_column in fieldnames:
            return label_column
    return None


def make_other_examples(input_path: Path, label: str) -> list[dict[str, str]]:
    if not input_path.exists():
        checked = ", ".join(DEFAULT_INPUT_CANDIDATES)
        raise FileNotFoundError(
            f"Cannot find input file: {input_path}. If --input-name is omitted, checked: {checked}"
        )
    with input_path.open("r", newline="", encoding="utf-8-sig") as handle:
        reader = csv.DictReader(handle)
        if reader.fieldnames is None:
            raise ValueError(f"Input file has no header row: {input_path}")
        fieldnames = list(reader.fieldnames)
        missing = set(KEEP_COLUMNS) - set(fieldnames) - OPTIONAL_EMPTY_COLUMNS
        if missing:
            raise ValueError(
                f"Input file is missing required columns: {sorted(missing)}"
            )
        label_column = find_label_column(fieldnames)
        total_rows = 0
        other_rows = []
        for row in reader:
            total_rows += 1
            if label_column is not None and row.get(label_column) != label:
                continue
            other_rows.append({column: row.get(column, "") for column in KEEP_COLUMNS})
    if label_column is not None:
        print(
            f"Filtered {label_column} == {label}: {len(other_rows)} / {total_rows} rows"
        )
    else:
        print(
            "No label column found; treating all input rows as already filtered examples."
        )
    return other_rows


def main() -> None:
    args = parse_args()
    run_dir = resolve_run_dir(args)
    input_path = resolve_input_path(run_dir, args.input_name)
    output_path = resolve_output_path(run_dir, args.output_name)
    if not run_dir.exists():
        raise FileNotFoundError(f"Cannot find run directory: {run_dir}")
    output_path.parent.mkdir(parents=True, exist_ok=True)
    other_examples = make_other_examples(input_path, args.label)
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=KEEP_COLUMNS)
        writer.writeheader()
        writer.writerows(other_examples)
    print(f"Input: {input_path}")
    print(f"Saved: {output_path}")
    print(f"Columns: {', '.join(KEEP_COLUMNS)}")
    print(f"Rows: {len(other_examples)}")


if __name__ == "__main__":
    main()
