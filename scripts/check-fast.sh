#!/usr/bin/env bash
set -euo pipefail

test -f AGENTS.md
test -f PRODUCT.md
test -f DESIGN.md
test -f docs/projects/frontier-lab-intelligence/tasks.md
test -f docs/references/case-prompt.md
test -f docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf
test -f docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.txt
test -f docs/references/context.md
test -f docs/references/research-notes.md
test -f docs/references/build-log.md
test -f docs/references/build-log.jsonl
test -f docs/architecture/overview.md

grep -Eqi "deadline|due|submission|unknown" docs/projects/frontier-lab-intelligence/tasks.md || {
  echo "Tracker should record deadline/submission instructions or unknowns."
  exit 1
}

if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python
fi

# Build log is generated: JSONL is the source of truth, markdown is rendered.
# Renderer is idempotent (<100ms); regenerate and stage only when it changed.
"$PYTHON" scripts/render-build-log.py
if ! git diff --quiet -- docs/references/build-log.md 2>/dev/null; then
  git add docs/references/build-log.md
fi

if find src tests -type f -name '*.py' 2>/dev/null | grep -q .; then
  if [ ! -f pyproject.toml ]; then
    echo "Python files exist but pyproject.toml is missing; add pyproject or document a different validation path."
    exit 1
  fi
  "$PYTHON" -m compileall src tests
  if "$PYTHON" -m pytest --version >/dev/null 2>&1; then
    "$PYTHON" -m pytest -q
  else
    echo "pytest not installed; compile-only validation passed."
  fi
fi

find docs -type f -name '*.md' -print | sort >/dev/null
echo "check-fast.sh: OK"
