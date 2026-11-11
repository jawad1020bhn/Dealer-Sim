#!/usr/bin/env node
// Adapted from DietrichGebert/ponytail@96608e0 scripts/check-rule-copies.js (MIT).
// Guards the vendored install:
//   - AGENTS.md is the canonical rule text and carries no upstream repo-specific aside
//   - any host rule file that exists still matches AGENTS.md
//   - the ten load-bearing rules are present in AGENTS.md and skills/ponytail/SKILL.md
//   - .claude/skills mirrors skills/ byte for byte, as real files (skill hosts skip symlinks)
//
//   node scripts/check-ponytail-sync.js
'use strict';

const fs = require('fs');
const path = require('path');

const root = path.join(__dirname, '..');

function read(relPath) {
  return fs.readFileSync(path.join(root, relPath), 'utf8').replace(/\r\n/g, '\n').trim();
}

function stripFrontmatter(text) {
  return text.replace(/^---\n[\s\S]*?\n---\n*/, '').trim();
}

const agents = read('AGENTS.md');

let failed = false;

// Upstream's last paragraph only makes sense in ponytail's own repo; scripts/update-ponytail.sh
// strips it. If it is back, the rule text was copied without the strip step.
if (agents.includes('agents working on the ponytail repo')) {
  console.error('AGENTS.md carries upstream\'s ponytail-repo aside; run scripts/update-ponytail.sh.');
  failed = true;
}

// Host rule files are optional: the install keeps one folder, and a host that needs its own
// path gets a copy. Any copy that exists must equal AGENTS.md, frontmatter aside.
const optionalCopies = [
  ['.cursor/rules/ponytail.mdc', stripFrontmatter],
  ['.windsurf/rules/ponytail.md', text => text.trim()],
  ['.clinerules/ponytail.md', text => text.trim()],
  ['.agents/rules/ponytail.md', text => text.trim()],
  ['.qoder/rules/ponytail.md', text => text.trim()],
  ['.github/copilot-instructions.md', text => text.trim()],
  ['.kiro/steering/ponytail.md', stripFrontmatter],
];

let copies = 0;
for (const [relPath, normalize] of optionalCopies) {
  if (!fs.existsSync(path.join(root, relPath))) continue;
  copies += 1;
  if (normalize(read(relPath)) !== agents) {
    console.error(`${relPath} drifted from AGENTS.md`);
    failed = true;
  }
}

// Skill discovery in Claude Code and friends walks .claude/skills and skips symlinks, so the
// host path must hold real files. They are a mirror of skills/, and this is what keeps them equal.
const SKILLS = ['ponytail', 'ponytail-review', 'ponytail-audit', 'ponytail-debt', 'ponytail-gain', 'ponytail-help'];
const hostRoot = path.join(root, '.claude/skills');
if (fs.existsSync(hostRoot) && fs.lstatSync(hostRoot).isSymbolicLink()) {
  console.error('.claude/skills is a symlink; skill discovery skips it. Run scripts/update-ponytail.sh.');
  failed = true;
}
for (const name of SKILLS) {
  const canonicalPath = path.join('skills', name, 'SKILL.md');
  const hostPath = path.join('.claude/skills', name, 'SKILL.md');
  if (!fs.existsSync(path.join(root, hostPath))) {
    console.error(`${hostPath} is missing; run scripts/update-ponytail.sh.`);
    failed = true;
  } else if (read(hostPath) !== read(canonicalPath)) {
    console.error(`${hostPath} drifted from ${canonicalPath}`);
    failed = true;
  }
}

// SKILL.md is the runtime source of truth and is longer than the compact body,
// so it cannot be byte-compared. This is a canary: the rules that carry the
// behavior must survive verbatim in both files.
const INVARIANTS = [
  'in this codebase', // ladder rung: reuse what already exists
  'grep every caller', // root-cause bug fix
  'never about the change itself', // scope: callers, tests and fixtures
  'shortcut: <the limit>, <when to upgrade>', // shortcut marker comment
  'correct on edge cases', // robust-variant rule
  'Lazy code without its check is unfinished', // test reflex
  // the "never cut" carve-outs: pin each so a reword cannot silently drop one
  'validation at trust boundaries',
  'prevents data loss',
  'security',
  'accessibility',
];

for (const [label, text] of [['skills/ponytail/SKILL.md', read('skills/ponytail/SKILL.md')], ['AGENTS.md', agents]]) {
  for (const phrase of INVARIANTS) {
    if (!text.includes(phrase)) {
      console.error(`${label} is missing rule invariant: "${phrase}"`);
      failed = true;
    }
  }
}

if (failed) {
  console.error('Re-copy the rule files from upstream so the shared rules match.');
  process.exit(1);
}

console.log(
  `skills/ is intact; ${copies} host rule cop${copies === 1 ? 'y' : 'ies'} match AGENTS.md; ` +
    `${SKILLS.length} skills mirrored to .claude/skills; ${INVARIANTS.length} rule invariants present.`
);
