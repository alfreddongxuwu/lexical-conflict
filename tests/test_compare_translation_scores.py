"""Numeric and matching invariants for translation-quality comparisons."""

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import unittest
from pathlib import Path
from tempfile import TemporaryDirectory

import pandas as pd

from compare_translation_scores import ScoredRun, _baseline_labels, _paired, _read


def rows():
    return pd.DataFrame([
        dict(mapping_id=str(i), prompt_id=str(i), context_type="CK_context",
             frame_id="F2", source_item_id=f"s{i}", target_item_id=f"t{i}",
             source_sentence_zh=f"source{i}", source_freq_band="high",
             target_freq_band="low", reference=f"reference{i}",
             baseline_label="EXPECTED" if i == 0 else "OTHER",
             empty=False, failed=False, bleu=score, chrf=score, comet=score)
        for i, score in enumerate((0.2, 0.6, 0.9))])


class PairingTests(unittest.TestCase):
    def compare(self, a, b):
        return _paired(ScoredRun("main", "model", "literal_pk_en", a),
                       ScoredRun("main", "model", "literal_pk_en", b),
                       ["mapping_id", "context_type"], "F2", "F5")

    def test_pairing_ignores_order_and_uses_complete_pairs(self):
        a, b = rows(), rows()
        b["frame_id"] = "F5"
        b.loc[0, ["bleu", "chrf", "comet"]] = 0.5
        b.loc[1, ["bleu", "chrf", "comet"]] = float("nan")
        b.loc[1, "empty"] = True
        b.loc[1, "failed"] = True
        result = self.compare(a, b.iloc[::-1])
        all_rows = next(r for r in result if r["baseline_label"] == "all" and r["metric"] == "chrf")
        self.assertEqual(all_rows["matched"], 3)
        self.assertEqual(all_rows["scored_pairs"], 2)
        self.assertAlmostEqual(all_rows["mean_difference"], 0.15)
        self.assertAlmostEqual(all_rows["left_mean"], 0.55)
        self.assertAlmostEqual(all_rows["right_mean"], 0.70)
        self.assertEqual((all_rows["higher"], all_rows["tied"], all_rows["lower"]), (1, 1, 0))
        self.assertEqual(all_rows["right_empty"], 1)
        self.assertEqual(all_rows["right_missing_score"], 1)
        other = next(r for r in result if r["baseline_label"] == "OTHER" and r["metric"] == "chrf")
        self.assertEqual(other["scored_pairs"], 1)
        self.assertEqual(other["mean_difference"], 0)

    def test_unmatched_rows_remain_visible(self):
        result = self.compare(rows(), rows().iloc[:2])
        record = next(r for r in result if r["baseline_label"] == "all")
        self.assertEqual((record["left_rows"], record["right_rows"], record["left_only"]), (3, 2, 1))
        self.assertEqual(record["scored_pairs"], 2)

    def test_duplicate_pair_keys_rejected(self):
        with self.assertRaises(pd.errors.MergeError):
            self.compare(pd.concat([rows(), rows().iloc[:1]]), rows())

    def test_followup_pairs_hold_frame_fixed(self):
        a = rows()
        f5 = a.copy()
        f5["frame_id"] = "F5"
        a = pd.concat([a, f5])
        b = a.copy()
        b.loc[b.frame_id.eq("F5"), ["bleu", "chrf", "comet"]] += 0.1
        result = _paired(ScoredRun("main", "model", "literal_pk_en", a),
                         ScoredRun("may_mean", "model", "literal_pk_en", b.iloc[::-1]),
                         ["mapping_id", "context_type", "frame_id"], "main", "may_mean")
        effects = {r["frame"]: r["mean_difference"] for r in result
                   if r["metric"] == "comet" and r["baseline_label"] == "all"}
        self.assertEqual(effects["F2"], 0)
        self.assertAlmostEqual(effects["F5"], 0.1)

    def test_changed_source_reference_or_item_rejected(self):
        for column in ("source_sentence_zh", "reference", "target_item_id"):
            with self.subTest(column=column):
                changed = rows()
                changed.loc[0, column] = "different"
                with self.assertRaisesRegex(ValueError, "mismatch"):
                    self.compare(rows(), changed)

    def test_baseline_alignment_and_missing_match(self):
        experiment = rows().drop(columns="baseline_label")
        experiment["context_category"] = "fruit"
        experiment["literal_pk_en"] = experiment.reference
        baseline = rows()
        baseline["context_category"] = "fruit"
        matched = _baseline_labels(experiment, baseline)
        self.assertEqual(matched.baseline_label.tolist(), ["EXPECTED", "OTHER", "OTHER"])
        with self.assertRaisesRegex(ValueError, "Missing baseline"):
            _baseline_labels(experiment, baseline.iloc[:2])
        baseline.loc[0, "source_sentence_zh"] = "different"
        with self.assertRaisesRegex(ValueError, "Baseline source differs"):
            _baseline_labels(experiment, baseline)


class ReversePairingTests(unittest.TestCase):
    def test_reverse_pairing_and_baseline(self):
        a = rows().rename(columns={"source_sentence_zh": "source_sentence_en"})
        a["direction"] = "English-Mandarin"
        a["context_category"] = "fruit"
        a["literal_pk_zh"] = a.reference
        baseline = a.copy()
        experiment = a.drop(columns="baseline_label")
        self.assertEqual(_baseline_labels(experiment, baseline).baseline_label.tolist(),
                         ["EXPECTED", "OTHER", "OTHER"])
        b = a.iloc[::-1].copy()
        b["chrf"] += .1
        result = _paired(ScoredRun("main", "model", "literal_pk_zh", a),
                         ScoredRun("main", "model", "literal_pk_zh", b),
                         ["mapping_id", "context_type"], "F2", "F5")
        record = next(r for r in result if r["metric"] == "chrf" and r["baseline_label"] == "all")
        self.assertEqual(record["direction"], "English-Mandarin")
        self.assertAlmostEqual(record["mean_difference"], .1)
        b.loc[0, "direction"] = "Mandarin-English"
        with self.assertRaisesRegex(ValueError, "Direction"):
            _paired(ScoredRun("main", "model", "literal_pk_zh", a),
                    ScoredRun("main", "model", "literal_pk_zh", b),
                    ["mapping_id", "context_type"], "F2", "F5")

    def test_reference_language_and_ambiguous_source_rejected(self):
        a = rows().rename(columns={"source_sentence_zh": "source_sentence_en"})
        a["response"] = "蝴蝶"
        a["literal_pk_en"] = "butterfly"
        with TemporaryDirectory() as tmp:
            path = Path(tmp) / "scores.csv"
            a.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "Reference language"):
                _read(path, "literal_pk_en")
            a["source_sentence_zh"] = "蝴蝶"
            a.to_csv(path, index=False)
            with self.assertRaisesRegex(ValueError, "exactly one"):
                _read(path, "literal_pk_en")


class ConventionalPairingTests(unittest.TestCase):
    def make_runs(self):
        from compare_translation_scores import _conventional_pairs
        a = rows()
        a["context_category"] = "fruit"
        a["baseline_type"] = "normal_lexical"
        a["frame_id"] = "none"
        a["response"] = "answer"
        b = a.copy()
        b["frame_id"] = "F2"
        b["baseline_type"] = "conventional_meaning"
        b["conventional_label"] = ["EXPECTED", "EXPECTED", "OTHER"]
        b["chrf"] += .1
        for data in (a, b):
            for key, value in dict(model="model", temperature="0.0", seed="2026", num_ctx="4096",
                                   num_predict="128", think="auto", think_resolved="unset").items():
                data[key] = value
        return a, b

    def compare(self, a, b, group="baseline"):
        from compare_translation_scores import _conventional_pairs
        return _conventional_pairs(ScoredRun(group, "model", "literal_expected_en", a),
            ScoredRun("conventional_meaning", "model", "literal_expected_en", b), group, "conventional_meaning/F2")

    def test_numeric_deltas_lexical_and_missingness(self):
        a, b = self.make_runs()
        result = self.compare(a, b.iloc[::-1])
        lexical = next(r for r in result if r["metric"] == "expected_word" and r["baseline_label"] == "all")
        self.assertAlmostEqual(lexical["mean_difference"], 1 / 3)
        self.assertEqual((lexical["higher"], lexical["lower"], lexical["settings_matched"]), (1, 0, 3))
        quality = next(r for r in result if r["metric"] == "chrf" and r["baseline_label"] == "all")
        self.assertAlmostEqual(quality["mean_difference"], .1)
        self.assertAlmostEqual(quality["ci_low"], .1)
        b.loc[1, "conventional_label"] = "FAILED"
        b.loc[1, "failed"] = True
        b.loc[1, "empty"] = True
        b.loc[1, ["bleu", "chrf", "comet"]] = float("nan")
        result = self.compare(a, b)
        lexical = next(r for r in result if r["metric"] == "expected_word" and r["baseline_label"] == "all")
        self.assertEqual(lexical["scored_pairs"], 2)
        self.assertEqual(lexical["right_failed"], 1)
        self.assertEqual(lexical["mean_difference"], 0)
        result = self.compare(a, b.iloc[:2])
        self.assertEqual(result[0]["left_only"], 1)

    def test_mismatches_duplicates_and_settings(self):
        a, b = self.make_runs()
        for key in ["source_sentence_zh", "reference", "source_freq_band", "context_category"]:
            changed = b.copy()
            changed.loc[0, key] = "wrong"
            with self.subTest(key=key), self.assertRaisesRegex(ValueError, "mismatch"):
                self.compare(a, changed)
        with self.assertRaisesRegex(ValueError, "one frame"):
            self.compare(a, pd.concat([b, b.iloc[:1]]))
        b.loc[0, "num_predict"] = "1048"
        self.assertEqual(self.compare(a, b)[0]["settings_different"], 1)
        self.assertEqual(self.compare(a.drop(columns="seed"), b)[0]["settings_unknown"], 3)

    def test_conflict_reuse_has_equal_item_weight(self):
        a, b = self.make_runs()
        a["frame_id"] = "F2"
        a = pd.concat([a, a.iloc[:1].assign(mapping_id="extra")], ignore_index=True)
        a.loc[3, "chrf"] = 0
        result = self.compare(a, b, "main")
        record = next(r for r in result if r["metric"] == "chrf" and r["baseline_label"] == "all")
        self.assertEqual((record["matched"], record["right_rows"], record["source_items"]), (4, 3, 3))
        self.assertAlmostEqual(record["mean_difference"], (.2 + .1 + .1) / 3)

    def test_own_label_preserved_and_reference_rejected(self):
        a, b = self.make_runs()
        b["literal_expected_en"] = b.reference
        b["baseline_label"] = b.conventional_label
        attached = _baseline_labels(b.drop(columns="conventional_label"), a)
        self.assertEqual(attached.conventional_label.tolist(), ["EXPECTED", "EXPECTED", "OTHER"])
        self.assertEqual(attached.baseline_label.tolist(), a.baseline_label.tolist())
        b.loc[0, "literal_expected_en"] = "wrong"
        with self.assertRaisesRegex(ValueError, "Conventional reference"):
            _baseline_labels(b.drop(columns="conventional_label"), a)


if __name__ == "__main__":
    unittest.main()
