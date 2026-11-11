// Tests for scripts/update-ponytail.sh against a fixture "upstream" directory
// (PONYTAIL_SRC), so no network and no real upstream clone are needed.
//
//   node --test
'use strict';

const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const os = require('os');
const path = require('path');
const { spawnSync } = require('child_process');

const repo = path.join(__dirname, '..');
const UPSTREAM_ASIDE =
  '\n\n(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)\n';

// The vendored files double as the upstream fixture: the layout under skills/ and the
// host directories is what the script copies from.
function fakeUpstream() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ponytail-upstream-'));
  const put = (from, to) => {
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.copyFileSync(from, to);
  };
  for (const s of ['ponytail', 'ponytail-review', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help']) {
    put(path.join(repo, '.claude/skills', s, 'SKILL.md'), path.join(dir, 'skills', s, 'SKILL.md'));
  }
  for (const rel of ['AGENTS.md', '.cursor/rules/ponytail.mdc', '.windsurf/rules/ponytail.md', '.clinerules/ponytail.md',
    '.agents/rules/ponytail.md', '.qoder/rules/ponytail.md', '.kiro/steering/ponytail.md', '.github/copilot-instructions.md']) {
    put(path.join(repo, rel), path.join(dir, rel));
  }
  // Upstream ships the aside; the script exists to drop it.
  fs.writeFileSync(path.join(dir, 'AGENTS.md'), fs.readFileSync(path.join(dir, 'AGENTS.md'), 'utf8').trimEnd() + UPSTREAM_ASIDE);
  fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify({ name: 'fixture', version: '9.9.9' }));
  return dir;
}

// A throwaway copy of this repo, so the script's writes stay out of the working tree.
function stageRepo() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ponytail-repo-'));
  for (const rel of ['AGENTS.md', 'THIRD_PARTY_NOTICES.md', 'scripts', '.claude', '.cursor', '.windsurf',
    '.clinerules', '.agents', '.qoder', '.kiro', '.github']) {
    fs.cpSync(path.join(repo, rel), path.join(dir, rel), { recursive: true });
  }
  return dir;
}

function runUpdate(dir, upstream) {
  return spawnSync('bash', [path.join(dir, 'scripts/update-ponytail.sh')], {
    cwd: dir,
    encoding: 'utf8',
    env: { ...process.env, PONYTAIL_SRC: upstream },
  });
}

test('re-vendors from a fixture upstream and strips the aside', () => {
  const dir = stageRepo();
  const result = runUpdate(dir, fakeUpstream());
  assert.strictEqual(result.status, 0, result.stderr);

  const agents = fs.readFileSync(path.join(dir, 'AGENTS.md'), 'utf8');
  assert.ok(!agents.includes('agents working on the ponytail repo'), 'aside still present');
  assert.ok(agents.endsWith('anything the user asked for.\n'), 'AGENTS.md not trimmed to the rule body');

  const notice = fs.readFileSync(path.join(dir, 'THIRD_PARTY_NOTICES.md'), 'utf8');
  assert.match(notice, /^- Version: 9\.9\.9 \(commit unknown\)$/m);
});

test('the update leaves a repo the check accepts', () => {
  const dir = stageRepo();
  assert.strictEqual(runUpdate(dir, fakeUpstream()).status, 0);
  const check = spawnSync(process.execPath, [path.join(dir, 'scripts/check-ponytail-sync.js')], { encoding: 'utf8' });
  assert.strictEqual(check.status, 0, check.stderr);
});

test('fails loudly when the upstream source is not there', () => {
  const result = runUpdate(stageRepo(), path.join(os.tmpdir(), 'ponytail-does-not-exist'));
  assert.notStrictEqual(result.status, 0);
});
