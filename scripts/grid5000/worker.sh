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
SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
SOURCE_DIR="$(cd "${SCRIPT_DIR}/../.." && pwd)"

if [[ ! "${OAR_JOB_ID}" =~ ^[0-9]+$ ]]; then
    printf '%s\n' 'OAR_JOB_ID must be numeric' >&2
    exit 2
fi
JOB_SCRATCH="${TMPDIR:-/tmp}/agrifm-g-${OAR_JOB_ID}"
if [[ -e "${JOB_SCRATCH}" ]]; then
    printf 'refusing to reuse job scratch: %s\n' "${JOB_SCRATCH}" >&2
    exit 2
fi
mkdir -m 700 -p -- "${JOB_SCRATCH}"
cleanup_job_scratch() {
    rm -rf -- "${JOB_SCRATCH}"
}
trap cleanup_job_scratch EXIT
mkdir -m 700 -p -- "${JOB_SCRATCH}/tmp"
export TMPDIR="${JOB_SCRATCH}/tmp"
export PIP_CACHE_DIR="${JOB_SCRATCH}/pip-cache"
export UV_CACHE_DIR="${JOB_SCRATCH}/uv-cache"
export UV_PROJECT_ENVIRONMENT="${JOB_SCRATCH}/venv"
export HF_HOME="${JOB_SCRATCH}/hf-cache"
export HF_HUB_DISABLE_TELEMETRY=1

UV_BIN="$(command -v uv || true)"
if [[ -z "$UV_BIN" ]]; then
    python3 -m pip install --prefix "${JOB_SCRATCH}/uv-prefix" \
        --no-cache-dir --disable-pip-version-check 'uv==0.11.16'
    UV_BIN="${JOB_SCRATCH}/uv-prefix/bin/uv"
fi

"$UV_BIN" sync --project "$SOURCE_DIR" --locked --no-dev --extra vision
cd "$SOURCE_DIR"
"$UV_BIN" run --project "$SOURCE_DIR" --locked --no-dev --extra vision \
    python -m scripts.grid5000.worker --spec "$SPEC_PATH"
