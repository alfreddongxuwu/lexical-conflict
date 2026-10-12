"""Build a conventional-meaning baseline without modifying historical inputs."""
from __future__ import annotations

import argparse
import csv
from collections import Counter
from dataclasses import dataclass
from pathlib import Path

from paths import PROJECT_ROOT

DESIGN_DIR = PROJECT_ROOT / "data/design"
PROCESSED_DIR = PROJECT_ROOT / "data/processed"

BASELINE_PROMPT_COLUMNS = [
    "prompt_id",
    "baseline_type",
    "baseline_id",
    "source_item_id",
    "source_category",
    "context_category",
    "source_word_zh",
    "standard_en",
    "source_freq_band",
    "source_rank_in_category",
    "context_template_id",
    "source_sentence_zh",
    "literal_expected_en",
    "prompt",
]

def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def make_prompt(source_sentence_zh: str) -> str:
    return (
        "Task: Translate Mandarin to English. Output only the English translation without explanations or notes.\n"
        f"Translate: {source_sentence_zh}"
    )


def make_sentence(context: dict, source_word_zh: str) -> str:
    return context["zh_template"].format(source_word_zh=source_word_zh)


def make_literal_expected(context: dict, standard_en: str) -> str:
    return context["literal_en_template"].format(standard_en=standard_en)


def make_row(
    prompt_counter: int,
    baseline_type: str,
    baseline_id: str,
    item: dict,
    context: dict,
) -> dict:
    source_sentence_zh = make_sentence(context, item["source_word_zh"])

    return {
        "prompt_id": f"baseline_{prompt_counter:06d}",
        "baseline_type": baseline_type,
        "baseline_id": baseline_id,
        "source_item_id": item["item_id"],
        "source_category": item["category"],
        "context_category": context["category"],
        "source_word_zh": item["source_word_zh"],
        "standard_en": item["standard_en"],
        "source_freq_band": item["freq_band"],
        "source_rank_in_category": item["rank_in_category"],
        "context_template_id": context["template_id"],
        "source_sentence_zh": source_sentence_zh,
        "literal_expected_en": make_literal_expected(context, item["standard_en"]),
        "prompt": make_prompt(source_sentence_zh),
    }


@dataclass
class ConventionalBaseline:
    """Existing normal sentences crossed with the existing rule frames."""

    normal: list[dict[str, str]]
    frames: list[dict[str, str]]

    @classmethod
    def load(cls) -> "ConventionalBaseline":
        baseline = read_csv(PROCESSED_DIR / "prompts_baseline.csv")
        normal = [row for row in baseline if row["baseline_type"] == "normal_lexical"]
        items = read_csv(PROCESSED_DIR / "items.csv")
        contexts = {row["category"]: row for row in read_csv(DESIGN_DIR / "contexts.csv")}
        if len(items) != 150 or len(normal) != 150:
            raise ValueError("Expected 150 inventory items and normal baseline rows")
        strata = Counter((row["category"], row["freq_band"]) for row in items)
        expected_strata = {(category, band) for category in contexts for band in ("high", "medium", "low")}
        if len(contexts) != 5 or set(strata) != expected_strata or set(strata.values()) != {10}:
            raise ValueError("Expected five categories, three frequency bands and ten items per cell")
        by_id = {row["source_item_id"]: row for row in normal}
        if len(by_id) != len(normal) or set(by_id) != {row["item_id"] for row in items}:
            raise ValueError("Normal baseline must cover each inventory item once")
        for item in items:
            row = by_id[item["item_id"]]
            expected = make_row(1, "normal_lexical", row["baseline_id"], item, contexts[item["category"]])
            for key in BASELINE_PROMPT_COLUMNS:
                if key != "prompt_id" and row[key] != expected[key]:
                    raise ValueError(f"Normal baseline {key} mismatch: {item['item_id']}")
        frames = read_csv(DESIGN_DIR / "frames.csv")
        if len(frames) != 5 or len({frame["frame_id"] for frame in frames}) != 5:
            raise ValueError("Expected five unique frames")
        return cls(normal, frames)

    def build(self) -> list[dict[str, str]]:
        rows = []
        for normal in self.normal:
            for frame in self.frames:
                text = frame["frame_text_template"].format(
                    source_word_zh=normal["source_word_zh"], prompted_en=normal["standard_en"])
                task, translate = normal["prompt"].split("\n")
                identity = f"conventional_meaning_{normal['source_item_id']}_{frame['frame_id']}"
                rows.append({**normal, "prompt_id": identity, "baseline_id": identity,
                    "baseline_type": "conventional_meaning", "frame_id": frame["frame_id"],
                    "frame_name": frame["frame_name"], "frame_text": text,
                    "prompted_en": normal["standard_en"],
                    "prompt": f"{task}\n{text}\n{translate}"})
        return rows

    def validate(self, rows: list[dict[str, str]]) -> None:
        expected = {(r["source_item_id"], r["frame_id"]): r for r in self.build()}
        seen = set()
        for row in rows:
            key = (row["source_item_id"], row["frame_id"])
            if key in seen or key not in expected:
                raise ValueError(f"Duplicate or unknown word-frame identity: {key}")
            seen.add(key)
            for field, value in expected[key].items():
                if row.get(field) != value:
                    raise ValueError(f"Conventional baseline {field} mismatch: {key}")
        if seen != set(expected):
            raise ValueError("Missing word-frame combinations")
        if len({r["prompt"] for r in rows}) != len(rows):
            raise ValueError("Duplicate conventional prompt text")

    def validate_conflict_matches(self, rows: list[dict[str, str]], conflicts: list[dict[str, str]]) -> None:
        """Compare saved conflict prompts after replacing only their definition slot."""
        by_key = {(r["source_item_id"], r["frame_id"]): r for r in rows}
        seen = set()
        for conflict in conflicts:
            if conflict.get("context_type") == "CK_context":
                continue
            key = (conflict["source_item_id"], conflict["frame_id"])
            baseline = by_key[key]
            for field, reference in (("source_sentence_zh", "source_sentence_zh"),
                                     ("literal_pk_en", "literal_expected_en")):
                if conflict[field] != baseline[reference]:
                    raise ValueError(f"Conflict {field} mismatch: {key}")
            old = f"{conflict['source_word_zh']} means {conflict['prompted_en']}."
            new = f"{conflict['source_word_zh']} means {baseline['standard_en']}."
            if conflict["prompt"].count(old) != 1 or conflict["prompt"].replace(old, new) != baseline["prompt"]:
                raise ValueError(f"Conflict prompt differs outside the definition: {key}")
            seen.add(key)
        if seen != set(by_key):
            raise ValueError("Missing conflict matches")

def main() -> None:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("output", type=Path)
    args = parser.parse_args()
    design = ConventionalBaseline.load()
    rows = design.build()
    design.validate(rows)
    for name in ("prompts.csv", "prompts_exp2.csv"):
        design.validate_conflict_matches(rows, read_csv(PROCESSED_DIR / name))
    args.output.parent.mkdir(parents=True, exist_ok=True)
    with args.output.open("x", encoding="utf-8-sig", newline="") as handle:
        writer = csv.DictWriter(handle, fieldnames=list(rows[0]))
        writer.writeheader()
        writer.writerows(rows)
    print(f"Saved {len(rows)} validated prompts to {args.output}")


if __name__ == "__main__":
    main()
