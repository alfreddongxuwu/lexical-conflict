"""Controlled prompt changes and lexical coding invariants."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))
import copy
import unittest

import pandas as pd

import make_conventional_prompts as builder
from code_english_baseline import auto_label_row, validate_for_auto_coding


class ConventionalBaselineTests(unittest.TestCase):
    def setUp(self):
        normal = dict(prompt_id="baseline_1", baseline_id="normal_lexical_x", baseline_type="normal_lexical",
            source_item_id="x", source_word_zh="苹果", standard_en="apple",
            source_sentence_zh="这些苹果熟了。", literal_expected_en="These apples are ripe.",
            context_category="fruit", source_category="fruit", source_freq_band="high",
            prompt=builder.make_prompt("这些苹果熟了。"))
        frames = [dict(frame_id=f"F{i}", frame_name=f"frame{i}",
            frame_text_template=f"Frame {i}: {{source_word_zh}} means {{prompted_en}}.") for i in range(1, 6)]
        self.design = builder.ConventionalBaseline([normal], frames)

    def test_only_rule_added_to_normal_prompt(self):
        original = copy.deepcopy(self.design.normal)
        rows = self.design.build()
        self.design.validate(rows)
        self.assertEqual(self.design.normal, original)
        for row in rows:
            lines = row["prompt"].splitlines()
            self.assertEqual("\n".join([lines[0], lines[-1]]), original[0]["prompt"])
            self.assertEqual(row["prompted_en"], original[0]["standard_en"])

    def test_prompt_metadata_and_coverage_rejections(self):
        for field, bad in [("prompted_en", "monkey"), ("context_category", "animal"),
                           ("source_sentence_zh", "different"), ("literal_expected_en", "different"),
                           ("frame_text", "rewritten"), ("prompt_id", "duplicate")]:
            with self.subTest(field=field):
                rows = self.design.build()
                rows[0][field] = bad
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    self.design.validate(rows)
        rows = self.design.build()
        rows[0]["prompt"] = rows[0]["prompt"].splitlines()[1] + "\n" + self.design.normal[0]["prompt"]
        with self.assertRaisesRegex(ValueError, "prompt mismatch"):
            self.design.validate(rows)
        with self.assertRaisesRegex(ValueError, "Duplicate"):
            self.design.validate(self.design.build() + self.design.build()[:1])
        with self.assertRaisesRegex(ValueError, "Missing"):
            self.design.validate(self.design.build()[:-1])

    def test_conflict_substitution_and_rejection(self):
        rows = self.design.build()
        conflicts = [{**r, "context_type": "PK_context", "prompted_en": "monkey",
                      "literal_pk_en": r["literal_expected_en"],
                      "prompt": r["prompt"].replace("means apple.", "means monkey.")} for r in rows]
        self.design.validate_conflict_matches(rows, conflicts)
        conflicts[0]["prompt"] += " Extra instruction."
        with self.assertRaisesRegex(ValueError, "outside the definition"):
            self.design.validate_conflict_matches(rows, conflicts)

    def test_coding_synonym_empty_failure_and_quoted_rule(self):
        row = {**self.design.build()[0], "status": "ok"}
        forms = {"x": ["apple", "apples", "pome"]}
        for response, status, expected in [("These apples are ripe.", "ok", "EXPECTED"),
                ("A pome.", "ok", "EXPECTED"), ("A monkey.", "ok", "OTHER"),
                ("", "ok", "FAILED"), ("apple", "error", "FAILED"),
                ("The rule says apple, but I translate it as monkey.", "ok", "EXPECTED")]:
            with self.subTest(response=response, status=status):
                candidate = pd.Series({**row, "response": response, "status": status})
                self.assertEqual(auto_label_row(candidate, forms).baseline_label, expected)
                self.assertEqual(candidate.response, response)
        validate_for_auto_coding(pd.DataFrame([{**row, "response": "apples"}]))
        with self.assertRaisesRegex(ValueError, "Unexpected baseline_type"):
            validate_for_auto_coding(pd.DataFrame([{**row, "response": "apples", "baseline_type": "unknown"}]))


if __name__ == "__main__":
    unittest.main()
