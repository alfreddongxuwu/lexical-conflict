import pandas as pd
from paths import PROCESSED_DIR


PILOT_DIRECTIONS = [
    ("animal", "vehicle"),
    ("fruit", "music"),
]

PILOT_CONFIGS = [
    {
        "name": "main/non-May",
        "input_file": PROCESSED_DIR / "prompts.csv",
        "output_file": PROCESSED_DIR / "prompts_pilot.csv",
    },
    {
        "name": "May follow-up",
        "input_file": PROCESSED_DIR / "prompts_may.csv",
        "output_file": PROCESSED_DIR / "prompts_pilot_may.csv",
    },
]


def load_prompts(input_file) -> pd.DataFrame:
    if not input_file.exists():
        raise FileNotFoundError(f"Cannot find full prompt file at: {input_file}")

    return pd.read_csv(input_file)


def make_pilot_prompts(prompts: pd.DataFrame) -> pd.DataFrame:
    masks = []

    for source_category, target_category in PILOT_DIRECTIONS:
        mask = (
            (prompts["source_category"] == source_category)
            & (prompts["target_category"] == target_category)
        )
        masks.append(mask)

    combined_mask = masks[0]
    for mask in masks[1:]:
        combined_mask = combined_mask | mask

    return prompts[combined_mask].copy()


def validate_pilot_prompts(pilot: pd.DataFrame, full_prompts: pd.DataFrame) -> None:
    expected_n = len(PILOT_DIRECTIONS) * 30 * 5 * 2

    if len(pilot) != expected_n:
        counts = (
            full_prompts
            .groupby(["source_category", "target_category"])
            .size()
            .reset_index(name="n")
            .sort_values(["source_category", "target_category"])
        )
        raise ValueError(
            f"Expected {expected_n} pilot prompts, found {len(pilot)}. "
            "Available source_category x target_category counts:\n"
            f"{counts.to_string(index=False)}"
        )

    if pilot["prompt_id"].duplicated().any():
        raise ValueError("Duplicate prompt_id found in pilot prompts.")

    counts = (
        pilot
        .groupby(["source_category", "target_category", "frame_id", "context_type"])
        .size()
        .reset_index(name="n")
    )
    bad_counts = counts[counts["n"] != 30]

    if len(bad_counts) > 0:
        raise ValueError(
            "Expected 30 prompts for each source_category x target_category x "
            f"frame_id x context_type cell.\n{bad_counts}"
        )

    context_values = set(pilot["context_type"].unique())
    if context_values != {"PK_context", "CK_context"}:
        raise ValueError(f"Unexpected context_type values: {context_values}")


def main() -> None:
    for config in PILOT_CONFIGS:
        name = config["name"]
        input_file = config["input_file"]
        output_file = config["output_file"]

        prompts = load_prompts(input_file)
        pilot = make_pilot_prompts(prompts)
        validate_pilot_prompts(pilot, prompts)

        pilot.to_csv(output_file, index=False, encoding="utf-8-sig")

        print(f"Saved {len(pilot)} {name} pilot prompts to {output_file}")
        print("Pilot direction counts:")
        print(
            pilot
            .groupby(["source_category", "target_category"])
            .size()
            .reset_index(name="n")
            .to_string(index=False)
        )


if __name__ == "__main__":
    main()
