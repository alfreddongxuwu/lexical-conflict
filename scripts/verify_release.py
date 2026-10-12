import csv
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
manifest = ROOT / "checksums.sha256"
if manifest.exists():
    for line in manifest.read_text().splitlines():
        digest, name = line.split("  ", 1)
        path = ROOT / name
        if (
            not path.is_file()
            or hashlib.sha256(path.read_bytes()).hexdigest() != digest
        ):
            raise SystemExit(f"Checksum mismatch: {name}")
experiments = json.loads((ROOT / "configs/experiments.json").read_text())
total = 0
for name, spec in experiments.items():
    files = sorted((ROOT / "results/runs" / name).glob("*/responses_merged.csv"))
    assert len(files) == spec["models"], name
    for path in files:
        with path.open(encoding="utf-8-sig", newline="") as f:
            rows = list(csv.DictReader(f))
        assert len(rows) == spec["rows_per_model"], str(path)
        assert len({r["prompt_id"] for r in rows}) == len(rows), str(path)
        assert all((r["response"].strip() for r in rows)), str(path)
        coded = path.with_name(
            "responses_baseline_autocoded.csv"
            if name == "baseline"
            else "responses_autocoded.csv"
        )
        with coded.open(encoding="utf-8-sig", newline="") as f:
            codes = list(csv.DictReader(f))
        assert [r["prompt_id"] for r in rows] == [r["prompt_id"] for r in codes]
        label = "baseline_label" if name == "baseline" else "auto_label"
        allowed = (
            {"EXPECTED", "OTHER"}
            if name == "baseline"
            else {"CK", "PK", "BOTH", "OTHER"}
        )
        assert all((r[label] in allowed for r in codes))
        total += len(rows)
assert total == 213750
assert len(list((ROOT / "statistics").glob("*/results/models/*.rds"))) == 12
print("Verified 48 runs, 213750 responses, coding labels, and 12 saved model files.")
