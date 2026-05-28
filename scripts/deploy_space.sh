#!/usr/bin/env bash
# Deploy main → Hugging Face Space.
#
# GitHub (origin) carries the full README; the Space carries a minimal one.
# The `space-deploy` branch holds the minimal README and uses a merge=ours
# driver (see .gitattributes on that branch) so merging main never clobbers it.
#
# Usage:  ./scripts/deploy_space.sh
set -euo pipefail

# The merge=ours driver is per-clone local config; ensure it exists (idempotent).
git config merge.ours.driver true

current=$(git rev-parse --abbrev-ref HEAD)

git checkout space-deploy
git merge main --no-edit          # README.md stays minimal via merge=ours
git push space space-deploy:main
git checkout "$current"

echo "✓ Deployed main → Space. GitHub keeps the full README; the Space keeps its minimal one."
