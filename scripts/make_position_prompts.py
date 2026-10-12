#!/usr/bin/env python3
"""Build rule-position × reiteration prompts from the saved Exp1 prompts.

Build the B, E, BE, BM, ME, BME, M×2 and M×3 lexical-rule layouts.
"""

from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from enum import Enum
from pathlib import Path
from typing import Mapping, Sequence


PROJECT_DIR = Path(__file__).resolve().parents[1]
DATA_DIR = PROJECT_DIR / "data"
DEFAULT_OUTPUT_DIR = PROJECT_DIR / "data/processed"
EXPECTED_ROWS = 6_000
TASK_LINE = (
    "Task: Translate Mandarin to English. Output only the English translation "
    "without explanations or notes."
)
TRANSLATE_PREFIX = "Translate: "
ADDED_COLUMNS = ("position", "reiteration_count")


class Slot(str, Enum):
    B = "B"  # own line before the task line
    M = "M"  # between the task and translate lines (the Exp1 slot)
    E = "E"  # own line after the translate line


SLOT_ORDER = (Slot.B, Slot.M, Slot.E)


@dataclass(frozen=True)
class Cell:
    experiment_id: str
    copies: tuple[tuple[Slot, int], ...]  # slot -> copies, in prompt order

    @property
    def slots(self) -> tuple[Slot, ...]:
        return tuple(slot for slot, _ in self.copies)

    @property
    def position(self) -> str:
        return "".join(slot.value for slot in self.slots)

    @property
    def reiteration_count(self) -> int:
        return sum(n for _, n in self.copies)


def spread(*slots: Slot) -> tuple[tuple[Slot, int], ...]:
    return tuple((slot, 1) for slot in slots)


# Cells saved by earlier runs: rebuilt only to check the builder against them.
EXP1_CELL = Cell("main", ((Slot.M, 1),))
REITERATION_CELL = Cell("reiteration", ((Slot.M, 5),))

NEW_CELLS = (
    Cell("position_B", spread(Slot.B)),
    Cell("position_E", spread(Slot.E)),
    Cell("position_BM", spread(Slot.B, Slot.M)),
    Cell("position_BE", spread(Slot.B, Slot.E)),
    Cell("position_ME", spread(Slot.M, Slot.E)),
    Cell("position_BME", spread(Slot.B, Slot.M, Slot.E)),
    Cell("reiteration_2", ((Slot.M, 2),)),
    Cell("reiteration_3", ((Slot.M, 3),)),
)


@dataclass(frozen=True)
class FrameRule:
    """A frame's lead-in and the unit repeated by the reiteration follow-up."""

    frame_id: str
    lead_in: str  # rendered with {source_word_zh}/{prompted_en} placeholders
    unit: str


@dataclass(frozen=True)
class RenderedRule:
    lead_in: str
    unit: str
    rule: str  # "{w} means {e}." — the string counted per copy

    @property
    def first(self) -> str:
        return f"{self.lead_in} {self.unit}" if self.lead_in else self.unit


def read_csv(path: Path) -> list[dict[str, str]]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def read_columns(path: Path) -> tuple[str, ...]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return tuple(next(csv.reader(handle)))


def derive_frame_rules(
    frames: Sequence[Mapping[str, str]],
    frames_reiteration: Sequence[Mapping[str, str]],
) -> dict[str, FrameRule]:
    """Split each frame into lead-in and repeated unit.

    The reiteration template must equal the Exp1 template followed by four
    space-joined copies of one unit, and the Exp1 template must end with it.
    """
    reiteration_by_id = {row["frame_id"]: row["frame_text_template"] for row in frames_reiteration}
    rules: dict[str, FrameRule] = {}
    for frame in frames:
        frame_id = frame["frame_id"]
        main = frame["frame_text_template"]
        repeated = reiteration_by_id.get(frame_id)
        if repeated is None or not repeated.startswith(main + " "):
            raise ValueError(f"Reiteration template for {frame_id} does not extend the Exp1 template")
        extra = repeated[len(main) + 1:]
        unit = None
        for candidate_len in range(1, len(extra) + 1):
            candidate = extra[:candidate_len]
            if " ".join([candidate] * 4) == extra:
                unit = candidate
                break
        if unit is None or not main.endswith(unit):
            raise ValueError(f"Cannot derive a repeated unit for {frame_id}")
        rules[frame_id] = FrameRule(frame_id, main[: -len(unit)].strip(), unit)
    if set(rules) != set(reiteration_by_id):
        raise ValueError("Exp1 and reiteration frame tables list different frames")
    return rules


def render_rule(frame: FrameRule, row: Mapping[str, str]) -> RenderedRule:
    values = {"source_word_zh": row["source_word_zh"], "prompted_en": row["prompted_en"]}
    rendered = RenderedRule(
        lead_in=frame.lead_in.format(**values),
        unit=frame.unit.format(**values),
        rule="{source_word_zh} means {prompted_en}.".format(**values),
    )
    if rendered.first != row["frame_text"]:
        raise ValueError(f"Frame table does not reproduce Exp1 frame_text for {row['prompt_id']}")
    return rendered


def exp1_prompt(row: Mapping[str, str]) -> str:
    return f"{TASK_LINE}\n{row['frame_text']}\n{TRANSLATE_PREFIX}{row['source_sentence_zh']}"


def slot_lines(cell: Cell, rule: RenderedRule) -> dict[Slot, str]:
    lines: dict[Slot, str] = {}
    for index, (slot, copies) in enumerate(cell.copies):
        if copies < 1:
            raise ValueError(f"{cell.experiment_id}: slot {slot.value} needs at least one copy")
        units = [rule.unit] * copies
        if index == 0:
            units[0] = rule.first
        lines[slot] = " ".join(units)
    return lines


def build_cell(
    cell: Cell,
    exp1_rows: Sequence[Mapping[str, str]],
    frame_rules: Mapping[str, FrameRule],
) -> list[dict[str, str]]:
    rows = []
    for exp1 in exp1_rows:
        if exp1["prompt"] != exp1_prompt(exp1):
            raise ValueError(f"Saved Exp1 prompt has an unexpected layout: {exp1['prompt_id']}")
        rule = render_rule(frame_rules[exp1["frame_id"]], exp1)
        lines = slot_lines(cell, rule)
        prompt_lines = [
            lines.get(Slot.B),
            TASK_LINE,
            lines.get(Slot.M),
            f"{TRANSLATE_PREFIX}{exp1['source_sentence_zh']}",
            lines.get(Slot.E),
        ]
        row = dict(exp1)
        row["frame_text"] = "\n".join(lines[slot] for slot in cell.slots)
        row["prompt"] = "\n".join(line for line in prompt_lines if line is not None)
        row["position"] = cell.position
        row["reiteration_count"] = str(cell.reiteration_count)
        rows.append(row)
    validate_cell(cell, rows, exp1_rows, frame_rules)
    return rows


def parse_slots(prompt: str, prompt_id: str) -> dict[Slot, str]:
    """Return the rule line found in each slot of a prompt."""
    lines = prompt.split("\n")
    task = [i for i, line in enumerate(lines) if line == TASK_LINE]
    translate = [i for i, line in enumerate(lines) if line.startswith(TRANSLATE_PREFIX)]
    if len(task) != 1 or len(translate) != 1 or task[0] > translate[0]:
        raise ValueError(f"{prompt_id}: expected one task line before one translate line")
    t, s = task[0], translate[0]
    regions = {Slot.B: lines[:t], Slot.M: lines[t + 1:s], Slot.E: lines[s + 1:]}
    found: dict[Slot, str] = {}
    for slot, region in regions.items():
        if len(region) > 1:
            raise ValueError(f"{prompt_id}: more than one line in slot {slot.value}")
        if region:
            if not region[0].strip():
                raise ValueError(f"{prompt_id}: empty line in slot {slot.value}")
            found[slot] = region[0]
    return found


def validate_cell(
    cell: Cell,
    rows: Sequence[Mapping[str, str]],
    exp1_rows: Sequence[Mapping[str, str]],
    frame_rules: Mapping[str, FrameRule],
) -> None:
    if len(rows) != len(exp1_rows):
        raise ValueError(f"{cell.experiment_id}: expected {len(exp1_rows)} rows, found {len(rows)}")
    keys = [(r["mapping_id"], r["frame_id"], r["context_type"]) for r in rows]
    exp1_keys = {(r["mapping_id"], r["frame_id"], r["context_type"]) for r in exp1_rows}
    if len(set(keys)) != len(keys) or set(keys) != exp1_keys:
        raise ValueError(f"{cell.experiment_id}: rows do not cover each Exp1 mapping × frame × context once")
    if len({r["prompt_id"] for r in rows}) != len(rows):
        raise ValueError(f"{cell.experiment_id}: duplicate prompt_id")
    if len({r["prompt"] for r in rows}) != len(rows):
        raise ValueError(f"{cell.experiment_id}: duplicate prompt text")
    exp1_by_id = {r["prompt_id"]: r for r in exp1_rows}
    for row in rows:
        prompt_id = row["prompt_id"]
        exp1 = exp1_by_id.get(prompt_id)
        if exp1 is None or keys_of(exp1) != keys_of(row):
            raise ValueError(f"{cell.experiment_id}: {prompt_id} does not match its Exp1 row")
        if row["position"] != cell.position or row["reiteration_count"] != str(cell.reiteration_count):
            raise ValueError(f"{cell.experiment_id}: {prompt_id} has wrong position/reiteration_count columns")
        rule = render_rule(frame_rules[row["frame_id"]], exp1)
        found = parse_slots(row["prompt"], prompt_id)
        if tuple(slot for slot in SLOT_ORDER if slot in found) != cell.slots:
            occupied = "".join(slot.value for slot in SLOT_ORDER if slot in found)
            raise ValueError(f"{cell.experiment_id}: {prompt_id} has rule lines in {occupied or 'no'} slots, expected {cell.position}")
        for slot, copies in cell.copies:
            if found[slot].count(rule.rule) != copies:
                raise ValueError(
                    f"{cell.experiment_id}: {prompt_id} slot {slot.value} has "
                    f"{found[slot].count(rule.rule)} rule copies, expected {copies}"
                )
        if row["prompt"].count(rule.rule) != cell.reiteration_count:
            raise ValueError(f"{cell.experiment_id}: {prompt_id} rule count differs from reiteration_count")
        if rule.lead_in:
            if row["prompt"].count(rule.lead_in) != 1:
                raise ValueError(f"{cell.experiment_id}: {prompt_id} frame lead-in does not occur exactly once")
            if not found[cell.slots[0]].startswith(rule.lead_in):
                raise ValueError(f"{cell.experiment_id}: {prompt_id} frame lead-in is not in the earliest slot")


def keys_of(row: Mapping[str, str]) -> tuple[str, str, str]:
    return (row["mapping_id"], row["frame_id"], row["context_type"])


def check_against_saved(
    cell: Cell,
    built: Sequence[Mapping[str, str]],
    saved: Sequence[Mapping[str, str]],
) -> None:
    """Require the rebuilt cell to equal a saved prompt file character for character."""
    saved_by_key = {keys_of(row): row for row in saved}
    if len(saved_by_key) != len(built):
        raise ValueError(f"{cell.experiment_id}: saved file has {len(saved_by_key)} rows, rebuilt {len(built)}")
    for row in built:
        saved_row = saved_by_key.get(keys_of(row))
        if saved_row is None:
            raise ValueError(f"{cell.experiment_id}: no saved row for {keys_of(row)}")
        for column in ("prompt", "frame_text"):
            if row[column] != saved_row[column]:
                raise ValueError(f"{cell.experiment_id}: {row['prompt_id']} {column} differs from the saved file")


@dataclass(frozen=True)
class SavedDesign:
    exp1_rows: list[dict[str, str]]
    exp1_columns: tuple[str, ...]
    reiteration_rows: list[dict[str, str]]
    frame_rules: dict[str, FrameRule]


def load_saved() -> SavedDesign:
    exp1_path = DATA_DIR / "processed" / "prompts.csv"
    return SavedDesign(
        exp1_rows=read_csv(exp1_path),
        exp1_columns=read_columns(exp1_path),
        reiteration_rows=read_csv(DATA_DIR / "processed" / "prompts_reiteration.csv"),
        frame_rules=derive_frame_rules(
            read_csv(DATA_DIR / "design" / "frames.csv"),
            read_csv(DATA_DIR / "design" / "frames_reiteration.csv"),
        ),
    )


def build_all(design: SavedDesign) -> dict[str, list[dict[str, str]]]:
    if len(design.exp1_rows) != EXPECTED_ROWS:
        raise ValueError(f"Expected {EXPECTED_ROWS} Exp1 prompts, found {len(design.exp1_rows)}")
    for cell, saved in ((EXP1_CELL, design.exp1_rows), (REITERATION_CELL, design.reiteration_rows)):
        check_against_saved(cell, build_cell(cell, design.exp1_rows, design.frame_rules), saved)
    return {cell.experiment_id: build_cell(cell, design.exp1_rows, design.frame_rules) for cell in NEW_CELLS}


def write_outputs(output_dir: Path, outputs: Mapping[str, Sequence[Mapping[str, str]]], columns: Sequence[str]) -> list[Path]:
    output_dir.mkdir(parents=True, exist_ok=True)
    targets = {name: output_dir / f"prompts_{name}.csv" for name in outputs}
    existing = [str(path) for path in targets.values() if path.exists()]
    if existing:
        raise FileExistsError(f"Refusing to overwrite output files: {', '.join(existing)}")
    for name, path in targets.items():
        with path.open("x", newline="", encoding="utf-8-sig") as handle:
            writer = csv.DictWriter(handle, fieldnames=columns)
            writer.writeheader()
            writer.writerows(outputs[name])
    return list(targets.values())


def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    args = parser.parse_args()
    design = load_saved()
    outputs = build_all(design)
    columns = design.exp1_columns + ADDED_COLUMNS
    for path in write_outputs(args.output_dir, outputs, columns):
        print(f"Wrote {EXPECTED_ROWS} rows: {path}")


if __name__ == "__main__":
    main()
