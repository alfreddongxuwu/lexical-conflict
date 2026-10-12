import csv
import math
import re
from paths import RAW_DIR, INTERIM_DIR

BCC_FILE = RAW_DIR / "bcc.txt"
CATEGORY_FILE = RAW_DIR / "categories.txt"
OUTPUT_DIR = INTERIM_DIR / "category_freq_top60"


def read_bcc_frequency(bcc_file):
    freq_dict = {}
    total_tokens = 0
    with open(bcc_file, "r", encoding="utf-8-sig") as f:
        for line_number, line in enumerate(f, start=1):
            line = line.strip()
            if not line:
                continue
            if line.lower() in {"token,count", "word,count", "词,频次", "词语,频次"}:
                continue
            try:
                token, count_str = line.rsplit(",", 1)
            except ValueError:
                print(f"Warning: Could not parse line {line_number}: {line}")
                continue
            token = token.strip()
            count_str = count_str.strip()
            try:
                count = int(count_str)
            except ValueError:
                print(f"Warning: Invalid count on line {line_number}: {line}")
                continue
            if token:
                freq_dict[token] = count
                total_tokens += count
    return (freq_dict, total_tokens)


def read_category_file(category_file):
    categories = {}
    current_category = None
    with open(category_file, "r", encoding="utf-8-sig") as f:
        for line_number, raw_line in enumerate(f, start=1):
            line = raw_line.strip()
            if not line:
                continue
            if line.endswith(":") or line.endswith("："):
                current_category = line[:-1].strip()
                categories[current_category] = []
                continue
            if current_category is None:
                print(
                    f"Warning: Found item before any category header on line {line_number}: {line}"
                )
                continue
            parts = line.split(maxsplit=1)
            if len(parts) == 1:
                word_zh = parts[0].strip()
                standard_en = ""
                print(
                    f"Warning: No English translation found on line {line_number}: {line}"
                )
            else:
                word_zh = parts[0].strip()
                standard_en = parts[1].strip()
            categories[current_category].append(
                {"word_zh": word_zh, "standard_en": standard_en}
            )
    return categories


def safe_filename(name):
    name = name.strip()
    name = re.sub("\\s+", "_", name)
    name = re.sub("[^\\w\\u4e00-\\u9fff-]", "", name)
    return name


def write_category_csvs(categories, freq_dict, total_tokens, output_dir):
    output_dir.mkdir(parents=True, exist_ok=True)
    for category_name, items in categories.items():
        output_path = output_dir / f"{safe_filename(category_name)}_freq_top60.csv"
        rows = []
        for item in items:
            word_zh = item["word_zh"]
            standard_en = item["standard_en"]
            raw_count = freq_dict.get(word_zh, 0)
            freq_per_million = raw_count / total_tokens * 1000000
            log_freq_per_million = math.log10(freq_per_million + 1)
            rows.append(
                {
                    "category": category_name,
                    "word_zh": word_zh,
                    "standard_en": standard_en,
                    "raw_count": raw_count,
                    "freq_per_million": freq_per_million,
                    "log_freq_per_million": log_freq_per_million,
                    "found_in_bcc": "yes" if word_zh in freq_dict else "no",
                }
            )
        rows.sort(key=lambda x: x["log_freq_per_million"], reverse=True)
        with open(output_path, "w", encoding="utf-8-sig", newline="") as f:
            writer = csv.DictWriter(
                f,
                fieldnames=[
                    "category",
                    "word_zh",
                    "standard_en",
                    "raw_count",
                    "freq_per_million",
                    "log_freq_per_million",
                    "found_in_bcc",
                ],
            )
            writer.writeheader()
            writer.writerows(rows)
        print(f"Saved: {output_path}")


def main():
    print("Reading BCC frequency file...")
    freq_dict, total_tokens = read_bcc_frequency(BCC_FILE)
    print(f"Total unique tokens: {len(freq_dict):,}")
    print(f"Total token count: {total_tokens:,}")
    print("Reading category file...")
    categories = read_category_file(CATEGORY_FILE)
    print("Categories found:")
    for category_name, items in categories.items():
        print(f"  {category_name}: {len(items)} words")
    print("Writing category frequency CSV files...")
    write_category_csvs(categories, freq_dict, total_tokens, OUTPUT_DIR)
    print("Done.")


if __name__ == "__main__":
    main()
