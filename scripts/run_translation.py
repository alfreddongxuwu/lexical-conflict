"""Run translation prompts locally with resume, selection and dry-run support."""
import argparse, importlib, sys
from pathlib import Path
sys.path.insert(0, str(Path(__file__).resolve().parent))
parser = argparse.ArgumentParser(add_help=False)
parser.add_argument('provider', choices=['ollama', 'openai'])
args, remaining = parser.parse_known_args()
module = importlib.import_module('run_' + args.provider + '_translation')
raise SystemExit(module.main(remaining))
