# Dealer-Sim

## Agent setup

This repo uses [Ponytail](https://github.com/DietrichGebert/ponytail) — a skill that makes coding agents favour the smallest change that fully solves the task.

| Path | What it is |
| --- | --- |
| `AGENTS.md` | The always-on ruleset. Read automatically by Codex, GitHub Copilot, OpenCode, Jules, Zed, Amp and most other harnesses. |
| `CLAUDE.md` | One line, `@AGENTS.md`, so Claude Code loads the same ruleset. |
| `.claude/skills/ponytail/SKILL.md` | The skill itself: lazy senior dev mode (`/ponytail [lite\|full\|ultra\|off]`). |
| `.claude/skills/ponytail-review/SKILL.md` | `/ponytail-review` — review a change for bugs, security, load, missing tests, speed, and what to cut. |
| `.claude/skills/ponytail-audit/SKILL.md` | `/ponytail-audit` — the same check across the whole repo, most important first. |
| `.claude/skills/ponytail-debt/SKILL.md` | `/ponytail-debt` — collect the `shortcut:` comments into a debt ledger. |
| `.claude/skills/ponytail-gain/SKILL.md` | `/ponytail-gain` — show the measured impact scoreboard. |
| `.claude/skills/ponytail-help/SKILL.md` | `/ponytail-help` — quick reference. |
| `.cursor/rules/ponytail.mdc` | Same ruleset as a Cursor rule. |
| `.clinerules/ponytail.md` | Cline. |
| `.windsurf/rules/ponytail.md` | Windsurf. |
| `.kiro/steering/ponytail.md` | Kiro steering file. |
| `.qoder/rules/ponytail.md` | Qoder. |
| `.agents/rules/ponytail.md` | Antigravity and other `.agents/rules` readers. |
| `.github/copilot-instructions.md` | GitHub Copilot Chat in the editors. |
| `scripts/check-ponytail-sync.js` | Verifies every rule file still matches `AGENTS.md`. |

`.claude/skills/` is the Claude Code project-skill path and is also read by other hosts that discover `SKILL.md` folders (Freebuff, and any agent you point at the directory). Hosts without skill support get the rules from whichever rule file above they read. The seven rule files are copies of the same text, so `node scripts/check-ponytail-sync.js` is what catches drift; it needs a checkout with `node` on `PATH`.

This is the instruction-tier install: the rules and the six skills work, but there is no lifecycle hook, so the level does not persist between sessions and there is no statusline band. For that, install the full plugin in your agent (`/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`).

Hosts that scan a root `skills/` directory instead of `.claude/skills/` need one copy: `mkdir -p skills && cp -r .claude/skills/* skills/`. Not done here, because it would be a second copy of the same six files to keep in sync.

### Updating

The files are vendored verbatim from upstream, so an update is the same copy again:

```bash
git clone --depth 1 https://github.com/DietrichGebert/ponytail.git /tmp/ponytail
cp /tmp/ponytail/AGENTS.md .
for s in ponytail ponytail-review ponytail-audit ponytail-debt ponytail-gain ponytail-help; do
  mkdir -p ".claude/skills/$s" && cp "/tmp/ponytail/skills/$s/SKILL.md" ".claude/skills/$s/SKILL.md"
done
cp /tmp/ponytail/.cursor/rules/ponytail.mdc .cursor/rules/
cp /tmp/ponytail/.windsurf/rules/ponytail.md .windsurf/rules/
cp /tmp/ponytail/.clinerules/ponytail.md .clinerules/
cp /tmp/ponytail/.agents/rules/ponytail.md .agents/rules/
cp /tmp/ponytail/.qoder/rules/ponytail.md .qoder/rules/
cp /tmp/ponytail/.kiro/steering/ponytail.md .kiro/steering/
cp /tmp/ponytail/.github/copilot-instructions.md .github/
node scripts/check-ponytail-sync.js
```

Then bump the version and commit hash in `THIRD_PARTY_NOTICES.md`. Installed at v5.3.3. MIT licensed, see that file.
