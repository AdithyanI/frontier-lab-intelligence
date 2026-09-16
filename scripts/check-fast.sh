#!/usr/bin/env bash
set -euo pipefail

REQUIRE_RUNTIME=0
case "${1:-}" in
  "") ;;
  --require-runtime) REQUIRE_RUNTIME=1; shift ;;
  *) echo "Usage: scripts/check-fast.sh [--require-runtime]" >&2; exit 2 ;;
esac
if [ "$#" -ne 0 ]; then
  echo "Usage: scripts/check-fast.sh [--require-runtime]" >&2
  exit 2
fi

PYTHON_RUNTIME=0
if [ -e .venv ] || [ -L .venv ]; then
  if [ ! -x .venv/bin/python ]; then
    echo "Existing .venv is incomplete; repair it using docs/references/service-lifecycle.md." >&2
    exit 1
  fi
  PYTHON=.venv/bin/python
  PYTHON_RUNTIME=1
else
  PYTHON=python3
fi
if [ "$REQUIRE_RUNTIME" -eq 1 ] && { [ "$PYTHON_RUNTIME" -eq 0 ] || [ ! -d frontend/node_modules ]; }; then
  echo "Full runtime checks require .venv and frontend/node_modules. Restore dependencies using docs/references/service-lifecycle.md." >&2
  exit 1
fi

# Check source without installing the package or recreating bytecode caches.
export PYTHONPATH="${PWD}/src${PYTHONPATH:+:${PYTHONPATH}}"
export PYTHONDONTWRITEBYTECODE=1

test -f AGENTS.md
test -f PRODUCT.md
test -f DESIGN.md
test -f docs/references/case-prompt.md
test -f docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf
test -f docs/references/build-log/current.jsonl
test -d docs/references/build-log/archive
test ! -e docs/references/build-log.jsonl
test ! -e scripts/render-build-log.py
test -f docs/architecture/overview.md
test -f docs/architecture/code-map.md
test -f docs/references/data-lifecycle.md
test -f docs/references/implementation-contracts.md
test -f docs/STATUS.md

# Domain code is package-owned. Keep the root package restricted to shared
# composition/runtime plumbing so new work cannot recreate the former flat
# module pile.
for domain in ingestion registry network evidence routing scoring insights delivery web; do
  test -d "src/fli/$domain"
done
unexpected_root_modules=$(find src/fli -maxdepth 1 -type f -name '*.py' \
  ! -name '__init__.py' ! -name 'cli.py' ! -name 'llm_responses.py' \
  ! -name 'store.py' ! -name 'paths.py' -print)
if [ -n "$unexpected_root_modules" ]; then
  echo "Domain modules must live in a package, not directly under src/fli:"
  echo "$unexpected_root_modules"
  exit 1
fi
test ! -e data/signal-events.db

# React ownership mirrors product domains. Keep route implementation inside
# features, cross-feature primitives inside shared, and composition inside app.
for area in app shared styles features/architecture features/evidence \
  features/insights features/network; do
  test -d "frontend/src/$area"
done
test ! -d frontend/src/pages
test ! -d frontend/src/components
unexpected_frontend_root=$(find frontend/src -maxdepth 1 -type f \
  \( -name '*.ts' -o -name '*.tsx' \) ! -name 'main.tsx' -print)
if [ -n "$unexpected_frontend_root" ]; then
  echo "React modules must be owned by app, features, or shared:"
  echo "$unexpected_frontend_root"
  exit 1
fi

# Active prompt paths are semantic and stable. Contract versions and hashes
# belong in run metadata rather than mutable filenames.
for prompt in \
  src/fli/registry/prompts/identity_context.txt \
  src/fli/registry/prompts/evaluation.txt \
  src/fli/registry/prompts/relevance.txt \
  src/fli/routing/prompts/audience_routing.txt \
  src/fli/insights/prompts/investment_company_analysis.txt; do
  test -f "$prompt"
done
versioned_active_prompts=$(find src/fli -path '*/prompts/*' -type f \
  -name '*_v[0-9]*.txt' -print)
if [ -n "$versioned_active_prompts" ]; then
  echo "Active prompt filenames must be semantic; keep versions in run metadata:"
  echo "$versioned_active_prompts"
  exit 1
fi


# Build-log history is sharded and machine-maintained. Validate every shard,
# render the complete reviewer artifact, and stage it only when it changed.
"$PYTHON" scripts/build-log.py --plain validate
"$PYTHON" scripts/build-log.py --plain render
if ! git diff --quiet -- docs/references/build-log.md 2>/dev/null; then
  git add docs/references/build-log.md
fi

if find src tests -type f -name '*.py' 2>/dev/null | grep -q .; then
  if [ ! -f pyproject.toml ]; then
    echo "Python files exist but pyproject.toml is missing; add pyproject or document a different validation path."
    exit 1
  fi
  "$PYTHON" - <<'PY'
from pathlib import Path

count = 0
for root in (Path("src"), Path("tests"), Path("scripts")):
    for path in root.rglob("*.py"):
        compile(path.read_bytes(), str(path), "exec")
        count += 1
print(f"Python syntax: OK ({count} files; no bytecode written)")
PY
  if [ "$PYTHON_RUNTIME" -eq 1 ]; then
    "$PYTHON" -m pytest -q -p no:cacheprovider
  else
    echo "SKIP Python runtime tests: .venv is absent in this parked/clean checkout."
  fi
fi

# A local Artifact Store is optional in clean clones. When present, prove that
# every live observation still resolves to the primary X account's raw post or
# one of that account's replies in the same conversation.
if [ "$PYTHON_RUNTIME" -eq 1 ]; then
  artifact_db="$("$PYTHON" -c 'from fli.paths import data_path; print(data_path("derived", "artifacts", "artifacts.db"))')"
  if [ -f "$artifact_db" ]; then
    "$PYTHON" -m fli.cli artifacts audit-lineage \
      --db "$artifact_db" \
      --no-input >/dev/null
  fi
else
  echo "SKIP live Artifact Store lineage audit: .venv is absent; preserved data is not opened."
fi

if [ -f frontend/package.json ]; then
  npm --prefix frontend run test --if-present
  if [ -d frontend/node_modules ]; then
    npm --prefix frontend run lint
    npm --prefix frontend run build
    if ! git diff --quiet -- src/fli/web/dist 2>/dev/null; then
      git add src/fli/web/dist
    fi
  else
    echo "SKIP frontend lint/build: frontend/node_modules is absent in this parked/clean checkout."
  fi
fi

find docs -type f -name '*.md' -print | sort >/dev/null
echo "check-fast.sh: OK"
