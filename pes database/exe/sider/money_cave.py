"""What MLMoney.lua puts into the game, and the same arithmetic as Python.

    python3 money_cave.py            print the layout and the code bytes
    python3 money_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                     and compare it with the bytes kept in this file

MLMoney.lua changes two places of PES2017.exe (sha256 44b0caaa...) and fills a piece of
unused memory with two small routines and their tables.

Fee, fcn_038ab832 (MASTER_LEAGUE.md 6.2). The 17 bytes at 0x038ab8db hold the rating part
of the formula, `9000 * max(0, rating - 68)`, left in edi. They become a call to FEE_CODE:

    edi         = VALUE[rating] * AGE[age] / 100, at most 99,999,900
    edi        += edi * (popularity * FAME) / 100000
    [ebp - 0xc] = 0.0        the factor of the salary part; the game goes on to compute
                             trunc(salary * factor) + edi, which is now edi

rating is in eax there (0 to 255; above 99 counts as 99). age is 6 bits of the player
record (+0x1c, bits 7-12; what the game's getter fcn_038278b0 gives for field 0x2b).
popularity is the 12-bit number at +0xb4, bits 11-22. Everything after that in the
function is as before: a handed-in figure taken as it is, the random change, the limit.

Salary, fcn_038ac66e (6.1). The 98 bytes from 0x038ac875 compute A = 30 * rating - 500
into [ebp - 0x38] and B (the three steps at 65, 75, 85) into [ebp - 0x34]. The first 7
bytes become a call to SALARY_CODE and a jump over the rest:

    [ebp - 0x38] = SALARY[rating]
    [ebp - 0x34] = 0

so `salary = trunc((role bonus + popularity part + SALARY[rating]) * club factor) + ...`.

The memory used is the end of the section .trace: the section's content ends at
0x047b005d, its declared size at 0x047b0123, and its last page runs to 0x047b0fff. The
section is readable, writable and executable. Nothing in the exe refers to an address
there (checked: every 4-byte value in that range is part of an instruction or of text).
"""
import struct
import sys

CAP = 99999900
UNIT = 100                      # the screens show 100 times the stored amount
CAVE = 0x047b0200
VALUE_TAB = CAVE                # 100 dwords, by rating 0-99
SALARY_TAB = CAVE + 0x190       # 100 dwords, by rating 0-99
AGE_TAB = CAVE + 0x320          # 64 words, percent, by age 0-63
FAME_AT = CAVE + 0x3a0          # dword: percent of value per 1000 popularity points
MARK_AT = CAVE + 0x3a4          # 4 bytes "MLM1"
FEE_CODE = CAVE + 0x3c0
SALARY_CODE = CAVE + 0x430
CAVE_SIZE = 0x460
CAVE_LIMIT = 0x047b1000

FEE_SITE = 0x038ab8db
FEE_SITE_OLD = bytes.fromhex('83f844760c8db8bcffffff69ff28230000')
SALARY_SITE = 0x038ac875
SALARY_SITE_OLD = bytes.fromhex('89c1c1e10429c1')
SALARY_BLOCK_END = 0x038ac8d7

FEE_SOURCE = f'''
    cmp eax, 99
    jbe f1
    mov eax, 99
f1: mov edi, dword ptr [eax*4 + {VALUE_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {AGE_TAB}]
    mov eax, edi
    mul ecx
    mov ecx, 100
    div ecx
    cmp eax, {CAP}
    jbe f2
    mov eax, {CAP}
f2: mov edi, eax
    mov ecx, dword ptr [ebx + 0xb4]
    shr ecx, 11
    and ecx, 0xfff
    imul ecx, dword ptr [{FAME_AT}]
    mul ecx
    mov ecx, 100000
    div ecx
    add edi, eax
    mov dword ptr [ebp - 0xc], 0
    ret
'''
SALARY_SOURCE = f'''
    cmp eax, 99
    jbe s1
    mov eax, 99
s1: mov ecx, dword ptr [eax*4 + {SALARY_TAB}]
    mov dword ptr [ebp - 0x38], ecx
    mov dword ptr [ebp - 0x34], 0
    ret
'''
# the assembled routines (python3 money_cave.py build checks them against the source above)
FEE_BYTES = bytes.fromhex(
    '83f8637605b8630000008b3c8500027b048b4b1cc1e90783e13f0fb70c4d20057b0489f8f7e1b964000000f7f1'
    '3d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0da0057b04f7e1b9a0860100f7f1'
    '01c7c745f400000000c3')
SALARY_BYTES = bytes.fromhex('83f8637605b8630000008b0c8590037b04894dc8c745cc00000000c3')

# limits the module keeps, so that no step of the routines can overflow
MAX_AGE_PERCENT = 1000
MAX_FAME = 100
MAX_SALARY = 40000000


def call(site, target):
    return b'\xe8' + struct.pack('<i', target - (site + 5))


FEE_SITE_NEW = call(FEE_SITE, FEE_CODE) + b'\x90' * 12
SALARY_SITE_NEW = call(SALARY_SITE, SALARY_CODE) + b'\xeb' + bytes([SALARY_BLOCK_END - (SALARY_SITE + 7)])
assert len(FEE_SITE_NEW) == len(FEE_SITE_OLD) and len(SALARY_SITE_NEW) == len(SALARY_SITE_OLD)
assert FEE_CODE + len(FEE_BYTES) <= SALARY_CODE and SALARY_CODE + len(SALARY_BYTES) <= CAVE + CAVE_SIZE


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def curve(knots, lo, hi, geometric):
    """Value for every whole number lo..hi from a list of (x, y) knots: straight lines
    between the knots (or, geometric, straight lines of the logarithm), the end values
    outside them."""
    out = []
    for x in range(lo, hi + 1):
        if x <= knots[0][0]:
            y = knots[0][1]
        elif x >= knots[-1][0]:
            y = knots[-1][1]
        else:
            for (x1, y1), (x2, y2) in zip(knots, knots[1:]):
                if x1 <= x <= x2:
                    t = (x - x1) / (x2 - x1)
                    y = y1 * (y2 / y1) ** t if geometric else y1 + (y2 - y1) * t
                    break
        out.append(y)
    return out


def amount(millions):
    """Millions on the screen -> stored amount, rounded to 10 (1,000 on the screen)."""
    return int(millions * 1000 + 0.5) * 10


def tables(value, age, fame, salary):
    """The four settings of MLMoney.lua -> (VALUE, AGE, FAME, SALARY) as the module stores
    them. salary may be None (the salary formula stays the game's)."""
    v = [min(CAP, max(1, amount(m))) for m in curve(value, 0, 99, True)]
    a = [min(MAX_AGE_PERCENT, max(0, int(p + 0.5))) for p in curve(age, 0, 63, False)]
    s = [min(MAX_SALARY, max(1, amount(m / 2.0))) for m in curve(salary, 0, 99, True)] if salary else None
    return v, a, min(MAX_FAME, max(0, int(fame + 0.5))), s


def image(t):
    v, a, fame, s = t
    d = struct.pack('<100I', *v) + struct.pack('<100I', *(s or [0] * 100)) + struct.pack('<64H', *a)
    d += struct.pack('<I', fame) + b'MLM1'
    d = d.ljust(FEE_CODE - CAVE, b'\0') + FEE_BYTES
    d = d.ljust(SALARY_CODE - CAVE, b'\0') + SALARY_BYTES
    return d.ljust(CAVE_SIZE, b'\0')


def fee(t, rating, age, popularity, base=0, percent=0, keep=False):
    """The transfer fee with MLMoney.lua in place (stored amount; the screen shows 100 times it).
    base, percent, keep: as in ../tools/money.py fee()."""
    v, a, fame, _ = t
    x = min(CAP, v[min(rating, 99)] * a[age] // 100)
    x += x * (popularity * fame) // 100000
    if keep:
        x = base
    if percent:
        x += int(x * f32(percent / 100.0))
    return max(1, min(CAP, x))


def salary(t, rating, popularity, role_bonus=0, rank=300, band_bonus=0, awards=0):
    """The yearly salary with MLMoney.lua in place. role_bonus: R of MASTER_LEAGUE.md 6.1;
    band_bonus: T (with its 20 * field 0x20)."""
    x = popularity
    if popularity > 800:
        x += (5 * popularity - 4000) * 2
    if popularity > 1800:
        x += (5 * popularity - 9000) * 4
    f = f32(1.0) if rank > 250 else f32((251 - rank) * 0.004000000189989805 + 1.0)
    return max(1, min(CAP, awards + band_bonus + int((role_bonus + x + t[3][min(rating, 99)]) * f)))


def build():
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_32)
    return bytes(ks.asm(FEE_SOURCE, FEE_CODE)[0]), bytes(ks.asm(SALARY_SOURCE, SALARY_CODE)[0])


if __name__ == '__main__':
    if sys.argv[1:] == ['build']:
        assert build() == (FEE_BYTES, SALARY_BYTES), 'the bytes kept in this file are not what the source assembles to'
        print('ok: the source assembles to the bytes kept in this file')
    print('memory   %08x - %08x' % (CAVE, CAVE + CAVE_SIZE - 1))
    print('fee      %08x: %s -> %s' % (FEE_SITE, FEE_SITE_OLD.hex(), FEE_SITE_NEW.hex()))
    print('salary   %08x: %s -> %s' % (SALARY_SITE, SALARY_SITE_OLD.hex(), SALARY_SITE_NEW.hex()))
    print('fee code     %08x: %s' % (FEE_CODE, FEE_BYTES.hex()))
    print('salary code  %08x: %s' % (SALARY_CODE, SALARY_BYTES.hex()))
