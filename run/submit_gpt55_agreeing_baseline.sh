#!/usr/bin/env bash
# Local compatibility entrypoint: first 75 prompts, then the remaining 675.
set -euo pipefail
task_project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$task_project_dir"
task_stage=${1:-}
[[ $task_stage == first || $task_stage == rest ]] || { echo "Usage: $0 first|rest [--dry-run]" >&2; exit 2; }
shift
[[ $# -le 1 && ( $# -eq 0 || $1 == --dry-run ) ]] || exit 2
task_python=${PYTHON_BIN:-python3}
task_run=${GPT_BASELINE_RUN:-outputs/runs/conventional_meaning/chatgpt5_5_instant}
task_start=0; task_limit=75
if [[ $task_stage == rest ]]; then
  task_start=75; task_limit=675
  if [[ $# -eq 0 ]]; then
    "$task_python" scripts/check_gpt55_agreeing_baseline.py first --run-dir "$task_run"
  fi
fi
exec "$task_python" scripts/run_translation.py openai \
  --prompts data/processed/prompts_conventional_meaning.csv \
  --run-dir "$task_run" --model gpt-5.5 --model-id chatgpt5_5_instant \
  --experiment-id conventional_meaning --start "$task_start" --limit "$task_limit" \
  --reasoning-effort none --text-verbosity low --max-output-tokens 128 \
  --store false --max-retries 0 "$@"
