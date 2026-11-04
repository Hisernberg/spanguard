#!/usr/bin/env bash
# Push the final repo state to GitHub. Requires a valid token:
#   GH_TOKEN=ghp_xxx bash scripts/gh_push.sh "final benchmark results"
# Also updates topics. (The earlier token in .secrets/env expired mid-task.)
set -euo pipefail
cd "$(dirname "$0")/.."
MSG="${1:-benchmark: committed run records, charts, model family}"
TOKEN="${GH_TOKEN:-$(sed -n 's/^export GH_TOKEN="\(.*\)"/\1/p' /home/z/my-project/.secrets/env)}"
if [ -z "$TOKEN" ]; then echo "No GH_TOKEN. Create one at https://github.com/settings/tokens (repo, delete_repo, workflow scopes) and re-run." >&2; exit 1; fi
git remote remove origin 2>/dev/null || true
git remote add origin "https://x-access-token:${TOKEN}@github.com/Hisernberg/spanguard.git"
git push -u origin main
git push origin --tags 2>/dev/null || true
curl -sS -X PUT -H "Authorization: token $TOKEN" "https://api.github.com/repos/Hisernberg/spanguard/topics" \
  -d '{"names":["meta-hackathon-2026","meta-ai-hackathon","prompt-injection","ai-agents","llm-security","gateway","huggingface","meta-global-ai-hackathon-2026","baseten"]}' > /dev/null
echo "pushed + topics set"
