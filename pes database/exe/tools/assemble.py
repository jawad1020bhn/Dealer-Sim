"""Build the output files from the raw batches of decompile.py.

    python3 assemble.py <work folder> <functions_found.tsv> <inventory folder> <output folder>

Writes into <output folder>:
  c/XXX.c.xz        the C of every function whose address starts with 0xXXX
                    (1 MB of code per file), in address order
  functions.tsv.xz  one row per start: address, shape, size, blocks, call
                    sites, data pointers, callees, lines of C, status, hint.
                    status: ok / inside fcn_X (not a start: the address lies in
                    that function) / not analysed (Rizin found no function,
                    mostly padding) / not decompiled (the decompiler gave an
                    error) / skipped (over 45 s or over the memory ceiling) /
                    glue, not decompiled (shapes other than function)
  calls.tsv.xz      caller, callee: one row per pair, direct calls only
  string_refs.tsv.xz  function, string address, text
  import_refs.tsv.xz  function, dll, import name
  evidence.tsv      one row per batch: the REA Evidence ids, counts, skipped
  sections.tsv, imports.tsv, exports.tsv, strings.tsv.xz   copies of the inventory

Changes made to the decompiler text, nothing else:
  fcn.02a4c00f, func_0x02a4c00f   ->  fcn_02a4c00f
  (*(code *)0x43d975e)(...)       ->  GetSystemTimeAsFileTime(...)   (imports.tsv: the
                                      value the file stores in the import slot)
  0x1efd1dc                       ->  0x1efd1dc /* "fox::DefaultThreadName" */   (strings.tsv:
                                      a constant that is the address of a string)
  a header line per function.

hint is a guess, not a fact: the first string of the form Class::Method the
function refers to (the game passes such names to its task and log calls)."""
import glob
import json
import lzma
import os
import re
import sys
from collections import defaultdict

FCN = re.compile(r'\b(?:fcn\.|func_0x)([0-9a-f]{8})\b')
IMPCALL = re.compile(r'\(\*\(code \*\)0x([0-9a-f]+)\)')
HEX = re.compile(r'\b0x([0-9a-f]{7,8})\b')
HINT = re.compile(r'^[A-Za-z_]\w*(?:::[A-Za-z_~]\w*)+$')
IDENT = re.compile(r'^[A-Za-z_]\w*$')


def tsv(path):
    op = lzma.open if path.endswith('.xz') else open
    with op(path, 'rt', encoding='utf-8') as f:
        rows = [l.rstrip('\n').split('\t') for l in f]
    return rows[1:]


def xz(path, text):
    with lzma.open(path, 'wt', encoding='utf-8', preset=6) as f:
        f.write(text)


def blocks(out):
    """-> [(address, facts or None, C text)]"""
    res = []
    for part in out.split('FN_BEGIN ')[1:]:
        head, _, rest = part.partition('\n')
        if 'FN_END ' + head not in rest:
            continue
        facts, _, code = rest.partition('FN_CODE\n')
        code = code[:code.rindex('FN_END ' + head)]
        try:
            j = json.loads(facts.strip() or '[]')
        except ValueError:
            j = []
        res.append((int(head, 16), j[0] if j else None, code.strip('\n')))
    return res


def main(work, found, inv, outdir):
    os.makedirs(os.path.join(outdir, 'c'), exist_ok=True)
    starts = {int(r[0], 16): r for r in tsv(found)}
    imports, slots = {}, {}                  # value in file -> name, slot -> (dll, name)
    for slot, val, dll, name in tsv(os.path.join(inv, 'imports.tsv')):
        slots[int(slot, 16)] = (dll, name)
        imports.setdefault(int(val, 16), name if IDENT.match(name) else 'IMPORT("%s!%s")' % (dll, name))
    # the text as written in strings.tsv: backslash, tab and line ends are escaped
    strings = {int(a, 16): t for a, k, t in tsv(os.path.join(inv, 'strings.tsv'))}

    def clean(code):
        code = FCN.sub(lambda m: 'fcn_' + m.group(1), code)
        code = IMPCALL.sub(lambda m: imports.get(int(m.group(1), 16), m.group(0)), code)

        def const(m):
            v = int(m.group(1), 16)
            if v in imports:
                return '&' + imports[v]
            if v in strings:
                return '%s /* "%s" */' % (m.group(0), strings[v][:60].replace('*/', '* /').replace('\n', ' '))
            return m.group(0)
        return HEX.sub(const, code)

    info, files = {}, defaultdict(list)
    calls, srefs, irefs, evid = set(), [], set(), []
    for jf in sorted(glob.glob(os.path.join(work, 'batches', '*.json'))):
        rec = json.load(open(jf))
        out = open(jf[:-5] + '.out', encoding='utf-8', errors='replace').read()
        done = blocks(out)
        for a, facts, code in done:
            if a not in starts:
                continue
            st = 'ok'
            if facts and facts['offset'] != a:
                # no function starts here: Rizin answered for the function this address lies in
                st, facts = 'inside fcn_%08x' % facts['offset'], None
            elif facts is None:
                st = 'not analysed'
            elif not code.strip() or '{' not in code:
                st = 'not decompiled'
            size = nbbs = 0
            callees, hint = set(), ''
            if facts:
                size, nbbs = facts.get('realsz', facts.get('size', 0)), facts.get('nbbs', 0)
                callees = {x['to'] for x in facts.get('callrefs', []) if x['type'] == 'CALL'}
                for t in callees & set(slots):          # call dword [import slot]
                    irefs.add((a,) + slots[t])
                callees -= set(slots)
                for c in sorted(callees):
                    calls.add((a, c))
                seen = set()
                for x in facts.get('datarefs', []):
                    t = x['to'] if isinstance(x, dict) else x
                    if t in slots:
                        irefs.add((a,) + slots[t])
                    if t in strings and t not in seen:
                        seen.add(t)
                        srefs.append((a, t))
                        if not hint and HINT.match(strings[t]):
                            hint = strings[t]
            lines = 0
            if st == 'ok':
                code = clean(code)
                lines = code.count('\n') + 1
                r = starts[a]
                files[a >> 20].append((a, '// ==== fcn_%08x  size %d  blocks %d  call sites %s  data pointers %s%s\n%s\n'
                                       % (a, size, nbbs, r[1], r[2], '  hint ' + hint if hint else '', code)))
            info[a] = (size, nbbs, len(callees), lines, st, hint)
        evid.append((os.path.basename(jf)[:-5], ' '.join(rec['evidence_ids']), len(done), ' '.join(rec['skipped'])))
        for a in rec.get('skipped', []):
            info[int(a, 16)] = (0, 0, 0, 0, 'skipped: over 45 s or over the memory ceiling', '')

    for old in glob.glob(os.path.join(outdir, 'c', '*.c.xz')):
        os.remove(old)
    for k in sorted(files):
        xz(os.path.join(outdir, 'c', '%03x.c.xz' % k), '\n'.join(t for _, t in sorted(files[k])))
    rows = ['address\tshape\tsize\tblocks\tcall_sites\tdata_pointers\tcallees\tc_lines\tstatus\thint']
    for a in sorted(starts):
        r = starts[a]
        i = info.get(a, (0, 0, 0, 0, 'not run' if r[4] == 'function' else 'glue, not decompiled', ''))
        rows.append('0x%08x\t%s\t%d\t%d\t%s\t%s\t%d\t%d\t%s\t%s' % (a, r[4], i[0], i[1], r[1], r[2], i[2], i[3], i[4], i[5]))
    xz(os.path.join(outdir, 'functions.tsv.xz'), '\n'.join(rows) + '\n')
    xz(os.path.join(outdir, 'calls.tsv.xz'),
       'caller\tcallee\n' + ''.join('0x%08x\t0x%08x\n' % p for p in sorted(calls)))
    xz(os.path.join(outdir, 'string_refs.tsv.xz'),
       'function\tstring\ttext\n' + ''.join('0x%08x\t0x%08x\t%s\n' % (a, t, strings[t]) for a, t in sorted(srefs)))
    xz(os.path.join(outdir, 'import_refs.tsv.xz'),
       'function\tdll\tname\n' + ''.join('0x%08x\t%s\t%s\n' % r for r in sorted(irefs)))
    keep = [l for l in open(os.path.join(inv, 'evidence.tsv')).read().split('\n') if l.startswith('inventory')]
    with open(os.path.join(outdir, 'evidence.tsv'), 'w') as f:
        f.write('step\tcommand_or_functions\tevidence_ids\tstatus_or_skipped\n')
        f.write(''.join(l + '\n' for l in keep))
        for b, e, n, sk in evid:
            f.write('decompile batch %s\t%d functions\t%s\t%s\n' % (b, n, e, sk or 'ok'))
    for n in ('sections.tsv', 'imports.tsv', 'exports.tsv'):
        open(os.path.join(outdir, n), 'w').write(open(os.path.join(inv, n)).read())
    xz(os.path.join(outdir, 'strings.tsv.xz'), open(os.path.join(inv, 'strings.tsv'), encoding='utf-8').read())
    st = defaultdict(int)
    for a, r in starts.items():
        if r[4] == 'function':
            st[info.get(a, (0, 0, 0, 0, 'not run', ''))[4].split(' fcn_')[0]] += 1
    print('functions: ' + ', '.join('%s %d' % kv for kv in sorted(st.items())))
    print('call pairs %d, string references %d, import references %d, hints %d, C lines %d' % (
        len(calls), len(srefs), len(irefs), sum(1 for i in info.values() if i[5]), sum(i[3] for i in info.values())))


if __name__ == '__main__':
    main(*sys.argv[1:5])
