// Tests for scripts/check-ponytail-sync.js. Each case stages a throwaway copy of the
// vendored files, breaks one thing, and asserts the check's exit code and message.
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
const STAGED = [
  'AGENTS.md',
  'scripts',
  '.claude',
  '.cursor',
  '.windsurf',
  '.clinerules',
  '.agents',
  '.qoder',
  '.kiro',
  '.github',
];

function stage() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ponytail-sync-'));
  for (const rel of STAGED) fs.cpSync(path.join(repo, rel), path.join(dir, rel), { recursive: true });
  return dir;
}

function run(dir) {
  return spawnSync(process.execPath, [path.join(dir, 'scripts/check-ponytail-sync.js')], { encoding: 'utf8' });
}

function append(dir, rel, text) {
  const file = path.join(dir, rel);
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8') + text);
}

test('passes on the committed files', () => {
  const dir = stage();
  const result = run(dir);
  assert.strictEqual(result.status, 0, result.stderr);
  assert.match(result.stdout, /Rule copies match AGENTS\.md/);
});

test('fails when a host rule copy drifts', () => {
  const dir = stage();
  append(dir, '.windsurf/rules/ponytail.md', '\nextra rule\n');
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /\.windsurf\/rules\/ponytail\.md drifted from AGENTS\.md/);
});

test('fails when the frontmatter-bearing copies drift', () => {
  const dir = stage();
  append(dir, '.cursor/rules/ponytail.mdc', '\nextra rule\n');
  assert.strictEqual(run(dir).status, 1);
});

test('fails when a rule invariant is missing from the skill', () => {
  const dir = stage();
  const file = path.join(dir, '.claude/skills/ponytail/SKILL.md');
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replaceAll('accessibility', 'a11y'));
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /missing rule invariant: "accessibility"/);
});

test("fails when upstream's ponytail-repo aside is back in AGENTS.md", () => {
  const dir = stage();
  append(dir, 'AGENTS.md', '\n\n(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)\n');
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /ponytail-repo aside/);
});
