#!/usr/bin/env bash
set -e

# ---------
# Usage check
# ---------
if [ "$#" -ne 4 ]; then
    echo "Usage:"
    echo "  ./scripts/finalize_pr.sh \\"
    echo "    \"<commit subject>\" \\"
    echo "    \"<commit body>\" \\"
    exit 1
fi

COMMIT_SUBJECT="$1"
COMMIT_BODY="$2"

# -----------------------------
# Safety checks
# -----------------------------
# Check for modified files OR untracked files
if [[ -z $(git status --porcelain) ]]; then
  echo "No changes (modified or new) detected. Aborting."
  exit 1
fi

# if git diff --quiet; then
#   echo "No changes detected. Aborting."
#   exit 1
# fi

CURRENT_BRANCH=$(git branch --show-current)

if [[ "$CURRENT_BRANCH" == "main" || "$CURRENT_BRANCH" == "master" || "$CURRENT_BRANCH" == "integration" ]]; then
  echo "You are on $CURRENT_BRANCH. Please create a feature branch first."
  exit 1
fi

# -----------------------------
# Commit
# -----------------------------
echo "Staging changes..."
cd "$(git rev-parse --show-toplevel)"
git add .

echo "Creating commit..."
git commit \
  -m "$COMMIT_SUBJECT" \
  -m "$COMMIT_BODY"

# -----------------------------
# Push
# -----------------------------
echo "Pushing branch..."
git push -u origin "$CURRENT_BRANCH"

echo "✅ Commit created successfully."