"""Class names and virtual-function tables, from the C++ type records in the exe.

    python3 rtti.py <PES2017.exe> [out.tsv.xz]        # default ../output/classes.tsv.xz

MSVC keeps, for every class with virtual functions, a type record
(".?AVName@Namespace@@"), a locator record that points to it, and in front of
each virtual-function table a pointer to the locator. Reading the three gives
"this table belongs to this class", so a virtual call can be followed by hand:
`(**(code **)(*obj + 8))()` is entry 2 of the table of obj's class.

Columns: vtable address, class, offset of this table inside the object (0 = the
main table, other = a base class placed later), number of entries, the entries.
"""
import lzma
import os
import re
import struct
import sys

from layout import CODE_HI, CODE_LO, SECTIONS, load, off

RDATA = next((v, s) for n, v, f, s in SECTIONS if n == '.xtls')
DATA = next((v, s) for n, v, f, s in SECTIONS if n == '.code')


def demangle(name):
    """.?AVCmnGrowthCheck@process@@ -> process::CmnGrowthCheck (templates are left as they are)."""
    m = re.match(r'\.\?A[VU]([A-Za-z_][\w]*(?:@[A-Za-z_]\w*)*)@@$', name)
    return '::'.join(reversed(m.group(1).split('@'))) if m else name


def classes(d):
    """[(vtable, class, offset in object, [entries])]"""
    types = {}                                          # type record address -> name
    for lo, size in (RDATA, DATA):
        o, end = off(lo), off(lo) + size
        i = d.find(b'.?A', o, end)
        while i >= 0:
            j = d.find(b'\0', i, i + 2048)
            if j > i:
                types[lo + (i - o) - 8] = d[i:j].decode('latin1')
            i = d.find(b'.?A', i + 3, end)
    lo, size = RDATA
    o = off(lo)
    words = struct.unpack_from('<%dI' % (size // 4), d, o)
    locators = {}                                       # locator address -> (type record, offset)
    for k in range(len(words) - 4):
        if words[k] == 0 and words[k + 3] in types and words[k + 2] == 0 and words[k + 1] < 0x10000:
            locators[lo + 4 * k] = (words[k + 3], words[k + 1])
    res = []
    for k in range(len(words) - 1):
        if words[k] in locators and CODE_LO <= words[k + 1] < CODE_HI:
            t, offset = locators[words[k]]
            entries = []
            n = k + 1
            while n < len(words) and CODE_LO <= words[n] < CODE_HI and (n == k + 1 or words[n - 1] not in locators):
                if n > k + 1 and words[n] in locators:
                    break
                entries.append(words[n])
                n += 1
            res.append((lo + 4 * (k + 1), demangle(types[t]), offset, entries))
    return res


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    dest = argv[2] if len(argv) > 2 else os.path.join(here, '..', 'output', 'classes.tsv.xz')
    rows = classes(load(argv[1]))
    with lzma.open(dest, 'wt', encoding='utf-8') as f:
        f.write('vtable\tclass\toffset\tentries\tfunctions\n')
        for v, name, offset, entries in sorted(rows):
            f.write('0x%08x\t%s\t%d\t%d\t%s\n' % (v, name, offset, len(entries), ' '.join('0x%08x' % e for e in entries)))
    print('%d tables of %d classes written to %s' % (len(rows), len({r[1] for r in rows}), os.path.normpath(dest)))


if __name__ == '__main__':
    main(sys.argv)
