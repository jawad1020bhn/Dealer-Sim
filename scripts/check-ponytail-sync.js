#!/usr/bin/env node
// Adapted from DietrichGebert/ponytail@96608e0 scripts/check-rule-copies.js (MIT).
// Fails when a host rule file drifts from AGENTS.md, or when a load-bearing rule
// disappears from AGENTS.md or the ponytail SKILL.md.
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
// The trailing aside is ponytail-repo-only, so the host copies leave it out.
const canonical = agents.replace(/\n\n\(Yes, this file also applies[\s\S]*?\)$/, '').trim();

// Compact copies: same body as AGENTS.md, host-specific frontmatter stripped.
const copies = [
  ['.cursor/rules/ponytail.mdc', stripFrontmatter],
  ['.windsurf/rules/ponytail.md', text => text.trim()],
  ['.clinerules/ponytail.md', text => text.trim()],
  ['.agents/rules/ponytail.md', text => text.trim()],
  ['.qoder/rules/ponytail.md', text => text.trim()],
  ['.github/copilot-instructions.md', text => text.trim()],
  ['.kiro/steering/ponytail.md', stripFrontmatter],
];

let failed = false;

for (const [relPath, normalize] of copies) {
  if (normalize(read(relPath)) !== canonical) {
    console.error(`${relPath} drifted from AGENTS.md`);
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

for (const [label, text] of [['.claude/skills/ponytail/SKILL.md', read('.claude/skills/ponytail/SKILL.md')], ['AGENTS.md', agents]]) {
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

console.log(`Rule copies match AGENTS.md; ${INVARIANTS.length} rule invariants present in SKILL.md and AGENTS.md.`);
