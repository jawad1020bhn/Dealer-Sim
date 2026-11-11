# Dealer-Sim

## Agent setup

This repo uses [Ponytail](https://github.com/DietrichGebert/ponytail) — a skill that makes coding agents favour the smallest change that fully solves the task.

| Path | What it is |
| --- | --- |
| `AGENTS.md` | The always-on ruleset, the single source of truth for the rule text. Read automatically by Codex, GitHub Copilot, OpenCode, Jules, Zed, Amp and most other harnesses. |
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
| `scripts/check-ponytail-sync.js` | Fails if a rule copy drifts from `AGENTS.md`. |
| `scripts/update-ponytail.sh` | Re-vendors everything from upstream and re-pins the notice. |
| `tests/` | Proves the check fails when it should, and that the update script vendors cleanly. |
| `.github/workflows/ponytail-sync.yml` | Runs both on every push and pull request. |

`.claude/skills/` is the Claude Code project-skill path and is also read by other hosts that discover `SKILL.md` folders (Freebuff, and any agent you point at the directory). Hosts without skill support get the rules from whichever rule file above they read. The seven rule files are copies of the same text as `AGENTS.md`, so run the check after touching any of them:

```bash
node scripts/check-ponytail-sync.js   # rule copies + 10 load-bearing rules
node --test                            # the check's own tests
```

This is the instruction-tier install: the rules and the six skills work, but there is no lifecycle hook, so the level does not persist between sessions and there is no statusline band. For that, install the full plugin in your agent (`/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`).

Hosts that scan a root `skills/` directory instead of `.claude/skills/` need one copy: `mkdir -p skills && cp -r .claude/skills/* skills/`. Not done here, because it would be a second copy of the same six files to keep in sync.

### Updating

```bash
scripts/update-ponytail.sh
```

It clones upstream, copies `AGENTS.md`, the six skills and the seven rule files, drops the one upstream paragraph that only applies to ponytail's own repo, re-pins the version and commit in `THIRD_PARTY_NOTICES.md`, and runs the check. `PONYTAIL_SRC=/path/to/checkout scripts/update-ponytail.sh` uses an existing clone instead of hitting the network: that is also how you roll back to an older tag. Needs `git`, `node` and `bash`; no npm dependencies anywhere in this repo.

Installed at v5.3.3 (`96608e0`). MIT licensed, see `THIRD_PARTY_NOTICES.md`.
