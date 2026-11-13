
#!/usr/bin/env bash
# scripts/upgrade_probe.sh
set -Eeuo pipefail

cd "$(dirname "$0")/.."

MODE="${1:-}"

if [[ "$MODE" != "baseline" && "$MODE" != "upgrade" ]]; then
    echo "usage: $0 baseline|upgrade"
    exit 2
fi

: "${TEST_DATABASE_URL:?Set TEST_DATABASE_URL to a disposable test database}"

export DATABASE_URL="$TEST_DATABASE_URL"

PY="${PYTHON:-python3}"
VENV=".venv-probe-$MODE"
REPORT="upgrade_report_$MODE.txt"

redact() {
    sed -E \
      "s/(password=')[^']+/\1***/g; s#(://[^:/@]+:)[^@]+@#\1***@#g"
}

# Never remove an existing probe environment without confirmation.
if [[ -d "$VENV" ]]; then
    echo "Probe environment already exists: $VENV"
    echo "Inspect it before removing or recreating it."
    exit 1
fi

"$PY" -m venv "$VENV"

trap 'echo "Probe failed. Inspect $REPORT and the environment $VENV."' ERR

source "$VENV/bin/activate"

python -m pip install --upgrade pip

UPGRADE_RE='^(fastapi|uvicorn|python-multipart|pydantic|pydantic-settings|httpx|playwright|sentry-sdk|opentelemetry-)'

{
    echo "== mode: $MODE"
    echo "== python: $(python --version)"

    if [[ "$MODE" == "baseline" ]]; then
        pip install -r requirements-dev.txt
    else
        grep -vE '^\s*(#|$)' requirements.txt |
            grep -vE "$UPGRADE_RE" > "$VENV/base.txt"

        grep -vE '^\s*(-r|#|$)' requirements-dev.txt \
            >> "$VENV/base.txt"

        pip install -r "$VENV/base.txt"

        pip install -U \
            fastapi "uvicorn[standard]" python-multipart \
            "pydantic[email]" pydantic-settings httpx playwright \
            "sentry-sdk[fastapi]" opentelemetry-api \
            opentelemetry-sdk opentelemetry-exporter-otlp \
            opentelemetry-instrumentation-fastapi \
            opentelemetry-instrumentation-sqlalchemy
    fi

    echo
    echo "== pip check"
    pip check

    echo
    echo "== key versions"
    pip list --format=freeze

    echo
    echo "== tests"
    python -m pytest -q -p no:cacheprovider app/tests \
        -W "ignore::DeprecationWarning"

    echo
    echo "== frozen set"
    pip freeze

} 2>&1 | redact | tee "$REPORT"

echo "Report saved to $REPORT"
