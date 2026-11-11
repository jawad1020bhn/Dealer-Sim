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

const stage = require('./stage');

function run(dir) {
  return spawnSync(process.execPath, [path.join(dir, 'scripts/check-ponytail-sync.js')], { encoding: 'utf8' });
}

function write(dir, rel, text, append = false) {
  const file = path.join(dir, rel);
  fs.mkdirSync(path.dirname(file), { recursive: true });
  if (append) fs.appendFileSync(file, text);
  else fs.writeFileSync(file, text);
}

test('passes on the committed files', () => {
  const result = run(stage());
  assert.strictEqual(result.status, 0, result.stderr);
  assert.match(result.stdout, /skills\/ is intact/);
  assert.match(result.stdout, /0 host rule copies/);
});

test('fails when an optional host rule copy drifts', () => {
  const dir = stage();
  write(dir, '.windsurf/rules/ponytail.md', fs.readFileSync(path.join(dir, 'AGENTS.md'), 'utf8') + '\nextra rule\n');
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /\.windsurf\/rules\/ponytail\.md drifted from AGENTS\.md/);
});

test('a matching optional host copy is accepted', () => {
  const dir = stage();
  write(dir, '.github/copilot-instructions.md', fs.readFileSync(path.join(dir, 'AGENTS.md'), 'utf8'));
  const result = run(dir);
  assert.strictEqual(result.status, 0, result.stderr);
  assert.match(result.stdout, /1 host rule copy match/);
});

test('fails when a rule invariant is missing from the skill', () => {
  const dir = stage();
  const file = path.join(dir, 'skills/ponytail/SKILL.md');
  fs.writeFileSync(file, fs.readFileSync(file, 'utf8').replaceAll('accessibility', 'a11y'));
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /missing rule invariant: "accessibility"/);
});

test('fails when skills/ is not reachable through .claude/skills', () => {
  const dir = stage();
  fs.rmSync(path.join(dir, '.claude'), { recursive: true });
  fs.mkdirSync(path.join(dir, '.claude/skills'), { recursive: true }); // a copy, not a link
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /does not resolve to \.\/skills/);
});

test("fails when upstream's ponytail-repo aside is back in AGENTS.md", () => {
  const dir = stage();
  write(dir, 'AGENTS.md', '\n\n(Yes, this file also applies to agents working on the ponytail repo itself. Especially to them.)\n', true);
  const result = run(dir);
  assert.strictEqual(result.status, 1);
  assert.match(result.stderr, /ponytail-repo aside/);
});
