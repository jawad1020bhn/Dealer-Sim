"""Self-check of ../output against the exe.

    python3 check.py <PES2017.exe>

1. every start of shape `function` has a status, and every `ok` one has its C
2. a known function: the C of 0x038e77af (the compiler's stack-cookie set-up)
   names five Windows imports and the constant 0xbb40e64e
3. direct calls: for 300 functions at least 97 % of the callees in calls.tsv.xz
   are found as call or jmp targets in the function's own bytes (a scan that
   does not use Rizin; a function in several pieces has calls outside them)
4. strings: 300 rows of string_refs.tsv.xz have that text at that address in the exe
5. the import value map is the one in the file"""
import glob
import lzma
import os
import random
import re
import struct
import sys

import find
from layout import CODE_LO, CODE_HI, CODE_OFF, load, off, u32

OUT = find.OUT


def main(exe):
    d = load(exe)
    random.seed(17)
    fn = list(find.rows('functions.tsv.xz'))
    todo = [r for r in fn if r[1] == 'function']
    assert all(r[8] != 'not run' for r in todo), 'functions without a result'
    ok = {int(r[0], 16): r for r in todo if r[8] == 'ok'}
    seen = {}
    for path in sorted(glob.glob(os.path.join(OUT, 'c', '*.c.xz'))):
        for head, body in find.functions(path):
            a = int(head.split()[0][4:], 16)
            assert a not in seen and (a >> 20) == int(os.path.basename(path)[:3], 16)
            seen[a] = body.count('\n')
    assert set(seen) == set(ok), (len(seen), len(ok))
    print('1 ok: %d starts of shape function, %d with C, %d without (%s)' % (
        len(todo), len(ok), len(todo) - len(ok),
        ', '.join('%s %d' % (k, sum(1 for r in todo if r[8].split(' fcn_')[0] == k))
                  for k in sorted({r[8].split(' fcn_')[0] for r in todo} - {'ok'}))))
    inside = [r for r in todo if r[8].startswith('inside fcn_')]
    assert all(int(r[8][11:], 16) != int(r[0], 16) for r in inside)

    c = find.show('0x038e77af')
    for w in ('GetSystemTimeAsFileTime', 'GetCurrentProcessId', 'GetCurrentThreadId', 'GetTickCount',
              'QueryPerformanceCounter', '0xbb40e64e'):
        assert w in c, w
    print('2 ok: fcn_038e77af names its five imports')

    calls = {}
    for a, b in find.rows('calls.tsv.xz'):
        calls.setdefault(int(a, 16), set()).add(int(b, 16))
    sample = random.sample(sorted(a for a in ok if a in calls), 300)
    n = miss = 0
    for a in sample:
        size = int(ok[a][2])
        o = CODE_OFF + a - CODE_LO
        b = d[o:o + size + 5]
        found = set()
        for op in (b'\xe8', b'\xe9'):                 # call, and jmp: a tail call
            i = b.find(op)
            while i >= 0 and i + 5 <= len(b):
                found.add((a + i + 5 + struct.unpack_from('<i', b, i + 1)[0]) & 0xffffffff)
                i = b.find(op, i + 1)
        inside = {t for t in calls[a] if CODE_LO <= t < CODE_HI}
        n += len(inside & found)
        miss += len(inside - found)
    # a function made of several pieces has calls outside [start, start + size)
    assert miss <= 0.03 * n, (n, miss)
    print('3 ok: 300 functions, %d callees confirmed by the byte scan, %d not in the main piece' % (n, miss))

    refs = list(find.rows('string_refs.tsv.xz'))
    for f, s, t in random.sample(refs, 300):
        raw = re.sub(r'\\(.)', lambda m: {'t': '\t', 'n': '\n', 'r': '\r'}.get(m.group(1), m.group(1)), t)
        o = off(int(s, 16))
        assert d[o:o + len(raw.encode('utf-8'))] == raw.encode('utf-8') \
            or d[o:o + 2 * len(raw)] == raw.encode('utf-16le'), (s, t)
    print('4 ok: 300 of %d string references read back from the exe' % len(refs))

    for l in open(os.path.join(OUT, 'imports.tsv')).read().split('\n')[1:]:
        if l:
            slot, val, dll, name = l.split('\t')
            assert u32(d, off(int(slot, 16))) == int(val, 16)
    print('5 ok: import slots')


if __name__ == '__main__':
    main(sys.argv[1])
