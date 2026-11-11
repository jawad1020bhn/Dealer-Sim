// Throwaway copy of the vendored install, so tests can break it without touching the repo.
// Not a test file: node --test only picks up *.test.js here.
'use strict';

const fs = require('fs');
const os = require('os');
const path = require('path');

const repo = path.join(__dirname, '..');
const STAGED = ['AGENTS.md', 'THIRD_PARTY_NOTICES.md', 'skills', '.claude', 'scripts'];

module.exports = function stage() {
  const dir = fs.mkdtempSync(path.join(os.tmpdir(), 'ponytail-stage-'));
  for (const rel of STAGED) fs.cpSync(path.join(repo, rel), path.join(dir, rel), { recursive: true });

  // fs.cpSync copies a directory symlink as a directory. Rebuild .claude/skills exactly as
  // the repo has it: a link when it is a link, a copy when it is a copy.
  const from = path.join(repo, '.claude', 'skills');
  const to = path.join(dir, '.claude', 'skills');
  fs.rmSync(to, { recursive: true, force: true });
  if (fs.lstatSync(from).isSymbolicLink()) fs.symlinkSync(fs.readlinkSync(from), to, 'dir');
  else fs.cpSync(from, to, { recursive: true });

  return dir;
};
