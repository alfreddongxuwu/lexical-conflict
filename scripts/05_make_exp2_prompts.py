import pandas as pd
from paths import DESIGN_DIR, PROCESSED_DIR

MAPPINGS_FILE = PROCESSED_DIR / "mappings_exp2.csv"
OUTPUT_FILE = PROCESSED_DIR / "prompts_exp2.csv"
PROMPT_COLUMNS = [
    "prompt_id",
    "mapping_id",
    "frame_id",
    "frame_name",
    "context_type",
    "context_category",
    "source_item_id",
    "target_item_id",
    "source_category",
    "target_category",
    "source_word_zh",
    "standard_en",
    "prompted_word_zh",
    "prompted_en",
    "source_freq_band",
    "target_freq_band",
    "pairing_round",
    "pairing_seed",
    "source_sentence_zh",
    "literal_pk_en",
    "literal_ck_en",
    "frame_text",
    "prompt",
]


def make_prompt(frame_text: str, source_sentence_zh: str) -> str:
    return f"Task: Translate Mandarin to English. Output only the English translation without explanations or notes.\n{frame_text}\nTranslate: {source_sentence_zh}"


def make_prompts() -> pd.DataFrame:
    mappings = pd.read_csv(MAPPINGS_FILE)
    frames = pd.read_csv(DESIGN_DIR / "frames.csv")
    contexts = pd.read_csv(DESIGN_DIR / "contexts.csv")
    context_by_category = {row["category"]: row for _, row in contexts.iterrows()}
    rows: list[dict] = []
    for prompt_counter, (_, mapping, frame) in enumerate(
        (
            (None, mapping, frame)
            for _, mapping in mappings.iterrows()
            for _, frame in frames.iterrows()
        ),
        start=1,
    ):
        category = mapping["source_category"]
        if category != mapping["target_category"]:
            raise ValueError(f"Cross-category Exp2 mapping: {mapping['mapping_id']}")
        if category not in context_by_category:
            raise ValueError(f"No sentence context for category={category}")
        context = context_by_category[category]
        frame_text = frame["frame_text_template"].format(
            source_word_zh=mapping["source_word_zh"], prompted_en=mapping["prompted_en"]
        )
        source_sentence_zh = context["zh_template"].format(
            source_word_zh=mapping["source_word_zh"]
        )
        literal_pk_en = context["literal_en_template"].format(
            standard_en=mapping["standard_en"]
        )
        literal_ck_en = context["literal_en_template"].format(
            standard_en=mapping["prompted_en"]
        )
        rows.append(
            {
                "prompt_id": f"exp2_prompt_{prompt_counter:06d}",
                "mapping_id": mapping["mapping_id"],
                "frame_id": frame["frame_id"],
                "frame_name": frame["frame_name"],
                "context_type": "within_category_context",
                "context_category": category,
                "source_item_id": mapping["source_item_id"],
                "target_item_id": mapping["target_item_id"],
                "source_category": category,
                "target_category": category,
                "source_word_zh": mapping["source_word_zh"],
                "standard_en": mapping["standard_en"],
                "prompted_word_zh": mapping["prompted_word_zh"],
                "prompted_en": mapping["prompted_en"],
                "source_freq_band": mapping["source_freq_band"],
                "target_freq_band": mapping["target_freq_band"],
                "pairing_round": mapping["pairing_round"],
                "pairing_seed": mapping["pairing_seed"],
                "source_sentence_zh": source_sentence_zh,
                "literal_pk_en": literal_pk_en,
                "literal_ck_en": literal_ck_en,
                "frame_text": frame_text,
                "prompt": make_prompt(frame_text, source_sentence_zh),
            }
        )
    return pd.DataFrame(rows, columns=PROMPT_COLUMNS)


def validate_prompts(prompts: pd.DataFrame) -> None:
    if len(prompts) != 3000:
        raise ValueError(f"Expected 3000 Exp2 prompts, found {len(prompts)}")
    if prompts["prompt_id"].duplicated().any():
        raise ValueError("Duplicate prompt_id found")
    if prompts["prompt"].duplicated().any():
        raise ValueError("Duplicate prompt text found")
    counts = prompts.groupby(["mapping_id", "frame_id"]).size()
    if len(counts) != 3000 or not (counts == 1).all():
        raise ValueError("Each Exp2 mapping x frame must occur exactly once")
    mapping_counts = prompts.groupby("mapping_id").size()
    if len(mapping_counts) != 600 or not (mapping_counts == 5).all():
        raise ValueError("Each Exp2 mapping must occur in all five frames")
    if set(prompts["context_type"]) != {"within_category_context"}:
        raise ValueError("Unexpected Exp2 context_type")
    if not (prompts["context_category"] == prompts["source_category"]).all():
        raise ValueError("Context category does not match the shared item category")
    if not (prompts["source_category"] == prompts["target_category"]).all():
        raise ValueError("Exp2 prompt contains cross-category meanings")
    contains_source = prompts.apply(
        lambda row: row["source_word_zh"] in row["source_sentence_zh"], axis=1
    )
    if not contains_source.all():
        raise ValueError("A source sentence does not contain its source word")


def main() -> None:
    prompts = make_prompts()
    validate_prompts(prompts)
    prompts.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Saved {len(prompts)} prompts to: {OUTPUT_FILE}")
    print("Rows by category, source band, target band, round, and seed:")
    print(
        prompts.groupby(
            [
                "source_category",
                "source_freq_band",
                "target_freq_band",
                "pairing_round",
                "pairing_seed",
            ]
        )
        .size()
        .reset_index(name="n")
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
