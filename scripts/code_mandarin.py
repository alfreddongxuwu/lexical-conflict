"""Code saved English-to-Mandarin responses for known lexical items.

Usage: python code_mandarin.py INPUT_CSV_OR_RUN_DIR ITEMS_CSV OUTPUT_CSV

Matching uses the explicit accepted-translation inventory for each item.
Simplified, traditional and synonymous forms are listed; response text is unchanged.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
import unicodedata
from pathlib import Path
from typing import Iterable

from result_validity import row_is_valid


ACCEPTED_TRANSLATIONS_FILE = Path(__file__).resolve().parents[1] / "data/coding/accepted_translations_zh.csv"


@dataclass(frozen=True)
class AcceptedTranslations:
    by_item: dict[str, tuple[str, ...]]

    @property
    def inventory(self) -> tuple[str, ...]:
        return tuple(dict.fromkeys(term for terms in self.by_item.values() for term in terms))


RESPONSE_COLUMNS = {
    "prompt_id",
    "source_sentence_en",
    "source_item_id",
    "direction",
    "response",
    "status",
}
ITEM_COLUMNS = {"item_id", "source_word_zh", "source_word_en"}
PAIR_CODE_COLUMNS = {
    "contains_pk", "contains_ck", "pk_terms", "ck_terms",
    "pk_matched_terms", "ck_matched_terms", "auto_label",
}
BASELINE_CODE_COLUMNS = {
    "contains_expected", "expected_terms", "expected_matched_terms",
    "auto_label", "baseline_label",
}
CODE_COLUMNS = PAIR_CODE_COLUMNS | BASELINE_CODE_COLUMNS


def _read_csv(path: Path) -> tuple[list[str], list[dict[str, str]]]:
    with path.open(encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        columns = reader.fieldnames or []
        if not columns:
            raise ValueError(f"CSV has no header: {path}")
        if len(columns) != len(set(columns)):
            raise ValueError(f"CSV has duplicate column names: {path}")
        rows = list(reader)
    for line, row in enumerate(rows, start=2):
        if None in row or any(value is None for value in row.values()):
            raise ValueError(f"CSV row {line} has the wrong number of fields: {path}")
    return columns, rows


def load_response_rows(input_path: Path) -> tuple[list[str], list[dict[str, str]]]:
    if input_path.is_file():
        return _read_csv(input_path)
    if not input_path.is_dir():
        raise FileNotFoundError(f"Input CSV or run directory not found: {input_path}")

    shard_paths = sorted((input_path / "shards").glob("*.csv"))
    if not shard_paths:
        raise FileNotFoundError(f"No CSV shards found in {input_path / 'shards'}")
    columns: list[str] | None = None
    rows: list[dict[str, str]] = []
    seen_prompt_ids: set[str] = set()
    for shard_path in shard_paths:
        shard_columns, shard_rows = _read_csv(shard_path)
        if columns is None:
            columns = shard_columns
        elif shard_columns != columns:
            raise ValueError(f"Shard columns differ from the first shard: {shard_path}")
        for row in shard_rows:
            prompt_id = row.get("prompt_id", "").strip()
            if prompt_id and prompt_id in seen_prompt_ids:
                raise ValueError(f"Duplicate prompt_id across input rows: {prompt_id}")
            if prompt_id:
                seen_prompt_ids.add(prompt_id)
            rows.append(row)
    assert columns is not None
    return columns, rows


def normalize_match_text(text: str) -> str:
    """Normalize matching copies only; never write this value back to response."""
    return unicodedata.normalize("NFKC", text).casefold()


def _occurrences(text: str, term: str) -> Iterable[tuple[int, int]]:
    start = 0
    while True:
        index = text.find(term, start)
        if index < 0:
            return
        yield index, index + len(term)
        start = index + 1


def find_matched_terms(response: str, candidate_terms: Iterable[str], inventory_terms: Iterable[str]) -> list[str]:
    """Match Chinese terms and suppress a short term inside a known longer term."""
    normalized_response = normalize_match_text(response)
    normalized_inventory = {
        normalize_match_text(term) for term in inventory_terms if term.strip()
    }
    inventory_spans = [
        (start, end)
        for term in normalized_inventory
        for start, end in _occurrences(normalized_response, term)
    ]
    matched: list[str] = []
    for term in candidate_terms:
        normalized_term = normalize_match_text(term)
        if not normalized_term:
            continue
        spans = list(_occurrences(normalized_response, normalized_term))
        has_standalone_or_full_match = any(
            not any(
                longer_start <= start and end <= longer_end
                and (longer_end - longer_start) > (end - start)
                for longer_start, longer_end in inventory_spans
            )
            for start, end in spans
        )
        if has_standalone_or_full_match and term not in matched:
            matched.append(term)
    return matched


def load_items(items_path: Path) -> tuple[dict[str, dict[str, str]], list[str]]:
    columns, rows = _read_csv(items_path)
    missing = ITEM_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Items CSV missing columns: {sorted(missing)}")
    items: dict[str, dict[str, str]] = {}
    inventory: list[str] = []
    for line, row in enumerate(rows, start=2):
        item_id = row["item_id"].strip()
        if not item_id:
            raise ValueError(f"Items CSV row {line} has empty item_id")
        if item_id in items:
            raise ValueError(f"Duplicate item_id in items CSV: {item_id}")
        for column in ("source_word_zh", "source_word_en"):
            if not row[column].strip():
                raise ValueError(f"Items CSV row {line} has empty {column} for {item_id}")
        items[item_id] = row
        term = row["source_word_zh"].strip()
        if term not in inventory:
            inventory.append(term)
    return items, inventory


def load_accepted_translations(
    path: Path, items: dict[str, dict[str, str]],
) -> AcceptedTranslations:
    columns, rows = _read_csv(path)
    required = {"item_id", "source_word_zh", "accepted_zh"}
    if not required <= set(columns):
        raise ValueError(f"Accepted translations missing columns: {sorted(required - set(columns))}")
    forms: dict[str, list[str]] = {}
    seen: set[tuple[str, str]] = set()
    for row in rows:
        item_id = row["item_id"].strip()
        if item_id not in items:
            raise ValueError(f"Unknown accepted-translation item_id: {item_id}")
        if row["source_word_zh"] != items[item_id]["source_word_zh"]:
            raise ValueError(f"Accepted translation canonical item mismatch: {item_id}")
        term = row["accepted_zh"].strip()
        if not term:
            raise ValueError(f"Empty accepted translation: {item_id}")
        key = item_id, normalize_match_text(term)
        if key in seen:
            raise ValueError(f"Duplicate accepted translation: {key}")
        seen.add(key)
        forms.setdefault(item_id, []).append(term)
    for item_id, item in items.items():
        if item_id not in forms:
            raise ValueError(f"Missing accepted translations for item_id={item_id}")
        if normalize_match_text(item["source_word_zh"]) not in {
            normalize_match_text(term) for term in forms[item_id]
        }:
            raise ValueError(f"Accepted translations omit canonical item: {item_id}")
    return AcceptedTranslations({item_id: tuple(terms) for item_id, terms in forms.items()})


def _require_item(items: dict[str, dict[str, str]], item_id: str, role: str) -> str:
    item_id = item_id.strip()
    if not item_id:
        raise ValueError(f"Missing {role} item ID")
    if item_id not in items:
        raise ValueError(f"Unknown {role} item_id: {item_id}")
    term = items[item_id]["source_word_zh"].strip()
    if not term:
        raise ValueError(f"Missing {role} source term for item_id={item_id}")
    return term


def code_responses(
    columns: list[str], rows: list[dict[str, str]], items: dict[str, dict[str, str]],
    accepted: AcceptedTranslations,
) -> tuple[list[str], list[dict[str, str]]]:
    if set(accepted.by_item) != set(items):
        raise ValueError("Accepted translations must cover exactly the item inventory")
    inventory = accepted.inventory
    missing = RESPONSE_COLUMNS - set(columns)
    if missing:
        raise ValueError(f"Response CSV missing columns: {sorted(missing)}")
    has_pair_columns = {"literal_pk_zh", "literal_ck_zh"} <= set(columns)
    has_expected_column = "literal_expected_zh" in columns
    has_any_pair_column = bool({"literal_pk_zh", "literal_ck_zh"} & set(columns))
    if has_any_pair_column and has_expected_column:
        raise ValueError("Response CSV mixes experiment and baseline reference schemas")
    if not has_pair_columns and not has_expected_column:
        raise ValueError(
            "Response CSV needs literal_pk_zh and literal_ck_zh, or literal_expected_zh"
        )
    if CODE_COLUMNS & set(columns):
        raise ValueError(f"Input already contains code columns: {sorted(CODE_COLUMNS & set(columns))}")
    if not rows:
        raise ValueError("Input contains no response rows")
    if has_pair_columns and "target_item_id" not in columns:
        raise ValueError("Experiment response CSV missing columns: ['target_item_id']")

    ref_style: str | None = None
    seen_prompt_ids: set[str] = set()
    coded_rows: list[dict[str, str]] = []
    for line, row in enumerate(rows, start=2):
        prompt_id = row["prompt_id"].strip()
        if not prompt_id:
            raise ValueError(f"Input row {line} has empty prompt_id")
        if prompt_id in seen_prompt_ids:
            raise ValueError(f"Duplicate prompt_id: {prompt_id}")
        seen_prompt_ids.add(prompt_id)
        if row["direction"].strip() != "English-Mandarin":
            raise ValueError(f"Input row {line} direction must be English-Mandarin")
        if not row["source_sentence_en"].strip():
            raise ValueError(f"Input row {line} has empty source_sentence_en")

        has_pair = (
            has_pair_columns
            and bool(row["literal_pk_zh"].strip())
            and bool(row["literal_ck_zh"].strip())
        )
        has_expected = has_expected_column and bool(row["literal_expected_zh"].strip())
        if has_pair == has_expected:
            raise ValueError(
                f"Input row {line} must contain either literal_pk_zh + literal_ck_zh "
                "or literal_expected_zh"
            )
        style = "pair" if has_pair else "baseline"
        if ref_style is not None and style != ref_style:
            raise ValueError("Input mixes experiment and baseline reference schemas")
        ref_style = style

        pk_term = _require_item(items, row["source_item_id"], "source")
        if "source_word_zh" in columns and row["source_word_zh"].strip() != pk_term:
            raise ValueError(f"Input row {line} source_word_zh mismatches source item")
        if "source_word_en" in columns:
            expected_en = items[row["source_item_id"].strip()]["source_word_en"].strip()
            if row["source_word_en"].strip().casefold() != expected_en.casefold():
                raise ValueError(f"Input row {line} source_word_en mismatches source item")
        target_id = row.get("target_item_id", "").strip()
        if style == "pair":
            ck_term = _require_item(items, target_id, "target")
            for target_term_column in ("target_word_zh", "prompted_word_zh"):
                if (target_term_column in columns
                        and row[target_term_column].strip() != ck_term):
                    raise ValueError(
                        f"Input row {line} {target_term_column} mismatches target item"
                    )
            for reference, term in ((row["literal_pk_zh"], pk_term),
                                    (row["literal_ck_zh"], ck_term)):
                if normalize_match_text(term) not in normalize_match_text(reference):
                    raise ValueError(f"Input row {line} reference omits canonical item term {term}")
        else:
            ck_term = ""
            if target_id:
                _require_item(items, target_id, "target")
            if normalize_match_text(pk_term) not in normalize_match_text(row["literal_expected_zh"]):
                raise ValueError(f"Input row {line} expected reference omits canonical item term {pk_term}")

        pk_terms = accepted.by_item[row["source_item_id"].strip()]
        ck_terms = accepted.by_item[target_id] if style == "pair" else ()
        valid = row_is_valid(row)
        pk_matched = find_matched_terms(row["response"], pk_terms, inventory) if valid and style == "pair" else []
        ck_matched = find_matched_terms(row["response"], ck_terms, inventory) if valid and style == "pair" else []
        expected_matched = find_matched_terms(row["response"], pk_terms, inventory) if valid and style == "baseline" else []
        if not valid:
            label = "FAILED"
        elif style == "baseline":
            label = "EXPECTED" if expected_matched else "OTHER"
        elif pk_matched and ck_matched:
            label = "BOTH"
        elif pk_matched:
            label = "PK"
        elif ck_matched:
            label = "CK"
        else:
            label = "OTHER"

        coded = dict(row)
        if style == "pair":
            coded.update({
                "contains_pk": str(bool(pk_matched)).lower(),
                "contains_ck": str(bool(ck_matched)).lower(),
                "pk_terms": "|".join(pk_terms),
                "ck_terms": "|".join(ck_terms),
                "pk_matched_terms": "|".join(pk_matched),
                "ck_matched_terms": "|".join(ck_matched),
                "auto_label": label,
            })
        else:
            coded.update({
                "contains_expected": str(bool(expected_matched)).lower(),
                "expected_terms": "|".join(pk_terms),
                "expected_matched_terms": "|".join(expected_matched),
                "auto_label": label,
                "baseline_label": label,
            })
        coded_rows.append(coded)
    code_columns = PAIR_CODE_COLUMNS if ref_style == "pair" else BASELINE_CODE_COLUMNS
    return [*columns, *sorted(code_columns)], coded_rows


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("input_csv", type=Path, help="response CSV or run directory with shards/")
    parser.add_argument("items_csv", type=Path)
    parser.add_argument("output_csv", type=Path)
    args = parser.parse_args()
    output_path = args.output_csv.resolve()
    if output_path.exists():
        parser.error(f"Output already exists: {output_path}")
    if output_path in {args.input_csv.resolve(), args.items_csv.resolve()}:
        parser.error("Output path must differ from the input and items files")

    columns, rows = load_response_rows(args.input_csv)
    items, _ = load_items(args.items_csv)
    accepted = load_accepted_translations(ACCEPTED_TRANSLATIONS_FILE, items)
    output_columns, coded_rows = code_responses(columns, rows, items, accepted)
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=output_columns, extrasaction="raise")
        writer.writeheader()
        writer.writerows(coded_rows)
    counts: dict[str, int] = {}
    for row in coded_rows:
        counts[row["auto_label"]] = counts.get(row["auto_label"], 0) + 1
    print(f"Saved {len(coded_rows)} coded rows to {output_path}; labels={counts}")


if __name__ == "__main__":
    main()
