import csv
from paths import INTERIM_DIR

INPUT_DIR = INTERIM_DIR / "category_freq_top60"
OUTPUT_DIR = INTERIM_DIR / "category_freq_top30"
FREQUENCY_COLUMN = "log_freq_per_million"


def read_csv_file(file_path):
    with open(file_path, "r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        rows = list(reader)
        fieldnames = reader.fieldnames
    return (rows, fieldnames)


def write_csv_file(file_path, rows, fieldnames):
    with open(file_path, "w", encoding="utf-8-sig", newline="") as f:
        writer = csv.DictWriter(f, fieldnames=fieldnames)
        writer.writeheader()
        writer.writerows(rows)


def add_frequency_ranks(rows):
    rows.sort(
        key=lambda row: float(row[FREQUENCY_COLUMN]) if row[FREQUENCY_COLUMN] else 0,
        reverse=True,
    )
    for index, row in enumerate(rows, start=1):
        row["rank_within_category"] = index
    return rows


def select_frequency_bands(rows):
    selected_rows = []
    band_ranges = [("High", 1, 10), ("Medium", 26, 35), ("Low", 51, 60)]
    new_rank = 1
    for band_name, start_rank, end_rank in band_ranges:
        for row in rows:
            rank = row["rank_within_category"]
            if start_rank <= rank <= end_rank:
                row = row.copy()
                row["rank_within_category"] = new_rank
                row["frequency_band"] = band_name
                selected_rows.append(row)
                new_rank += 1
    return selected_rows


def process_category_file(input_path, output_path):
    rows, fieldnames = read_csv_file(input_path)
    if len(rows) < 60:
        print(
            f"Warning: {input_path} has only {len(rows)} rows. Rank 51-60 may be incomplete."
        )
    rows = add_frequency_ranks(rows)
    selected_rows = select_frequency_bands(rows)
    new_fieldnames = list(fieldnames)
    if "rank_within_category" not in new_fieldnames:
        new_fieldnames.append("rank_within_category")
    if "frequency_band" not in new_fieldnames:
        new_fieldnames.append("frequency_band")
    write_csv_file(output_path, selected_rows, new_fieldnames)


def main():
    OUTPUT_DIR.mkdir(parents=True, exist_ok=True)
    for input_path in INPUT_DIR.glob("*.csv"):
        output_filename = input_path.name.replace("_top60.csv", "_top30.csv")
        output_path = OUTPUT_DIR / output_filename
        process_category_file(input_path, output_path)
        print(f"Saved: {output_path}")
    print("Done.")


if __name__ == "__main__":
    main()
