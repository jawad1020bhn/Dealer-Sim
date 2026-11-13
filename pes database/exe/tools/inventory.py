"""Sections, imports, exports and strings of PES2017.exe.

    python3 inventory.py <PES2017.exe> <output folder>

Sections, imports and exports come from Rizin through REA (iSj, iij, iEj);
the strings are read here from the two data sections.

Writes sections.tsv, imports.tsv, exports.tsv, strings.tsv and the REA Evidence
ids of the three commands to evidence.tsv.

imports.tsv has the value stored in each import slot in the file. The slots
are in a read-only section, so the decompiler replaces a call through a slot
by a call to that value; assemble.py turns the value back into the name."""
import json
import math
import os
import re
import sys
from collections import Counter

import rea
from layout import SECTIONS, load, off, u32

DATA = ('.xtls', '.code')
ASCII = re.compile(rb'(?:[\x20-\x7e]|[\xc2-\xf4][\x80-\xbf]{1,3}){4,}\x00')
UTF16 = re.compile(rb'(?:[\x20-\x7e]\x00){4,}\x00\x00')


def strings(d):
    """-> [(address, kind, text)] NUL-terminated, 4 characters or more"""
    rows = []
    for n, v, f, s in SECTIONS:
        if n not in DATA:
            continue
        b = d[f:f + s]
        for m in ASCII.finditer(b):
            raw = m.group()[:-1]
            try:
                t = raw.decode('utf-8')
            except UnicodeDecodeError:
                continue
            rows.append((v + m.start(), 'utf8' if len(t) != len(raw) else 'ascii', t))
        for m in UTF16.finditer(b):
            if m.start() % 2 == 0:
                rows.append((v + m.start(), 'utf16', m.group()[:-2].decode('utf-16le')))
    rows.sort()
    return rows


def main(exe, outdir):
    d = load(exe)
    os.makedirs(outdir, exist_ok=True)
    ev = open(os.path.join(outdir, 'evidence.tsv'), 'w')

    def ask(cmd):
        out, err, rec = rea.run(exe, cmd)
        assert rea.status(rec) == 'ok', (cmd, rea.status(rec))
        ev.write('inventory\t%s\t%s\t%s\n' % (cmd, rec['evidence_id'], rea.status(rec)))
        return json.loads(out)

    secs = ask('iSj')
    with open(os.path.join(outdir, 'sections.tsv'), 'w') as f:
        f.write('name\taddress\tfile_offset\tfile_size\tperm\tzero_bytes_pct\tentropy_bits\twhat\n')
        what = {'.srdata': 'original code, blanked (padding left)', '.sdata': 'original code tail, blanked',
                '.xtls': 'read-only data: strings, vtables, constants', '.code': 'writable data',
                '.idata': 'data', '.trace': 'the code that runs', '.xcode': 'intact copy of .sdata, runs',
                '.link': 'entry point stub', '.xtext': 'import table', '.data': 'encrypted',
                '.edata': 'exports and resources', '.text': 'stub', '.data1': 'stub', '.reloc': 'stub'}
        for s in secs:
            b = d[s['paddr']:s['paddr'] + s['size']]
            c = Counter(b)
            ent = -sum(x / len(b) * math.log2(x / len(b)) for x in c.values()) if b else 0
            f.write('%s\t0x%08x\t0x%08x\t%d\t%s\t%.1f\t%.2f\t%s\n' % (
                s['name'], s['vaddr'], s['paddr'], s['size'], s['perm'],
                100 * c[0] / max(1, len(b)), ent, what.get(s['name'], '')))
        assert [(s['name'], s['vaddr'], s['paddr']) for s in secs] == [(n, v, o) for n, v, o, _ in SECTIONS]

    imps = ask('iij')
    with open(os.path.join(outdir, 'imports.tsv'), 'w') as f:
        f.write('slot\tvalue_in_file\tdll\tname\n')
        for i in imps:
            f.write('0x%08x\t0x%08x\t%s\t%s\n' % (i['plt'], u32(d, off(i['plt'])), i['libname'], i['name']))

    exps = ask('iEj')
    with open(os.path.join(outdir, 'exports.tsv'), 'w') as f:
        f.write('address\tname\tmangled\n')
        for e in exps:
            f.write('0x%08x\t%s\t%s\n' % (e['vaddr'], e['name'], e.get('realname', '')))

    st = strings(d)
    with open(os.path.join(outdir, 'strings.tsv'), 'w') as f:
        f.write('address\tkind\ttext\n')
        for a, k, t in st:
            f.write('0x%08x\t%s\t%s\n' % (a, k, t.replace('\\', '\\\\').replace('\t', '\\t')
                                               .replace('\n', '\\n').replace('\r', '\\r')))
    print('sections %d, imports %d, exports %d, strings %d' % (len(secs), len(imps), len(exps), len(st)))


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
