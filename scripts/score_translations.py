"""Score saved lexical-conflict CSVs without changing their text.

Run using an environment with configs/requirements-analysis.txt installed:
    python scripts/score_translations.py INPUT.csv OUTPUT_DIR --no-comet

Omit --no-comet to compute COMET-22 locally on an available GPU or CPU.
Writes literal_pk_en.csv (Conventional) and literal_ck_en.csv (Use Lexicon) for
Mandarin→English inputs, or literal_pk_zh.csv and literal_ck_zh.csv for
English→Mandarin inputs. Baseline inputs instead produce the corresponding
literal_expected output. Each output preserves
all original columns and adds bleu, chrf, and comet. BLEU/chrF are divided
by 100; COMET retains its native scale. Blank hypotheses have blank metric cells.
Output paths must be new; existing input and output files are never overwritten.
English targets use chrF++; Mandarin targets use character-only chrF and
Chinese-tokenized BLEU.
"""

from __future__ import annotations

import argparse
import csv
import os
from pathlib import Path

METRICS = ("bleu", "chrf", "comet")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path)
    parser.add_argument("output_dir", type=Path)
    parser.add_argument("--no-comet", action="store_true", help="CPU-only BLEU and chrF (chrF++ for English targets)")
    args = parser.parse_args()

    with args.input_csv.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        rows = list(reader)
    if not rows:
        parser.error("Input CSV contains no rows")
    if len(columns) != len(set(columns)):
        parser.error("Input CSV contains duplicate column names")
    source_columns = {"source_sentence_zh", "source_sentence_en"} & set(columns)
    if len(source_columns) != 1:
        parser.error("Input must contain exactly one source column: source_sentence_zh or source_sentence_en")
    source_column = next(iter(source_columns))
    reverse = source_column == "source_sentence_en"
    target_language = "zh" if reverse else "en"
    expected_direction = "English-Mandarin" if reverse else "Mandarin-English"

    required = {"prompt_id", source_column, "response"}
    missing = required - set(columns)
    if missing:
        parser.error(f"Missing columns: {sorted(missing)}")
    if "direction" in columns:
        directions = {(row.get("direction") or "").strip() for row in rows}
        if directions != {expected_direction}:
            parser.error(f"direction must be consistently {expected_direction!r}; found {sorted(directions)}")
    if any(column in columns for column in METRICS):
        parser.error("Input already contains metric columns; use the original response CSV")
    reference_suffix = "zh" if reverse else "en"
    primary = f"literal_pk_{reference_suffix}"
    opposite = f"literal_ck_{reference_suffix}"
    expected = f"literal_expected_{reference_suffix}"
    has_pair = primary in columns or opposite in columns
    has_expected = expected in columns
    if has_pair and has_expected:
        parser.error("Input mixes paired and baseline reference schemas")
    if has_pair:
        references = (primary, opposite)
    else:
        references = (expected,)
    missing = set(references) - set(columns)
    if missing:
        parser.error(f"Missing reference columns: {sorted(missing)}")

    seen = set()
    for line, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            parser.error(f"CSV row {line} has the wrong number of fields")
        for column in ("prompt_id", source_column, *references):
            if not row[column].strip():
                parser.error(f"CSV row {line} has empty {column}")
        if row["prompt_id"] in seen:
            parser.error(f"Duplicate prompt_id: {row['prompt_id']}")
        seen.add(row["prompt_id"])

    outputs = [args.output_dir / f"{reference}.csv" for reference in references]
    for output in outputs:
        if output.exists():
            parser.error(f"Output already exists: {output}")

    from scoring import Scorer

    scorer = Scorer(target_language=target_language)
    sources = [row[source_column] for row in rows]
    # Only whitespace-only responses count as empty. Persist the original text.
    hypotheses = [row["response"] if row["response"].strip() else "" for row in rows]
    args.output_dir.mkdir(parents=True, exist_ok=True)
    for reference, output in zip(references, outputs):
        scores = scorer.score_rows(
            sources, hypotheses, [row[reference] for row in rows],
            with_comet=not args.no_comet,
        )
        with output.open("x", encoding="utf-8-sig", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=[*columns, *METRICS])
            writer.writeheader()
            for row, score in zip(rows, scores):
                writer.writerow({**row, **score})
        print(f"{output}: reference={reference}; rows={len(rows)}; empty={hypotheses.count('')}")
        for metric in METRICS:
            values = [score[metric] for score in scores if score[metric] is not None]
            mean = f"{sum(values) / len(values):.4f}" if values else "null"
            print(f"  {metric}: mean={mean}; scored={len(values)}")
    if any(hypotheses):
        print(f"BLEU: {scorer.bleu.get_signature()}")
        print(f"{scorer.chrf_label}: {scorer.chrf.get_signature()}")
    print("COMET: skipped" if args.no_comet else "COMET: Unbabel/wmt22-comet-da")


if __name__ == "__main__":
    main()
