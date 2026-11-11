#!/usr/bin/env bash
# Re-vendor Ponytail from upstream and re-pin THIRD_PARTY_NOTICES.md.
#   scripts/update-ponytail.sh          # clone upstream's main
#   PONYTAIL_SRC=/path scripts/update-ponytail.sh   # use an existing checkout
set -euo pipefail
cd "$(dirname "$0")/.."

tmp=$(mktemp -d)
trap 'rm -rf "$tmp"' EXIT

src=${PONYTAIL_SRC:-}
if [ -z "$src" ]; then
  git clone --depth 1 --quiet https://github.com/DietrichGebert/ponytail.git "$tmp/ponytail"
  src=$tmp/ponytail
fi

for s in ponytail ponytail-review ponytail-audit ponytail-debt ponytail-gain ponytail-help; do
  mkdir -p "skills/$s"
  cp "$src/skills/$s/SKILL.md" "skills/$s/SKILL.md"
  # Skill hosts skip symlinks, so .claude/skills holds real copies of skills/.
  mkdir -p ".claude/skills/$s"
  cp "skills/$s/SKILL.md" ".claude/skills/$s/SKILL.md"
done

# Host rule files are opt-in: a copy that exists is refreshed, a missing one stays missing.
for rel in .cursor/rules/ponytail.mdc .windsurf/rules/ponytail.md .clinerules/ponytail.md \
  .agents/rules/ponytail.md .qoder/rules/ponytail.md .kiro/steering/ponytail.md .github/copilot-instructions.md; do
  if [ -e "$rel" ]; then cp "$src/$rel" "$rel"; fi
done

# Upstream's last paragraph is about ponytail's own repo, so it is dropped here.
# scripts/check-ponytail-sync.js fails if it ever comes back.
node -e '
const fs = require("fs");
const [, from, to] = process.argv;
const text = fs.readFileSync(from, "utf8").replace(/\r\n/g, "\n")
  .replace(/\n\n\(Yes, this file also applies[\s\S]*?\)\s*$/, "");
fs.writeFileSync(to, text.trimEnd() + "\n");
' "$src/AGENTS.md" AGENTS.md

version=$(node -p "require('$src/package.json').version")
commit=$(git -C "$src" rev-parse HEAD 2>/dev/null || echo unknown)
node -e '
const fs = require("fs");
const [, file, version, commit] = process.argv;
const text = fs.readFileSync(file, "utf8")
  .replace(/^- Version: .*$/m, `- Version: ${version} (commit ${commit})`);
fs.writeFileSync(file, text);
' THIRD_PARTY_NOTICES.md "$version" "$commit"

node scripts/check-ponytail-sync.js
echo "Ponytail updated to $version ($commit)."
