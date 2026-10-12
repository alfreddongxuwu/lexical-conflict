import pandas as pd
from paths import INTERIM_DIR, PROCESSED_DIR

INPUT_DIR = INTERIM_DIR / "category_freq_top30"
INPUT_FILES = [
    INPUT_DIR / "Animal_freq_top30.csv",
    INPUT_DIR / "Fruit_freq_top30.csv",
    INPUT_DIR / "Vehicle_freq_top30.csv",
    INPUT_DIR / "Occupation_freq_top30.csv",
    INPUT_DIR / "Musical_instrument_freq_top30.csv",
]
OUTPUT_FILE = PROCESSED_DIR / "items.csv"
CATEGORY_MAP = {
    "Animal": "animal",
    "Fruit": "fruit",
    "Vehicle": "vehicle",
    "Occupation": "occupation",
    "Musical instrument": "music",
}


def standardize_category(category_value: str) -> str:
    category_value = str(category_value).strip()
    return CATEGORY_MAP.get(category_value, category_value.lower().replace(" ", "_"))


def assign_freq_band(rank: int) -> str:
    if 1 <= rank <= 10:
        return "high"
    elif 11 <= rank <= 20:
        return "medium"
    elif 21 <= rank <= 30:
        return "low"
    else:
        return "unused"


def make_item_id(category: str, rank: int) -> str:
    return f"{category}_{rank:03d}"


def main():
    all_dfs = []
    for path in INPUT_FILES:
        if not path.exists():
            raise FileNotFoundError(f"Input file not found: {path}")
        df = pd.read_csv(path)
        required_columns = {
            "category",
            "word_zh",
            "standard_en",
            "raw_count",
            "freq_per_million",
            "log_freq_per_million",
        }
        missing_columns = required_columns - set(df.columns)
        if missing_columns:
            raise ValueError(
                f"{path} is missing required columns: {sorted(missing_columns)}"
            )
        df = df[
            [
                "category",
                "word_zh",
                "standard_en",
                "raw_count",
                "freq_per_million",
                "log_freq_per_million",
            ]
        ].copy()
        df = df.rename(
            columns={
                "word_zh": "source_word_zh",
                "raw_count": "raw_count_bcc",
                "freq_per_million": "freq_per_million_bcc",
                "log_freq_per_million": "log_freq_per_million_bcc",
            }
        )
        df["category"] = df["category"].apply(standardize_category)
        all_dfs.append(df)
    items = pd.concat(all_dfs, ignore_index=True)
    items = items.sort_values(
        by=["category", "log_freq_per_million_bcc"], ascending=[True, False]
    ).reset_index(drop=True)
    items["rank_in_category"] = items.groupby("category").cumcount() + 1
    items["freq_band"] = items["rank_in_category"].apply(assign_freq_band)
    items["item_id"] = items.apply(
        lambda row: make_item_id(row["category"], row["rank_in_category"]), axis=1
    )
    items["notes"] = ""
    items = items[
        [
            "item_id",
            "category",
            "source_word_zh",
            "standard_en",
            "raw_count_bcc",
            "freq_per_million_bcc",
            "log_freq_per_million_bcc",
            "rank_in_category",
            "freq_band",
            "notes",
        ]
    ]
    OUTPUT_FILE.parent.mkdir(parents=True, exist_ok=True)
    items.to_csv(OUTPUT_FILE, index=False, encoding="utf-8-sig")
    print(f"Saved merged item file to: {OUTPUT_FILE}")
    print(f"Total rows: {len(items)}")
    print(items["category"].value_counts().sort_index())
    print(items["freq_band"].value_counts().sort_index())


if __name__ == "__main__":
    main()
