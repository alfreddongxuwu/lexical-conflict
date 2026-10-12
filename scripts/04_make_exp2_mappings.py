import random
import sys
from pathlib import Path
import pandas as pd

SCRIPT_DIR = Path(__file__).resolve().parent
sys.path.append(str(SCRIPT_DIR))
from paths import DESIGN_DIR, PROCESSED_DIR, PROJECT_ROOT

ITEMS_FILE = PROCESSED_DIR / "items.csv"
TRANSLATIONS_FILE = PROJECT_ROOT / "data/coding/accepted_translations.csv"
RAW_OUTPUT_FILE = DESIGN_DIR / "exp2_mappings_before_overlap_adjustment.csv"
ISSUES_OUTPUT_FILE = DESIGN_DIR / "exp2_overlap_initial.csv"
ADJUSTMENTS_OUTPUT_FILE = DESIGN_DIR / "exp2_overlap_adjustments.csv"
FINAL_OUTPUT_FILE = PROCESSED_DIR / "mappings_exp2.csv"
CATEGORIES = ["animal", "fruit", "vehicle", "occupation", "music"]
FREQ_BANDS = ["high", "medium", "low"]
ROUND_SEEDS = {1: 2027, 2: 2028}
PAIRING_SCHEME = "independent_seeded_rounds_then_adjacent_overlap_repairs"
GROUP_COLUMNS = [
    "source_category",
    "source_freq_band",
    "target_freq_band",
    "pairing_round",
]
PAIR_KEY_COLUMNS = [
    "source_category",
    "source_freq_band",
    "target_freq_band",
    "source_item_id",
    "target_item_id",
]
TARGET_COLUMNS = [
    "target_item_id",
    "prompted_word_zh",
    "prompted_en",
    "target_rank_in_category",
]


def validate_items(items: pd.DataFrame) -> None:
    required = {
        "item_id",
        "category",
        "source_word_zh",
        "standard_en",
        "rank_in_category",
        "freq_band",
    }
    missing = required - set(items.columns)
    if missing:
        raise ValueError(f"items.csv is missing columns: {sorted(missing)}")
    if items["item_id"].duplicated().any():
        raise ValueError("items.csv contains duplicate item_id values")
    if set(items["category"]) != set(CATEGORIES):
        raise ValueError("items.csv does not contain the expected categories")
    for category in CATEGORIES:
        subset = items[items["category"] == category]
        counts = subset["freq_band"].value_counts().to_dict()
        expected = {band: 10 for band in FREQ_BANDS}
        if len(subset) != 30 or counts != expected:
            raise ValueError(
                f"Unexpected counts for {category}: total={len(subset)}, bands={counts}"
            )


def load_accepted_forms(items: pd.DataFrame) -> dict[str, set[str]]:
    translations = pd.read_csv(TRANSLATIONS_FILE, keep_default_na=False)
    required = {"item_id", "accepted_en"}
    missing = required - set(translations.columns)
    if missing:
        raise ValueError(
            f"accepted_translations.csv is missing columns: {sorted(missing)}"
        )
    forms_by_item = {
        str(item_id): {
            str(value).strip().lower()
            for value in rows["accepted_en"]
            if str(value).strip()
        }
        for item_id, rows in translations.groupby("item_id", sort=False)
    }
    missing_items = set(items["item_id"].astype(str)) - set(forms_by_item)
    if missing_items:
        raise ValueError(
            f"Items missing accepted translations: {sorted(missing_items)}"
        )
    return forms_by_item


def band_records(items: pd.DataFrame, category: str, freq_band: str) -> list[dict]:
    subset = items[
        (items["category"] == category) & (items["freq_band"] == freq_band)
    ].sort_values("rank_in_category")
    records = subset.to_dict("records")
    if len(records) != 10:
        raise ValueError(f"Expected 10 items for {category}/{freq_band}")
    return records


def generate_raw_mappings(items: pd.DataFrame) -> pd.DataFrame:
    rows = []
    for pairing_round, pairing_seed in ROUND_SEEDS.items():
        rng = random.Random(pairing_seed)
        for category in CATEGORIES:
            for source_band in FREQ_BANDS:
                for target_band in FREQ_BANDS:
                    if source_band == target_band:
                        continue
                    sources = band_records(items, category, source_band)
                    targets = band_records(items, category, target_band)
                    rng.shuffle(targets)
                    for source, target in zip(sources, targets):
                        rows.append(
                            {
                                "source_item_id": source["item_id"],
                                "target_item_id": target["item_id"],
                                "source_category": category,
                                "target_category": category,
                                "source_word_zh": source["source_word_zh"],
                                "standard_en": source["standard_en"],
                                "prompted_word_zh": target["source_word_zh"],
                                "prompted_en": target["standard_en"],
                                "source_freq_band": source_band,
                                "target_freq_band": target_band,
                                "source_rank_in_category": source["rank_in_category"],
                                "target_rank_in_category": target["rank_in_category"],
                                "pairing_round": pairing_round,
                                "pairing_seed": pairing_seed,
                                "mapping_type": "within_category_cross_frequency",
                                "pairing_scheme": PAIRING_SCHEME,
                                "notes": "",
                            }
                        )
    mappings = pd.DataFrame(rows)
    mappings.insert(
        0,
        "mapping_id",
        [f"exp2_map_{index:04d}" for index in range(1, len(mappings) + 1)],
    )
    return mappings


def translation_overlap(
    source_item_id: str, target_item_id: str, forms_by_item: dict[str, set[str]]
) -> set[str]:
    return forms_by_item[str(source_item_id)] & forms_by_item[str(target_item_id)]


def repeated_pair_mask(mappings: pd.DataFrame) -> pd.Series:
    return mappings.duplicated(PAIR_KEY_COLUMNS, keep=False)


def audit_initial_issues(
    mappings: pd.DataFrame, forms_by_item: dict[str, set[str]]
) -> pd.DataFrame:
    repeated = repeated_pair_mask(mappings)
    rows = []
    for index, mapping in mappings.iterrows():
        overlap = sorted(
            translation_overlap(
                mapping["source_item_id"], mapping["target_item_id"], forms_by_item
            )
        )
        issue_types = []
        if repeated.at[index]:
            issue_types.append("pair_overlap")
        if overlap:
            issue_types.append("translation_overlap")
        if not issue_types:
            continue
        rows.append(
            {
                "mapping_id": mapping["mapping_id"],
                "issue_types": "|".join(issue_types),
                "source_category": mapping["source_category"],
                "source_freq_band": mapping["source_freq_band"],
                "target_freq_band": mapping["target_freq_band"],
                "pairing_round": mapping["pairing_round"],
                "pairing_seed": mapping["pairing_seed"],
                "source_item_id": mapping["source_item_id"],
                "source_word_zh": mapping["source_word_zh"],
                "standard_en": mapping["standard_en"],
                "target_item_id": mapping["target_item_id"],
                "prompted_word_zh": mapping["prompted_word_zh"],
                "prompted_en": mapping["prompted_en"],
                "overlapping_accepted_forms": "|".join(overlap),
            }
        )
    return pd.DataFrame(rows)


def pair_repeats_in_other_round(
    mappings: pd.DataFrame, row_index: int, proposed_target_id: str
) -> bool:
    row = mappings.loc[row_index]
    matches = mappings[
        (mappings["source_category"] == row["source_category"])
        & (mappings["source_freq_band"] == row["source_freq_band"])
        & (mappings["target_freq_band"] == row["target_freq_band"])
        & (mappings["pairing_round"] != row["pairing_round"])
        & (mappings["source_item_id"] == row["source_item_id"])
        & (mappings["target_item_id"] == proposed_target_id)
    ]
    return not matches.empty


def row_issue_types(
    mappings: pd.DataFrame, row_index: int, forms_by_item: dict[str, set[str]]
) -> list[str]:
    row = mappings.loc[row_index]
    issues = []
    if pair_repeats_in_other_round(mappings, row_index, row["target_item_id"]):
        issues.append("pair_overlap")
    if translation_overlap(row["source_item_id"], row["target_item_id"], forms_by_item):
        issues.append("translation_overlap")
    return issues


def proposed_pair_is_clean(
    mappings: pd.DataFrame,
    row_index: int,
    proposed_target_id: str,
    forms_by_item: dict[str, set[str]],
) -> bool:
    source_item_id = mappings.at[row_index, "source_item_id"]
    return not translation_overlap(
        source_item_id, proposed_target_id, forms_by_item
    ) and (not pair_repeats_in_other_round(mappings, row_index, proposed_target_id))


def swap_adjacent_targets(
    raw_mappings: pd.DataFrame, forms_by_item: dict[str, set[str]]
) -> tuple[pd.DataFrame, pd.DataFrame]:
    mappings = raw_mappings.copy()
    logs = []
    swap_counter = 1
    for group_key, group in mappings.groupby(GROUP_COLUMNS, sort=False):
        indices = list(group.sort_values("source_rank_in_category").index)
        max_group_swaps = 100
        group_swaps = 0
        while True:
            bad_indices = [
                index
                for index in indices
                if row_issue_types(mappings, index, forms_by_item)
            ]
            repeated_round_two = [
                index
                for index in bad_indices
                if mappings.at[index, "pairing_round"] == 2
                and "pair_overlap" in row_issue_types(mappings, index, forms_by_item)
            ]
            candidates = repeated_round_two or bad_indices
            if not candidates:
                break
            bad_index = candidates[0]
            position = indices.index(bad_index)
            neighbor_positions = []
            if position + 1 < len(indices):
                neighbor_positions.append(position + 1)
            if position - 1 >= 0:
                neighbor_positions.append(position - 1)
            neighbor_index = None
            for neighbor_position in neighbor_positions:
                proposed_neighbor = indices[neighbor_position]
                bad_target = mappings.at[bad_index, "target_item_id"]
                neighbor_target = mappings.at[proposed_neighbor, "target_item_id"]
                if proposed_pair_is_clean(
                    mappings, bad_index, neighbor_target, forms_by_item
                ) and proposed_pair_is_clean(
                    mappings, proposed_neighbor, bad_target, forms_by_item
                ):
                    neighbor_index = proposed_neighbor
                    break
            if neighbor_index is None:
                raise RuntimeError(
                    f"No valid immediate-neighbor swap for group={group_key}, mapping={mappings.at[bad_index, 'mapping_id']}"
                )
            bad_before = mappings.loc[bad_index].copy()
            neighbor_before = mappings.loc[neighbor_index].copy()
            issue_types = row_issue_types(mappings, bad_index, forms_by_item)
            overlap_forms = sorted(
                translation_overlap(
                    bad_before["source_item_id"],
                    bad_before["target_item_id"],
                    forms_by_item,
                )
            )
            first_target = mappings.loc[bad_index, TARGET_COLUMNS].copy()
            second_target = mappings.loc[neighbor_index, TARGET_COLUMNS].copy()
            mappings.loc[bad_index, TARGET_COLUMNS] = second_target.values
            mappings.loc[neighbor_index, TARGET_COLUMNS] = first_target.values
            swap_id = f"exp2_swap_{swap_counter:02d}"
            for index in [bad_index, neighbor_index]:
                note = str(mappings.at[index, "notes"]).strip()
                mappings.at[index, "notes"] = f"{note};{swap_id}".strip(";")
            logs.append(
                {
                    "adjustment_id": swap_id,
                    "issue_types": "|".join(issue_types),
                    "overlapping_accepted_forms": "|".join(overlap_forms),
                    "source_category": bad_before["source_category"],
                    "source_freq_band": bad_before["source_freq_band"],
                    "target_freq_band": bad_before["target_freq_band"],
                    "pairing_round": bad_before["pairing_round"],
                    "pairing_seed": bad_before["pairing_seed"],
                    "problem_mapping_id": bad_before["mapping_id"],
                    "problem_source_item_id": bad_before["source_item_id"],
                    "problem_source_word_zh": bad_before["source_word_zh"],
                    "problem_standard_en": bad_before["standard_en"],
                    "problem_target_before_item_id": bad_before["target_item_id"],
                    "problem_prompted_before_en": bad_before["prompted_en"],
                    "neighbor_mapping_id": neighbor_before["mapping_id"],
                    "neighbor_source_item_id": neighbor_before["source_item_id"],
                    "neighbor_source_word_zh": neighbor_before["source_word_zh"],
                    "neighbor_standard_en": neighbor_before["standard_en"],
                    "neighbor_target_before_item_id": neighbor_before["target_item_id"],
                    "neighbor_prompted_before_en": neighbor_before["prompted_en"],
                    "problem_target_after_item_id": mappings.at[
                        bad_index, "target_item_id"
                    ],
                    "problem_prompted_after_en": mappings.at[bad_index, "prompted_en"],
                    "neighbor_target_after_item_id": mappings.at[
                        neighbor_index, "target_item_id"
                    ],
                    "neighbor_prompted_after_en": mappings.at[
                        neighbor_index, "prompted_en"
                    ],
                }
            )
            swap_counter += 1
            group_swaps += 1
            if group_swaps > max_group_swaps:
                raise RuntimeError(f"Too many swaps while repairing group={group_key}")
    return (mappings, pd.DataFrame(logs))


def validate_structure(mappings: pd.DataFrame) -> None:
    if len(mappings) != 600:
        raise ValueError(f"Expected 600 mappings, found {len(mappings)}")
    if mappings["mapping_id"].duplicated().any():
        raise ValueError("Duplicate mapping_id found")
    if not (mappings["source_category"] == mappings["target_category"]).all():
        raise ValueError("Cross-category mapping found")
    if (mappings["source_freq_band"] == mappings["target_freq_band"]).any():
        raise ValueError("Within-frequency mapping found")
    expected_seeds = mappings["pairing_round"].map(ROUND_SEEDS)
    if not (mappings["pairing_seed"] == expected_seeds).all():
        raise ValueError("Round and seed do not agree")
    counts = mappings.groupby(GROUP_COLUMNS).size()
    if len(counts) != 60 or not (counts == 10).all():
        raise ValueError("Expected 60 groups with 10 mappings each")
    for key, group in mappings.groupby(GROUP_COLUMNS, sort=False):
        if group["source_item_id"].nunique() != 10:
            raise ValueError(f"Sources are not one-to-one in {key}")
        if group["target_item_id"].nunique() != 10:
            raise ValueError(f"Targets are not one-to-one in {key}")


def validate_final_overlaps(
    mappings: pd.DataFrame, forms_by_item: dict[str, set[str]]
) -> None:
    repeated = int(repeated_pair_mask(mappings).sum())
    translation = sum(
        (
            bool(
                translation_overlap(
                    row["source_item_id"], row["target_item_id"], forms_by_item
                )
            )
            for _, row in mappings.iterrows()
        )
    )
    if repeated or translation:
        raise ValueError(
            f"Final overlaps remain: repeated_rows={repeated}, translation_overlap_rows={translation}"
        )


def main() -> None:
    items = pd.read_csv(ITEMS_FILE)
    validate_items(items)
    forms_by_item = load_accepted_forms(items)
    raw_mappings = generate_raw_mappings(items)
    validate_structure(raw_mappings)
    initial_issues = audit_initial_issues(raw_mappings, forms_by_item)
    final_mappings, adjustments = swap_adjacent_targets(raw_mappings, forms_by_item)
    validate_structure(final_mappings)
    validate_final_overlaps(final_mappings, forms_by_item)
    RAW_OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    raw_mappings.to_csv(RAW_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    initial_issues.to_csv(ISSUES_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    adjustments.to_csv(ADJUSTMENTS_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    final_mappings.to_csv(FINAL_OUTPUT_FILE, index=False, encoding="utf-8-sig")
    pair_issue_rows = (
        initial_issues["issue_types"].str.contains("pair_overlap", regex=False).sum()
    )
    translation_issue_rows = (
        initial_issues["issue_types"]
        .str.contains("translation_overlap", regex=False)
        .sum()
    )
    print(f"Saved raw mappings: {RAW_OUTPUT_FILE}")
    print(f"Saved initial issue audit: {ISSUES_OUTPUT_FILE}")
    print(f"Saved adjustment log: {ADJUSTMENTS_OUTPUT_FILE}")
    print(f"Saved final mappings: {FINAL_OUTPUT_FILE}")
    print(f"Raw mapping rows: {len(raw_mappings)}")
    print(f"Initial repeated-pair rows: {int(pair_issue_rows)}")
    print(f"Initial translation-overlap rows: {int(translation_issue_rows)}")
    print(f"Adjacent swaps: {len(adjustments)}")
    print("Final repeated-pair rows: 0")
    print("Final translation-overlap rows: 0")


if __name__ == "__main__":
    main()
