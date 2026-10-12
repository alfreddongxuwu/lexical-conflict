from pathlib import Path
import pandas as pd
from paths import DESIGN_DIR, PROCESSED_DIR

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
    "prompted_en",
    "source_freq_band",
    "target_freq_band",
    "source_sentence_zh",
    "literal_pk_en",
    "literal_ck_en",
    "frame_text",
    "prompt",
]


def load_inputs():
    mappings = pd.read_csv(PROCESSED_DIR / "mappings.csv")
    frames = pd.read_csv(DESIGN_DIR / "frames.csv")
    contexts = pd.read_csv(DESIGN_DIR / "contexts.csv")
    return (mappings, frames, contexts)


def make_prompt(frame_text: str, source_sentence_zh: str) -> str:
    return f"Task: Translate Mandarin to English. Output only the English translation without explanations or notes.\n{frame_text}\nTranslate: {source_sentence_zh}"


def make_prompts():
    mappings, frames, contexts = load_inputs()
    context_by_category = {row["category"]: row for _, row in contexts.iterrows()}
    rows = []
    prompt_counter = 1
    for _, mapping in mappings.iterrows():
        for _, frame in frames.iterrows():
            frame_text = frame["frame_text_template"].format(
                source_word_zh=mapping["source_word_zh"],
                prompted_en=mapping["prompted_en"],
            )
            for context_type in ["PK_context", "CK_context"]:
                if context_type == "PK_context":
                    context_category = mapping["source_category"]
                elif context_type == "CK_context":
                    context_category = mapping["target_category"]
                else:
                    raise ValueError(f"Unknown context_type: {context_type}")
                if context_category not in context_by_category:
                    raise ValueError(
                        f"Context category {context_category} not found in contexts.csv"
                    )
                context = context_by_category[context_category]
                source_sentence_zh = context["zh_template"].format(
                    source_word_zh=mapping["source_word_zh"]
                )
                literal_pk_en = context["literal_en_template"].format(
                    standard_en=mapping["standard_en"]
                )
                literal_ck_en = context["literal_en_template"].format(
                    standard_en=mapping["prompted_en"]
                )
                prompt = make_prompt(
                    frame_text=frame_text, source_sentence_zh=source_sentence_zh
                )
                rows.append(
                    {
                        "prompt_id": f"prompt_{prompt_counter:06d}",
                        "mapping_id": mapping["mapping_id"],
                        "frame_id": frame["frame_id"],
                        "frame_name": frame["frame_name"],
                        "context_type": context_type,
                        "context_category": context_category,
                        "source_item_id": mapping["source_item_id"],
                        "target_item_id": mapping["target_item_id"],
                        "source_category": mapping["source_category"],
                        "target_category": mapping["target_category"],
                        "source_word_zh": mapping["source_word_zh"],
                        "standard_en": mapping["standard_en"],
                        "prompted_en": mapping["prompted_en"],
                        "source_freq_band": mapping["source_freq_band"],
                        "target_freq_band": mapping["target_freq_band"],
                        "source_sentence_zh": source_sentence_zh,
                        "literal_pk_en": literal_pk_en,
                        "literal_ck_en": literal_ck_en,
                        "frame_text": frame_text,
                        "prompt": prompt,
                    }
                )
                prompt_counter += 1
    prompts = pd.DataFrame(rows, columns=PROMPT_COLUMNS)
    return prompts


def validate_prompts(prompts: pd.DataFrame):
    expected_n = 600 * 5 * 2
    if len(prompts) != expected_n:
        raise ValueError(f"Expected {expected_n} prompts, found {len(prompts)}")
    if prompts["prompt_id"].duplicated().any():
        raise ValueError("Duplicate prompt_id found")
    if prompts["prompt"].duplicated().any():
        duplicated = prompts[prompts["prompt"].duplicated(keep=False)]
        raise ValueError(f"Duplicate prompt text found. Example:\n{duplicated.head()}")
    bad_rows = prompts[
        ~prompts.apply(
            lambda row: row["source_word_zh"] in row["source_sentence_zh"], axis=1
        )
    ]
    if len(bad_rows) > 0:
        raise ValueError(
            f"Some source sentences do not contain source_word_zh:\n{bad_rows.head()}"
        )
    counts = prompts.groupby(["mapping_id", "frame_id", "context_type"]).size()
    if not (counts == 1).all():
        raise ValueError(
            "Each mapping × frame × context_type should occur exactly once"
        )
    context_values = set(prompts["context_type"].unique())
    if context_values != {"PK_context", "CK_context"}:
        raise ValueError(f"Unexpected context_type values: {context_values}")


def main():
    prompts = make_prompts()
    validate_prompts(prompts)
    output_path = PROCESSED_DIR / "prompts.csv"
    prompts.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(prompts)} prompts to {output_path}")


if __name__ == "__main__":
    main()
