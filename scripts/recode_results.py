import argparse
from pathlib import Path
import sys
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))
from lexconflict import autocode as main_coding
from lexconflict import autocode_baseline as baseline_coding

parser = argparse.ArgumentParser()
parser.add_argument("--check", action="store_true")
parser.add_argument("--output-dir", default="outputs/recoded")
args = parser.parse_args()
forms = main_coding.load_accepted_translations()
total = 0
for source in sorted((ROOT / "results/runs").glob("*/*/responses_merged.csv")):
    baseline = source.parent.parent.name == "baseline"
    coding = baseline_coding if baseline else main_coding
    frame = pd.read_csv(source, keep_default_na=False)
    coding.validate_for_auto_coding(frame)
    added = frame.apply(coding.auto_label_row, axis=1, forms_by_item_id=forms)
    name = "responses_baseline_autocoded.csv" if baseline else "responses_autocoded.csv"
    if args.check:
        expected = pd.read_csv(source.with_name(name), keep_default_na=False)
        assert frame.prompt_id.equals(expected.prompt_id), str(source)
        for column in added:
            pd.testing.assert_series_equal(
                added[column].astype(str),
                expected[column].astype(str),
                check_names=False,
            )
    else:
        target = (
            ROOT
            / args.output_dir
            / source.relative_to(ROOT / "results/runs").parent
            / name
        )
        target.parent.mkdir(parents=True, exist_ok=True)
        pd.concat([frame, added], axis=1).to_csv(
            target, index=False, encoding="utf-8-sig"
        )
    total += len(frame)
    print(source.parent.parent.name, source.parent.name, len(frame), flush=True)
print(
    f"Verified {total} recoded responses."
    if args.check
    else f"Recoded {total} responses."
)
