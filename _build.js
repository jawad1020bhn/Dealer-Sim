'use strict';
/* Rebuilds the <script> block of NIGHTLEDGER.html from _extracted.js, and checks it in CI-style.
   _extracted.js *is* the whole client JS (engine + presentation layer + tail); the HTML is a
   build artefact. Editing the HTML directly is how the two copies drifted before.
   Run: node _build.js | node _build.js --check */
const fs = require('fs');
const html = fs.readFileSync('NIGHTLEDGER.html', 'utf8');
const js = fs.readFileSync('_extracted.js', 'utf8');
const i = html.indexOf('<script>') + 8, j = html.indexOf('</script>', i);
const out = html.slice(0, i) + js + html.slice(j);
if (process.argv.includes('--check')) {
  const same = out === html;
  console.log(same ? 'build: up to date (' + js.length + ' chars of JS)' : 'build: STALE — run node _build.js');
  process.exit(same ? 0 : 1);
}
fs.writeFileSync('NIGHTLEDGER.html', out);
console.log('rebuilt NIGHTLEDGER.html ·', out.length, 'chars · JS', js.length);
