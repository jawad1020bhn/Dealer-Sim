# Dealer-Sim

## Agent setup

This repo uses [Ponytail](https://github.com/DietrichGebert/ponytail) — a skill that makes coding agents favour the smallest change that fully solves the task.

| Path | What it is |
| --- | --- |
| `AGENTS.md` | The always-on ruleset. Read automatically by Codex, GitHub Copilot, OpenCode, Jules, Zed, Amp, Cursor-style agents and most other harnesses. |
| `.claude/skills/ponytail/SKILL.md` | The skill itself: lazy senior dev mode (`/ponytail [lite\|full\|ultra\|off]`). |
| `.claude/skills/ponytail-review/SKILL.md` | `/ponytail-review` — review a change for bugs, security, load, missing tests, speed, and what to cut. |
| `.claude/skills/ponytail-audit/SKILL.md` | `/ponytail-audit` — the same check across the whole repo, most important first. |
| `.claude/skills/ponytail-debt/SKILL.md` | `/ponytail-debt` — collect the `shortcut:` comments into a debt ledger. |
| `.claude/skills/ponytail-gain/SKILL.md` | `/ponytail-gain` — show the measured impact scoreboard. |
| `.claude/skills/ponytail-help/SKILL.md` | `/ponytail-help` — quick reference. |
| `CLAUDE.md` | One line, `@AGENTS.md`, so Claude Code loads the same ruleset. |

`.claude/skills/` is the Claude Code project-skill path and is also read by other hosts that discover `SKILL.md` folders (Freebuff, and any agent you point at the directory). Hosts without skill support still get the rules through `AGENTS.md`.

This is the instruction-tier install: the rules and the six skills work, but there is no lifecycle hook, so the level does not persist between sessions and there is no statusline band. For that, install the full plugin in your agent (`/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`). If a host-specific rule file is wanted as well (`.cursor/rules/ponytail.mdc`, `.clinerules/ponytail.md`, `.github/copilot-instructions.md`, `.kiro/steering/ponytail.md`), copy it from upstream — all of them are the same ruleset in that host's format.

### Updating

The files are vendored verbatim from upstream, so an update is the same copy again:

```bash
git clone --depth 1 https://github.com/DietrichGebert/ponytail.git /tmp/ponytail
cp /tmp/ponytail/AGENTS.md AGENTS.md
for s in ponytail ponytail-review ponytail-audit ponytail-debt ponytail-gain ponytail-help; do
  mkdir -p ".claude/skills/$s" && cp "/tmp/ponytail/skills/$s/SKILL.md" ".claude/skills/$s/SKILL.md"
done
```

Then bump the version and commit hash in `THIRD_PARTY_NOTICES.md`. Installed at v5.3.3. MIT licensed, see that file.
