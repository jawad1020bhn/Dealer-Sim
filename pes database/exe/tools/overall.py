"""The game's overall rating, fcn_04067af3(values, position), with its tables
read from the exe (nothing typed by hand).

    python3 overall.py <PES2017.exe>          # print the tables

`values` is the list of 39 numbers the game builds for a player (fcn_0383899a):
    [0]      registered position
    [1..13]  playable rating at position 0..12 (0 = C, 1 = B, 2 = A)
    [14..38] abilities, see ABILITY
Positions here are the game's internal codes: 0 CF, 1 SS, 2 LWF, 3 RWF, 4 AMF,
5 DMF, 6 CMF, 7 LMF, 8 RMF, 9 CB, 10 LB, 11 RB, 12 GK (the edit file counts
the other way, GK = 0; FILE_POS converts).

Read from the code, not from a label: which slot holds which ability. The
names in ABILITY follow the order of the weight rows and agree with the
formula in ../../tools/rate.py, which was fitted on EA ratings.
"""
import struct
import sys

from layout import load, off

POSITIONS = ['CF', 'SS', 'LWF', 'RWF', 'AMF', 'DMF', 'CMF', 'LMF', 'RMF', 'CB', 'LB', 'RB', 'GK']
FILE_POS = [12, 9, 10, 11, 5, 6, 7, 8, 4, 2, 3, 1, 0]      # edit-file code -> internal (switch in fcn_0383899a)
ABILITY = {14: 'atk', 15: 'ball_ctrl', 16: 'drib', 17: 'lowpass', 18: 'loftpass', 19: 'finish',
           20: 'place_kick', 21: 'swerve', 22: 'header', 23: 'def', 24: 'ball_win', 25: 'kick_pwr',
           26: 'speed', 27: 'exp_pwr', 28: 'body_ctrl', 29: 'phys', 30: 'jump', 31: 'gk',
           33: 'stamina', 35: 'cover', 36: 'catching', 37: 'clearing', 38: 'reflex'}
# slot 32 is not read. Slot 34 is a 2-bit player field (attribute 30 of the
# getter fcn_038278b0): always under 25, so its row adds weight x 1.


class Tables:
    def __init__(self, exe):
        d = exe if isinstance(exe, (bytes, bytearray)) else load(exe)

        def ints(a, n):
            return list(struct.unpack_from('<%di' % n, d, off(a)))
        self.column_pos = ints(0x222bba0, 13)       # table column -> internal position
        self.rows = ints(0x222bbd8, 20)             # slot read by each weight row
        self.weights = [ints(0x222bc28 + 52 * r, 13) for r in range(20)]
        self.registered = ints(0x222c038, 13)       # bonus at the registered position
        self.rated_a = ints(0x222c06c, 13)          # bonus at another position rated A
        self.rated_b = ints(0x222c0a0, 13)          # ... rated B
        self.mean_rows = ints(0x222c0d8, 19)
        self.blend = ints(0x222c128, 100)


def _term(v, slot):
    if slot == 28:
        return (v[28] + v[29]) >> 1
    if slot == 31:
        return (v[35] + v[31]) >> 1
    if slot == 32:
        return (v[36] + v[37] + v[38]) // 3
    return v[slot]


def overall(t, v, pos):
    """Line by line what fcn_04067af3 and fcn_04067a53 do."""
    if pos not in t.column_pos:
        return 70
    col = t.column_pos.index(pos)
    total = 0
    for r, slot in enumerate(t.rows):
        x = _term(v, slot)
        total += t.weights[r][col] * (1 if x < 25 else x - 25)
    o = (total + 50) // 100
    if v[0] == pos:
        o += t.registered[col]
    elif v[pos + 1] == 1:
        o += t.rated_b[col]
    elif v[pos + 1] >= 2:
        o += t.rated_a[col]
    if v[0] == pos and pos != 12:
        mean = (sum(_term(v, s) for s in t.mean_rows) * 100 // 19 + 50) // 100
        o = (o * 60 + 50 + (t.blend[mean] if mean < 100 else 70) * 40) // 100
    return 109 if o >= 110 else max(o, 40)


def values(p):
    """The 39 numbers for a player dict of ../../tools/lib.py (P17)."""
    v = [0] * 39
    v[0] = FILE_POS[p['reg_pos']]
    for k, name in enumerate(POSITIONS):
        v[1 + k] = p['pp_' + name]
    for slot, name in ABILITY.items():
        v[slot] = p[name]
    return v


if __name__ == '__main__':
    t = Tables(sys.argv[1])
    print('columns:', ' '.join(POSITIONS[p] for p in t.column_pos))
    for r, slot in enumerate(t.rows):
        name = {28: 'body_ctrl+phys /2', 31: 'gk+cover /2', 32: 'catch+clear+reflex /3',
                34: '(2-bit field: 1)'}.get(slot, ABILITY.get(slot))
        print('%-22s' % name, ' '.join('%3d' % w for w in t.weights[r]))
    for name in ('registered', 'rated_a', 'rated_b'):
        print('%-22s' % ('bonus ' + name), ' '.join('%3d' % w for w in getattr(t, name)))
    print('blend table:', t.blend)
