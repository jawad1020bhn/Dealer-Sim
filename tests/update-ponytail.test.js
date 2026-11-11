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
const SKILLS = ['ponytail', 'ponytail-review', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help'];
const UPSTREAM_ASIDE =
  '\n\n(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)\n';

// The vendored files double as the upstream fixture: the layout under skills/ is what
// the script copies from.
function fakeUpstream() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ponytail-upstream-'));
  const put = (from, to) => {
    fs.mkdirSync(path.dirname(to), { recursive: true });
    fs.copyFileSync(from, to);
  };
  for (const s of SKILLS) put(path.join(repo, 'skills', s, 'SKILL.md'), path.join(dir, 'skills', s, 'SKILL.md'));
  put(path.join(repo, 'AGENTS.md'), path.join(dir, 'AGENTS.md'));
  // Upstream ships the aside; the script exists to drop it.
  fs.writeFileSync(path.join(dir, 'AGENTS.md'), fs.readFileSync(path.join(dir, 'AGENTS.md'), 'utf8').trimEnd() + UPSTREAM_ASIDE);
  fs.writeFileSync(path.join(dir, 'package.json'), JSON.stringify({ name: 'fixture', version: '9.9.9' }));
  return dir;
}

const stageRepo = require('./stage');

function runUpdate(dir, upstream, env = {}) {
  return spawnSync('bash', [path.join(dir, 'scripts/update-ponytail.sh')], {
    cwd: dir,
    encoding: 'utf8',
    env: { ...process.env, PONYTAIL_SRC: upstream, ...env },
  });
}

test('re-vendors into skills/ and strips the aside', () => {
  const dir = stageRepo();
  const result = runUpdate(dir, fakeUpstream());
  assert.strictEqual(result.status, 0, result.stderr);

  for (const s of SKILLS) assert.ok(fs.existsSync(path.join(dir, 'skills', s, 'SKILL.md')), `missing ${s}`);

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

test('refreshes an existing host copy and leaves a missing one missing', () => {
  const dir = stageRepo();
  const upstream = fakeUpstream();
  // Host copies upstream carry the rule body without the aside.
  fs.mkdirSync(path.join(upstream, '.github'), { recursive: true });
  fs.writeFileSync(path.join(upstream, '.github/copilot-instructions.md'),
    fs.readFileSync(path.join(repo, 'AGENTS.md'), 'utf8'));
  fs.mkdirSync(path.join(dir, '.github'), { recursive: true });
  fs.writeFileSync(path.join(dir, '.github/copilot-instructions.md'), 'stale\n');

  assert.strictEqual(runUpdate(dir, upstream).status, 0);
  assert.ok(fs.readFileSync(path.join(dir, '.github/copilot-instructions.md'), 'utf8').startsWith('# Ponytail'));
  assert.ok(!fs.existsSync(path.join(dir, '.windsurf')), 'should not create adapters that were absent');
});

test('fails loudly when the upstream source is not there', () => {
  const result = runUpdate(stageRepo(), path.join(os.tmpdir(), 'ponytail-does-not-exist'));
  assert.notStrictEqual(result.status, 0);
});
