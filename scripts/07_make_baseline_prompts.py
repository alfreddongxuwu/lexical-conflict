import csv
from pathlib import Path
from paths import DESIGN_DIR, PROCESSED_DIR

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
BASELINE_TYPES = {"normal_lexical", "anomalous_no_lexicon"}


def read_csv(path: Path) -> list[dict]:
    with path.open(newline="", encoding="utf-8-sig") as handle:
        return list(csv.DictReader(handle))


def write_csv(path: Path, rows: list[dict], columns: list[str]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.DictWriter(handle, fieldnames=columns)
        writer.writeheader()
        writer.writerows(rows)


def make_prompt(source_sentence_zh: str) -> str:
    return f"Task: Translate Mandarin to English. Output only the English translation without explanations or notes.\nTranslate: {source_sentence_zh}"


def make_sentence(context: dict, source_word_zh: str) -> str:
    return context["zh_template"].format(source_word_zh=source_word_zh)


def make_literal_expected(context: dict, standard_en: str) -> str:
    return context["literal_en_template"].format(standard_en=standard_en)


def make_row(
    prompt_counter: int, baseline_type: str, baseline_id: str, item: dict, context: dict
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


def make_baseline_prompts() -> list[dict]:
    items = read_csv(PROCESSED_DIR / "items.csv")
    mappings = read_csv(PROCESSED_DIR / "mappings.csv")
    contexts = read_csv(DESIGN_DIR / "contexts.csv")
    items_by_id = {item["item_id"]: item for item in items}
    contexts_by_category = {context["category"]: context for context in contexts}
    rows = []
    prompt_counter = 1
    for item in items:
        context = contexts_by_category[item["category"]]
        rows.append(
            make_row(
                prompt_counter=prompt_counter,
                baseline_type="normal_lexical",
                baseline_id=f"normal_lexical_{item['item_id']}",
                item=item,
                context=context,
            )
        )
        prompt_counter += 1
    for mapping in mappings:
        item = items_by_id[mapping["source_item_id"]]
        context_category = mapping["target_category"]
        context = contexts_by_category[context_category]
        rows.append(
            make_row(
                prompt_counter=prompt_counter,
                baseline_type="anomalous_no_lexicon",
                baseline_id=f"anomalous_no_lexicon_{item['item_id']}_{context_category}",
                item=item,
                context=context,
            )
        )
        prompt_counter += 1
    return rows


def validate_baseline_prompts(rows: list[dict]) -> None:
    expected_counts = {"normal_lexical": 150, "anomalous_no_lexicon": 600}
    if len(rows) != sum(expected_counts.values()):
        raise ValueError(f"Expected 750 baseline prompts, found {len(rows)}")
    values_by_type = {baseline_type: 0 for baseline_type in BASELINE_TYPES}
    for row in rows:
        if row["baseline_type"] not in BASELINE_TYPES:
            raise ValueError(f"Unexpected baseline_type: {row['baseline_type']}")
        values_by_type[row["baseline_type"]] += 1
        if row["source_word_zh"] not in row["source_sentence_zh"]:
            raise ValueError(
                f"source_word_zh missing from sentence: {row['baseline_id']}"
            )
        if row["baseline_type"] == "normal_lexical":
            if row["source_category"] != row["context_category"]:
                raise ValueError(
                    f"Normal baseline uses wrong context: {row['baseline_id']}"
                )
        if row["baseline_type"] == "anomalous_no_lexicon":
            if row["source_category"] == row["context_category"]:
                raise ValueError(
                    f"Anomalous baseline uses source-category context: {row['baseline_id']}"
                )
    if values_by_type != expected_counts:
        raise ValueError(f"Unexpected baseline counts: {values_by_type}")
    for key in ["prompt_id", "baseline_id", "prompt"]:
        values = [row[key] for row in rows]
        if len(values) != len(set(values)):
            raise ValueError(f"Duplicate {key} found")
    anomalous = [row for row in rows if row["baseline_type"] == "anomalous_no_lexicon"]
    contexts_per_item: dict[str, set[str]] = {}
    for row in anomalous:
        contexts_per_item.setdefault(row["source_item_id"], set()).add(
            row["context_category"]
        )
    bad_items = {
        item_id: sorted(contexts)
        for item_id, contexts in contexts_per_item.items()
        if len(contexts) != 4
    }
    if bad_items:
        raise ValueError(
            f"Each source item should have four anomalous contexts: {bad_items}"
        )


def main() -> None:
    rows = make_baseline_prompts()
    validate_baseline_prompts(rows)
    output_path = PROCESSED_DIR / "prompts_baseline.csv"
    write_csv(output_path, rows, BASELINE_PROMPT_COLUMNS)
    print(f"Saved {len(rows)} baseline prompts to {output_path}")


if __name__ == "__main__":
    main()
