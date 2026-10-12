"""Behavioral invariants for Mandarin lexical response coding."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import csv
import tempfile
import unittest
from pathlib import Path

from code_mandarin import (AcceptedTranslations, code_responses, find_matched_terms,
                           load_accepted_translations, load_items, load_response_rows)


ITEMS = [
    {"item_id": "animal_005", "source_word_zh": "蝴蝶", "source_word_en": "butterfly"},
    {"item_id": "animal_019", "source_word_zh": "鳄鱼", "source_word_en": "crocodile"},
    {"item_id": "music_011", "source_word_zh": "腰鼓", "source_word_en": "waist drum"},
    {"item_id": "music_018", "source_word_zh": "手鼓", "source_word_en": "hand drum"},
]
INVENTORY = [row["source_word_zh"] for row in ITEMS]
ACCEPTED = AcceptedTranslations({r["item_id"]: (r["source_word_zh"],) for r in ITEMS})
PAIR_COLUMNS = [
    "prompt_id", "source_sentence_en", "literal_pk_zh", "literal_ck_zh",
    "source_item_id", "target_item_id", "direction", "response", "status",
]


def pair_row(prompt_id="p1", response="蝴蝶。", status="ok"):
    return {
        "prompt_id": prompt_id,
        "source_sentence_en": "These butterfly are ripe enough to eat.",
        "literal_pk_zh": "这些蝴蝶已经熟到可以吃了。",
        "literal_ck_zh": "这些鳄鱼已经熟到可以吃了。",
        "source_item_id": "animal_005",
        "target_item_id": "animal_019",
        "direction": "English-Mandarin",
        "response": response,
        "status": status,
    }


class MandarinCodingTests(unittest.TestCase):
    def code(self, rows, columns=None):
        return code_responses(columns or PAIR_COLUMNS, rows, {r["item_id"]: r for r in ITEMS}, ACCEPTED)[1]

    def test_synonyms_traditional_forms_and_shared_forms(self):
        forms = AcceptedTranslations({**ACCEPTED.by_item,
            "animal_005": ("蝴蝶", "蝶"), "animal_019": ("鳄鱼", "鱷魚")})
        raw = "  蝶和鱷魚。\n"
        rows = [pair_row("pk", "蝶。"), pair_row("ck", "鱷魚。"), pair_row("both", raw)]
        coded = code_responses(PAIR_COLUMNS, rows, {r["item_id"]: r for r in ITEMS}, forms)[1]
        self.assertEqual([r["auto_label"] for r in coded], ["PK", "CK", "BOTH"])
        self.assertEqual(coded[-1]["response"], raw)
        self.assertEqual(coded[0]["pk_terms"], "蝴蝶|蝶")
        shared = AcceptedTranslations({**forms.by_item, "animal_019": ("鳄鱼", "蝶")})
        result = code_responses(PAIR_COLUMNS, [pair_row(response="蝶。")],
                                {r["item_id"]: r for r in ITEMS}, shared)[1]
        self.assertEqual(result[0]["auto_label"], "BOTH")

    def test_baseline_uses_the_same_accepted_alternatives(self):
        row = pair_row(response="鱷魚。")
        row["source_item_id"] = "animal_019"
        row["literal_expected_zh"] = "鳄鱼。"
        for key in ("literal_pk_zh", "literal_ck_zh", "target_item_id"):
            del row[key]
        forms = AcceptedTranslations({**ACCEPTED.by_item, "animal_019": ("鳄鱼", "鱷魚")})
        coded = code_responses(list(row), [row], {r["item_id"]: r for r in ITEMS}, forms)[1][0]
        self.assertEqual(coded["baseline_label"], "EXPECTED")
        self.assertEqual(coded["expected_matched_terms"], "鱷魚")

    def test_alternative_inventory_validates_coverage_identity_and_duplicates(self):
        items = {r["item_id"]: r for r in ITEMS}
        rows = [{"item_id": r["item_id"], "source_word_zh": r["source_word_zh"],
                 "accepted_zh": r["source_word_zh"]} for r in ITEMS]
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "accepted_translations.csv"
            def write(data):
                with path.open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=list(rows[0]))
                    writer.writeheader()
                    writer.writerows(data)
            write(rows + [{**rows[1], "accepted_zh": "鱷魚"}])
            accepted = load_accepted_translations(path, items)
            self.assertEqual(accepted.by_item["animal_019"], ("鳄鱼", "鱷魚"))
            for data, message in [
                (rows[:-1], "Missing accepted translations"),
                (rows + [rows[0]], "Duplicate accepted translation"),
                ([{**rows[0], "accepted_zh": ""}, *rows[1:]], "Empty accepted translation"),
                ([{**rows[0], "item_id": "unknown"}, *rows[1:]], "Unknown accepted-translation"),
                ([{**rows[0], "source_word_zh": "wrong"}, *rows[1:]], "canonical item mismatch"),
                ([{**rows[0], "accepted_zh": "蝶"}, *rows[1:]], "omit canonical item"),
            ]:
                write(data)
                with self.assertRaisesRegex(ValueError, message):
                    load_accepted_translations(path, items)

    def test_isolated_terms_punctuation_and_mixed_english(self):
        coded = self.code([pair_row(response="答案是：蝴蝶, not 鳄鱼! (mixed English).")])[0]
        self.assertEqual(coded["auto_label"], "BOTH")
        self.assertEqual(coded["pk_matched_terms"], "蝴蝶")
        self.assertEqual(coded["ck_matched_terms"], "鳄鱼")

    def test_longer_inventory_term_suppresses_only_embedded_shorter_match(self):
        # 腰鼓 and 手鼓 are known item terms; an isolated 鼓 still counts.
        matched = find_matched_terms("腰鼓、鼓声和手鼓", ["鼓"], INVENTORY)
        self.assertEqual(matched, ["鼓"])
        self.assertEqual(find_matched_terms("腰鼓、手鼓", ["鼓"], INVENTORY), [])

    def test_pk_ck_other_empty_and_failed(self):
        rows = self.code([
            pair_row("pk", "蝴蝶。"),
            pair_row("ck", "鳄鱼。"),
            pair_row("other", "没有相关词。"),
            pair_row("empty", ""),
            pair_row("failed", "蝴蝶。", "error"),
        ])
        self.assertEqual([row["auto_label"] for row in rows], ["PK", "CK", "OTHER", "FAILED", "FAILED"])
        self.assertEqual([row["contains_pk"] for row in rows], ["true", "false", "false", "false", "false"])

    def test_baseline_expected_other_failed_and_comparison_label(self):
        columns = [c for c in PAIR_COLUMNS if c not in {"literal_pk_zh", "literal_ck_zh", "target_item_id"}]
        columns.append("literal_expected_zh")
        rows = []
        for prompt_id, response, status in (("yes", "蝴蝶。", "ok"), ("no", "鳄鱼。", "ok"), ("bad", "", "ok")):
            row = {key: value for key, value in pair_row(prompt_id, response, status).items()
                   if key not in {"literal_pk_zh", "literal_ck_zh"}}
            row["literal_expected_zh"] = "这些蝴蝶已经熟到可以吃了。"
            rows.append(row)
        coded = self.code(rows, columns)
        self.assertEqual([row["auto_label"] for row in coded], ["EXPECTED", "OTHER", "FAILED"])
        self.assertEqual(coded[0]["baseline_label"], "EXPECTED")
        self.assertNotIn("baseline_label", self.code([pair_row()])[0])
        self.assertNotIn("contains_pk", coded[0])

    def test_saved_response_text_is_unchanged_in_output(self):
        raw = "  蝴蝶, but not 鳄鱼。\n(附注)  "
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            input_path, items_path, output_path = root / "input.csv", root / "items.csv", root / "coded.csv"
            with input_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=PAIR_COLUMNS)
                writer.writeheader()
                writer.writerow(pair_row(response=raw))
            with items_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=["item_id", "source_word_zh", "source_word_en"])
                writer.writeheader()
                writer.writerows(ITEMS)
            columns, rows = load_response_rows(input_path)
            items, inventory = load_items(items_path)
            from code_mandarin import code_responses
            output_columns, coded = code_responses(columns, rows, items, ACCEPTED)
            with output_path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=output_columns)
                writer.writeheader()
                writer.writerows(coded)
            with output_path.open(encoding="utf-8", newline="") as f:
                actual = next(csv.DictReader(f))["response"]
        self.assertEqual(actual, raw)

    def test_shards_merge_and_duplicate_prompt_ids_are_rejected(self):
        with tempfile.TemporaryDirectory() as directory:
            root = Path(directory)
            shards = root / "shards"
            shards.mkdir()
            for name, rows in (("shard_b.csv", [pair_row("p2")]), ("shard_a.csv", [pair_row("p1")])):
                with (shards / name).open("w", encoding="utf-8", newline="") as f:
                    writer = csv.DictWriter(f, fieldnames=PAIR_COLUMNS)
                    writer.writeheader()
                    writer.writerows(rows)
            columns, rows = load_response_rows(root)
            self.assertEqual([row["prompt_id"] for row in rows], ["p1", "p2"])
            with (shards / "shard_c.csv").open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=PAIR_COLUMNS)
                writer.writeheader()
                writer.writerow(pair_row("p1"))
            with self.assertRaisesRegex(ValueError, "Duplicate prompt_id"):
                load_response_rows(root)

    def test_duplicate_prompt_and_unknown_or_missing_items_fail_closed(self):
        with self.assertRaisesRegex(ValueError, "Duplicate prompt_id"):
            self.code([pair_row(), pair_row()])
        unknown = pair_row()
        unknown["source_item_id"] = "missing"
        with self.assertRaisesRegex(ValueError, "Unknown source item_id"):
            self.code([unknown])
        missing = pair_row()
        missing["target_item_id"] = ""
        with self.assertRaisesRegex(ValueError, "Missing target item ID"):
            self.code([missing])

    def test_missing_reference_metadata_and_item_terms_fail_closed(self):
        incomplete = pair_row()
        incomplete["literal_ck_zh"] = ""
        with self.assertRaisesRegex(ValueError, "either literal_pk_zh"):
            self.code([incomplete])
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "items.csv"
            fields = ["item_id", "source_word_zh", "source_word_en"]
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows([*ITEMS, ITEMS[0]])
            with self.assertRaisesRegex(ValueError, "Duplicate item_id"):
                load_items(path)
            with path.open("w", encoding="utf-8", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=fields)
                writer.writeheader()
                writer.writerows([{**ITEMS[0], "source_word_zh": ""}, *ITEMS[1:]])
            with self.assertRaisesRegex(ValueError, "empty source_word_zh"):
                load_items(path)

    def test_reference_must_contain_canonical_item_term_and_schemas_cannot_mix(self):
        mismatch = pair_row()
        mismatch["literal_pk_zh"] = "这些动物已经熟到可以吃了。"
        with self.assertRaisesRegex(ValueError, "omits canonical item term 蝴蝶"):
            self.code([mismatch])
        mixed_columns = [*PAIR_COLUMNS, "literal_expected_zh"]
        mixed = pair_row()
        mixed["literal_expected_zh"] = "这些蝴蝶已经熟到可以吃了。"
        with self.assertRaisesRegex(ValueError, "mixes experiment and baseline"):
            self.code([mixed], mixed_columns)

    def test_present_prompted_target_term_must_match_target_item(self):
        columns = [*PAIR_COLUMNS, "prompted_word_zh"]
        row = pair_row()
        row["prompted_word_zh"] = "蝴蝶"
        with self.assertRaisesRegex(ValueError, "prompted_word_zh mismatches target item"):
            self.code([row], columns)


if __name__ == "__main__":
    unittest.main()
