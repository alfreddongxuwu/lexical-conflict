"""Direction-aware translation scoring invariants."""

from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import csv
import io
import sys
import tempfile
import unittest
from contextlib import redirect_stderr
from pathlib import Path
from unittest.mock import patch

import score_translations
from scoring import Scorer


class CaptureScorer:
    calls = []

    def __init__(self, target_language="en"):
        self.target_language = target_language
        self.delegate = Scorer(target_language=target_language)
        self.bleu = self.delegate.bleu
        self.chrf = self.delegate.chrf
        self.chrf_label = self.delegate.chrf_label

    def score_rows(self, sources, hypotheses, references, *, with_comet=True):
        self.calls.append((self.target_language, sources, hypotheses, references, with_comet))
        return self.delegate.score_rows(sources, hypotheses, references, with_comet=with_comet)


class ReverseScoringTests(unittest.TestCase):
    def setUp(self):
        CaptureScorer.calls = []
        self.temp = tempfile.TemporaryDirectory()
        self.root = Path(self.temp.name)

    def tearDown(self):
        self.temp.cleanup()

    def write_csv(self, name, columns, rows):
        path = self.root / name
        with path.open("w", encoding="utf-8", newline="") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(rows)
        return path

    def run_cli(self, source, output):
        with patch.object(sys, "argv", ["score_translations.py", str(source), str(output), "--no-comet"]), \
             patch("scoring.Scorer", CaptureScorer):
            score_translations.main()

    def run_cli_with_error(self, source, output):
        stderr = io.StringIO()
        with patch.object(sys, "argv", ["score_translations.py", str(source), str(output), "--no-comet"]), \
             redirect_stderr(stderr):
            with self.assertRaises(SystemExit) as raised:
                score_translations.main()
        self.assertEqual(raised.exception.code, 2)
        return stderr.getvalue()

    def test_reverse_paired_schema_uses_english_source_chinese_refs_and_preserves_text(self):
        columns = ["prompt_id", "direction", "source_sentence_en", "literal_pk_zh", "literal_ck_zh", "response"]
        rows = [
            {"prompt_id": "p1", "direction": "English-Mandarin", "source_sentence_en": "  English source. ",
             "literal_pk_zh": "普通意思。", "literal_ck_zh": "冲突意思。", "response": "  普通意思。  "},
            {"prompt_id": "p2", "direction": "English-Mandarin", "source_sentence_en": "Another source.",
             "literal_pk_zh": "第二个意思。", "literal_ck_zh": "另一个意思。", "response": " \t "},
        ]
        source = self.write_csv("reverse.csv", columns, rows)
        output = self.root / "scored"
        self.run_cli(source, output)

        self.assertEqual([call[0] for call in CaptureScorer.calls], ["zh", "zh"])
        self.assertEqual(CaptureScorer.calls[0][1], ["  English source. ", "Another source."])
        self.assertEqual(CaptureScorer.calls[0][2], ["  普通意思。  ", ""])
        self.assertEqual(CaptureScorer.calls[0][3], ["普通意思。", "第二个意思。"])
        self.assertEqual(CaptureScorer.calls[1][3], ["冲突意思。", "另一个意思。"])
        self.assertFalse(any(call[4] for call in CaptureScorer.calls))

        for reference in ("literal_pk_zh", "literal_ck_zh"):
            with (output / f"{reference}.csv").open(encoding="utf-8-sig", newline="") as handle:
                scored = list(csv.DictReader(handle))
            self.assertEqual([row["response"] for row in scored], ["  普通意思。  ", " \t "])
            self.assertEqual(scored[0]["source_sentence_en"], "  English source. ")
            self.assertTrue(float(scored[0]["bleu"]) > 0)
            self.assertTrue(float(scored[0]["chrf"]) > 0)
            self.assertEqual((scored[1]["bleu"], scored[1]["chrf"], scored[1]["comet"]), ("", "", ""))

    def test_reverse_baseline_schema_writes_expected_filename(self):
        source = self.write_csv(
            "baseline.csv",
            ["prompt_id", "source_sentence_en", "literal_expected_zh", "response"],
            [{"prompt_id": "p1", "source_sentence_en": "English.",
              "literal_expected_zh": "中文。", "response": "中文。"}],
        )
        output = self.root / "baseline-scored"
        self.run_cli(source, output)
        self.assertTrue((output / "literal_expected_zh.csv").is_file())

    def test_mandarin_metrics_are_chinese_bleu_and_character_chrf(self):
        scorer = Scorer(target_language="zh")
        result = scorer.score_rows(["source"], ["这些蝴蝶已经熟到可以吃了。"],
                                   ["这些蝴蝶已经熟到可以吃了。"], with_comet=False)[0]
        self.assertEqual((result["bleu"], result["chrf"]), (1.0, 1.0))
        self.assertEqual(scorer.bleu.tokenizer.__class__.__name__, "TokenizerZh")
        self.assertEqual(scorer.chrf.word_order, 0)
        self.assertEqual(scorer.chrf_label, "chrF")
        english = Scorer()
        self.assertEqual(english.target_language, "en")
        self.assertEqual(english.bleu.tokenizer.__class__.__name__, "Tokenizer13a")
        self.assertEqual(english.chrf.word_order, 2)
        self.assertEqual(english.chrf_label, "chrF++")

    def test_existing_mandarin_to_english_schema_keeps_default_selection(self):
        source = self.write_csv(
            "forward.csv",
            ["prompt_id", "source_sentence_zh", "literal_pk_en", "literal_ck_en", "response"],
            [{"prompt_id": "p1", "source_sentence_zh": "中文源句。", "literal_pk_en": "ordinary",
              "literal_ck_en": "opposite", "response": "ordinary"}],
        )
        output = self.root / "forward-scored"
        self.run_cli(source, output)
        call = CaptureScorer.calls[0]
        self.assertEqual(call[0], "en")
        self.assertEqual(call[1:4], (["中文源句。"], ["ordinary"], ["ordinary"]))
        self.assertTrue((output / "literal_pk_en.csv").is_file())
        self.assertTrue((output / "literal_ck_en.csv").is_file())

    def test_ambiguous_source_columns_and_inconsistent_direction_rejected(self):
        cols = ["prompt_id", "source_sentence_en", "source_sentence_zh", "literal_expected_zh", "response"]
        source = self.write_csv("mixed-sources.csv", cols, [{
            "prompt_id": "p1", "source_sentence_en": "English", "source_sentence_zh": "中文",
            "literal_expected_zh": "中文。", "response": "中文。",
        }])
        self.assertIn("exactly one source column", self.run_cli_with_error(source, self.root / "out1"))

        source = self.write_csv("wrong-direction.csv",
                                ["prompt_id", "direction", "source_sentence_en", "literal_expected_zh", "response"],
                                [{"prompt_id": "p1", "direction": "Mandarin-English", "source_sentence_en": "English",
                                  "literal_expected_zh": "中文。", "response": "中文。"}])
        self.assertIn("direction must be consistently", self.run_cli_with_error(source, self.root / "out2"))

    def test_blank_reference_and_existing_output_rejected(self):
        columns = ["prompt_id", "source_sentence_en", "literal_expected_zh", "response"]
        source = self.write_csv("blank-ref.csv", columns, [{
            "prompt_id": "p1", "source_sentence_en": "English", "literal_expected_zh": "  ", "response": "中文。",
        }])
        self.assertIn("empty literal_expected_zh", self.run_cli_with_error(source, self.root / "out"))

        source = self.write_csv("valid.csv", columns, [{
            "prompt_id": "p1", "source_sentence_en": "English", "literal_expected_zh": "中文。", "response": "中文。",
        }])
        output = self.root / "existing"
        output.mkdir()
        (output / "literal_expected_zh.csv").write_text("keep", encoding="utf-8")
        self.assertIn("already exists", self.run_cli_with_error(source, output))
        self.assertEqual((output / "literal_expected_zh.csv").read_text(encoding="utf-8"), "keep")


if __name__ == "__main__":
    unittest.main()
