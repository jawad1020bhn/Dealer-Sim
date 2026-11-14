"""The fields of a player, team and manager record of the edit data, as the game
reads them: where each field sits in the record, its width and its valid range.

    python3 fields.py <PES2017.exe> [out.tsv]        # default ../output/edit_fields.tsv

The game has one table per record kind: 32 bytes per field = field number,
reader, writer, minimum, default, maximum, width in bits, type. Each reader is
run (emu.py) on records with a single bit set; the bits that come out are the
field's place in the record. Needs `pip install unicorn`.
"""
import os
import struct
import sys

from emu import Game
from layout import CODE_HI, CODE_LO, load, off

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))

#        record kind, table address, numeric fields, record size
TABLES = (('player', 0x02511768, 0x6a, 0xbc), ('team', 0x025110b8, 0x20, 0x1e0), ('manager', 0x02512fb0, 0x0b, 0x58))
EDITED = ('e_player', 'e_basic', 'e_regpos', 'e_playpos', 'e_ability', 'e_skill', 'e_style', 'e_com', 'e_motion')


def lib_names():
    """bit in the player record -> the name tools/lib.py gives the field that starts there."""
    import lib
    names = {0: 'id', 32: 'u4', 64: 'u8', 80: 'nation', 96: 'height', 104: 'weight', 112: 'gc1', 120: 'gc2'}
    bit = 16 * 8
    for name, width in lib.F17:
        names[bit] = name
        bit += width
    return names


def table(d, address, count):
    """[(field, reader, writer, minimum, default, maximum, width, type)]"""
    return [struct.unpack_from('<8I', d, off(address) + 32 * i) for i in range(count)]


def read_field(g, reader, record, out):
    g.write(out, bytes(8))
    g.call(reader, [out], ecx=record)
    return struct.unpack('<I', g.read(out, 4))[0]


def place(g, reader, size, record, out):
    """(first bit, bit count) of the field in the record; the bits must be consecutive and in order."""
    bits = []
    for bit in range(size * 8):
        raw = bytearray(size)
        raw[bit // 8] |= 1 << (bit % 8)
        g.write(record, raw)
        v = read_field(g, reader, record, out)
        if v:
            assert v == 1 << len(bits), 'bits out of order'
            bits.append(bit)
    assert bits and bits == list(range(bits[0], bits[0] + len(bits))), 'field is not one run of bits'
    return bits[0], len(bits)


def fields(g, d):
    """[(kind, field, name, first bit, bits, minimum, default, maximum)]"""
    names = lib_names()
    out = g.alloc(size=8)
    rows = []
    for kind, address, count, size in TABLES:
        record = g.alloc(size=size)
        for i, (field, reader, writer, lo, default, hi, width, _) in enumerate(table(d, address, count)):
            assert field == i and CODE_LO <= reader < CODE_HI and CODE_LO <= writer < CODE_HI, (kind, i)
            bit, n = place(g, reader, size, record, out)
            assert n == width and lo <= default <= hi < 1 << width, (kind, field)
            rows.append((kind, field, names.get(bit, '') if kind == 'player' else '', bit, n, lo, default, hi))
    return rows


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    here = os.path.dirname(os.path.abspath(__file__))
    dest = argv[2] if len(argv) > 2 else os.path.join(here, '..', 'output', 'edit_fields.tsv')
    rows = fields(Game(argv[1]), load(argv[1]))
    with open(dest, 'w') as f:
        f.write('record\tfield\tname in tools/lib.py\tbyte\tbit\tbits\tminimum\tdefault\tmaximum\n')
        for kind, field, name, bit, n, lo, default, hi in rows:
            f.write('%s\t%d\t%s\t0x%02x\t%d\t%d\t%d\t%d\t%d\n' % (kind, field, name, bit // 8, bit % 8, n, lo, default, hi))
    print('%d fields written to %s' % (len(rows), os.path.normpath(dest)))


if __name__ == '__main__':
    main(sys.argv)
