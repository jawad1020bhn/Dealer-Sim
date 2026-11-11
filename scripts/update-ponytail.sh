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
  mkdir -p ".claude/skills/$s"
  cp "$src/skills/$s/SKILL.md" ".claude/skills/$s/SKILL.md"
done

cp "$src/.cursor/rules/ponytail.mdc" .cursor/rules/ponytail.mdc
cp "$src/.windsurf/rules/ponytail.md" .windsurf/rules/ponytail.md
cp "$src/.clinerules/ponytail.md" .clinerules/ponytail.md
cp "$src/.agents/rules/ponytail.md" .agents/rules/ponytail.md
cp "$src/.qoder/rules/ponytail.md" .qoder/rules/ponytail.md
cp "$src/.kiro/steering/ponytail.md" .kiro/steering/ponytail.md
cp "$src/.github/copilot-instructions.md" .github/copilot-instructions.md

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
commit=$(git -C "$src" rev-parse HEAD)
node -e '
const fs = require("fs");
const [, file, version, commit] = process.argv;
const text = fs.readFileSync(file, "utf8")
  .replace(/^- Version: .*$/m, `- Version: ${version} (commit ${commit})`);
fs.writeFileSync(file, text);
' THIRD_PARTY_NOTICES.md "$version" "$commit"

node scripts/check-ponytail-sync.js
echo "Ponytail updated to $version ($commit)."
