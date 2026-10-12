from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pandas as pd
from paths import DESIGN_DIR, PROCESSED_DIR

REITERATION_COUNT = 5


def load_main_prompt_module():
    module_path = Path(__file__).with_name("05_make_prompts.py")
    spec = spec_from_file_location("main_prompt_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load prompt builder from {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_reiteration_inputs():
    mappings = pd.read_csv(PROCESSED_DIR / "mappings.csv")
    frames = pd.read_csv(DESIGN_DIR / "frames_reiteration.csv")
    contexts = pd.read_csv(DESIGN_DIR / "contexts.csv")
    return (mappings, frames, contexts)


def validate_reiteration_wording(prompts: pd.DataFrame) -> None:
    for _, row in prompts.iterrows():
        rule = f"{row['source_word_zh']} means {row['prompted_en']}."
        occurrences = row["frame_text"].count(rule)
        if occurrences != REITERATION_COUNT:
            raise ValueError(
                f"Every reiteration frame_text should repeat the lexical rule {REITERATION_COUNT} times; found {occurrences} in {row['prompt_id']}."
            )
        prompt_occurrences = row["prompt"].count(rule)
        if prompt_occurrences != REITERATION_COUNT:
            raise ValueError(
                f"Every reiteration prompt should repeat the lexical rule {REITERATION_COUNT} times; found {prompt_occurrences} in {row['prompt_id']}."
            )


def main() -> None:
    prompt_builder = load_main_prompt_module()
    prompt_builder.load_inputs = load_reiteration_inputs
    prompts = prompt_builder.make_prompts()
    prompt_builder.validate_prompts(prompts)
    validate_reiteration_wording(prompts)
    output_path = PROCESSED_DIR / "prompts_reiteration.csv"
    prompts.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(prompts)} reiteration prompts to {output_path}")


if __name__ == "__main__":
    main()
