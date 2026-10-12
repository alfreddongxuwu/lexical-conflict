from importlib.util import module_from_spec, spec_from_file_location
from pathlib import Path
import pandas as pd
from paths import DESIGN_DIR, PROCESSED_DIR


def load_main_prompt_module():
    module_path = Path(__file__).with_name("05_make_prompts.py")
    spec = spec_from_file_location("main_prompt_builder", module_path)
    if spec is None or spec.loader is None:
        raise RuntimeError(f"Cannot load prompt builder from {module_path}")
    module = module_from_spec(spec)
    spec.loader.exec_module(module)
    return module


def load_may_inputs():
    mappings = pd.read_csv(PROCESSED_DIR / "mappings.csv")
    frames = pd.read_csv(DESIGN_DIR / "frames_may.csv")
    contexts = pd.read_csv(DESIGN_DIR / "contexts.csv")
    return (mappings, frames, contexts)


def validate_may_wording(prompts: pd.DataFrame) -> None:
    if not prompts["frame_text"].str.contains(" may mean ", regex=False).all():
        raise ValueError("Every may prompt frame_text should contain ' may mean '.")
    if prompts["frame_text"].str.contains(" means ", regex=False).any():
        raise ValueError("May prompt frame_text should not contain ' means '.")
    if not prompts["prompt"].str.contains(" may mean ", regex=False).all():
        raise ValueError("Every may prompt should contain ' may mean '.")
    if prompts["prompt"].str.contains(" means ", regex=False).any():
        raise ValueError("May prompt should not contain ' means '.")


def main() -> None:
    prompt_builder = load_main_prompt_module()
    prompt_builder.load_inputs = load_may_inputs
    prompts = prompt_builder.make_prompts()
    prompt_builder.validate_prompts(prompts)
    validate_may_wording(prompts)
    output_path = PROCESSED_DIR / "prompts_may.csv"
    prompts.to_csv(output_path, index=False, encoding="utf-8-sig")
    print(f"Saved {len(prompts)} may prompts to {output_path}")


if __name__ == "__main__":
    main()
