"""Runs MLMoney.lua outside the game and then runs the game's own code with its changes.

    python3 test_money.py <PES2017.exe>        needs: pip install lupa unicorn

The exe is loaded into a CPU emulator (../tools/emu.py). The module gets only the names
Sider gives a Lua module, and a memory.read / memory.write that work on the emulator's
memory. Then the game's salary and fee functions are run as machine code, with the
module's changes in them, on random players, and compared with money_cave.py.

What this shows: the module's logic, and that the changed code computes what
money_cave.py says. What it does not show: Sider, Windows, the running game.
"""
import os
import random
import re
import struct
import sys

from lupa.luajit21 import LuaRuntime

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import money                                     # noqa: E402
import money_cave as mc                          # noqa: E402
from emu import Game                             # noqa: E402

MODULE = os.path.join(HERE, 'MLMoney.lua')
MODE_OBJECT, MENU_OBJECT, PLAYER_RECORD, RANDOM = 0x026503e0, 0x0264f3e8, 0x03822835, 0x03855998
SALARY, FEE = 0x038ac66e, 0x038ab832
# what the module may touch: (address, size). Reads: the three pieces of code it checks
# and its memory. Writes: its memory and the two places.
READS = ((0x038ab89e, 120), (0x038ac86f, 110), (0x038aca2b, 49), (mc.CAVE, mc.CAVE_SIZE))
WRITES = ((mc.CAVE, mc.CAVE_SIZE), (mc.FEE_SITE, 17), (mc.SALARY_SITE, 7))


def settings(source):
    """The four tables as written in the Lua file -> Python lists."""
    def knots(name):
        text = re.search(r'^local %s = (\{.*?^\}|false)' % name, source, re.S | re.M).group(1)
        return None if text == 'false' else [(float(a), float(b)) for a, b in re.findall(r'\{\s*([\d.]+),\s*([\d.]+)\s*\}', text)]
    return knots('VALUE'), knots('AGE'), float(re.search(r'^local FAME = ([\d.]+)', source, re.M).group(1)), knots('SALARY')


def run(g, source, sticky=True):
    """Runs the module's init on the emulator's memory. -> (log lines, reads, writes)"""
    lua = LuaRuntime(encoding=None, unpack_returned_tuples=True)
    lines, reads, writes = [], [], []

    def read(address, count):
        reads.append((int(address), int(count)))
        return g.read(int(address), int(count))

    def write(address, data):
        writes.append((int(address), len(data)))
        if sticky:
            poke(g, int(address), data)

    make = lua.eval('''function(source, log, read, write)
        local env = { assert = assert, table = table, pairs = pairs, ipairs = ipairs, string = string,
                      math = math, tonumber = tonumber, tostring = tostring, unpack = unpack,
                      error = error, _VERSION = _VERSION, type = type,
                      os = { time = os.time, clock = os.clock, date = os.date },
                      log = log, memory = { read = read, write = write } }
        local chunk = assert(loadstring(source, "MLMoney.lua"))
        setfenv(chunk, env)
        local module = chunk()
        assert(type(module) == "table" and type(module.init) == "function")
        module.init({ sider_dir = ".\\\\" })
    end''')
    make(source.encode(), lambda text: lines.append(text.decode()), read, write)
    return lines, reads, writes


def poke(g, address, data):
    """Write to the emulator's memory and drop its translated copy of the code there."""
    g.write(address, data)
    g.mu.ctl_remove_cache(address, address + len(data))


def inside(calls, allowed):
    return all(any(a <= address and address + count <= a + n for a, n in allowed) for address, count in calls)


class Harness:
    """The game's salary and fee functions with chosen answers for what they would look up
    (the same set-up as ../tools/check_findings.py, checks 7 and 8)."""

    def __init__(self, exe):
        self.g = g = Game(exe)
        self.v = v = {}
        mode, holder, menu = g.alloc(size=0xf00000), g.alloc(size=0x40), g.alloc(size=0x40)
        g.write(holder + 0x30, struct.pack('<I', mode))
        g.write(MODE_OBJECT, struct.pack('<I', holder))
        g.write(menu + 0x20, struct.pack('<I', 0x13))        # Master League
        g.write(MENU_OBJECT, struct.pack('<I', menu))
        self.rec = rec = g.alloc(size=0x400)
        g.replace(PLAYER_RECORD, lambda g, a: rec)
        g.replace(0x03879e04, lambda g, a: 17)               # league of the club: not 60, 61, 62
        g.replace(0x02c7d227, lambda g, a: 1)
        g.replace(0x03138333, lambda g, a: v['rank'])
        g.replace(0x0385400e, lambda g, a: v['band'])
        g.replace(0x0318c209, lambda g, a: 0)                # no award holders
        g.replace(0x0388d14a, lambda g, a: 0)
        g.replace(0x0381e2eb, lambda g, a: a(0))
        g.replace(RANDOM, lambda g, a: v['random'].pop(0))
        for a in (0x03853b42, 0x03853b52, 0x0383899a):
            g.replace(a, lambda g, a: v['overall'])

        def field(g, a):
            g.write(a(1), struct.pack('<I', v['field20'] if a(0) == 0x20 else 0))
            return 0
        g.replace(0x038278b0, field)
        self.pid, self.team = g.alloc(struct.pack('<II', 1234, 1)), g.alloc(struct.pack('<I', 0x4066))
        self.zero, self.number = g.alloc(b'\0' * 8), g.alloc(b'\0' * 4)
        self.kind, self.change, self.one = g.alloc(b'\0' * 4), g.alloc(b'\0' * 4), g.alloc(b'\1')
        g.write(rec + 0x2c, struct.pack('<II', 1234, 1))
        g.write(rec + 0xbc, struct.pack('<h', -1))
        self.clean = {a: g.read(a, n) for a, n in READS + WRITES}

    def restore(self):
        for a, d in self.clean.items():
            poke(self.g, a, d)

    def unchanged(self):
        return all(self.g.read(a, len(d)) == d for a, d in self.clean.items())

    def salary_cases(self, n, want):
        g, v, rec = self.g, self.v, self.rec
        for _ in range(n):
            o = random.choice([random.randint(40, 99), random.randint(40, 99), random.randint(100, 255)])
            x = random.choice([0, 800, 801, 1800, 1801, 4095, random.randint(0, 4095)])
            role, level = random.randint(0, 22), random.randint(0, 3)
            given = random.randint(0, 1)                     # the rating is handed in, or looked up
            v.update(rank=random.choice([1, 250, 251, 300, random.randint(1, 300)]), band=random.randint(0, 7),
                     field20=random.randint(40, 99), overall=o)
            g.write(rec + 0xb4, struct.pack('<II', x << 11, level << 26))
            g.write(rec + 0xc4, bytes([role]))
            g.write(self.number, struct.pack('<I', o if given else 0))
            got = g.call(SALARY, [self.pid, self.team, self.zero, self.zero, self.number])
            assert got == want(o, x, role, level, v['rank'], v['band'], v['field20']), (o, x, role, level, v, got)

    def fee_cases(self, n, want):
        g, v, rec = self.g, self.v, self.rec
        for _ in range(n):
            o = random.choice([random.randint(40, 99), random.randint(40, 99), random.randint(100, 255)])
            x, age = random.randint(0, 4095), random.randint(0, 63)
            base, given = random.randint(1, 400000), random.choice([0, 0, 777])
            k, own, do = random.choice([0, 1, 2, 3]), random.randint(0, 1), random.randint(0, 1)
            v['overall'] = o
            g.write(rec + 0x1c, struct.pack('<I', random.getrandbits(32) & ~(0x3f << 7) | age << 7))
            g.write(rec + 0xb4, struct.pack('<II', x << 11 | random.getrandbits(11) | random.getrandbits(9) << 23,
                                            own << 28))
            g.write(rec + 0xcc, struct.pack('<I', base))
            g.write(self.number, struct.pack('<I', given))
            g.write(self.kind, struct.pack('<I', k))
            g.write(self.change, bytes([do]))
            r, sign = random.randint(0, 49), random.randint(0, 1)
            v['random'] = [] if not do else [r] if k in (1, 2) else [sign, r % 20]
            percent = (0 if not do else (-r or 1) if k == 1 else (r or 1) if k == 2
                       else ((r % 20) or 1 if sign == 0 else -(r % 20) or 1))
            got = g.call(FEE, [self.pid, self.number, self.kind, self.change, self.one])
            assert got == want(o, age, x, given or base, percent, bool(k and not own)), (o, age, x, base, given, k, own, do, got)


def old_salary(o, x, role, level, rank, band, field20):
    return money.salary(min(o, 255), x, role, level, rank, band, field20)


def main(exe):
    random.seed(2017)
    source = open(MODULE, encoding='utf-8').read()
    h = Harness(exe)
    g = h.g
    value, age, fame, salary = settings(source)
    t = mc.tables(value, age, fame, salary)

    def new_salary(o, x, role, level, rank, band, field20):
        bonus = money.AGE_BONUS[band]
        return mc.salary(t, o, x, money.role_bonus(role, level), rank, bonus + field20 * 20 if bonus else 0)

    def new_fee(o, age, x, base, percent, keep):
        return mc.fee(t, o, age, x, base, percent, keep)

    def old_fee(o, age, x, base, percent, keep):
        return money.fee(base, o, x & 0xfff, percent, keep)

    # 0. before the module: the game's own formulas (the harness itself is sound)
    h.salary_cases(300, old_salary)
    h.fee_cases(300, old_fee)
    print('ok 0: without the module the emulated game gives the amounts of ../tools/money.py')

    # 1. the module as it is
    lines, reads, writes = run(g, source)
    print('\n'.join('    ' + l for l in lines))
    assert lines[-1] == 'RESULT: installed. Values and salaries come from the tables.', lines[-1]
    assert inside(reads, READS) and inside(writes, WRITES), (reads, writes)
    assert g.read(mc.CAVE, mc.CAVE_SIZE) == mc.image(t), 'the tables or routines differ from money_cave.py'
    assert g.read(mc.FEE_SITE, 17) == mc.FEE_SITE_NEW and g.read(mc.SALARY_SITE, 7) == mc.SALARY_SITE_NEW
    print('ok 1: the module passes its checks, writes only its memory and the two places, and what it '
          'wrote is what money_cave.py builds from the same settings')

    n = 3000
    h.salary_cases(n, new_salary)
    h.fee_cases(n, new_fee)
    print('ok 2: with the changes in, the game\'s salary and fee code give the amounts of money_cave.py '
          'for %d + %d random players (ratings 40 to 255, ages 0 to 63, with and without the random change)' % (n, n))

    # 3. SALARY = false: only the fee changes
    h.restore()
    off = re.sub(r'^local SALARY = \{.*?^\}', 'local SALARY = false', source, flags=re.S | re.M)
    assert off != source
    lines, reads, writes = run(g, off)
    assert lines[-1] == 'RESULT: installed. Values come from the tables; salaries are the game\'s own.', lines[-1]
    assert g.read(mc.SALARY_SITE, 7) == mc.SALARY_SITE_OLD and g.read(mc.FEE_SITE, 17) == mc.FEE_SITE_NEW
    h.salary_cases(500, old_salary)
    h.fee_cases(500, new_fee)
    print('ok 3: with SALARY = false the salary code is untouched and gives the game\'s own amounts; '
          'the fee comes from the tables')

    # 4. cases in which nothing may be written
    def refused(name, source, prepare, last, sticky=True, may_write_cave=False):
        h.restore()
        prepare()
        before = {a: g.read(a, n) for a, n in READS + WRITES}
        lines, reads, writes = run(g, source, sticky)
        assert lines[-1].startswith(last), (name, lines[-1])
        assert inside(reads, READS), name
        if may_write_cave:
            assert writes == [(mc.CAVE, mc.CAVE_SIZE)], (name, writes)
        else:
            assert writes == [] and all(g.read(a, len(d)) == d for a, d in before.items()), name
        return lines

    refused('WRITE = false', source.replace('local WRITE = true', 'local WRITE = false'), lambda: None,
            'RESULT: nothing written (WRITE = false). All checks passed.')
    for name, at in (('fee code', 0x038ab8e8), ('fee code', 0x038ab8a0), ('salary code', 0x038ac8b5),
                     ('salary sum', 0x038aca40)):
        lines = refused(name, source, lambda: poke(g, at, bytes([g.read(at, 1)[0] ^ 1])), 'RESULT: nothing written. This game')
        assert any(l.startswith('check: %-12s' % name) and l.endswith('DIFFERENT') for l in lines), lines
    lines = refused('memory in use', source, lambda: poke(g, mc.CAVE + 0x45f, b'\x01'), 'RESULT: nothing written. This game')
    assert any(l.endswith('NOT EMPTY') for l in lines) and not any(l.endswith('DIFFERENT') for l in lines), lines
    refused('bad settings', source.replace('{ 85, 65 }', '{ 85, 0 }'), lambda: None, 'RESULT: nothing written. Settings: VALUE')
    refused('bad settings', source.replace('{ 29, 80 }', '{ 26, 80 }'), lambda: None, 'RESULT: nothing written. Settings: AGE')
    refused('bad settings', source.replace('local FAME = 10', 'local FAME = 500'), lambda: None, 'RESULT: nothing written. Settings: FAME')
    refused('write does not stick', source, lambda: None, 'RESULT: the tables could not be written', sticky=False,
            may_write_cave=True)
    h.restore()
    assert h.unchanged()
    h.salary_cases(200, old_salary)
    h.fee_cases(200, old_fee)
    print('ok 4: WRITE = false, one changed byte in each checked piece of code, memory not empty, faulty '
          'settings: nothing is written; a write that does not stick: the code is not touched')

    # 5. the one player we have screen numbers of
    assert money.fee(72597, 89, 955) * mc.UNIT == 36743200
    assert [o for o in range(60, 100) if any(money.fee(72597, o, x) == 367432 for x in range(3001))] == [89]
    print('ok 5: Bruno Fernandes as the user saw him (rating 89, salary 7,259,700, value 36,743,200): the '
          'game\'s formula gives exactly that value from that salary with popularity 955, and with no other '
          'rating from 60 to 99')
    print('      with the module his value will read: ' + ', '.join(
        'age %d: %s' % (a, format(mc.fee(t, 89, a, 955) * mc.UNIT, ',')) for a in (30, 31, 32, 33)))


if __name__ == '__main__':
    main(sys.argv[1])
