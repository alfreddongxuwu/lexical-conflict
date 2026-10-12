"""Code English baseline responses with the original accepted-form rules.

Usage: python code_english_baseline.py INPUT_CSV_OR_RUN_DIR OUTPUT_CSV
Output preserves raw responses and metadata. A quoted expected word also matches;
EXPECTED is lexical presence, not a translation-quality judgment.
"""
from __future__ import annotations

import argparse
import re
from pathlib import Path

import pandas as pd

from code_mandarin import load_response_rows
from paths import PROJECT_ROOT
from result_validity import row_is_valid


def normalize_text(text: str) -> str:
    if pd.isna(text):
        return ""
    text = str(text).lower().replace("’", "'").replace("“", '"').replace("”", '"')
    return re.sub(r"\s+", " ", text).strip()


def load_accepted_translations() -> dict[str, list[str]]:
    table = pd.read_csv(PROJECT_ROOT / "data/coding/accepted_translations.csv", keep_default_na=False)
    if not {"item_id", "accepted_en"} <= set(table):
        raise ValueError("Accepted translations require item_id and accepted_en")
    return {str(item): list(dict.fromkeys(normalize_text(v) for v in rows.accepted_en if normalize_text(v)))
            for item, rows in table.groupby("item_id", sort=False)}


def auto_label_row(row: pd.Series, forms_by_item_id: dict[str, list[str]]) -> pd.Series:
    forms = forms_by_item_id.get(str(row["source_item_id"]))
    if not forms:
        raise ValueError(f"No accepted translations for {row['source_item_id']}")
    valid = row_is_valid(row)
    response = normalize_text(row.get("response", ""))
    matches = [form for form in forms if valid and re.search(rf"(?<![A-Za-z]){re.escape(form)}(?![A-Za-z])", response)]
    return pd.Series(dict(contains_expected=bool(matches), expected_forms="|".join(forms),
        expected_matched_forms="|".join(matches),
        baseline_label="FAILED" if not valid else "EXPECTED" if matches else "OTHER"))


def validate_for_auto_coding(rows: pd.DataFrame) -> None:
    required = {"prompt_id", "baseline_type", "source_item_id", "response", "status"}
    if missing := required - set(rows):
        raise ValueError(f"Missing columns: {sorted(missing)}")
    if rows.empty or rows.prompt_id.eq("").any() or rows.prompt_id.duplicated().any():
        raise ValueError("Empty input or empty/duplicate prompt_id")
    if not rows.baseline_type.isin(["normal_lexical", "anomalous_no_lexicon", "conventional_meaning"]).all():
        raise ValueError("Unexpected baseline_type")
    conventional = rows[rows.baseline_type.eq("conventional_meaning")]
    if not conventional.empty:
        if "frame_id" not in conventional or conventional.frame_id.eq("").any():
            raise ValueError("Conventional baseline requires frame_id")
        if conventional.duplicated(["source_item_id", "frame_id"]).any():
            raise ValueError("Duplicate conventional word-frame")


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input", type=Path)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    if args.output.exists():
        parser.error(f"Output already exists: {args.output}")
    columns, records = load_response_rows(args.input)
    if set(columns) & {"baseline_label", "contains_expected", "expected_forms", "expected_matched_forms"}:
        parser.error("Input is already coded; supply original responses")
    rows = pd.DataFrame(records)
    validate_for_auto_coding(rows)
    coded = rows.apply(auto_label_row, axis=1, forms_by_item_id=load_accepted_translations())
    result = pd.concat([rows, coded], axis=1)
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8-sig", newline="") as handle:
        result.to_csv(handle, index=False)
    groups = ["baseline_type"] + (["frame_id"] if "frame_id" in result else [])
    for identity, subset in result.groupby(groups, dropna=False):
        valid = subset.baseline_label.ne("FAILED")
        expected = subset.baseline_label.eq("EXPECTED").sum()
        rate = f"{100 * expected / valid.sum():.2f}%" if valid.any() else "null"
        print(f"{identity}: total={len(subset)}, valid={valid.sum()}, failed={(~valid).sum()}, "
              f"empty={subset.response.str.strip().eq('').sum()}, expected={expected}, expected/valid={rate}")
    print(args.output)


if __name__ == "__main__":
    main()
