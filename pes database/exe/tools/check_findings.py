"""Self-check of ../NOTES.md and ../MASTER_LEAGUE.md: runs the game's own machine code (emu.py) on real
inputs and compares it with savefile.py, overall.py, money.py, yearplan.py, fixtures.py, clubai.py and
../../tools/rate.py.

    python3 check_findings.py <PES2017.exe> <save file>

Needs `pip install unicorn capstone`. About one and a half minutes.
"""
import hashlib
import os
import struct
import sys

import clubai
import fixtures
import yearplan as year_plan
import fields
import money
import overall
import savefile
from emu import Game
from layout import load, off

sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', '..', 'tools'))

SHA_INIT, SHA_UPDATE, SHA_FINAL, SHA_BLOCK, SHA_DIGEST = 0x0378933e, 0x0378b599, 0x0378be99, 0x037893be, 0x0378aec3
SAME64, STREAM, STREAM_KEY, GAME_NAME, OVERALL = 0x037892be, 0x0378b253, 0x0378b203, 0x03814ee3, 0x04067af3
APPLY_PLAYER_FIELD, APPLY_MANAGER_FIELD = 0x040a04b1, 0x040aadb3
MODE_OBJECT, MENU_OBJECT, PLAYER_RECORD, RANDOM = 0x026503e0, 0x0264f3e8, 0x03822835, 0x03855998
SALARY, FEE, DAY_EVENTS = 0x038ac66e, 0x038ab832, 0x038b0b21
LEAGUE_CREATE, LEAGUE_VTABLE, COMPETITION, NEW_MATCH, NEW, DELETE, FREE = (
    0x03774725, 0x02138c00, 0x03822783, 0x0381e07b, 0x02a000b0, 0x02a000c0, 0x02bc5b9a)
MODE_GETTER, LEVEL_MAX, LEVEL_MIN = 0x0381c0e5, 0x0365d08d, 0x0365d12d


def master_league(exe):
    """Checks 7 to 9. The formulas run as machine code; the functions that would fetch a
    player, a ranking place or a random number are answered with chosen values."""
    import random
    g = Game(exe)
    mode = g.alloc(size=0xf00000)                       # empty mode data: no competitions, no awards
    holder = g.alloc(size=0x40)
    g.write(holder + 0x30, struct.pack('<I', mode))
    g.write(MODE_OBJECT, struct.pack('<I', holder))
    menu = g.alloc(size=0x40)
    g.write(menu + 0x20, struct.pack('<I', 0x13))       # mode number 19 = Master League (kind 12)
    g.write(MENU_OBJECT, struct.pack('<I', menu))
    rec = g.alloc(size=0x400)
    v = {}
    g.replace(PLAYER_RECORD, lambda g, a: rec)
    g.replace(0x03879e04, lambda g, a: 17)               # league of the club: not one of 60, 61, 62
    g.replace(0x02c7d227, lambda g, a: 1)                # "the club is a real one"
    g.replace(0x03138333, lambda g, a: v['rank'])        # place in the club ranking
    g.replace(0x0385400e, lambda g, a: v['band'])
    g.replace(0x0318c209, lambda g, a: 0)                # no award holders
    g.replace(0x0388d14a, lambda g, a: 0)
    g.replace(0x0381e2eb, lambda g, a: a(0))
    g.replace(0x0385adf6, lambda g, a: v['season'])
    g.replace(0x038b0769, lambda g, a: 0)                # the sort of the day's events
    g.replace(RANDOM, lambda g, a: v['random'].pop(0))
    for a in (0x03853b42, 0x03853b52, 0x0383899a):
        g.replace(a, lambda g, a: v['overall'])

    def field(g, a):
        g.write(a(1), struct.pack('<I', v['field20'] if a(0) == 0x20 else 0))
        return 0
    g.replace(0x038278b0, field)
    got_rows = []
    g.replace(0x03365af8, lambda g, a: got_rows.append(struct.unpack('<I', g.read(a(0) + 8, 4))[0]) or 0)

    random.seed(2017)
    pid, team = g.alloc(struct.pack('<II', 1234, 1)), g.alloc(struct.pack('<I', 0x4066))
    zero, number, kind, change = g.alloc(b'\0' * 8), g.alloc(b'\0' * 4), g.alloc(b'\0' * 4), g.alloc(b'\0' * 4)
    g.write(rec + 0x2c, struct.pack('<II', 1234, 1))
    g.write(rec + 0xbc, struct.pack('<h', -1))
    n = 3000
    for _ in range(n):
        o = random.randint(40, 99)
        x = random.choice([0, 800, 801, 1800, 1801, 4095, random.randint(0, 4095)])
        role, level = random.randint(0, 22), random.randint(0, 3)
        v.update(rank=random.choice([1, 250, 251, 300, random.randint(1, 300)]), band=random.randint(0, 7),
                 field20=random.randint(40, 99), overall=o)
        g.write(rec + 0xb4, struct.pack('<II', x << 11, level << 26))
        g.write(rec + 0xc4, bytes([role]))
        g.write(number, struct.pack('<I', o))
        want = money.salary(o, x, role, level, v['rank'], v['band'], v['field20'])
        assert g.call(SALARY, [pid, team, zero, zero, number]) == want, (o, x, role, level, v)
    print('7 ok: the game\'s salary code (fcn_038ac66e) and money.salary give the same amount for %d random players '
          '(awards and title bonuses not run)' % n)

    for _ in range(n):
        o, x, base, given = random.randint(40, 99), random.randint(0, 4095), random.randint(1, 400000), random.choice([0, 0, 777])
        k, own, do = random.choice([0, 1, 2, 3]), random.randint(0, 1), random.randint(0, 1)
        v['overall'] = o
        g.write(rec + 0xb4, struct.pack('<II', x << 11, own << 28))
        g.write(rec + 0xcc, struct.pack('<I', base))
        g.write(number, struct.pack('<I', given))
        g.write(kind, struct.pack('<I', k))
        g.write(change, bytes([do]))
        r, sign = random.randint(0, 49), random.randint(0, 1)
        v['random'] = [] if not do else [r] if k in (1, 2) else [sign, r % 20]
        percent = 0 if not do else (-r or 1) if k == 1 else (r or 1) if k == 2 else ((r % 20) or 1 if sign == 0 else -(r % 20) or 1)
        want = money.fee(given or base, o, x, percent, keep=bool(k and not own))
        assert g.call(FEE, [pid, number, kind, change, g.alloc(b'\1')]) == want, (o, x, base, given, k, own, do, r, sign)
    print('8 ok: the game\'s transfer fee code (fcn_038ab832) and money.fee give the same amount for %d random cases, '
          'with and without the random change' % n)

    table = year_plan.rows(load(exe))
    days = 0
    for mode_number, mode_kind in ((0x13, year_plan.ML), (0x14, year_plan.BL), (0x12, year_plan.LEAGUE), (0, 0)):
        g.write(menu + 0x20, struct.pack('<I', mode_number))
        for january in (0, 1):
            v['season'] = january
            for year in (2016, 2017):
                for flags in ((0, 0, 0, 0), (1, 1, 2, 1)) if year == 2017 else ((0, 0, 0, 0),):
                    g.write(mode + 0xdcb686, bytes([flags[0]]))
                    g.write(mode + 0xdc9d78, struct.pack('<I', 0x56 if flags[1] else 0))
                    g.write(mode + 0xdc9cbc, bytes([flags[2]]))
                    g.write(mode + 0xddce71, bytes([flags[3]]))
                    for month in range(1, 13):
                        for day in range(1, 32):
                            del got_rows[:]
                            g.call(DAY_EVENTS, [g.alloc(b'\0' * 12), g.alloc(struct.pack('<HBB', year, month, day))])
                            want = year_plan.events(table, mode_kind, january, year, month, day, *flags)
                            assert got_rows == want, (mode_kind, january, year, month, day, flags, got_rows, want)
                            days += 1
                            g.top -= 32
    print('9 ok: the game\'s year-plan code (fcn_038b0b21) and yearplan.events put the same events on each day '
          '(%d days: four modes, both season kinds, flags on and off)' % days)


def league_and_levels(exe):
    """Checks 10 and 11. Check 10 runs process::LeagueCreation on a made-up competition of n
    teams with two legs and reads the table it builds; no match record is handed out, so the
    code stops after the table."""
    g = Game(exe)
    box = {}
    g.replace(MODE_GETTER, lambda s, a: box['holder'])
    g.replace(COMPETITION, lambda s, a: box['competition'])
    g.replace(NEW_MATCH, lambda s, a: 0)
    g.replace(NEW, lambda s, a: s.alloc(size=a(0) + 16))
    g.replace(DELETE, lambda s, a: 0)
    g.replace(FREE, lambda s, a: 0)

    def table(n, legs, swap_sides):
        g.free_all()
        competition = g.alloc(size=0x224)
        g.write(competition, struct.pack('<H', 17))
        g.write(competition + 0x148, b''.join(struct.pack('<I', 100 + i) for i in range(n)))
        g.write(competition + 0x21c, struct.pack('<I', (legs << 30) | (n << 16)))
        box['competition'] = competition
        box['holder'] = g.alloc(size=0x40)
        g.write(box['holder'] + 0x30, struct.pack('<I', g.alloc(size=0x100)))
        creator = g.alloc(struct.pack('<I', LEAGUE_VTABLE), size=0x40)
        g.call(LEAGUE_CREATE, [17, swap_sides], ecx=creator)
        first, last = struct.unpack('<2I', g.read(creator + 4, 8))
        assert last - first == 16, 'one table expected for two legs'
        first, last = struct.unpack('<2I', g.read(first, 8))
        rows = []
        for p in range(first, last, 16):
            a, b = struct.unpack('<2I', g.read(p, 8))
            rows.append(list(struct.unpack('<%di' % ((b - a) // 4), g.read(a, b - a))))
        return rows

    sizes = range(2, 25)
    for n in sizes:
        want = fixtures.plan(n)
        assert table(n, 2, 0) == want, n
        assert table(n, 2, 1) == [list(column) for column in zip(*want)], n       # sides changed
        played = sorted(sorted(pair) for matches in fixtures.rounds(n) for pair in matches)
        assert played == sorted([a, b] for a in range(n) for b in range(a + 1, n) for _ in (0, 1)), n
        for matches in fixtures.rounds(n):
            busy = [team for pair in matches for team in pair]
            assert len(busy) == len(set(busy)) and len(matches) == n // 2, n
    print('10 ok: the game\'s league fixture code (fcn_03774725, fcn_037741b4) and fixtures.plan build the same '
          'table for leagues of %d to %d teams with two legs, also with the sides changed' % (sizes[0], sizes[-1]))

    g.free_all()
    p = g.alloc(size=8)
    for level in range(-1, 12):
        g.write(p, struct.pack('<i', level))
        got = (g.call(LEVEL_MIN, [p]) & 0xff, g.call(LEVEL_MAX, [p]) & 0xff)
        assert got == clubai.window(level), (level, got)
    print('11 ok: the game\'s overall window of a computer club (fcn_0365d12d, fcn_0365d08d) is '
          'clubai.LEVEL_MIN / LEVEL_MAX for the levels 0 to 9')


def game_sha(g, data):
    """(context address, digest) from the game's SHA-512 code."""
    ctx, buf, out = g.alloc(size=0xc8), g.alloc(data), g.alloc(size=64)
    g.call(SHA_INIT, ecx=ctx)
    g.call(SHA_UPDATE, [buf, len(data), SHA_BLOCK], ecx=ctx)
    g.call(SHA_FINAL, [SHA_BLOCK], ecx=ctx)
    g.call(SHA_DIGEST, [out, 0x40], ecx=ctx)
    return ctx, g.read(out, 64)


def game_stream(g, key, data):
    k, src, dst = g.alloc(key), g.alloc(data), g.alloc(size=len(data) + 4)
    g.call(STREAM, [src, len(data)], ecx=k, edx=dst)
    return g.read(dst, len(data))


def main(exe, save):
    d = load(exe)
    g = Game(exe)
    raw = open(save, 'rb').read()
    s = savefile.read(save)

    # 1. the master key
    name = g.read(g.call(GAME_NAME), 40).split(b'\0')[0].decode()
    assert name == savefile.GAME_NAME, name
    ctx, digest = game_sha(g, name.encode('utf-16-le'))
    assert digest == savefile.MASTER == s['header'][:64] == hashlib.sha512(name.encode('utf-16-le')).digest()
    print('1 ok: the game\'s hash code is SHA-512; master key = SHA-512 of UTF-16 "%s"; the save header starts with it'
          % name)

    # 2. the stream cipher and the key of each part
    hashes = s['hashes']
    rolling = bytes(64)
    for i in range(5):
        rolling = bytes(a ^ b for a, b in zip(rolling, hashes[64 * i:64 * i + 64]))
    r, k = g.alloc(rolling), g.alloc(size=64)
    g.call(STREAM_KEY, [k, 0xb0, 0], ecx=r)
    key = g.read(k, 64)
    assert key == savefile._stream_key(hashes, 0xb0)
    assert game_stream(g, key, raw[0x140:0x1f0]) == s['header']
    o = 0x1f0 + len(s['description']) + len(s['logo'])
    for n in (1, 2, 3, 4, 5, 15, 16, 17, 4099):                     # short and odd lengths: the first words and the tail
        assert game_stream(g, savefile._stream_key(hashes, 2), raw[o:o + n]) == s['data'][:n], n
    assert savefile.write(s, keep_hashes=True) == raw
    print('2 ok: the game\'s stream code decrypts the header and data as savefile.py does; '
          'savefile.py rewrites the file byte for byte (%d bytes)' % len(raw))

    # 3. what the reader does with the hashes
    assert d[off(0x0378dda1)] == 0xe8 and d[off(0x0378dda6):off(0x0378dda6) + 4] == bytes.fromhex('84c00f85')
    jump = 0x0378ddae + struct.unpack_from('<i', d, off(0x0378dda8) + 2)[0]
    assert jump == 0x0378dcf6            # call same64; test al,al; jne -> the error exit
    true = savefile.true_hashes(s)
    seen = []
    for i, part in enumerate(savefile.PARTS):
        g.free_all()
        ctx, digest = game_sha(g, s[part])
        assert digest == true[64 * i:64 * i + 64]
        stored = g.alloc(hashes[64 * i:64 * i + 64])
        fresh = digest == hashes[64 * i:64 * i + 64]
        same = g.call(SAME64, [stored, 0x40], ecx=ctx) & 0xff
        assert same == 0, 'the reader would take the error exit for the ' + part
        seen.append('%s %s' % (part, 'fresh' if fresh else 'STALE'))
        wrong = g.alloc(bytes(x ^ 0x5a for x in digest))               # a hash that fits no content
        assert g.call(SAME64, [wrong, 0x40], ecx=ctx) & 0xff == 0
        assert g.call(SAME64, [g.alloc(g.read(ctx, 64)), 0x40], ecx=ctx) & 0xff == 1
    g.free_all()
    print('3 ok: the reader compares the stored hash with the hash state in the other byte order; the test '
          'returns "different" and the load goes on, for the right hash and for a wrong one (%s)' % ', '.join(seen))
    res = savefile.check(s)
    assert not any(v == 'FAIL' for v, _ in res), res

    # 4. the overall rating
    import lib
    import rate
    tmp = save + '.data.tmp'
    open(tmp, 'wb').write(s['data'])
    try:
        players = [p for p in lib.P17(tmp).players.values() if p['id']]
    finally:
        os.remove(tmp)
    t = overall.Tables(d)
    assert t.weights == [w for _, w in rate.ROWS] and t.registered == rate.REGISTERED
    assert t.rated_a == rate.RATED_A and t.rated_b == rate.RATED_B and t.blend == rate.BLEND
    buf = g.alloc(size=39 * 4)
    n = 0
    for p in players:
        v = overall.values(p)
        g.write(buf, struct.pack('<39i', *v))
        for f in range(13):
            pos = overall.FILE_POS[f]
            a = g.call(OVERALL, [buf, pos])
            assert a == overall.overall(t, v, pos) == rate.overall(p, f), (p['id'], f, a)
            n += 1
    print('4 ok: the game\'s rating code, overall.py and tools/rate.py give the same number for %d players '
          'at each of the 13 positions (%d results); the tables in rate.py are the ones in the exe' % (len(players), n))

    # 5. the record fields
    g.free_all()
    rows = fields.fields(g, d)
    named = [r for r in rows if r[0] == 'player']
    assert len(named) == 0x6a and all(r[2] for r in named), 'a player field starts where lib.py has no field'
    place = {r[2]: r for r in named}
    assert [place[f][1] for f in fields.EDITED] == list(range(1, 10)) and place['uD'][1] == 11
    assert [place[f][3] for f in fields.EDITED] == [191, 223, 255, 349, 350, 351, 366, 367, 368]
    wider = {'reg_pos': 5, 'injury': 3}                              # the game's field also takes lib.py's next spare bit
    assert all(r[4] == wider.get(r[2], w) for r in named for n, w in lib.F17 if n == r[2])
    out, record = g.alloc(size=8), g.alloc(size=0xbc)
    tab = fields.table(d, fields.TABLES[0][1], 0x6a)
    outside = 0
    for p in players:
        g.write(record, p['raw'])
        for field, reader, _, lo, _, hi, _, _ in tab:
            if 21 <= field <= 44 or field >= 97:                     # abilities and motions: the fields our tools write
                outside += not lo <= fields.read_field(g, reader, record, out) <= hi
    print('5 ok: the game\'s 106 player fields sit where tools/lib.py has them (also 32 team and 11 manager fields, '
          '../output/edit_fields.tsv); %d ability or motion values of the save are outside the game\'s range '
          '(such a field is left as the game has it)' % outside)

    # 6. names and the edited flags
    def applied(function, field, name_at, raw, flag_byte, flag_bit, argument):
        raw = bytearray(raw)
        raw[flag_byte] = raw[flag_byte] & ~(1 << flag_bit) & 0xff
        res = []
        for flag in (0, 1):
            raw[flag_byte] |= flag << flag_bit
            for old in (b'Old Name', b''):
                target = g.alloc(size=0x200)
                g.write(target + name_at, old + b'\0')
                g.call(function, [target, g.alloc(raw), field, argument])
                res.append(g.read(target + name_at, 0x40).split(b'\0')[0] != old)
        return res                                                   # flag 0 / name, flag 0 / no name, flag 1 / name, flag 1 / no name
    p = next(p for p in players if 0 < len(p['name'].encode()) < 16)
    m = next(s['data'][o:o + 0x58] for o in range(0x410118, 0x410118 + 850 * 0x58, 0x58)
             if 0 < len(s['data'][o + 9:o + 0x58].split(b'\0')[0]) < 16)
    for what, call in (('player', (APPLY_PLAYER_FIELD, 0x6a, 0x38, p['raw'], 191 // 8, 191 % 8)),
                       ('manager', (APPLY_MANAGER_FIELD, 0x0b, 0x34, m, 8, 0))):
        assert applied(*call, 0) == [False, True, True, True], what
        assert applied(*call, 1) == [True, True, True, True], what
    marked = sum(p['e_player'] for p in players)
    print('6 ok: on load the game takes a player\'s or manager\'s name from the edit file only if the record\'s '
          'edited flag is 1 or the game has no name for him (%d players of the save have the flag)' % marked)


if __name__ == '__main__':
    main(sys.argv[1], sys.argv[2])
    master_league(sys.argv[1])
    league_and_levels(sys.argv[1])
