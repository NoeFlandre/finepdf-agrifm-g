#!/usr/bin/env bash
set -euo pipefail

: "${AGRIFM_G_GRID5000_JOB:?the worker must run inside a Grid5000 OAR job}"
: "${OAR_JOB_ID:?OAR_JOB_ID is required}"
: "${OAR_NODEFILE:?OAR_NODEFILE is required}"

if [[ "${AGRIFM_G_GRID5000_JOB}" != "1" ]]; then
    printf '%s\n' 'AGRIFM_G_GRID5000_JOB must be 1' >&2
    exit 2
fi
if [[ "${1:-}" != "--spec" || "$#" -ne 2 ]]; then
    printf 'usage: %s --spec PATH\n' "$0" >&2
    exit 2
fi

SPEC_PATH="$2"
if [[ "$SPEC_PATH" == ~/* ]]; then
    SPEC_PATH="${HOME}/${SPEC_PATH#~/}"
fi
SPEC_PATH="$(cd "$(dirname "$SPEC_PATH")" && pwd)/$(basename "$SPEC_PATH")"
RUN_ROOT="$(dirname "$SPEC_PATH")"
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

mkdir -p -- "${RUN_ROOT}/pip-cache" "${RUN_ROOT}/uv-cache"
export PIP_CACHE_DIR="${RUN_ROOT}/pip-cache"
export UV_CACHE_DIR="${RUN_ROOT}/uv-cache"

UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" ]]; then
    python3 -m pip install --user --disable-pip-version-check 'uv==0.11.16'
    UV_BIN="${HOME}/.local/bin/uv"
fi

"$UV_BIN" sync --project "$SOURCE_DIR" --locked --no-dev
cd "$SOURCE_DIR"
exec "$UV_BIN" run --project "$SOURCE_DIR" --locked --no-dev \
    python -m scripts.grid5000.worker --spec "$SPEC_PATH"
