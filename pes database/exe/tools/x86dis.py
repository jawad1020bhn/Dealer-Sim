"""Disassemble a stretch of PES2017.exe (for code the decompile output lacks).

    python3 x86dis.py <PES2017.exe> <hex address> <byte count>

Needs `pip install capstone`. Do not rename this file to dis.py: that name
hides a module of the Python library and capstone no longer loads.
"""
import sys

import capstone

from layout import load, off


def dis(d, address, count):
    md = capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32)
    o = off(address)
    return ['%08x  %-8s %s' % (i.address, i.mnemonic, i.op_str) for i in md.disasm(d[o:o + count], address)]


if __name__ == '__main__':
    if len(sys.argv) != 4:
        sys.exit(__doc__)
    print('\n'.join(dis(load(sys.argv[1]), int(sys.argv[2], 16), int(sys.argv[3], 0))))
