#!/usr/bin/env bash
# CI gate: what must pass before anything is merged to main (CLAUDE.md §1.6, §3).
set -euo pipefail
cd "$(dirname "$0")/.."
make check
make smoke
docker compose config --quiet
echo "ci ok"
