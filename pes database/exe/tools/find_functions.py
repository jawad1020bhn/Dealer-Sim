"""Find function starts in the live code of PES2017.exe without running it.

    python3 find_functions.py <PES2017.exe> <out functions.tsv> [exports.tsv]

A start is an address in .trace/.xcode that is
  call   the target of a direct call (E8 rel32) found in the code, or
  ptr    stored as a pointer in the read-only or writable data (vtables,
         callbacks),
  (the exports and the two routines the entry stub calls are added as they are)
and that passes the boundary test: the byte before it ends a function or is
padding (int3, nop, ret, ret n, jmp), or it is called from two places or more,
or it opens with a frame set-up (push ebp; mov ebp, esp and its two variants:
a function that follows the jump table of a switch has no padding before it).
A byte E8 inside another instruction gives a random target; 0.7 % of random
targets fall in the code and the boundary test removes nearly all of those.

Each start gets a shape from its first bytes:
  function  ordinary code: these are decompiled
  atexit    push <fn>; call atexit; pop ecx; ret  (registers a destructor)
  unwind    lea/mov ecx, [ebp+x]; jmp <destructor>  (C++ exception clean-up)
  dtor      mov ecx, <global>; jmp <destructor>
  ehandler  the exception handler stub of one function
  thunk     a jump to another function

Output columns: address, calls (direct call sites), ptrs (data pointers),
boundary (1/0), shape."""
import struct
import sys
from collections import Counter

from layout import CODE_LO, CODE_HI, CODE_OFF, load, off

ENDS1 = {0xCC, 0x90, 0xC3}
ENTRY = (b'\x55\x89\xe5', b'\x53\x89\xe3', b'\x56\x89\xce')   # 66,491 / 2,128 / 2,021 of the decompiled functions


def boundary(d, a):
    o = CODE_OFF + a - CODE_LO
    if a == CODE_LO:
        return True
    b = d[o - 1]
    if b in ENDS1:
        return True
    if d[o - 3] == 0xC2:                       # ret n
        return True
    if d[o - 5] == 0xE9 or d[o - 2] == 0xEB:   # jmp rel32 / jmp rel8
        return True
    if d[o - 6:o - 4] == b'\xff\x25' or d[o - 7:o - 5] == b'\xff\x24':  # jmp [mem] / switch
        return True
    return False


def shape(d, a):
    o = CODE_OFF + a - CODE_LO
    b = d[o:o + 16]
    if b[0] == 0x68 and b[5] == 0xE8 and b[10:12] == b'\x59\xc3':
        return 'atexit'
    n = 0
    if b[:2] in (b'\x8d\x8d', b'\x8b\x8d'):
        n = 6
    elif b[:2] in (b'\x8d\x4d', b'\x8b\x4d'):
        n = 3
    if n:
        if b[n:n + 2] == b'\x83\xc1':
            n += 3
        elif b[n:n + 2] == b'\x81\xc1':
            n += 6
        if b[n] == 0xE9:
            return 'unwind'
    if b[0] == 0xB9 and b[5] == 0xE9:
        return 'dtor'
    if b[:7] == b'\x8b\x54\x24\x08\x8d\x42\x0c':
        return 'ehandler'
    if b[0] == 0xE9 or b[:2] == b'\xff\x25':
        return 'thunk'
    return 'function'


def find(d, extra=()):
    code = d[CODE_OFF:CODE_OFF + CODE_HI - CODE_LO]
    n = len(code)
    calls = Counter()
    i = code.find(b'\xe8')
    while i >= 0 and i + 5 <= n:
        t = (CODE_LO + i + 5 + struct.unpack_from('<i', code, i + 1)[0]) & 0xffffffff
        if CODE_LO <= t < CODE_HI:
            calls[t] += 1
        i = code.find(b'\xe8', i + 1)
    ptrs = Counter()
    for lo, size in ((0x01ea5000, 0x5c2600), (0x02468000, 0x523c00)):
        o = off(lo)
        for v in struct.unpack_from('<%dI' % (size // 4), d, o):
            if CODE_LO <= v < CODE_HI:
                ptrs[v] += 1
    link = off(0x047d6000)                      # the entry stub
    extra = set(extra)
    for i in range(link, link + 0x200):
        if d[i] == 0xE8:
            t = (0x047d6000 + i - link + 5 + struct.unpack_from('<i', d, i + 1)[0]) & 0xffffffff
            if CODE_LO <= t < CODE_HI:
                extra.add(t)
    rows = []
    for a in sorted(set(calls) | set(ptrs) | extra):
        b = boundary(d, a)
        c, p = calls[a], ptrs[a]
        o = CODE_OFF + a - CODE_LO
        if b or c >= 2 or a in extra or d[o:o + 3] in ENTRY:
            rows.append((a, c, p, int(b), shape(d, a)))
    return rows, len(calls), len(ptrs)


if __name__ == '__main__':
    d = load(sys.argv[1])
    extra = [int(l.split('\t')[0], 16) for l in open(sys.argv[3]).read().split('\n')[1:] if l] \
        if len(sys.argv) > 3 else []
    rows, nc, np_ = find(d, [a for a in extra if CODE_LO <= a < CODE_HI])
    with open(sys.argv[2], 'w') as f:
        f.write('address\tcalls\tptrs\tboundary\tshape\n')
        for a, c, p, b, k in rows:
            f.write('0x%08x\t%d\t%d\t%d\t%s\n' % (a, c, p, b, k))
    print('call targets in code %d, data pointers into code %d, kept %d' % (nc, np_, len(rows)))
    print('  called and at a boundary %d, off a boundary (called twice or more, or a frame set-up) %d, pointer only %d' % (
        sum(1 for r in rows if r[1] and r[3]), sum(1 for r in rows if not r[3]),
        sum(1 for r in rows if not r[1])))
    print('  shapes: ' + ', '.join('%s %d' % kv for kv in Counter(r[4] for r in rows).most_common()))
