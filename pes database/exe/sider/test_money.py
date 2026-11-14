"""Runs MLMoney.lua outside the game and then runs the game's own code with its changes.

    python3 test_money.py <PES2017.exe>        needs: pip install lupa unicorn

The exe is loaded into a CPU emulator (../tools/emu.py). The module gets only the names
Sider gives a Lua module, and a memory.read / memory.write that work on the emulator's
memory. Then the game's salary, fee, budget, prize and contract-years code is run as
machine code, with the module's changes in it, on random players and squads and on every
cup, stage and league place, and compared with money_cave.py.

What this shows: the module's logic, and that the changed code computes what
money_cave.py says. What it does not show: Sider, Windows, the running game.
"""
import os
import random
import re
import struct
import sys

from lupa.luajit21 import LuaRuntime

try:
    import keystone                              # noqa: F401  (only to assemble the routines once more)
    KEYSTONE = True
except ImportError:
    KEYSTONE = False

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path.insert(0, os.path.join(HERE, '..', 'tools'))
import money                                     # noqa: E402
import money_cave as mc                          # noqa: E402
from emu import Game, REG, RETURN, STACK, STACK_SIZE     # noqa: E402
from unicorn.x86_const import UC_X86_REG_EBP, UC_X86_REG_ESP    # noqa: E402

MODULE = os.path.join(HERE, 'MLMoney.lua')
MODE_OBJECT, MENU_OBJECT, PLAYER_RECORD, RANDOM = 0x026503e0, 0x0264f3e8, 0x03822835, 0x03855998
SALARY, FEE, BUDGETS, WAGE_BILL, CLUB_RECORD = 0x038ac66e, 0x038ab832, 0x038ad9c4, 0x038ad7a8, 0x03822969
NEW, NEW_TAGGED, DELETE, FREE = 0x02a000b0, 0x02bc5ebe, 0x02a000c0, 0x02bc5b9a
TRANSFER_BUDGET, SALARY_BUDGET, BALANCE = 0xdddfc4, 0xdddfdc, 0xdddfe4       # in the mode data
CUP_PRIZE, LEAGUE_PRIZE, YEARS_LIMIT, AWARD_HOLDER, LEAGUE_RECORD = 0x038aa307, 0x038a9ebb, 0x03887f5d, 0x0318c209, 0x03822ab9
# the two pieces of prize_step that pay a prize: (first instruction, where the run stops)
PAY_LEAGUE, PAY_CUP = (0x03640abe, 0x03640ae9), (0x03640b61, 0x03640b80)
MODES = (0x13, 0x13, 0x13, 0x12, 0x14, 0x28, 0)              # Master League and others
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

    def cup():
        return None if text('CUP') == 'false' else [(int(c), int(st), float(a)) for c, st, a in re.findall(
            r'\{\s*(\d+),\s*(\d+),\s*([\d.]+)\s*\}', text('CUP'))]

    def numbers(name):
        return None if text(name) == 'false' else [float(x) for x in re.findall(r'[\d.]+', text(name))]
    position = {n: float(p) for n, p in re.findall(r'(\w+)\s*=\s*([\d.]+)', text('POSITION'))}
    return mc.Tables(knots('VALUE'), knots('AGE'), position, number('SPREAD'), number('FAME'), knots('SALARY'),
                     knots('SALARY_AGE'), number('BUDGET_TRANSFER'), number('BUDGET_SALARY'), cup(),
                     numbers('LEAGUE'), numbers('LEAGUE_2'), number('PRIZE_TO_BUDGET'), number('PAY_GAP'),
                     number('BONUS'), number('YOUNG_YEARS'))


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


def signed(v):
    return struct.unpack('<i', struct.pack('<I', v & 0xffffffff))[0]


def inside(calls, allowed):
    return all(any(a <= address and address + count <= a + n for a, n in allowed) for address, count in calls)


class Harness:
    """The game's salary, fee, budget, prize and contract-years code with chosen answers for
    what it would look up (the set-up of ../tools/check_findings.py, checks 7 and 8, of
    ../tools/prize.py, and a club record)."""

    def __init__(self, exe):
        self.g = g = Game(exe)
        self.v = v = {'overall': None, 'league': 17, 'age': 0, 'holders': None}
        self.mode_data = mode = g.alloc(size=0xf00000)
        holder, menu = g.alloc(size=0x40), g.alloc(size=0x40)
        g.write(holder + 0x30, struct.pack('<I', mode))
        g.write(MODE_OBJECT, struct.pack('<I', holder))
        g.write(menu + 0x20, struct.pack('<I', 0x13))        # Master League
        g.write(MENU_OBJECT, struct.pack('<I', menu))
        self.menu = menu
        self.league = g.alloc(size=0x400)                    # record of a league
        self.holder = [g.alloc(size=0x100) for _ in range(4)]    # records of four award holders
        self.line = g.alloc(size=0x20)                       # one competition line of the account
        self.rec = rec = g.alloc(size=0x400)
        self.squad = [g.alloc(size=0x400) for _ in range(40)]
        self.by_id = {}
        self.club = club = g.alloc(size=0x400)
        g.replace(PLAYER_RECORD, lambda g, a: self.by_id.get(a(0) & 0xffff, rec))
        g.replace(CLUB_RECORD, lambda g, a: club)
        g.replace(WAGE_BILL, lambda g, a: v['wages'])
        g.replace(0x03879e04, lambda g, a: v['league'])      # league of the club; 17: not 60, 61, 62
        g.replace(LEAGUE_RECORD, lambda g, a: self.league)
        g.replace(0x038a4ebb, lambda g, a: 0)                # cup_prize: two "is not a cup" tests
        g.replace(0x038a4f07, lambda g, a: 0)
        g.replace(0x02c7d227, lambda g, a: 1)
        g.replace(0x03138333, lambda g, a: v['rank'])
        g.replace(0x0385400e, lambda g, a: v['band'])
        # the holder of award 0 to 3 (none: the award part is left out, as in version 2 of this test)
        g.replace(AWARD_HOLDER, lambda g, a: self.holder[struct.unpack('<I', g.read(a(0), 4))[0]] if v['holders'] else 0)
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
            g.write(a(1), struct.pack('<I', v['field20'] if a(0) == 0x20 else v['age'] if a(0) == 0x2b else 0))
            return 0
        g.replace(0x038278b0, field)
        self.pid, self.team = g.alloc(struct.pack('<II', 1234, 1)), g.alloc(struct.pack('<I', 0x4066))
        self.zero, self.number = g.alloc(b'\0' * 8), g.alloc(b'\0' * 4)
        self.kind, self.change, self.one = g.alloc(b'\0' * 4), g.alloc(b'\0' * 4), g.alloc(b'\1')
        self.clubid = g.alloc(struct.pack('<I', 100))
        g.write(rec + 0x2c, struct.pack('<II', 1234, 1))
        g.write(rec + 0xbc, struct.pack('<h', -1))
        self.heap = g.top
        self.clean = [(a, g.read(a, n)) for a, n in READS + ALL_SITES]

    def restore(self):
        for a, d in self.clean:
            poke(self.g, a, d)

    def unchanged(self):
        return all(self.g.read(a, len(d)) == d for a, d in self.clean)

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

    def salary_cases(self, n, want, ranks=None):
        """want(rating, age, popularity, role, level, rank, band, field 0x20, awards) -> salary.
        ranks: run one case for each of these places of the club ranking instead of n cases."""
        g, v, rec = self.g, self.v, self.rec
        for rank in ranks or [None] * n:
            o, age, position, _ = self.some_player()
            x = random.choice([0, 800, 801, 1800, 1801, 4095, random.randint(0, 4095)])
            role, level = random.randint(0, 22), random.randint(0, 3)
            given = random.randint(0, 1)                     # the rating is handed in, or looked up
            if rank is None:
                rank = random.choice([1, 250, 251, 300, random.randint(1, 300)])
            v.update(rank=rank, band=random.randint(0, 7), field20=random.randint(40, 99), overall=o)
            # which of the four awards the player holds (10,000 for the first, 5,000 for the others)
            won = random.choice([None, [random.randint(0, 1) for _ in range(4)]])
            v['holders'] = won is not None
            for i in range(4):
                g.write(self.holder[i] + 8, struct.pack('<II', 1234 if won and won[i] else 4321, 1))
            awards = 0 if not won else 10000 * won[0] + 5000 * sum(won[1:])
            self.player(rec, o, age, x, position, (1234, 1), level=level)
            g.write(rec + 0xb4, struct.pack('<II', x << 11, level << 26))
            g.write(rec + 0xc4, bytes([role]))
            g.write(self.number, struct.pack('<I', o if given else 0))
            got = g.call(SALARY, [self.pid, self.team, self.zero, self.zero, self.number])
            assert got == want(o, age, x, role, level, rank, v['band'], v['field20'], awards), (
                o, age, x, role, level, v, won, got)
        v['holders'] = None

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
            g.write(self.mode_data + TRANSFER_BUDGET, struct.pack('<i', before[0]))
            g.write(self.mode_data + SALARY_BUDGET, struct.pack('<i', before[1]))
            g.call(BUDGETS, [self.clubid])
            got = (struct.unpack('<i', g.read(self.mode_data + TRANSFER_BUDGET, 4))[0] - before[0],
                   struct.unpack('<i', g.read(self.mode_data + SALARY_BUDGET, 4))[0] - before[1])
            assert got == mc.budgets(t, fees, salaries, v['wages']), (size, got, mc.budgets(t, fees, salaries, v['wages']))
        self.by_id = {}
        g.top = self.heap


    def mode(self, number):
        self.g.write(self.menu + 0x20, struct.pack('<I', number))

    def cup_cases(self, t):
        """cup_prize for the competitions 0 to 100 and the stages 0 to 12. -> number of cases"""
        g = self.g
        for number in (0x13, 0x12):                          # every mode but 0x28 reads the same table
            self.mode(number)
            for competition in range(101):
                for stage in range(13):
                    g.write(self.number, struct.pack('<I', competition))
                    g.write(self.kind, struct.pack('<I', stage))
                    got = g.call(CUP_PRIZE, [self.number, self.kind, self.clubid])
                    assert got == mc.cup_prize(t, competition, stage), (competition, stage, got)
        self.mode(0x13)
        return 2 * 101 * 13

    def cup_other_mode(self):
        """cup_prize in game mode 0x28, which has a table of its own."""
        g, out = self.g, []
        self.mode(0x28)
        for competition in range(101):
            for stage in range(13):
                g.write(self.number, struct.pack('<I', competition))
                g.write(self.kind, struct.pack('<I', stage))
                out.append(g.call(CUP_PRIZE, [self.number, self.kind, self.clubid]))
        self.mode(0x13)
        return out

    def league_cases(self, t):
        """league_prize for every list, place and kind of season. -> number of cases"""
        g, v, n = self.g, self.v, 0
        for league in (17, 60, 61, 0x3458, 0x3459, 0x27d8, 0x27d9):
            for division in range(4):
                for half in range(4):
                    for place in range(28):
                        v['league'] = league
                        g.write(self.league + 0x218, struct.pack('<I', division << 30 | random.getrandbits(30)))
                        g.write(self.number, struct.pack('<I', place))
                        g.write(self.kind, struct.pack('<I', half))
                        got = signed(g.call(LEAGUE_PRIZE, [self.clubid, self.number, self.kind]))
                        assert got == mc.league_prize(t, league, division, place, half), (league, division, half, place, got)
                        n += 1
        v['league'] = 17
        return n

    def piece(self, begin, end, frame, **regs):
        """Runs the game's code from `begin` until `end` with ebp = frame. -> (registers after, esp moved?)"""
        mu = self.g.mu
        esp = frame - 0x400
        mu.reg_write(UC_X86_REG_ESP, esp)
        mu.reg_write(UC_X86_REG_EBP, frame)
        for k in REG:
            mu.reg_write(REG[k], regs.get(k, 0) & 0xffffffff)
        mu.emu_start(begin, end)
        out = {k: mu.reg_read(REG[k]) for k in REG}
        out['ebp'] = mu.reg_read(UC_X86_REG_EBP)
        return out, mu.reg_read(UC_X86_REG_ESP) - esp

    def prize_cases(self, n, t):
        """The two places of prize_step that pay a prize: what reaches the balance, the
        transfer budget and the account line."""
        g, frame = self.g, STACK + STACK_SIZE - 0x2000
        for case in range(n):
            amount = random.choice([0, 1, 99, 101, mc.CAP, 99999999, 100000000, 150000000, -1, -99, -5000,
                                    random.randint(1, 20000000), random.randint(1, 300000), random.randint(1, 300000)])
            number = random.choice(MODES)
            self.mode(number)
            before = [random.randint(-10 ** 9, 10 ** 9) for _ in range(3)]
            for at, value in zip((BALANCE, TRANSFER_BUDGET, SALARY_BUDGET), before):
                g.write(self.mode_data + at, struct.pack('<i', value))
            keep = {k: random.getrandbits(32) for k in ('ebx', 'esi', 'edi')}
            old_line = random.randint(0, 10 ** 6)
            g.write(self.line, struct.pack('<6I', 7, 99, old_line, 0, 0, 0))
            if case % 2:                                     # a league
                stage = random.randint(1, 24)
                g.write(frame - 0x30, struct.pack('<i', amount))
                g.write(frame - 0x34, struct.pack('<I', self.line))
                g.write(frame - 0x20, struct.pack('<I', stage))
                r, moved = self.piece(*PAY_LEAGUE, frame, **keep)
                line_amount = old_line + amount
                assert signed(r['eax']) == amount
            else:                                            # a cup
                stage = keep['esi'] = random.randint(0, 10)
                g.write(frame - 0x38, struct.pack('<i', amount))
                g.write(frame - 0x34, struct.pack('<I', self.line))
                r, moved = self.piece(*PAY_CUP, frame, eax=amount, **keep)
                line_amount = amount
            assert moved == 0 and r['ebp'] == frame and all(r[k] == keep[k] for k in keep), (case, moved, r, keep)
            line = struct.unpack('<3I', g.read(self.line, 12))
            assert line == (7, stage, line_amount & 0xffffffff) and g.read(self.line + 0x14, 1) == b'\1', (case, line)
            after = [signed(struct.unpack('<I', g.read(self.mode_data + at, 4))[0]) for at in (BALANCE, TRANSFER_BUDGET, SALARY_BUDGET)]
            want = mc.prize_paid(t, amount, number)
            assert (after[0] - before[0], after[1] - before[1], after[2] - before[2]) == want + (0,), (
                case, amount, number, after, before, want)
        self.mode(0x13)

    def bonus_routines(self, n, t):
        """The two bonus routines on their own: the result, and every other register as it was."""
        g, frame = self.g, STACK + STACK_SIZE - 0x2000
        for case in range(n):
            regs = {k: random.getrandbits(32) for k in REG}
            regs['esi'] = random.choice([0, 1000, 3000, 7500, 15000, random.randint(0, 20000)])
            a, b = random.randint(0, 40000), random.randint(0, 400000)
            g.write(frame - 0x50, struct.pack('<I', a))
            g.write(frame - 0x34, struct.pack('<I', b))
            g.write(frame - 0x400, struct.pack('<I', RETURN))
            want = dict(regs)
            if case % 2:
                r, moved = self.piece(mc.BONUS_R_CODE, RETURN, frame, **regs)
                want['esi'] = regs['esi'] * t.bonus // 100 + a
            else:
                r, moved = self.piece(mc.BONUS_END_CODE, RETURN, frame, **regs)
                want['eax'] = (a + b) * t.bonus // 100
            assert moved == 4 and r == dict(want, ebp=frame), (case, moved, r, want)

    def years_cases(self, t):
        g, v = self.g, self.v
        for age in range(64):
            v['age'] = age
            assert g.call(YEARS_LIMIT, [self.pid]) == mc.young_years(t, age), age
        v['age'] = 0


def main(exe):
    random.seed(2017)
    source = open(MODULE, encoding='utf-8').read()
    h = Harness(exe)
    g = h.g

    def old_salary(o, age, x, role, level, rank, band, field20, awards):
        return money.salary(min(o, 255), x, role, level, rank, band, field20, awards)

    def old_fee(o, age, x, position, ident, base, percent, keep):
        return money.fee(base, o, x & 0xfff, percent, keep)

    def new_salary(t):
        def f(o, age, x, role, level, rank, band, field20, awards):
            bonus = money.AGE_BONUS[band]
            return mc.salary(t, o, age, x, money.role_bonus(role, level), rank, bonus + field20 * 20 if bonus else 0, awards)
        return f

    def new_fee(t):
        return lambda o, age, x, position, ident, base, percent, keep: mc.fee(t, o, age, x, position, ident, base, percent, keep)

    def squad_fee(t):
        if t is None:
            return lambda o, age, x, position, ident, salary: money.fee(salary, o, x)
        return lambda o, age, x, position, ident, salary: mc.fee(t, o, age, x, position, ident)

    def check(t, n, squads, top=400000):
        """Every piece of the game the module can change, against money_cave.py with the
        settings t (None: against the game's own formulas). -> (cup cases, league cases)"""
        h.salary_cases(n, old_salary if t is None else new_salary(t))
        h.salary_cases(0, old_salary if t is None else new_salary(t), ranks=range(262))
        h.fee_cases(n, old_fee if t is None else new_fee(t))
        h.budget_cases(squads, squad_fee(t), t, top)
        cups = h.cup_cases(t)
        assert h.cup_other_mode() == mode28, 'the cup prizes of game mode 0x28 changed'
        leagues = h.league_cases(t)
        h.prize_cases(max(80, n // 5), t)
        h.years_cases(t)
        if t is not None and t.bonus is not None:
            h.bonus_routines(200, t)
        return cups, leagues

    def install(source, changed):
        """Runs the module on the clean game; checks what it read, wrote and reported."""
        h.restore()
        t = settings(source)
        lines, reads, writes = run(g, source)
        assert lines[-1] == INSTALLED + changed + '.', lines[-1]
        used = {name: (at, old, new) for name, at, old, new in t.sites()}
        places = tuple((at, len(old)) for at, old, _ in used.values())
        assert inside(reads, READS + places), reads
        assert inside(writes, CAVE + places), writes
        assert g.read(mc.CAVE, mc.CAVE_SIZE) == mc.image(t), 'the tables or routines differ from money_cave.py'
        for name, at, old, _ in mc.SITES:
            assert g.read(at, len(old)) == (used[name][2] if name in used else old), name
        assert [l.split()[1] + (' ' + l.split()[2] if l.split()[3] == 'at' else '') for l in lines if l.startswith('written:')] == list(used)
        return t, lines

    # 0. before the module: the game's own formulas (the harness itself is sound)
    mode28 = h.cup_other_mode()
    cups, leagues = check(None, 300, 40)
    assert all(mc.cup_prize(None, c, s) == a for c, s, a in mc.GAME_CUP_ROWS) and len({r[:2] for r in mc.GAME_CUP_ROWS}) == mc.CUP_ROWS
    print('ok 0: without the module the emulated game gives the amounts of ../tools/money.py (salary with role, '
          'age band and award bonuses at every place of the club ranking; fee); its budget function adds twice '
          'the mean of the 16 highest fees and the wage bill plus twice the mean of the 16 highest salaries; '
          'cup_prize and league_prize give the game\'s lists (%d and %d cases); a prize goes to the balance '
          'only; the contract limit is 3 years up to age 23' % (cups, leagues))

    # 1. the module as it is
    assert mc.lua_block(exe) in source, 'ROUTINES, SITES or CONTEXT of MLMoney.lua are not what money_cave.py makes'
    assert mc.build() == {name: getattr(mc, name) for _, _, name in mc.ROUTINES} if KEYSTONE else True
    everything = ('values, salaries, transfer budget, cup prizes, league prizes, prizes into the transfer budget, '
                  'pay gap, salary bonuses, contract years')
    t, lines = install(source, everything)
    print('\n'.join('    ' + l for l in lines))
    print('ok 1: the module passes its checks, writes only its memory and the places it reports, and what it '
          'wrote is what money_cave.py builds from the same settings')

    n = 3000
    cups, leagues = check(t, n, 150)
    assert (t.prize_share, t.gap, t.bonus, t.young_years) == (75, 3.0, 300, 5)
    assert mc.cup_prize(t, 2, 0) == 821200 and mc.cup_prize(t, 2, 7) == 296200 and mc.league_prize(t, 17, 0, 1) == 531000
    assert mc.prize_paid(t, 821200) == (821200, 615900) and mc.prize_paid(t, 821200, 0x12) == (821200, 0)
    print('ok 2: with the changes in, the game\'s code gives the amounts of money_cave.py: salary and fee for '
          '%d + %d random players (ratings 40 to 255, ages 0 to 63, every position, with and without awards '
          'and the random change) and for every place of the club ranking; the budgets of 150 squads of 0 to '
          '40 players; cup_prize for %d cases (competitions 0 to 100, stages 0 to 12, two game modes; mode '
          '0x28 keeps its own table); league_prize for %d cases (every list, place and half); the two places '
          'that pay a prize, in Master League and four other modes: balance, transfer budget, account line, '
          'registers and stack; the two bonus routines leave every other register as it was; the contract '
          'limit for every age' % (n, n, cups, leagues))

    # 3. the switches, and settings at their limits
    optional = ('SALARY', 'BUDGET_TRANSFER', 'BUDGET_SALARY', 'CUP', 'LEAGUE', 'LEAGUE_2', 'PRIZE_TO_BUDGET',
                'PAY_GAP', 'BONUS', 'YOUNG_YEARS')

    def only(**kept):
        """The module with every optional part off but the ones named (None: as in the file)."""
        text = source
        for name in optional:
            if name not in kept:
                text = setting(text, name, 'false')
            elif kept[name] is not None:
                text = setting(text, name, kept[name])
        return text

    t, _ = install(only(), 'values')
    assert len(t.sites()) == 1
    h.salary_cases(400, old_salary)
    h.fee_cases(400, new_fee(t))
    h.budget_cases(40, squad_fee(t), t)
    assert h.cup_cases(None) and h.league_cases(None)
    h.prize_cases(80, None)
    h.years_cases(None)
    second = '{\n    %s,\n}' % ', '.join('%g' % (7 - 0.25 * i) for i in range(24))
    alone = (('SALARY', None, 'salaries'), ('BUDGET_TRANSFER', None, 'transfer budget'), ('BUDGET_SALARY', '2.5', 'salary budget'),
             ('CUP', None, 'cup prizes'), ('LEAGUE', None, 'league prizes'), ('LEAGUE_2', second, 'league prizes'),
             ('PRIZE_TO_BUDGET', None, 'prizes into the transfer budget'), ('PAY_GAP', None, 'pay gap'),
             ('BONUS', None, 'salary bonuses'), ('YOUNG_YEARS', None, 'contract years'))
    for name, new, label in alone:
        t, _ = install(only(**{name: new}), 'values, ' + label)
        check(t, 150, 10)
    assert t.young_years == 5 and mc.young_years(t, 23) == 5 and mc.young_years(t, 24) == 5 and mc.young_years(None, 23) == 3
    both = setting(setting(source, 'BUDGET_SALARY', '2.5'), 'BUDGET_TRANSFER', '0.1')
    t, _ = install(both, everything.replace('transfer budget, cup', 'transfer budget, salary budget, cup'))
    assert (t.budget_transfer, t.budget_salary) == (10, 250)
    h.budget_cases(60, squad_fee(t), t)
    h.salary_cases(200, new_salary(t))
    plain = setting(setting(setting(source, 'SPREAD', '0'), 'POSITION', '{ %s }' % ', '.join(
        '%s = 100' % p for p in mc.POSITIONS)), 'SALARY_AGE', '{\n    { 20, 100 },\n}')
    t, _ = install(plain, everything)
    h.fee_cases(400, lambda o, age, x, position, ident, base, percent, keep: mc.fee(t, o, age, x, 5, (0, 0), base, percent, keep))
    for o, age, x in ((89, 30, 955), (94, 25, 0), (70, 19, 3000)):
        first = min(mc.CAP, t.value[o] * t.age[age] // 100)
        assert mc.fee(t, o, age, x) == first + first * x * t.fame // 100000      # the formula written out once more
    gaps = ('1', '1.5', '2', '2.75', '7.3', '10')
    for gap in gaps:                                         # the club factor at every place, for several gaps
        t, _ = install(setting(source, 'PAY_GAP', gap), everything)
        assert t.gap == float(gap)
        h.salary_cases(0, new_salary(t), ranks=list(range(262)) * 2)
    for share, bonus, years in (('1', '0', '1'), ('33', '1', '2'), ('100', '1000', '4')):
        t, _ = install(setting(setting(setting(source, 'PRIZE_TO_BUDGET', share), 'BONUS', bonus), 'YOUNG_YEARS', years), everything)
        assert (t.prize_share, t.bonus, t.young_years) == (int(share), int(bonus), int(years))
        h.salary_cases(300, new_salary(t))
        h.prize_cases(200, t)
        h.years_cases(t)
    limits = source
    cup_limits = '{\n%s}' % ''.join('    { %d, %d, %s },\n' % (c, st, ('2000', '0.001', '1234.567')[i % 3])
                                    for i, (c, st, _) in enumerate(mc.GAME_CUP_ROWS))
    for name, new in (('VALUE', '{\n    { 40, 900 }, { 99, 20000 },\n}'), ('AGE', '{\n    { 10, 300 }, { 50, 0 },\n}'),
                      ('POSITION', '{ %s }' % ', '.join('%s = %d' % (p, 200 - 15 * i) for i, p in enumerate(mc.POSITIONS))),
                      ('SPREAD', '30'), ('FAME', '100'), ('SALARY', '{\n    { 40, 500 }, { 99, 100000 },\n}'),
                      ('SALARY_AGE', '{\n    { 10, 200 }, { 50, 0 },\n}'), ('BUDGET_TRANSFER', '10'), ('BUDGET_SALARY', '10'),
                      ('CUP', cup_limits), ('LEAGUE', '{\n    %s,\n}' % ', '.join(['2000', '0'] * 11)),
                      ('LEAGUE_2', '{\n    %s,\n}' % ', '.join(['0', '2000', '0.004'] * 8)), ('PRIZE_TO_BUDGET', '100'),
                      ('PAY_GAP', '10'), ('BONUS', '1000'), ('YOUNG_YEARS', '1')):
        limits = setting(limits, name, new)
    t, _ = install(limits, everything.replace('transfer budget, cup', 'transfer budget, salary budget, cup'))
    assert max(t.value) == mc.CAP and max(t.salary) == mc.MAX_SALARY and max(t.age) == 300 and max(t.salary_age) == 200
    assert sorted({r[2] for r in t.cup_rows}) == [10, 12345670, 20000000] and max(t.league) == max(t.league_2) == 20000000
    check(t, 1500, 150, top=mc.CAP)
    print('ok 3: with every optional part switched off only the fee place is written and salary, prizes and '
          'contract limit are the game\'s own; each of the %d optional parts switched on alone changes its '
          'own places and nothing else; BUDGET_SALARY changes the salary budget; with spread, position and '
          'salary age switched off the value is VALUE x AGE plus popularity; PAY_GAP = %s give the club '
          'factor of money_cave.py at every place of the ranking; with every setting at its limit the code '
          'and money_cave.py still agree' % (len(alone), ', '.join(gaps)))

    # 4. cases in which nothing may be written
    def refused(name, source, prepare, last, sticky=True, may_write_cave=False):
        h.restore()
        prepare()
        before = [(a, g.read(a, n)) for a, n in READS + ALL_SITES]
        lines, reads, writes = run(g, source, sticky)
        assert lines[-1].startswith(last), (name, lines[-1])
        assert inside(reads, READS), name
        if may_write_cave:
            assert writes == [(mc.CAVE, mc.CAVE_SIZE)], (name, writes)
        else:
            assert writes == [] and all(g.read(a, len(d)) == d for a, d in before), name
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
           ('BUDGET_SALARY', setting(source, 'BUDGET_SALARY', '11')),
           ('CUP: entry 1: the game has no prize', source.replace('{ 2, 0, 82.12 }', '{ 2, 5, 82.12 }')),
           ('CUP: entry 14: the amount', source.replace('{ 4, 0, 5 }', '{ 4, 0, 0 }')),
           ('CUP: entry 14: the amount', source.replace('{ 4, 0, 5 }', '{ 4, 0, 2001 }')),
           ('CUP: entry 14 is not', source.replace('{ 4, 0, 5 }', '{ 4, 0 }')), ('CUP is not', setting(source, 'CUP', 'true')),
           ('LEAGUE is not a list of 22', source.replace('2.6, 2.6, 2.6,', '2.6, 2.6,')),
           ('LEAGUE: entry 1 is', source.replace('53.1,', '5310,')), ('LEAGUE: entry 2 is', source.replace('50.4,', '-1,')),
           ('LEAGUE_2 is not a list of 24', setting(source, 'LEAGUE_2', '{ 1, 2, 3 }')),
           ('LEAGUE_2: entry 24 is', setting(source, 'LEAGUE_2', '{ %s }' % ', '.join(['1'] * 23 + ['"x"']))),
           ('PRIZE_TO_BUDGET', setting(source, 'PRIZE_TO_BUDGET', '0')), ('PRIZE_TO_BUDGET', setting(source, 'PRIZE_TO_BUDGET', '101')),
           ('PAY_GAP', setting(source, 'PAY_GAP', '0.5')), ('PAY_GAP', setting(source, 'PAY_GAP', '11')),
           ('BONUS', setting(source, 'BONUS', '-1')), ('BONUS', setting(source, 'BONUS', '1001')),
           ('YOUNG_YEARS', setting(source, 'YOUNG_YEARS', '0')), ('YOUNG_YEARS', setting(source, 'YOUNG_YEARS', '6')),
           ('YOUNG_YEARS', setting(source, 'YOUNG_YEARS', 'true')))
    for name, text in bad:
        assert text != source, name
        refused('bad settings', text, lambda: None, 'RESULT: nothing written. Settings: ' + name)
    refused('write does not stick', source, lambda: None, 'RESULT: the tables could not be written', sticky=False,
            may_write_cave=True)
    h.restore()
    assert h.unchanged()
    check(None, 200, 20)
    print('ok 4: WRITE = false, one changed byte at %d places of the checked code and data, memory not empty, %d '
          'kinds of faulty settings: nothing is written; a write that does not stick: the code is not touched' % (flips, len(bad)))

    # 5. the one player we have screen numbers of
    assert money.fee(72597, 89, 955) * mc.UNIT == 36743200
    assert [o for o in range(60, 100) if any(money.fee(72597, o, x) == 367432 for x in range(3001))] == [89]
    print('ok 5: Bruno Fernandes as the user saw him without a module (rating 89, salary 7,259,700, value '
          '36,743,200): the game\'s formula gives exactly that value from that salary with popularity 955, and '
          'with no other rating from 60 to 99')
    t, exact = settings(source), settings(setting(source, 'SPREAD', '0'))
    assert [x for x in range(3001) if mc.fee(exact, 89, 32, x, 8) * mc.UNIT == 52973200] == [910]
    print('      as the user saw him with version 2 and SPREAD = 0 in a new career (age 32, value 52,973,200): '
          'the module\'s formula gives exactly that for an AMF of rating 89 with popularity 910, and with no '
          'other popularity')
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
