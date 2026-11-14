#!/usr/bin/env python3
"""Does test_money.py notice faults? Planted faults for the price ceiling (version 5).

    python3 planted_faults.py <PES2017.exe> routine      about 1 minute
    python3 planted_faults.py <PES2017.exe> files        about 20 minutes on two processors

routine: every bit of the ceiling routine is flipped in turn in the emulator's memory,
after the module is in, and the cases of Harness.choose_cases are run. Printed: the
flips after which all cases still passed.
files: one line of MLMoney.lua or money_cave.py is changed in a copy of this folder and
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
    ('MLMoney.lua', 'local v = CEILING[10 - level]', 'local v = CEILING[level + 1]'),
    ('MLMoney.lua', 'RANGE_TOP[level + 1] or 255', 'RANGE_TOP[10 - level] or 255'),
    ('MLMoney.lua', '["ceiling"] = ceiling.on,', '["ceiling"] = false,'),
    ('MLMoney.lua', '    return good and empty\nend\n\nfunction ceiling.write', '    return good\nend\n\nfunction ceiling.write'),
    ('MLMoney.lua', 'if ceiling.on and not ceiling.checks() then good = false end', 'if false then good = false end'),
    # "no ceiling" written as 0, wrong limits of the amounts, the rating rule always on
    ('MLMoney.lua', '(v == 0) and 0xffffffff or', '(v == 0) and 0 or'),
    ('MLMoney.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 100, 9999000)'),
    ('MLMoney.lua', 'clamp(amount(v), 100, 99990000)', 'clamp(amount(v), 1000, 99990000)'),
    ('MLMoney.lua', 'string.char(CEILING_RATING and RANGE_TOP', 'string.char(true and RANGE_TOP'),
    ('MLMoney.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.01 or v > 99999))'),
    ('MLMoney.lua', '(v ~= 0 and (v < 0.01 or v > 9999))', '(v ~= 0 and (v < 0.001 or v > 9999))'),
    # the second piece of memory: not read back, not written, a faulty setting let through,
    # a wrong rating, a wrong size, a wrong address
    ('MLMoney.lua', '    return memory.read(CAVE_2, CAVE_2_SIZE) == image\n', '    return true\n'),
    ('MLMoney.lua', 'if ceiling.on and not ceiling.write(image_2) then', 'if false then'),
    ('MLMoney.lua', 'if type(CEILING_RATING) ~= "boolean" then', 'if false then'),
    ('MLMoney.lua', 'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }',
     'local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 85, 99 }'),
    ('MLMoney.lua', 'local CAVE_2_SIZE = 0xcc', 'local CAVE_2_SIZE = 0xc8'),
    ('MLMoney.lua', 'local CAVE_2 = 0x047b0130', 'local CAVE_2 = 0x047b0128'),
    # the model: a rating equal to the top refused, the rating rule in both searches, a value
    # equal to the ceiling refused, the lowest list searched too, the order of the ceilings,
    # the place counted as written when it is off
    ('money_cave.py', 'if wide and rating > t.ceiling_top[level]:', 'if wide and rating >= t.ceiling_top[level]:'),
    ('money_cave.py', 'if wide and rating > t.ceiling_top[level]:', 'if rating > t.ceiling_top[level]:'),
    ('money_cave.py', 'player) <= t.ceiling[level]', 'player) < t.ceiling[level]'),
    ('money_cave.py', 'for overall in range(highest, lowest, -1):', 'for overall in range(highest, lowest - 1, -1):'),
    ('money_cave.py', 'if m else NO_CEILING for m in reversed(ceiling)]', 'if m else NO_CEILING for m in ceiling]'),
    ('money_cave.py', "'ceiling': self.ceiling is not None}", "'ceiling': True}"),
)


def routine(exe):
    sys.path.insert(0, HERE)
    import capstone
    import money_cave as mc
    import test_money as tm
    h = tm.Harness(exe)
    g = h.g
    source = open(tm.MODULE, encoding='utf-8').read()
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
