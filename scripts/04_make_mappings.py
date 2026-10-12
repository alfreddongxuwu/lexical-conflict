import sys
import random
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))
from paths import PROCESSED_DIR

ITEMS_FILE = PROCESSED_DIR / "items.csv"
OUTPUT_FILE = PROCESSED_DIR / "mappings.csv"
GLOBAL_SEED = 2026
PAIRING_SCHEME = "seeded_balanced_frequency_4-3-3"
CATEGORIES = ["animal", "fruit", "vehicle", "occupation", "music"]
TARGET_BAND_ALLOCATION = {
    "high": {"high": 4, "medium": 3, "low": 3},
    "medium": {"high": 3, "medium": 4, "low": 3},
    "low": {"high": 3, "medium": 3, "low": 4},
}


def validate_items(items: pd.DataFrame) -> None:
    required_columns = {
        "item_id",
        "category",
        "source_word_zh",
        "standard_en",
        "raw_count_bcc",
        "freq_per_million_bcc",
        "log_freq_per_million_bcc",
        "rank_in_category",
        "freq_band",
    }
    missing_columns = required_columns - set(items.columns)
    if missing_columns:
        raise ValueError(
            f"items.csv is missing required columns: {sorted(missing_columns)}"
        )
    actual_categories = set(items["category"].unique())
    expected_categories = set(CATEGORIES)
    if actual_categories != expected_categories:
        raise ValueError(
            f"Unexpected category set in items.csv.\nExpected: {sorted(expected_categories)}\nFound:    {sorted(actual_categories)}"
        )
    for category in CATEGORIES:
        category_items = items[items["category"] == category]
        if len(category_items) != 30:
            raise ValueError(
                f"Category '{category}' should have 30 items, but found {len(category_items)}."
            )
        band_counts = category_items["freq_band"].value_counts().to_dict()
        expected_band_counts = {"high": 10, "medium": 10, "low": 10}
        if band_counts != expected_band_counts:
            raise ValueError(
                f"Category '{category}' has unexpected frequency-band counts.\nExpected: {expected_band_counts}\nFound:    {band_counts}"
            )


def get_category_band_items(
    items: pd.DataFrame, category: str, freq_band: str
) -> pd.DataFrame:
    subset = items[
        (items["category"] == category) & (items["freq_band"] == freq_band)
    ].copy()
    subset = subset.sort_values("rank_in_category").reset_index(drop=True)
    if len(subset) != 10:
        raise ValueError(
            f"Expected 10 items for category={category}, freq_band={freq_band}, but found {len(subset)}."
        )
    return subset


def allocate_target_items(
    target_items_by_band: dict, source_band: str, rng: random.Random
) -> list:
    selected_targets = []
    allocation = TARGET_BAND_ALLOCATION[source_band]
    for target_band, n_items in allocation.items():
        available_targets = target_items_by_band[target_band]
        if len(available_targets) < n_items:
            raise ValueError(
                f"Not enough target items left in band '{target_band}'. Need {n_items}, found {len(available_targets)}."
            )
        selected_targets.extend(available_targets[:n_items])
        del available_targets[:n_items]
    rng.shuffle(selected_targets)
    return selected_targets


def make_mapping_rows_for_category_pair(
    items: pd.DataFrame, source_category: str, target_category: str, pair_index: int
) -> list:
    pair_seed = GLOBAL_SEED + pair_index
    rng = random.Random(pair_seed)
    source_items_by_band = {
        band: get_category_band_items(items, source_category, band)
        for band in ["high", "medium", "low"]
    }
    target_items_by_band = {
        band: get_category_band_items(items, target_category, band).to_dict("records")
        for band in ["high", "medium", "low"]
    }
    for band in ["high", "medium", "low"]:
        rng.shuffle(target_items_by_band[band])
    rows = []
    for source_band in ["high", "medium", "low"]:
        source_records = source_items_by_band[source_band].to_dict("records")
        rng.shuffle(source_records)
        selected_targets = allocate_target_items(
            target_items_by_band=target_items_by_band, source_band=source_band, rng=rng
        )
        if len(source_records) != len(selected_targets):
            raise ValueError(
                f"Source-target length mismatch for {source_category}->{target_category}, source_band={source_band}."
            )
        for source_item, target_item in zip(source_records, selected_targets):
            rows.append(
                {
                    "source_item_id": source_item["item_id"],
                    "target_item_id": target_item["item_id"],
                    "source_category": source_category,
                    "target_category": target_category,
                    "source_word_zh": source_item["source_word_zh"],
                    "standard_en": source_item["standard_en"],
                    "prompted_word_zh": target_item["source_word_zh"],
                    "prompted_en": target_item["standard_en"],
                    "source_freq_band": source_item["freq_band"],
                    "target_freq_band": target_item["freq_band"],
                    "source_rank_in_category": source_item["rank_in_category"],
                    "target_rank_in_category": target_item["rank_in_category"],
                    "mapping_type": "cross_category",
                    "pairing_scheme": PAIRING_SCHEME,
                    "global_seed": GLOBAL_SEED,
                    "pair_seed": pair_seed,
                    "notes": "",
                }
            )
    target_ids = [row["target_item_id"] for row in rows]
    if len(target_ids) != len(set(target_ids)):
        raise ValueError(
            f"Duplicate target items found in {source_category}->{target_category}."
        )
    source_ids = [row["source_item_id"] for row in rows]
    if len(source_ids) != len(set(source_ids)):
        raise ValueError(
            f"Duplicate source items found in {source_category}->{target_category}."
        )
    if len(rows) != 30:
        raise ValueError(
            f"{source_category}->{target_category} should have 30 mappings, but found {len(rows)}."
        )
    return rows


def main():
    if not ITEMS_FILE.exists():
        raise FileNotFoundError(f"Input file not found: {ITEMS_FILE}")
    items = pd.read_csv(ITEMS_FILE)
    validate_items(items)
    all_rows = []
    pair_index = 0
    for source_category in CATEGORIES:
        for target_category in CATEGORIES:
            if source_category == target_category:
                continue
            pair_rows = make_mapping_rows_for_category_pair(
                items=items,
                source_category=source_category,
                target_category=target_category,
                pair_index=pair_index,
            )
            all_rows.extend(pair_rows)
            pair_index += 1
    mappings = pd.DataFrame(all_rows)
    mappings.insert(
        0, "mapping_id", [f"map_{i:04d}" for i in range(1, len(mappings) + 1)]
    )
    final_columns = [
        "mapping_id",
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
        "source_rank_in_category",
        "target_rank_in_category",
        "mapping_type",
        "pairing_scheme",
        "global_seed",
        "pair_seed",
        "notes",
    ]
    mappings = mappings[final_columns]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    mappings.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Saved mappings to: {OUTPUT_FILE}")
    print(f"Total rows: {len(mappings)}")
    print()
    print("Rows by source_category -> target_category:")
    print(
        mappings.groupby(["source_category", "target_category"])
        .size()
        .reset_index(name="n")
        .to_string(index=False)
    )
    print()
    print("Target frequency-band counts by category pair:")
    print(
        mappings.groupby(["source_category", "target_category", "target_freq_band"])
        .size()
        .reset_index(name="n")
        .to_string(index=False)
    )


if __name__ == "__main__":
    main()
