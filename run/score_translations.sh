#!/usr/bin/env bash
set -euo pipefail
task_project_dir=$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)
cd -- "$task_project_dir"
exec "${PYTHON_BIN:-python3}" scripts/score_matrix.py "$@"
