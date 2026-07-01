#!/usr/bin/env bash
set -euo pipefail

ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
cd "$ROOT"

if [ -d .venv312 ]; then
  # shellcheck disable=SC1091
  source .venv312/bin/activate
fi

pytest tests -q
genvm-lint lint contracts/source_trail.py --json
genvm-lint validate contracts/source_trail.py --json
genvm-lint check contracts/source_trail.py --json
