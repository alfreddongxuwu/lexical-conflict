from __future__ import annotations

import sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "scripts"))

import sys
import tempfile
import unittest
from pathlib import Path


sys.path.insert(0, str(Path(__file__).parent))
import make_position_prompts as position


class PositionPromptTests(unittest.TestCase):
    @classmethod
    def setUpClass(cls):
        cls.design = position.load_saved()
        cls.outputs = position.build_all(cls.design)
        cls.cells = {cell.experiment_id: cell for cell in position.NEW_CELLS}

    def mutated(self, experiment_id: str, prompt_id: str, edit) -> list[dict[str, str]]:
        rows = [dict(row) for row in self.outputs[experiment_id]]
        target = next(row for row in rows if row["prompt_id"] == prompt_id)
        edit(target)
        return rows

    def assert_rejected(self, experiment_id: str, rows, message: str):
        with self.assertRaisesRegex(ValueError, message):
            position.validate_cell(self.cells[experiment_id], rows, self.design.exp1_rows, self.design.frame_rules)

    def test_live_cells_pair_with_exp1(self):
        exp1_ids = {row["prompt_id"] for row in self.design.exp1_rows}
        expected = {
            "position_B": ("B", 1), "position_E": ("E", 1), "position_BM": ("BM", 2),
            "position_BE": ("BE", 2), "position_ME": ("ME", 2), "position_BME": ("BME", 3),
            "reiteration_2": ("M", 2), "reiteration_3": ("M", 3),
        }
        self.assertEqual(set(self.outputs), set(expected))
        for name, rows in self.outputs.items():
            self.assertEqual(len(rows), position.EXPECTED_ROWS, name)
            self.assertEqual({row["prompt_id"] for row in rows}, exp1_ids, name)
            self.assertEqual({(row["position"], row["reiteration_count"]) for row in rows},
                             {(expected[name][0], str(expected[name][1]))}, name)

    def test_saved_cells_are_reproduced_and_differences_rejected(self):
        rebuilt = position.build_cell(position.REITERATION_CELL, self.design.exp1_rows, self.design.frame_rules)
        position.check_against_saved(position.REITERATION_CELL, rebuilt, self.design.reiteration_rows)
        saved = [dict(row) for row in self.design.reiteration_rows]
        saved[0]["prompt"] = saved[0]["prompt"].replace(" 蝴蝶 means red grape.", "", 1)
        with self.assertRaisesRegex(ValueError, "prompt differs from the saved file"):
            position.check_against_saved(position.REITERATION_CELL, rebuilt, saved)

    def test_wrong_copy_count_is_rejected(self):
        rows = self.mutated("reiteration_2", "prompt_000001",
                            lambda row: row.update(prompt=row["prompt"].replace("red grape.", "red grape. 蝴蝶 means red grape.", 1)))
        self.assert_rejected("reiteration_2", rows, "prompt_000001 slot M has 3 rule copies, expected 2")

    def test_wrong_slot_is_rejected(self):
        def move_rule_to_start(row):
            lines = row["prompt"].split("\n")
            row["prompt"] = "\n".join([lines[-1]] + lines[:-1])
        rows = self.mutated("position_E", "prompt_000002", move_rule_to_start)
        self.assert_rejected("position_E", rows, "prompt_000002 has rule lines in B slots, expected E")

    def test_repeated_lead_in_is_rejected(self):
        def repeat_lead_in(row):
            lines = row["prompt"].split("\n")
            lines[2] = lines[0]  # M copy carries the full frame text again
            row["prompt"] = "\n".join(lines)
        rows = self.mutated("position_BM", "prompt_000001", repeat_lead_in)
        self.assert_rejected("position_BM", rows, "prompt_000001 frame lead-in does not occur exactly once")

    def test_lead_in_outside_earliest_slot_is_rejected(self):
        def swap_b_and_m(row):
            lines = row["prompt"].split("\n")
            lines[0], lines[2] = lines[2], lines[0]
            row["prompt"] = "\n".join(lines)
        rows = self.mutated("position_BM", "prompt_000001", swap_b_and_m)
        self.assert_rejected("position_BM", rows, "prompt_000001 frame lead-in is not in the earliest slot")

    def test_wrong_metadata_is_rejected(self):
        rows = self.mutated("position_BE", "prompt_000003", lambda row: row.update(reiteration_count="1"))
        self.assert_rejected("position_BE", rows, "prompt_000003 has wrong position/reiteration_count columns")

    def test_missing_row_is_rejected(self):
        rows = [dict(row) for row in self.outputs["position_B"][1:]]
        self.assert_rejected("position_B", rows, "expected 6000 rows, found 5999")

    def test_frame_tables_must_repeat_one_unit_four_times(self):
        frames = [{"frame_id": "F2", "frame_text_template": "Lexicon: {w} means {e}."}]
        bad = [{"frame_id": "F2", "frame_text_template": "Lexicon: {w} means {e}. {w} means {e}. {w} means {e}."}]
        with self.assertRaisesRegex(ValueError, "Cannot derive a repeated unit for F2"):
            position.derive_frame_rules(frames, bad)

    def test_existing_outputs_are_not_overwritten(self):
        with tempfile.TemporaryDirectory() as tmp:
            rows = {"position_B": self.outputs["position_B"][:1]}
            columns = self.design.exp1_columns + position.ADDED_COLUMNS
            position.write_outputs(Path(tmp), rows, columns)
            with self.assertRaises(FileExistsError):
                position.write_outputs(Path(tmp), rows, columns)


if __name__ == "__main__":
    unittest.main()
