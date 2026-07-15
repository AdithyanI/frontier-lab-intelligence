#!/usr/bin/env bash
set -euo pipefail

test -f AGENTS.md
test -f PRODUCT.md
test -f DESIGN.md
test -f docs/references/case-prompt.md
test -f docs/references/source-material/BIT_Capital-Case_Study-Frontier_Lab_Intelligence.pdf
test -f docs/references/build-log/current.jsonl
test -d docs/references/build-log/archive
test -f docs/architecture/overview.md
test -f docs/STATUS.md

# Keep the cold-start route unambiguous without requiring an active project
# between phases. STATUS is the conceptual handoff; at most one tracker owns
# current execution state, and STATUS must name it when it exists.
grep -Fq 'docs/STATUS.md' AGENTS.md
active_tracker_count=$(find docs/projects -mindepth 2 -maxdepth 2 \
  -name tasks.md ! -path '*/archive/*' | wc -l | tr -d ' ')
if [ "$active_tracker_count" -gt 1 ]; then
  echo "More than one active project tracker exists; archive or consolidate until execution has one owner."
  find docs/projects -mindepth 2 -maxdepth 2 -name tasks.md \
    ! -path '*/archive/*' -print | sort
  exit 1
fi
if [ "$active_tracker_count" -eq 1 ]; then
  active_tracker=$(find docs/projects -mindepth 2 -maxdepth 2 \
    -name tasks.md ! -path '*/archive/*' -print)
  if ! grep -Fq "$active_tracker" docs/STATUS.md; then
    echo "docs/STATUS.md does not point to the active tracker: $active_tracker"
    exit 1
  fi
fi


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

# A canonical Audience Insights publication is valid only as an exact
# manifest/report pair. Clean clones have neither and skip this fast guardrail;
# once either exists, recompute the report and require byte-for-byte identity.
reconciliation_dir="data/derived/audience-insights-v2/production-reconciliation-v2"
reconciliation_manifest="$reconciliation_dir/manifest.json"
reconciliation_report="$reconciliation_dir/report.json"
if [ -e "$reconciliation_manifest" ] || [ -e "$reconciliation_report" ]; then
  if [ ! -f "$reconciliation_manifest" ] || [ ! -f "$reconciliation_report" ]; then
    echo "Canonical Audience Insights publication requires both manifest.json and report.json."
    exit 1
  fi
  mkdir -p tmp
  reconciliation_tmp=$(mktemp "tmp/production-reconciliation-report.XXXXXX")
  cleanup_reconciliation_tmp() {
    rm -f "$reconciliation_tmp"
  }
  trap cleanup_reconciliation_tmp EXIT
  "$PYTHON" -m fli.cli audience-insight-production-reconciliation \
    --manifest "$reconciliation_manifest" \
    --output "$reconciliation_tmp"
  if ! cmp -s "$reconciliation_tmp" "$reconciliation_report"; then
    echo "Canonical Audience Insights report is stale; regenerate it from manifest.json."
    exit 1
  fi
  cleanup_reconciliation_tmp
  trap - EXIT
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
