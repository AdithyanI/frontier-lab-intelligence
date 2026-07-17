#!/usr/bin/env bash
set -euo pipefail

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
for domain in ingestion registry network evidence routing scoring insights web; do
  test -d "src/fli/$domain"
done
unexpected_root_modules=$(find src/fli -maxdepth 1 -type f -name '*.py' \
  ! -name '__init__.py' ! -name 'cli.py' ! -name 'llm_responses.py' \
  ! -name 'store.py' -print)
if [ -n "$unexpected_root_modules" ]; then
  echo "Domain modules must live in a package, not directly under src/fli:"
  echo "$unexpected_root_modules"
  exit 1
fi
test ! -e data/signal-events.db

# Active prompt paths are semantic and stable. Contract versions and hashes
# belong in run metadata rather than mutable filenames.
for prompt in \
  src/fli/registry/prompts/identity_context.txt \
  src/fli/registry/prompts/evaluation.txt \
  src/fli/registry/prompts/relevance.txt \
  src/fli/routing/prompts/audience_routing.txt \
  src/fli/insights/prompts/ai_engineering.txt \
  src/fli/insights/prompts/investment.txt; do
  test -f "$prompt"
done
versioned_active_prompts=$(find src/fli -path '*/prompts/*' -type f \
  -name '*_v[0-9]*.txt' -print)
if [ -n "$versioned_active_prompts" ]; then
  echo "Active prompt filenames must be semantic; keep versions in run metadata:"
  echo "$versioned_active_prompts"
  exit 1
fi

# Keep the cold-start route unambiguous without limiting independent work to
# one active project. STATUS is the conceptual handoff and must name every
# active tracker so a cold agent can choose the relevant execution stream.
grep -Fq 'docs/STATUS.md' AGENTS.md
while IFS= read -r active_tracker; do
  if ! grep -Fq "$active_tracker" docs/STATUS.md; then
    echo "docs/STATUS.md does not point to the active tracker: $active_tracker"
    exit 1
  fi
done < <(find docs/projects -mindepth 2 -maxdepth 2 \
  -name tasks.md ! -path '*/archive/*' -print | sort)


if [ -x .venv/bin/python ]; then
  PYTHON=.venv/bin/python
else
  PYTHON=python
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
  "$PYTHON" -m compileall src tests
  if "$PYTHON" -m pytest --version >/dev/null 2>&1; then
    "$PYTHON" -m pytest -q
  else
    echo "pytest not installed; compile-only validation passed."
  fi
fi

# A local Artifact Store is optional in clean clones. When present, prove that
# every live observation still resolves to the primary X account's raw post or
# one of that account's replies in the same conversation.
artifact_db="data/derived/artifacts/artifacts.db"
if [ -f "$artifact_db" ]; then
  "$PYTHON" -m fli.cli artifacts audit-lineage \
    --db "$artifact_db" \
    --no-input >/dev/null
fi

if [ -f frontend/package.json ]; then
  npm --prefix frontend run test --if-present
  npm --prefix frontend run lint
  npm --prefix frontend run build
  if ! git diff --quiet -- src/fli/web/dist 2>/dev/null; then
    git add src/fli/web/dist
  fi
fi

find docs -type f -name '*.md' -print | sort >/dev/null
echo "check-fast.sh: OK"
