"""Section layout of PES2017.exe (sha256 44b0caaa...) and address helpers.

The protection moved the code. The original code sections (.srdata at
0x00401000 and .sdata) are blanked in the file: only the padding between
functions is left. The code that runs is in .trace and .xcode; .xcode is the
intact copy of .sdata, 0x292F000 higher. Data addresses (strings, globals,
import table) are the ordinary ones."""
import struct

BASE = 0x400000
#        name      vaddr       file off    file size
SECTIONS = [
    ('.srdata', 0x00401000, 0x00000600, 0x1a80400),  # original code, blanked
    ('.sdata',  0x01e82000, 0x01a80a00, 0x00022600),  # original code tail, blanked
    ('.xtls',   0x01ea5000, 0x01aa3000, 0x005c2600),  # read-only data: strings, vtables
    ('.code',   0x02468000, 0x02065600, 0x00523c00),  # writable data
    ('.text',   0x0298c000, 0x02589200, 0x00000200),
    ('.idata',  0x0298d000, 0x02589400, 0x00072a00),
    ('.trace',  0x02a00000, 0x025fbe00, 0x01db0200),  # live code
    ('.xcode',  0x047b1000, 0x043ac000, 0x00022e00),  # live copy of .sdata
    ('.data1',  0x047d4000, 0x043cee00, 0x00000200),
    ('.reloc',  0x047d5000, 0x043cf000, 0x00000200),
    ('.link',   0x047d6000, 0x043cf200, 0x00000200),  # entry point
    ('.xtext',  0x047d7000, 0x043cf400, 0x00005a00),  # import table
    ('.data',   0x047dd000, 0x043d4e00, 0x024e1a00),  # encrypted
    ('.edata',  0x06cbf000, 0x068b6800, 0x0005ce00),
]
CODE_LO, CODE_HI = 0x02a00000, 0x047d3e00   # .trace + .xcode, contiguous in file and memory
CODE_OFF = 0x025fbe00


def load(path):
    return open(path, 'rb').read()


def off(va):
    for n, v, f, s in SECTIONS:
        if v <= va < v + s:
            return f + va - v
    return None


def va(o):
    for n, v, f, s in SECTIONS:
        if f <= o < f + s:
            return v + o - f
    return None


def section(a):
    for n, v, f, s in SECTIONS:
        if v <= a < v + s:
            return n
    return None


def u32(d, o):
    return struct.unpack_from('<I', d, o)[0]


def cstr(d, a, limit=200):
    o = off(a)
    if o is None:
        return None
    e = d.find(b'\0', o, o + limit)
    if e < 0:
        return None
    return d[o:e]
