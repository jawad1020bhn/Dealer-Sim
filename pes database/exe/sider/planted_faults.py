#!/usr/bin/env python3
"""Does test_money.py notice faults? Planted faults for the price ceiling (MLTransfers.lua).

    python3 planted_faults.py <PES2017.exe> routine      about 1 minute
    python3 planted_faults.py <PES2017.exe> files        about 15 minutes on two processors

routine: every bit of the ceiling routine is flipped in turn in the emulator's memory,
after the two modules are in, and the cases of Harness.choose_cases are run. Printed: the
flips after which all cases still passed.
files: one line of MLTransfers.lua or money_cave.py is changed in a copy of this folder and
the whole test is run there. It must fail every time.
"""
import os
import random
import shutil
import struct
import subprocess
import sys
import tempfile
from concurrent.futures import ThreadPoolExecutor

HERE = os.path.dirname(os.path.abspath(__file__))
FAULTS = (
    # the ceilings and the ratings in the wrong order, a place not written, checks left out
    ('MLTransfers.lua', 'local v = CEILING[10 - level]', 'local v = CEILING[level + 1]'),
    ('MLTransfers.lua', 'RANGE_TOP[level + 1] or 255', 'RANGE_TOP[10 - level] or 255'),
    ('MLTransfers.lua', '    memory.write(SITE[2], new)\n', ''),
    ('MLTransfers.lua', 'if not (good and empty) then', 'if not good then'),
    ('MLTransfers.lua', 'for _, c in ipairs(CONTEXT) do\n        if not same(c[1], c[2], c[3]) then good = false end',
     'for _, c in ipairs(CONTEXT) do\n        if not same(c[1], c[2], c[3]) then good = true end'),
    # "no ceiling" written as 0, wrong limits of the amounts, the rating rule always on
    ('MLTransfers.lua', '(v == 0) and 0xffffffff or', '(v == 0) and 0 or'),
    ('MLTransfers.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 100, 9999000)'),
    ('MLTransfers.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 1000, 99990000)'),
    ('MLTransfers.lua', 'string.char(CEILING_RATING and RANGE_TOP', 'string.char(true and RANGE_TOP'),
    ('MLTransfers.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.01 or v > 99999))'),
    ('MLTransfers.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.001 or v > 9999))'),
    # the second piece of memory: not read back, not written, a faulty setting let through,
    # a wrong rating, a wrong size, a wrong address
    ('MLTransfers.lua', 'if memory.read(CAVE, CAVE_SIZE) ~= memory_image then', 'if false then'),
    ('MLTransfers.lua', '    memory.write(CAVE, memory_image)\n', ''),
    ('MLTransfers.lua', 'if type(CEILING_RATING) ~= "boolean" then', 'if false then'),
    ('MLTransfers.lua', 'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }',
     'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 85, 99 }'),
    ('MLTransfers.lua', 'local CAVE_SIZE = 0x180', 'local CAVE_SIZE = 0x17c'),
    ('MLTransfers.lua', 'local CAVE = 0x047d3c40 ', 'local CAVE = 0x047d3c38 '),
    # the model: a rating equal to the top refused, the rating rule in both searches, a value
    # equal to the ceiling refused, the lowest list searched too, the order of the ceilings,
    # the place counted as written when it is off
    ('money_cave.py', 'if wide and rating > t.ceiling_top[level]:', 'if wide and rating >= t.ceiling_top[level]:'),
    ('money_cave.py', 'if wide and rating > t.ceiling_top[level]:', 'if rating > t.ceiling_top[level]:'),
    ('money_cave.py', 'return price <= limit(', 'return price < limit('),
    ('money_cave.py', 'for overall in range(highest, lowest, -1):', 'for overall in range(highest, lowest - 1, -1):'),
    ('money_cave.py', 'if m else NO_CEILING for m in reversed(ceiling)]', 'if m else NO_CEILING for m in ceiling]'),
    ('money_cave.py', "'ceiling': self.ceiling is not None}", "'ceiling': True}"),
    # version 6, the limit. In the module: need written without its 100, the two discounts
    # swapped, a negative number let through
    ('MLTransfers.lua', 'u32(100 + math.floor(CEILING_NEED + 0.5))', 'u32(math.floor(CEILING_NEED + 0.5))'),
    ('MLTransfers.lua', '.. u32(math.floor(CEILING_LISTED + 0.5))\n        .. u32(math.floor(CEILING_FREE + 0.5))',
     '.. u32(math.floor(CEILING_FREE + 0.5))\n        .. u32(math.floor(CEILING_LISTED + 0.5))'),
    ('MLTransfers.lua', 'c[1] < 0 or c[1] > c[3] then', 'c[1] > c[3] then'),
    # in the model: need only in the second search, only for a slot with a band; a wrong
    # divisor of the stretch; the club left out of the hash; the discount for status 2
    # only; both discounts for a listed player without a contract
    ('money_cave.py', 'club, bool(wide or band))', 'club, bool(wide))'),
    ('money_cave.py', 'club, bool(wide or band))', 'club, bool(band))'),
    ('money_cave.py', '* t.ceiling_stretch) // 25600', '* t.ceiling_stretch) // 25500'),
    ('money_cave.py', '^ (club * HASH_B & 0xffffffff)', '^ (0 * HASH_B & 0xffffffff)'),
    ('money_cave.py', '    if status in (1, 2):\n        price = price * t.ceiling_free // 100\n    elif listed:',
     '    if status in (2,):\n        price = price * t.ceiling_free // 100\n    elif listed:'),
    ('money_cave.py', '        price = price * t.ceiling_free // 100\n    elif listed:',
     '        price = price * t.ceiling_free // 100\n    if listed:'),
    # the two files: MLTransfers.lua does not look for MLMoney.lua, looks at the wrong place,
    # does not compare the value routine, does not see that the ceiling is in already, writes
    # with WRITE = false
    ('MLTransfers.lua', 'local found = (mark ~= nil and string.sub(mark, 1, 3) == "MLM")', 'local found = (mark ~= nil)'),
    ('MLTransfers.lua', 'local MONEY_MARK = 0x047b065c', 'local MONEY_MARK = 0x047b0658'),
    ('MLTransfers.lua', 'if not same(c[1], c[2], c[3]) then money = false end', 'if not same(c[1], c[2], c[3]) then money = true end'),
    ('MLTransfers.lua', 'if there ~= nil and hex(there) == SITE[4] then', 'if false then'),
    ('MLTransfers.lua', '    if not WRITE then\n', '    if false then\n'),
)


def routine(exe):
    sys.path.insert(0, HERE)
    import capstone
    import money_cave as mc
    import test_money as tm
    h = tm.Harness(exe)
    g = h.g
    source = tm.two_modules()
    tm.run(g, source)
    t = tm.settings(source)
    usual = t.ceiling[:]
    random.seed(1)
    print('without a fault: %d of 400 lists changed by the ceiling, %d players refused' % h.choose_cases(400, t))
    good = g.read(mc.CEILING_CODE, len(mc.CEILING_BYTES))
    text = {}
    for i in capstone.Cs(capstone.CS_ARCH_X86, capstone.CS_MODE_32).disasm(mc.CEILING_BYTES, mc.CEILING_CODE):
        for k in range(i.size):
            text[i.address + k - mc.CEILING_CODE] = '%s %s' % (i.mnemonic, i.op_str)
    missed = []
    for k in range(len(good)):
        for bit in range(8):
            tm.poke(g, mc.CEILING_CODE + k, bytes([good[k] ^ 1 << bit]))
            random.seed(7)
            try:
                h.choose_cases(400, t)
                missed.append((k, bit, text[k]))
            except BaseException:                            # a failed case or a fault of the emulated processor
                for a in (tm.RECORD_BY_ID, tm.PLAYER_CLUB, tm.TODAY, tm.FOREIGN_RULE, tm.SQUAD_RULE):
                    g.replaced.pop(a, None)
                t.ceiling[:] = usual
                g.write(mc.CEILING_TAB, struct.pack('<10I', *usual))
            tm.poke(g, mc.CEILING_CODE + k, bytes([good[k]]))
    print('%d faults, %d noticed; not noticed:' % (8 * len(good), 8 * len(good) - len(missed)))
    for m in missed:
        print('  byte %d, bit %d: %s' % m)


def files(exe, which):
    root = tempfile.mkdtemp()

    def one(i):
        name, old, new = FAULTS[i]
        d = os.path.join(root, str(i))
        for sub in ('sider', 'tools'):
            shutil.copytree(os.path.join(HERE, '..', sub), os.path.join(d, sub), ignore=shutil.ignore_patterns('__pycache__'))
        path = os.path.join(d, 'sider', name)
        s = open(path, encoding='utf-8').read()
        assert s.count(old) == 1, (i, s.count(old))
        open(path, 'w', encoding='utf-8').write(s.replace(old, new))
        r = subprocess.run([sys.executable, 'test_money.py', exe], cwd=os.path.join(d, 'sider'), capture_output=True, text=True)
        return i, r.returncode, (r.stderr.strip().splitlines() or [''])[-1][:100]
    noticed = 0
    with ThreadPoolExecutor(2) as pool:
        for i, code, last in pool.map(one, which or range(len(FAULTS))):
            noticed += code != 0
            print('%2d %-13s %-11s %s | %s' % (i, FAULTS[i][0], 'noticed' if code else 'NOT NOTICED',
                                               FAULTS[i][2][:60].replace('\n', ' '), last), flush=True)
    print('%d of %d noticed' % (noticed, len(which or FAULTS)))
    shutil.rmtree(root, ignore_errors=True)


if __name__ == '__main__':
    if len(sys.argv) < 3 or sys.argv[2] not in ('routine', 'files'):
        sys.exit(__doc__)
    if sys.argv[2] == 'routine':
        routine(os.path.abspath(sys.argv[1]))
    else:
        files(os.path.abspath(sys.argv[1]), [int(a) for a in sys.argv[3:]])
