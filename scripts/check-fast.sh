#!/usr/bin/env bash
set -euo pipefail

test -f AGENTS.md
test -f PRODUCT.md
test -f DESIGN.md
test -f docs/projects/frontier-lab-intelligence/tasks.md
test -f docs/references/case-prompt.md
test -f docs/references/working-log.md
test -f docs/learning/README.md

grep -Eqi "deadline|due|submission|unknown" docs/projects/frontier-lab-intelligence/tasks.md || {
  echo "Tracker should record deadline/submission instructions or unknowns."
  exit 1
}

if find src tests -type f -name '*.py' 2>/dev/null | grep -q .; then
  if [ ! -f pyproject.toml ]; then
    echo "Python files exist but pyproject.toml is missing; add pyproject or document a different validation path."
    exit 1
  fi
  python -m compileall src tests
  if command -v pytest >/dev/null 2>&1; then
    pytest -q
  else
    echo "pytest not installed; compile-only validation passed."
  fi
fi

find docs -type f -name '*.md' -print | sort >/dev/null
echo "check-fast.sh: OK"
