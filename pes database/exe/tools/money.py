"""Master League money formulas, as Python (copied from PES2017.exe).

salary()  = fcn_038ac66e: the yearly salary a player has at a club.
fee()     = fcn_038ab832: the transfer fee asked for a player.
`check_findings.py` runs the game's own code on the same inputs and compares.
"""
import struct

CAP = 99999900                     # 0x5f5e09c, the largest amount


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


ROLE_A, ROLE_B = (5, 6, 8), (7, 9, 14)      # values of the role byte (player record + 0xc4)
AGE_BONUS = (0, 0, 0, 1000, 3000, 5000, 10000, 15000)


def role_bonus(role, level):
    """role: byte at player + 0xc4; level: 2 bits at player + 0xb8, bit 26 (0 = no level)."""
    if role in ROLE_A:
        return (0, 1000, 2000, 3000)[level]
    if role in ROLE_B:
        return (0, 5000, 7500, 10000)[level]
    return {18: 3000, 19: 15000}.get(role, 0)


def salary(overall, x, role=0, level=0, rank=300, band=0, field20=0, awards=0):
    """overall: rating; x: the 12-bit number at player + 0xb4, bit 11; rank: place of the
    club in the mode's club ranking (300 when the club is not in it); band: result of
    fcn_0385400e; field20: player field 0x20; awards: sum of the award bonuses."""
    a = 30 * overall - 500
    b = 300 * max(0, overall - 65) + 500 * max(0, overall - 75) + 700 * max(0, overall - 85)
    xx = x
    if x > 800:
        xx += (5 * x - 4000) * 2
    if x > 1800:
        xx += (5 * x - 9000) * 4
    f = f32(1.0) if rank > 250 else f32((251 - rank) * 0.004000000189989805 + 1.0)
    part = int((role_bonus(role, level) + xx + b + a) * f)
    t = AGE_BONUS[band] if band < 8 else 0
    if t:
        t += field20 * 20
    return max(1, min(CAP, awards + t + part))


def fee(base, overall, x, percent=0, keep=False):
    """base: the player's salary (player + 0xcc) or the figure handed in; percent: the
    random change, -50 .. +50 (0 = none); keep: the deal kind is not 0 and the player's
    "own" bit (player + 0xb8, bit 28) is clear: the figure is taken as it is."""
    factor = f32(x * 0.0002699999895412475 + 2.200000047683716)
    v = base if keep else int(base * factor) + max(0, overall - 68) * 9000
    if percent:
        v += int(v * f32(percent / 100.0))
    return max(1, min(CAP, v))
