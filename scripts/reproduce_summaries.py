import argparse
import os
from pathlib import Path
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
parser = argparse.ArgumentParser()
parser.add_argument("--output-dir", default="outputs/summary")
args = parser.parse_args()
target = (ROOT / args.output_dir).resolve()
if target.exists() and any(target.iterdir()):
    raise SystemExit(f"Output directory must be empty: {target}")
env = os.environ.copy()
env["PYTHONPATH"] = str(ROOT / "src") + os.pathsep + env.get("PYTHONPATH", "")
for experiment, folder, count in [
    ("main", "exp1", 9),
    ("may_mean", "may_mean", 9),
    ("reiteration", "reiteration", 9),
    ("thinking_on", "thinking_on", 3),
]:
    command = [
        sys.executable,
        "-m",
        "lexconflict.summarize_models",
        "--runs-root",
        str(ROOT / "results/runs"),
        "--output-dir",
        str(target / folder),
        "--main-experiment",
        experiment,
        "--expected-rows",
        "6000",
        "--expected-model-count",
        str(count),
    ]
    if experiment == "main":
        command += ["--baseline-output-dir", str(target / "baseline")]
    subprocess.run(command, cwd=ROOT, env=env, check=True)
subprocess.run(
    [
        sys.executable,
        "-m",
        "lexconflict.summarize_exp2_models",
        "--runs-root",
        str(ROOT / "results/runs"),
        "--output-dir",
        str(target / "exp2"),
        "--expected-rows",
        "3000",
        "--expected-model-count",
        "9",
    ],
    cwd=ROOT,
    env=env,
    check=True,
)
print(f"Rebuilt summaries in {target}")
