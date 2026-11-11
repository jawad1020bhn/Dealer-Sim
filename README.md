# Dealer-Sim

## Agent setup

This repo uses [Ponytail](https://github.com/DietrichGebert/ponytail) — a skill that makes coding agents favour the smallest change that fully solves the task. Everything that belongs to the skill lives in **one folder: `skills/`**.

```
skills/
  ponytail/SKILL.md          lazy senior dev mode  (/ponytail [lite|full|ultra|off])
  ponytail-review/SKILL.md   /ponytail-review   review a change
  ponytail-audit/SKILL.md    /ponytail-audit    review the whole repo
  ponytail-debt/SKILL.md     /ponytail-debt     collect the shortcut: comments
  ponytail-gain/SKILL.md     /ponytail-gain     measured impact scoreboard
  ponytail-help/SKILL.md     /ponytail-help     reference card
```

Point an agent at `skills/ponytail/SKILL.md`, or at a single command's file, and it has everything it needs.

| Path | What it is |
| --- | --- |
| `skills/` | The skill. The one folder to call when working on this project. |
| `AGENTS.md` | The compact ruleset, the same rules in one page. Read automatically by Codex, Copilot, OpenCode, Jules, Zed, Amp and most other harnesses, so the rules hold even when nobody invokes the skill. |
| `CLAUDE.md` | One line, `@AGENTS.md`, so Claude Code loads the same ruleset. |
| `.claude/skills` | A symlink to `skills/`, so Claude Code and other hosts that only scan `.claude/skills` still find the one folder. No second copy. |
| `scripts/check-ponytail-sync.js` | Verifies `skills/` and `AGENTS.md` still hold the ten load-bearing rules, keeps the link honest, and checks any host rule copy that exists. |
| `scripts/update-ponytail.sh` | Re-vendors from upstream, drops the one upstream paragraph that only applies to ponytail's own repo, re-pins the notice, runs the check. |
| `tests/` | 10 `node:test` cases covering both scripts. No dependencies. |
| `.github/workflows/ponytail-sync.yml` | Runs the check and the tests on every push and pull request. |

```bash
node scripts/check-ponytail-sync.js   # skills + AGENTS.md + link + 10 rules
node --test                            # 10 cases
```

### Hosts that want their own rule path

Only `AGENTS.md` and the link are provided by default. If a host needs a rule file at a fixed path, write it there and the check will keep it honest; the update script refreshes it too:

```bash
cp AGENTS.md .cursor/rules/ponytail.mdc        # or .windsurf/rules/, .clinerules/,
                                               # .agents/rules/, .qoder/rules/,
                                               # .kiro/steering/, .github/copilot-instructions.md
```

Cursor's `.mdc` and Kiro's steering file need their frontmatter (`description`/`globs`/`alwaysApply`, or `title`/`inclusion`) above that body. Those copies are opt-in so the repo keeps one folder rather than eight copies of the same text.

This is the instruction-tier install: the rules and the six skills work, but there is no lifecycle hook, so the level does not persist between sessions and there is no statusline band. For that, install the full plugin in your agent (`/plugin marketplace add DietrichGebert/ponytail`, then `/plugin install ponytail@ponytail`).

### Updating

```bash
scripts/update-ponytail.sh
```

It clones upstream, copies `AGENTS.md` and the six skills into `skills/`, strips the upstream aside, re-pins the version and commit in `THIRD_PARTY_NOTICES.md`, and runs the check. `PONYTAIL_SRC=/path/to/checkout scripts/update-ponytail.sh` uses an existing clone instead of the network: that is also how you roll back to an older tag. Needs `git`, `node` and `bash`; no npm dependencies anywhere in this repo.

Installed at v5.3.3 (`96608e0`). MIT licensed, see `THIRD_PARTY_NOTICES.md`.
