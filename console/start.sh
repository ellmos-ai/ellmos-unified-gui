#!/usr/bin/env sh
set -eu
repo_dir=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
PYTHONPATH="$repo_dir/src${PYTHONPATH:+:$PYTHONPATH}" \
  python -m unified_gui.console start "$@"
