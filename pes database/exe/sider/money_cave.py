"""What MLMoney.lua puts into the game, and the same arithmetic as Python.

    python3 money_cave.py            print the layout and the code bytes
    python3 money_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                     and compare it with the bytes kept in this file
    python3 money_cave.py context <PES2017.exe>
                                     print the CONTEXT list of MLMoney.lua from the exe file

MLMoney.lua changes up to four places of PES2017.exe (sha256 44b0caaa...) and fills a
piece of unused memory with four small routines and their tables.

Fee, fcn_038ab832 (MASTER_LEAGUE.md 6.2). The 17 bytes at 0x038ab8db hold the rating part
of the formula, `9000 * max(0, rating - 68)`, left in edi. They become a call to FEE_CODE:

    v           = VALUE[rating] * AGE[age] / 100
    v           = v * POSITION[registered position] / 100
    v           = v * (SPREAD_LOW + (hash * SPREAD_RANGE >> 8)) / 1000, at most 99,999,900
    edi         = v + v * (popularity * FAME) / 100000
    [ebp - 0xc] = 0.0        the factor of the salary part; the game goes on to compute
                             trunc(salary * factor) + edi, which is now edi

All divisions drop the remainder. rating is in eax there (0 to 255; above 99 counts as
99) and the player record in ebx. Of the record (what the game's getter fcn_038278b0
gives for fields 0x2b and 0x00): age = 6 bits at +0x1c, bits 7-12; registered position =
4 bits at +0x04, bits 28-31, in the edit file's order (0 GK ... 12 CF). popularity is the
12-bit number at +0xb4, bits 11-22. hash is one byte made from the player's id (the word
at +0x2c and the dword at +0x30), so it is the same for a player at every call.
Everything after that in the function is as before: a handed-in figure taken as it is,
the random change, the limit.

Salary, fcn_038ac66e (6.1). The 98 bytes from 0x038ac875 compute A = 30 * rating - 500
into [ebp - 0x38] and B (the three steps at 65, 75, 85) into [ebp - 0x34]. The first 7
bytes become a call to SALARY_CODE and a jump over the rest:

    [ebp - 0x38] = SALARY[rating] * SALARY_AGE[age] / 100
    [ebp - 0x34] = 0

so `salary = trunc((role bonus + popularity part + that) * club factor) + ...`.

Budgets, fcn_038ad9c4 (6.4). `add esi, esi; mov eax, [eax + 0x30]` at 0x038adc47 (the
mean value of the 16 best players, doubled) becomes a call to BUDGET_T_CODE:
`esi = esi * BUDGET_T / 100`, the same mov, and the zero flag the next jump reads.
`lea esi, [ecx + eax*2]; call 0x0381c0e5` at 0x038add08 (wage bill + twice the mean
salary of the 16 best paid) becomes a call to BUDGET_S_CODE and three nops:
`esi = ecx + eax * BUDGET_S / 100`, then a jump to 0x0381c0e5, which returns to the nops.

The memory used is the end of the section .trace: the section's content ends at
0x047b005d, its declared size at 0x047b0123, and its last page runs to 0x047b0fff. The
section is readable, writable and executable. No call or jump of the exe goes there.
"""
import struct
import sys

CAP = 99999900
UNIT = 100                      # the screens show 100 times the stored amount
CAVE = 0x047b0200
VALUE_TAB = CAVE                # 100 dwords, by rating 0-99
SALARY_TAB = CAVE + 0x190       # 100 dwords, by rating 0-99
AGE_TAB = CAVE + 0x320          # 64 words, percent, by age 0-63
SALARY_AGE_TAB = CAVE + 0x3a0   # 64 words, percent, by age 0-63
POSITION_TAB = CAVE + 0x420     # 16 words, percent, by registered position
FAME_AT = CAVE + 0x440          # dword: percent of value per 1000 popularity points
SPREAD_LOW_AT = CAVE + 0x444    # dword: lowest factor of the spread, in thousandths
SPREAD_RANGE_AT = CAVE + 0x448  # dword: width of the spread, in thousandths
BUDGET_T_AT = CAVE + 0x44c      # dword: transfer budget, percent of the mean value of the best 16
BUDGET_S_AT = CAVE + 0x450      # dword: salary budget, percent of the mean salary of the best 16
HUNDRED_AT = CAVE + 0x454       # dword 100
THOUSAND_AT = CAVE + 0x458      # dword 1000
MARK_AT = CAVE + 0x45c          # 4 bytes "MLM2"
FEE_CODE = CAVE + 0x480
SALARY_CODE = CAVE + 0x540
BUDGET_T_CODE = CAVE + 0x580
BUDGET_S_CODE = CAVE + 0x5a0
CAVE_SIZE = 0x5c0
CAVE_LIMIT = 0x047b1000

FEE_SITE = 0x038ab8db
FEE_SITE_OLD = bytes.fromhex('83f844760c8db8bcffffff69ff28230000')
SALARY_SITE = 0x038ac875
SALARY_SITE_OLD = bytes.fromhex('89c1c1e10429c1')
SALARY_BLOCK_END = 0x038ac8d7
BUDGET_T_SITE = 0x038adc47
BUDGET_T_SITE_OLD = bytes.fromhex('01f68b4030')
BUDGET_S_SITE = 0x038add08
BUDGET_S_SITE_OLD = bytes.fromhex('8d3441e8d5e3f6ff')
MODE_OBJECT_GETTER = 0x0381c0e5

POSITIONS = ('GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF')
HASH_A, HASH_B = 0x01000193, 0x9e3779b1

FEE_SOURCE = f'''
    cmp eax, 99
    jbe f1
    mov eax, 99
f1: mov eax, dword ptr [eax*4 + {VALUE_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    mov ecx, dword ptr [ebx + 4]
    shr ecx, 28
    movzx ecx, word ptr [ecx*2 + {POSITION_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    movzx ecx, word ptr [ebx + 0x2c]
    imul edx, dword ptr [ebx + 0x30], {HASH_A}
    xor ecx, edx
    imul ecx, ecx, {HASH_B}
    shr ecx, 24
    imul ecx, dword ptr [{SPREAD_RANGE_AT}]
    shr ecx, 8
    add ecx, dword ptr [{SPREAD_LOW_AT}]
    mul ecx
    div dword ptr [{THOUSAND_AT}]
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
s1: mov eax, dword ptr [eax*4 + {SALARY_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {SALARY_AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    mov dword ptr [ebp - 0x38], eax
    mov dword ptr [ebp - 0x34], 0
    ret
'''
BUDGET_T_SOURCE = f'''
    mov eax, dword ptr [eax + 0x30]
    push eax
    push edx
    mov eax, esi
    mul dword ptr [{BUDGET_T_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov esi, eax
    pop edx
    pop eax
    test esi, esi
    ret
'''
BUDGET_S_SOURCE = f'''
    push edx
    mul dword ptr [{BUDGET_S_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
    lea esi, [ecx + eax]
    jmp {MODE_OBJECT_GETTER}
'''
# the assembled routines (python3 money_cave.py build checks them against the source above)
FEE_BYTES = bytes.fromhex(
    '83f8637605b8630000008b048500027b048b4b1cc1e90783e13f0fb70c4d20057b04f7e1f73554067b048b4b04'
    'c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b179379ec1e9180faf0d48'
    '067b04c1e908030d44067b04f7e1f73558067b043d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1'
    'ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745f400000000c3')
SALARY_BYTES = bytes.fromhex(
    '83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f73554067b048945c8'
    'c745cc00000000c3')
BUDGET_T_BYTES = bytes.fromhex('8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3')
BUDGET_S_BYTES = bytes.fromhex('52f72550067b04f73554067b045a8d3401e92fb906ff')
ROUTINES = ((FEE_CODE, FEE_SOURCE, 'FEE_BYTES'), (SALARY_CODE, SALARY_SOURCE, 'SALARY_BYTES'),
            (BUDGET_T_CODE, BUDGET_T_SOURCE, 'BUDGET_T_BYTES'), (BUDGET_S_CODE, BUDGET_S_SOURCE, 'BUDGET_S_BYTES'))

# limits the module keeps, so that no step of the routines can overflow 32 bits
MAX_AGE_PERCENT = 300
MAX_POSITION_PERCENT = 200
MAX_SPREAD = 30
MAX_FAME = 100
MAX_SALARY = 40000000
MAX_SALARY_AGE_PERCENT = 200
MIN_BUDGET, MAX_BUDGET = 0.1, 10.0

# the code the routines rely on: name, address, byte count (MLMoney.lua compares these
# bytes of the running game with the bytes of the exe file before it writes anything)
CONTEXT = (
    ('fee code', 0x038ab832, 228),          # start of the fee function to the end of the changed part and its use
    ('salary code', 0x038ac6f8, 15),        # the player record goes into ebx
    ('salary code 2', 0x038ac86f, 110),     # the rating part and what follows
    ('salary sum', 0x038aca2b, 49),         # where the two numbers are added
    ('budget code', 0x038adc0b, 346),       # both budget sums to the place they are stored
    ('position', 0x03827961, 17),           # getter of the registered position
    ('age', 0x03827ba9, 20),                # getter of the age
)


def call(site, target):
    return b'\xe8' + struct.pack('<i', target - (site + 5))


FEE_SITE_NEW = call(FEE_SITE, FEE_CODE) + b'\x90' * 12
SALARY_SITE_NEW = call(SALARY_SITE, SALARY_CODE) + b'\xeb' + bytes([SALARY_BLOCK_END - (SALARY_SITE + 7)])
BUDGET_T_SITE_NEW = call(BUDGET_T_SITE, BUDGET_T_CODE)
BUDGET_S_SITE_NEW = call(BUDGET_S_SITE, BUDGET_S_CODE) + b'\x90' * 3
#        name, address, bytes of the game, bytes of the module
SITES = (('fee', FEE_SITE, FEE_SITE_OLD, FEE_SITE_NEW), ('salary', SALARY_SITE, SALARY_SITE_OLD, SALARY_SITE_NEW),
         ('budget 1', BUDGET_T_SITE, BUDGET_T_SITE_OLD, BUDGET_T_SITE_NEW),
         ('budget 2', BUDGET_S_SITE, BUDGET_S_SITE_OLD, BUDGET_S_SITE_NEW))
assert all(len(old) == len(new) for _, _, old, new in SITES)


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


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Tables:
    """The settings of MLMoney.lua as the module stores them.

    value, age: lists of (x, y) knots; position: {name: percent}; spread: percent;
    fame: percent per 1,000 points; salary: knots or None (the salary formula stays the
    game's); salary_age: knots; budget_transfer, budget_salary: factor or None (the
    game's own 2)."""

    def __init__(self, value, age, position, spread, fame, salary, salary_age, budget_transfer, budget_salary):
        self.value = [clamp(amount(m), 1, CAP) for m in curve(value, 0, 99, True)]
        self.age = [clamp(int(p + 0.5), 0, MAX_AGE_PERCENT) for p in curve(age, 0, 63, False)]
        self.position = [clamp(int(position[n] + 0.5), 0, MAX_POSITION_PERCENT) for n in POSITIONS] + [100] * 3
        s = clamp(int(spread + 0.5), 0, MAX_SPREAD)
        self.spread_low, self.spread_range = 1000 - 10 * s, 20 * s
        self.fame = clamp(int(fame + 0.5), 0, MAX_FAME)
        self.has_salary = bool(salary)
        self.salary = [clamp(amount(m / 2.0), 1, MAX_SALARY) for m in curve(salary, 0, 99, True)] if salary else [0] * 100
        self.salary_age = [clamp(int(p + 0.5), 0, MAX_SALARY_AGE_PERCENT) for p in curve(salary_age, 0, 63, False)]
        self.budget_transfer = None if not budget_transfer else int(budget_transfer * 100 + 0.5)
        self.budget_salary = None if not budget_salary else int(budget_salary * 100 + 0.5)

    def sites(self):
        """The places the module changes with these settings."""
        on = (True, self.has_salary, self.budget_transfer is not None, self.budget_salary is not None)
        return [s for s, used in zip(SITES, on) if used]


def image(t):
    d = struct.pack('<100I', *t.value) + struct.pack('<100I', *t.salary) + struct.pack('<64H', *t.age)
    d += struct.pack('<64H', *t.salary_age) + struct.pack('<16H', *t.position)
    assert len(d) == FAME_AT - CAVE
    d += struct.pack('<7I', t.fame, t.spread_low, t.spread_range, t.budget_transfer or 200, t.budget_salary or 200,
                     100, 1000) + b'MLM2'
    for at, _, name in ROUTINES:
        d = d.ljust(at - CAVE, b'\0') + globals()[name]
    assert len(d) <= CAVE_SIZE
    return d.ljust(CAVE_SIZE, b'\0')


def spread_hash(id_low, id_high):
    """The byte the fee routine makes from a player's id."""
    x = (id_low & 0xffff) ^ (id_high * HASH_A & 0xffffffff)
    return (x * HASH_B & 0xffffffff) >> 24


def fee(t, rating, age, popularity, position=5, player=(0, 0), base=0, percent=0, keep=False):
    """The transfer fee with MLMoney.lua in place (stored amount; the screen shows 100 times it).
    position: 0 GK ... 12 CF (the edit file's order); player: the two parts of the player's id;
    base, percent, keep: as in ../tools/money.py fee()."""
    x = t.value[min(rating, 99)] * t.age[age] // 100
    x = x * t.position[position] // 100
    x = min(CAP, x * (t.spread_low + (spread_hash(*player) * t.spread_range >> 8)) // 1000)
    x += x * (popularity * t.fame) // 100000
    if keep:
        x = base
    if percent:
        x += int(x * f32(percent / 100.0))
    return max(1, min(CAP, x))


def salary(t, rating, age, popularity, role_bonus=0, rank=300, band_bonus=0, awards=0):
    """The yearly salary with MLMoney.lua in place. role_bonus: R of MASTER_LEAGUE.md 6.1;
    band_bonus: T (with its 20 * field 0x20)."""
    x = popularity
    if popularity > 800:
        x += (5 * popularity - 4000) * 2
    if popularity > 1800:
        x += (5 * popularity - 9000) * 4
    f = f32(1.0) if rank > 250 else f32((251 - rank) * 0.004000000189989805 + 1.0)
    part = t.salary[min(rating, 99)] * t.salary_age[age] // 100
    return max(1, min(CAP, awards + band_bonus + int((role_bonus + x + part) * f)))


def budgets(t, fees, salaries, wage_bill):
    """What fcn_038ad9c4 adds to the transfer budget and to the salary budget of the
    user's club. fees, salaries: of every player of the squad. t = None: the game's own."""
    def mean(amounts):
        return (sum(sorted(amounts, reverse=True)[:16]) or 10000) // 16
    bt = 200 if t is None or t.budget_transfer is None else t.budget_transfer
    bs = 200 if t is None or t.budget_salary is None else t.budget_salary
    limit = lambda v: clamp(v, -99999999, 99999999)
    return limit(mean(fees) * bt // 100), limit(wage_bill + mean(salaries) * bs // 100)


def build():
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_32)
    return {name: bytes(ks.asm(source, at)[0]) for at, source, name in ROUTINES}


def context_lua(exe):
    """The CONTEXT list of MLMoney.lua, from the bytes of the exe file."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    from layout import load, off
    d = load(exe)
    lines = ['local CONTEXT = {']
    for name, at, n in CONTEXT:
        h = d[off(at):off(at) + n].hex()
        parts = [h[i:i + 88] for i in range(0, len(h), 88)]
        lines.append('    { "%s", 0x%08x,' % (name, at))
        lines.append('\n'.join('      %s"%s"' % ('.. ' if i else '', p) for i, p in enumerate(parts)) + ' },')
    lines.append('}')
    return '\n'.join(lines)


if __name__ == '__main__':
    if sys.argv[1:2] == ['context']:
        print(context_lua(sys.argv[2]))
        sys.exit(0)
    if sys.argv[1:] == ['build']:
        for name, code in build().items():
            assert code == globals()[name], '%s: the bytes kept in this file are not what the source assembles to: %s' % (name, code.hex())
        print('ok: the source assembles to the bytes kept in this file')
    print('memory   %08x - %08x' % (CAVE, CAVE + CAVE_SIZE - 1))
    for name, at, old, new in SITES:
        print('%-9s %08x: %s -> %s' % (name, at, old.hex(), new.hex()))
    for at, _, name in ROUTINES:
        print('%-15s %08x: %s' % (name, at, globals()[name].hex()))
