#!/bin/bash
echo "=== 1. BUILD VERIFICATION ==="
uv run python -c "import app.main" 2>&1
echo $?

echo "=== 2. CODE QUALITY (RUFF) ==="
uv run ruff check . 2>&1

echo "=== 2. CODE QUALITY (MYPY) ==="
uv run mypy app 2>&1

echo "=== 2. CODE QUALITY (TODOS) ==="
grep -rnw 'app' -e 'TODO\|FIXME' 2>&1

echo "=== 3. DATABASE ==="
uv run alembic check 2>&1

echo "=== 9. TESTING ==="
uv run pytest tests/ 2>&1

