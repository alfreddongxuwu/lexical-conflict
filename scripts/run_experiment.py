import argparse
import importlib
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / "src"))
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument("provider", choices=["ollama", "openai"])
args, remaining = parser.parse_known_args()
module = importlib.import_module("lexconflict.run_" + args.provider)
raise SystemExit(module.main(remaining))
