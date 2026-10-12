import argparse
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
from lexconflict.autocode import code_file

parser = argparse.ArgumentParser()
parser.add_argument("--run-dir", required=True)
parser.add_argument("--baseline", action="store_true")
args = parser.parse_args()
code_file(args.run_dir, args.baseline)
