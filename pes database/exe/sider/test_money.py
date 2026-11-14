"""Runs MLMoney.lua outside the game and then runs the game's own code with its changes.

    python3 test_money.py <PES2017.exe>        needs: pip install lupa unicorn

The exe is loaded into a CPU emulator (../tools/emu.py). The module gets only the names
Sider gives a Lua module, and a memory.read / memory.write that work on the emulator's
memory. Then the game's salary, fee and budget functions are run as machine code, with
the module's changes in them, on random players and squads, and compared with
money_cave.py.

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
SALARY, FEE, BUDGETS, WAGE_BILL, CLUB_RECORD = 0x038ac66e, 0x038ab832, 0x038ad9c4, 0x038ad7a8, 0x03822969
NEW, NEW_TAGGED, DELETE, FREE = 0x02a000b0, 0x02bc5ebe, 0x02a000c0, 0x02bc5b9a
TRANSFER_BUDGET, SALARY_BUDGET = 0xdddfc4, 0xdddfdc          # in the mode data
# what the module may touch: (address, size). Reads: the pieces of code it checks and
# its memory. Writes: its memory and the places it changes.
CAVE = ((mc.CAVE, mc.CAVE_SIZE),)
READS = tuple((at, n) for _, at, n in mc.CONTEXT) + CAVE
ALL_SITES = tuple((at, len(old)) for _, at, old, _ in mc.SITES)
INSTALLED = 'RESULT: installed. Changed: '


def settings(source):
    """The settings as written in the Lua file -> money_cave.Tables."""
    def text(name):
        return re.search(r'^local %s = (\{.*?^\}|[\w.]+)' % name, source, re.S | re.M).group(1)

    def knots(name):
        return None if text(name) == 'false' else [(float(a), float(b)) for a, b in
                                                   re.findall(r'\{\s*([\d.]+),\s*([\d.]+)\s*\}', text(name))]

    def number(name):
        return None if text(name) == 'false' else float(text(name))
    position = {n: float(p) for n, p in re.findall(r'(\w+)\s*=\s*([\d.]+)', text('POSITION'))}
    return mc.Tables(knots('VALUE'), knots('AGE'), position, number('SPREAD'), number('FAME'), knots('SALARY'),
                     knots('SALARY_AGE'), number('BUDGET_TRANSFER'), number('BUDGET_SALARY'))


def setting(source, name, new):
    """The Lua source with one setting replaced."""
    out, n = re.subn(r'^local %s = (\{.*?^\}|[\w.]+)' % name, lambda m: 'local %s = %s' % (name, new), source,
                     flags=re.S | re.M)
    assert n == 1, name
    return out


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
    """The game's salary, fee and budget functions with chosen answers for what they would
    look up (the set-up of ../tools/check_findings.py, checks 7 and 8, and a club record)."""

    def __init__(self, exe):
        self.g = g = Game(exe)
        self.v = v = {'overall': None}
        self.mode = mode = g.alloc(size=0xf00000)
        holder, menu = g.alloc(size=0x40), g.alloc(size=0x40)
        g.write(holder + 0x30, struct.pack('<I', mode))
        g.write(MODE_OBJECT, struct.pack('<I', holder))
        g.write(menu + 0x20, struct.pack('<I', 0x13))        # Master League
        g.write(MENU_OBJECT, struct.pack('<I', menu))
        self.rec = rec = g.alloc(size=0x400)
        self.squad = [g.alloc(size=0x400) for _ in range(40)]
        self.by_id = {}
        self.club = club = g.alloc(size=0x400)
        g.replace(PLAYER_RECORD, lambda g, a: self.by_id.get(a(0) & 0xffff, rec))
        g.replace(CLUB_RECORD, lambda g, a: club)
        g.replace(WAGE_BILL, lambda g, a: v['wages'])
        g.replace(0x03879e04, lambda g, a: 17)               # league of the club: not 60, 61, 62
        g.replace(0x02c7d227, lambda g, a: 1)
        g.replace(0x03138333, lambda g, a: v['rank'])
        g.replace(0x0385400e, lambda g, a: v['band'])
        g.replace(0x0318c209, lambda g, a: 0)                # no award holders
        g.replace(0x0388d14a, lambda g, a: 0)
        g.replace(0x0381e2eb, lambda g, a: a(0))
        g.replace(RANDOM, lambda g, a: v['random'].pop(0))
        g.replace(NEW, lambda g, a: g.alloc(size=a(0) + 16))
        g.replace(NEW_TAGGED, lambda g, a: g.alloc(size=a(1) + 16))
        g.replace(DELETE, lambda g, a: 0)
        g.replace(FREE, lambda g, a: 0)
        # the rating: a chosen number, or (budget cases) a byte kept in the fake record
        for a in (0x03853b42, 0x03853b52, 0x0383899a):
            g.replace(a, lambda g, a: v['overall'] if v['overall'] is not None else g.read(a(0) + 0x300, 1)[0])

        def field(g, a):
            g.write(a(1), struct.pack('<I', v['field20'] if a(0) == 0x20 else 0))
            return 0
        g.replace(0x038278b0, field)
        self.pid, self.team = g.alloc(struct.pack('<II', 1234, 1)), g.alloc(struct.pack('<I', 0x4066))
        self.zero, self.number = g.alloc(b'\0' * 8), g.alloc(b'\0' * 4)
        self.kind, self.change, self.one = g.alloc(b'\0' * 4), g.alloc(b'\0' * 4), g.alloc(b'\1')
        self.clubid = g.alloc(struct.pack('<I', 100))
        g.write(rec + 0x2c, struct.pack('<II', 1234, 1))
        g.write(rec + 0xbc, struct.pack('<h', -1))
        self.heap = g.top
        self.clean = {a: g.read(a, n) for a, n in READS + ALL_SITES}

    def restore(self):
        for a, d in self.clean.items():
            poke(self.g, a, d)

    def unchanged(self):
        return all(self.g.read(a, len(d)) == d for a, d in self.clean.items())

    def player(self, rec, o, age, x, position, ident, salary=0, own=0, level=0):
        """Fills a fake player record; every bit the routines do not read is random."""
        g = self.g
        low, high = ident
        g.write(rec + 0x04, struct.pack('<I', random.getrandbits(28) | position << 28))
        g.write(rec + 0x1c, struct.pack('<I', random.getrandbits(32) & ~(0x3f << 7) | age << 7))
        g.write(rec + 0x2c, struct.pack('<II', low, high))
        g.write(rec + 0xb4, struct.pack('<II', x << 11 | random.getrandbits(11) | random.getrandbits(9) << 23,
                                        own << 28 | level << 26))
        g.write(rec + 0xcc, struct.pack('<I', salary))
        g.write(rec + 0x300, bytes([o]))

    @staticmethod
    def some_player():
        o = random.choice([random.randint(40, 99), random.randint(40, 99), random.randint(100, 255)])
        ident = (random.getrandbits(32), random.getrandbits(32) | 1)
        return o, random.randint(0, 63), random.randint(0, 15), ident

    def salary_cases(self, n, want):
        g, v, rec = self.g, self.v, self.rec
        for _ in range(n):
            o, age, position, _ = self.some_player()
            x = random.choice([0, 800, 801, 1800, 1801, 4095, random.randint(0, 4095)])
            role, level = random.randint(0, 22), random.randint(0, 3)
            given = random.randint(0, 1)                     # the rating is handed in, or looked up
            v.update(rank=random.choice([1, 250, 251, 300, random.randint(1, 300)]), band=random.randint(0, 7),
                     field20=random.randint(40, 99), overall=o)
            self.player(rec, o, age, x, position, (1234, 1), level=level)
            g.write(rec + 0xb4, struct.pack('<II', x << 11, level << 26))
            g.write(rec + 0xc4, bytes([role]))
            g.write(self.number, struct.pack('<I', o if given else 0))
            got = g.call(SALARY, [self.pid, self.team, self.zero, self.zero, self.number])
            assert got == want(o, age, x, role, level, v['rank'], v['band'], v['field20']), (o, age, x, role, level, v, got)

    def fee_cases(self, n, want):
        g, v, rec = self.g, self.v, self.rec
        for _ in range(n):
            o, age, position, ident = self.some_player()
            x = random.randint(0, 4095)
            base, given = random.randint(1, 400000), random.choice([0, 0, 777])
            k, own, do = random.choice([0, 1, 2, 3]), random.randint(0, 1), random.randint(0, 1)
            v['overall'] = o
            self.player(rec, o, age, x, position, ident, base, own)
            g.write(self.number, struct.pack('<I', given))
            g.write(self.kind, struct.pack('<I', k))
            g.write(self.change, bytes([do]))
            r, sign = random.randint(0, 49), random.randint(0, 1)
            v['random'] = [] if not do else [r] if k in (1, 2) else [sign, r % 20]
            percent = (0 if not do else (-r or 1) if k == 1 else (r or 1) if k == 2
                       else ((r % 20) or 1 if sign == 0 else -(r % 20) or 1))
            got = g.call(FEE, [self.pid, self.number, self.kind, self.change, self.one])
            assert got == want(o, age, x, position, ident, given or base, percent, bool(k and not own)), (
                o, age, x, position, ident, base, given, k, own, do, got)

    def budget_cases(self, n, fee, t, top=400000):
        """Whole squads through fcn_038ad9c4: what it adds to the two budgets.
        fee(o, age, x, position, ident, salary) -> the fee of one player."""
        g, v = self.g, self.v
        v['overall'] = None
        for case in range(n):
            g.top = self.heap
            size = (0, 1, 15, 16, 17, 32, 40)[case] if case < 7 else random.randint(0, 40)
            fees, salaries, self.by_id = [], [], {}
            for i in range(size):
                o, age, position, ident = self.some_player()
                ident = (1000 + i, ident[1])
                x, salary = random.randint(0, 4095), random.randint(1, top)
                self.player(self.squad[i], o, age, x, position, ident, salary, own=1)
                self.by_id[ident[0]] = self.squad[i]
                g.write(self.club + 0xf8 + 8 * i, struct.pack('<II', *ident))
                fees.append(fee(o, age, x, position, ident, salary))
                salaries.append(salary)
            g.write(self.club + 0x328, struct.pack('<I', random.getrandbits(9) | size << 9 | random.getrandbits(16) << 16))
            v['wages'] = random.randint(0, 30000000)
            before = random.randint(-1000000, 1000000), random.randint(-1000000, 1000000)
            g.write(self.mode + TRANSFER_BUDGET, struct.pack('<i', before[0]))
            g.write(self.mode + SALARY_BUDGET, struct.pack('<i', before[1]))
            g.call(BUDGETS, [self.clubid])
            got = (struct.unpack('<i', g.read(self.mode + TRANSFER_BUDGET, 4))[0] - before[0],
                   struct.unpack('<i', g.read(self.mode + SALARY_BUDGET, 4))[0] - before[1])
            assert got == mc.budgets(t, fees, salaries, v['wages']), (size, got, mc.budgets(t, fees, salaries, v['wages']))
        self.by_id = {}
        g.top = self.heap


def main(exe):
    random.seed(2017)
    source = open(MODULE, encoding='utf-8').read()
    h = Harness(exe)
    g = h.g

    def old_salary(o, age, x, role, level, rank, band, field20):
        return money.salary(min(o, 255), x, role, level, rank, band, field20)

    def old_fee(o, age, x, position, ident, base, percent, keep):
        return money.fee(base, o, x & 0xfff, percent, keep)

    def new_salary(t):
        def f(o, age, x, role, level, rank, band, field20):
            bonus = money.AGE_BONUS[band]
            return mc.salary(t, o, age, x, money.role_bonus(role, level), rank, bonus + field20 * 20 if bonus else 0)
        return f

    def new_fee(t):
        return lambda o, age, x, position, ident, base, percent, keep: mc.fee(t, o, age, x, position, ident, base, percent, keep)

    def squad_fee(t):
        if t is None:
            return lambda o, age, x, position, ident, salary: money.fee(salary, o, x)
        return lambda o, age, x, position, ident, salary: mc.fee(t, o, age, x, position, ident)

    def install(source, changed):
        """Runs the module on the clean game; checks what it read, wrote and reported."""
        h.restore()
        t = settings(source)
        lines, reads, writes = run(g, source)
        assert lines[-1] == INSTALLED + changed + '.', lines[-1]
        used = t.sites()
        assert inside(reads, READS + tuple((at, len(old)) for _, at, old, _ in used)), reads
        assert inside(writes, CAVE + tuple((at, len(old)) for _, at, old, _ in used)), writes
        assert g.read(mc.CAVE, mc.CAVE_SIZE) == mc.image(t), 'the tables or routines differ from money_cave.py'
        for site in mc.SITES:
            assert g.read(site[1], len(site[2])) == (site[3] if site in used else site[2]), site[0]
        return t, lines

    # 0. before the module: the game's own formulas (the harness itself is sound)
    h.salary_cases(300, old_salary)
    h.fee_cases(300, old_fee)
    h.budget_cases(40, squad_fee(None), None)
    print('ok 0: without the module the emulated game gives the amounts of ../tools/money.py, and its budget '
          'function adds twice the mean of the 16 highest fees and the wage bill plus twice the mean of the '
          '16 highest salaries')

    # 1. the module as it is
    t, lines = install(source, 'values, salaries, transfer budget')
    print('\n'.join('    ' + l for l in lines))
    print('ok 1: the module passes its checks, writes only its memory and the places it reports, and what it '
          'wrote is what money_cave.py builds from the same settings')

    n = 3000
    h.salary_cases(n, new_salary(t))
    h.fee_cases(n, new_fee(t))
    h.budget_cases(150, squad_fee(t), t)
    print('ok 2: with the changes in, the game\'s salary, fee and budget code give the amounts of money_cave.py '
          'for %d + %d random players (ratings 40 to 255, ages 0 to 63, every position, with and without the '
          'random change) and 150 squads of 0 to 40 players' % (n, n))

    # 3. the switches, and settings at their limits
    off = setting(setting(source, 'SALARY', 'false'), 'BUDGET_TRANSFER', 'false')
    t, _ = install(off, 'values')
    h.salary_cases(400, old_salary)
    h.fee_cases(400, new_fee(t))
    h.budget_cases(40, squad_fee(t), t)
    both = setting(setting(source, 'BUDGET_SALARY', '2.5'), 'BUDGET_TRANSFER', '0.1')
    t, _ = install(both, 'values, salaries, transfer budget, salary budget')
    assert (t.budget_transfer, t.budget_salary) == (10, 250)
    h.budget_cases(60, squad_fee(t), t)
    h.salary_cases(200, new_salary(t))
    plain = setting(setting(setting(source, 'SPREAD', '0'), 'POSITION', '{ %s }' % ', '.join(
        '%s = 100' % p for p in mc.POSITIONS)), 'SALARY_AGE', '{\n    { 20, 100 },\n}')
    t, _ = install(plain, 'values, salaries, transfer budget')
    h.fee_cases(400, lambda o, age, x, position, ident, base, percent, keep: mc.fee(t, o, age, x, 5, (0, 0), base, percent, keep))
    for o, age, x in ((89, 30, 955), (94, 25, 0), (70, 19, 3000)):
        first = min(mc.CAP, t.value[o] * t.age[age] // 100)
        assert mc.fee(t, o, age, x) == first + first * x * t.fame // 100000      # the formula written out once more
    limits = source
    for name, new in (('VALUE', '{\n    { 40, 900 }, { 99, 20000 },\n}'), ('AGE', '{\n    { 10, 300 }, { 50, 0 },\n}'),
                      ('POSITION', '{ %s }' % ', '.join('%s = %d' % (p, 200 - 15 * i) for i, p in enumerate(mc.POSITIONS))),
                      ('SPREAD', '30'), ('FAME', '100'), ('SALARY', '{\n    { 40, 500 }, { 99, 100000 },\n}'),
                      ('SALARY_AGE', '{\n    { 10, 200 }, { 50, 0 },\n}'), ('BUDGET_TRANSFER', '10'), ('BUDGET_SALARY', '10')):
        limits = setting(limits, name, new)
    t, _ = install(limits, 'values, salaries, transfer budget, salary budget')
    assert max(t.value) == mc.CAP and max(t.salary) == mc.MAX_SALARY and max(t.age) == 300 and max(t.salary_age) == 200
    h.salary_cases(1500, new_salary(t))
    h.fee_cases(1500, new_fee(t))
    h.budget_cases(150, squad_fee(t), t, top=mc.CAP)
    print('ok 3: SALARY = false and BUDGET_TRANSFER = false leave those places alone and the game\'s own amounts '
          'come out; BUDGET_SALARY changes the salary budget; with spread, position and salary age switched '
          'off the value is VALUE x AGE plus popularity; with every setting at its limit the code and '
          'money_cave.py still agree')

    # 4. cases in which nothing may be written
    def refused(name, source, prepare, last, sticky=True, may_write_cave=False):
        h.restore()
        prepare()
        before = {a: g.read(a, n) for a, n in READS + ALL_SITES}
        lines, reads, writes = run(g, source, sticky)
        assert lines[-1].startswith(last), (name, lines[-1])
        assert inside(reads, READS), name
        if may_write_cave:
            assert writes == [(mc.CAVE, mc.CAVE_SIZE)], (name, writes)
        else:
            assert writes == [] and all(g.read(a, len(d)) == d for a, d in before.items()), name
        return lines

    refused('WRITE = false', setting(source, 'WRITE', 'false'), lambda: None,
            'RESULT: nothing written (WRITE = false). All checks passed.')
    flips = 0
    for name, at, size in mc.CONTEXT:
        for where in sorted({at, at + size // 2, at + size - 1}):
            lines = refused(name, source, lambda: poke(g, where, bytes([g.read(where, 1)[0] ^ 1])),
                            'RESULT: nothing written. This game')
            assert [l for l in lines if l.endswith('DIFFERENT')] == ['check: %-13s at %08x  DIFFERENT' % (name, at)], lines
            flips += 1
    for _, at, old, _ in mc.SITES:                           # every changed place lies inside a checked piece
        assert any(a <= at and at + len(old) <= a + n for _, a, n in mc.CONTEXT), hex(at)
    for where in (0, mc.CAVE_SIZE // 2, mc.CAVE_SIZE - 1):
        lines = refused('memory in use', source, lambda: poke(g, mc.CAVE + where, b'\x01'), 'RESULT: nothing written. This game')
        assert any(l.endswith('NOT EMPTY') for l in lines) and not any(l.endswith('DIFFERENT') for l in lines), lines
    bad = (('VALUE', source.replace('{ 85, 65 }', '{ 85, 0 }')), ('AGE', source.replace('{ 29, 80 }', '{ 26, 80 }')),
           ('SALARY_AGE', source.replace('{ 24, 90 }', '{ 24, -1 }')), ('SALARY', source.replace('{ 85, 10 }', '{ 85 }')),
           ('POSITION.GK', source.replace('GK = 45', 'GK = 450')), ('POSITION.CF', source.replace('CF = 110,', '')),
           ('SPREAD', setting(source, 'SPREAD', '31')), ('FAME', setting(source, 'FAME', '500')),
           ('BUDGET_TRANSFER', setting(source, 'BUDGET_TRANSFER', '0')), ('BUDGET_TRANSFER', setting(source, 'BUDGET_TRANSFER', 'true')),
           ('BUDGET_SALARY', setting(source, 'BUDGET_SALARY', '11')))
    for name, text in bad:
        assert text != source, name
        refused('bad settings', text, lambda: None, 'RESULT: nothing written. Settings: ' + name)
    refused('write does not stick', source, lambda: None, 'RESULT: the tables could not be written', sticky=False,
            may_write_cave=True)
    h.restore()
    assert h.unchanged()
    h.salary_cases(200, old_salary)
    h.fee_cases(200, old_fee)
    h.budget_cases(20, squad_fee(None), None)
    print('ok 4: WRITE = false, one changed byte at %d places of the checked code, memory not empty, %d kinds of '
          'faulty settings: nothing is written; a write that does not stick: the code is not touched' % (flips, len(bad)))

    # 5. the one player we have screen numbers of
    assert money.fee(72597, 89, 955) * mc.UNIT == 36743200
    assert [o for o in range(60, 100) if any(money.fee(72597, o, x) == 367432 for x in range(3001))] == [89]
    print('ok 5: Bruno Fernandes as the user saw him (rating 89, salary 7,259,700, value 36,743,200): the '
          'game\'s formula gives exactly that value from that salary with popularity 955, and with no other '
          'rating from 60 to 99')
    t, exact = settings(source), settings(setting(source, 'SPREAD', '0'))
    low, high = (1000 - 10 * 12) / 1000.0, (1000 + 10 * 12) / 1000.0
    for name, position in (('AMF', 8), ('CMF', 5)):
        print('      with the module, as %s, his value will read (SPREAD = 0 / range with SPREAD = 12): ' % name + '; '.join(
            'age %d: %s / %s to %s' % (a, format(mc.fee(exact, 89, a, 955, position) * mc.UNIT, ','),
                                       format(min(mc.fee(t, 89, a, 955, position, (i, 1)) for i in range(3000)) * mc.UNIT, ','),
                                       format(max(mc.fee(t, 89, a, 955, position, (i, 1)) for i in range(3000)) * mc.UNIT, ','))
            for a in (31, 32, 33)))
    counts = [0] * 256
    for i in range(1, 30001):
        counts[mc.spread_hash(i, 1)] += 1
    assert min(counts) > 60 and max(counts) < 180, (min(counts), max(counts))       # 117 expected per value
    print('      the 256 steps of the spread are used evenly by the ids 1 to 30,000 (%d to %d players each)' % (min(counts), max(counts)))


if __name__ == '__main__':
    main(sys.argv[1])
