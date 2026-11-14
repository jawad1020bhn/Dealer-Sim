"""Prize money of the career modes, read from PES2017.exe.

    python3 prize.py <PES2017.exe>
    python3 prize.py <PES2017.exe> check     runs the game's cup function on every pair

Prints the amounts as they are stored; the screens show them times 100.

Cups: `cup_prize` (fcn_038aa307(&competition, &stage, &club)) looks the pair
(competition, stage) up in a table of 12-byte rows (competition, stage, amount):
73 rows at 0x0216b178 for Master League, 26 rows at 0x0216b4e8 for game mode 0x28.
A cup that is not in the Master League table gets the amounts of FALLBACK.
Leagues: `league_prize` (fcn_038a9ebb(&club, &place, &half)) builds four lists on
its stack and picks one by the league and the division; it is run here in the
emulator for every place (needs `pip install unicorn`).
The stage comes from `cup_stage` (fcn_038a9115); the names in STAGES are inferred
from that function and from the order of the amounts, they were not seen in a game.
"""
import struct
import sys

from layout import load, off

CUP_TABLE, CUP_ROWS = 0x0216b178, 73
MODE28_TABLE, MODE28_ROWS = 0x0216b4e8, 26
CUP_PRIZE, LEAGUE_PRIZE = 0x038aa307, 0x038a9ebb
FALLBACK = {0: 20000, 1: 10000, 2: 5000, 3: 5000, 4: 1000, 5: 500, 6: 300}     # switch at 0x038aa42b
NO_PRIZE = (0x2d, 0x2e, 0x2f, 0x36, 0x37, 0x46, 0x47, 0x48)                    # compared at 0x038aa35a
STAGES = {0: 'winner', 1: 'runner-up', 2: 'third', 3: 'semi-final', 4: 'quarter-final',
          5: 'round of 16', 6: 'round of 32', 7: 'first knock-out round',
          8: 'group, at a place that goes on', 9: 'out in the group', 10: 'out in the league part'}
# Numbers 1, 5 and 73-84 are the entries of the edit file with these names; the rest are
# taken from the order of the list (2, 3, 4, 6, 7 and 8 have no entry in the edit file).
NAMES = {1: 'Club World Cup', 2: 'Champions League', 3: 'Europa League', 4: 'UEFA Super Cup',
         5: 'Libertadores', 6: 'Copa Sudamericana', 7: 'Recopa', 8: 'AFC Champions League',
         73: 'super cup England', 74: 'super cup Spain', 75: 'super cup France',
         76: 'super cup Italy', 77: 'super cup Netherlands', 78: 'super cup Portugal',
         79: 'super cup Argentina', 82: 'super cup Germany', 84: 'super cup (entry 84)'}


def rows(d, table, count):
    return [struct.unpack_from('<iii', d, off(table) + 12 * i) for i in range(count)]


def cups(d, table=CUP_TABLE, count=CUP_ROWS):
    """-> {competition: {stage: amount}} in the order of the table."""
    out = {}
    for competition, stage, amount in rows(d, table, count):
        out.setdefault(competition, {})[stage] = amount
    return out


def league_lists(exe, places=27):
    """Runs league_prize for every place. -> {name: [amount for place 0 .. places-1]}."""
    from emu import Game
    g = Game(exe)
    state = {}
    record = g.alloc(size=0x400)
    mode = g.alloc(size=0x40)
    g.replace(0x0381c0e5, lambda g, a: mode)                 # mode object
    g.replace(0x03879e04, lambda g, a: state['league'])      # league of the club
    g.replace(0x03822ab9, lambda g, a: record)               # record of the league
    club, place, half = g.alloc(struct.pack('<I', 100)), g.alloc(size=4), g.alloc(size=4)

    def prize(league, division, p, h=0):
        state['league'] = league
        g.write(record + 0x218, struct.pack('<I', division << 30))
        g.write(place, struct.pack('<I', p))
        g.write(half, struct.pack('<I', h))
        return struct.unpack('<i', struct.pack('<I', g.call(LEAGUE_PRIZE, [club, place, half])))[0]

    out = {}
    for name, league, division, h in (('league, division bits 0 or 1', 17, 1, 0),
                                      ('league, division bits 2 or 3', 17, 2, 0),
                                      ('league number 60', 60, 0, 0),
                                      ('league number 61', 61, 0, 0),
                                      ('half season (league 0x3458 or 0x27d8, half 1)', 0x3458, 0, 1),
                                      ('half season (league 0x3459 or 0x27d9, half 2)', 0x3459, 0, 2)):
        out[name] = [prize(league, division, p, h) for p in range(places)]
    return out


def check(exe):
    """Runs cup_prize in the emulator for every (competition, stage) and compares it with
    the tables as this file reads them. -> (cases, differences)."""
    from emu import Game
    d, g = load(exe), Game(exe)
    holder = g.alloc(size=0x40)
    g.replace(0x038a4ebb, lambda g, a: 0)                    # two "is a league" style tests
    g.replace(0x038a4f07, lambda g, a: 0)
    g.replace(0x03808865, lambda g, a: holder)               # holder + 0x20 = game mode
    competition, stage, club = g.alloc(size=4), g.alloc(size=4), g.alloc(struct.pack('<I', 100))

    def run(c, s, mode):
        g.write(holder + 0x20, struct.pack('<I', mode))
        g.write(competition, struct.pack('<I', c))
        g.write(stage, struct.pack('<I', s))
        return g.call(CUP_PRIZE, [competition, stage, club])

    cases = differ = 0
    table = cups(d)
    for c in list(table) + [15, 42, 99] + list(NO_PRIZE):
        for s in range(13):
            if s == 11 or c in NO_PRIZE:
                want = 0
            else:
                want = table.get(c, {}).get(s) or FALLBACK.get(s)
            if want is None:                                 # stage past the switch: eax is left as it was
                continue
            cases += 1
            differ += run(c, s, 0) != want
    for c, s, amount in rows(d, MODE28_TABLE, MODE28_ROWS):
        first = next(a for c2, s2, a in rows(d, MODE28_TABLE, MODE28_ROWS) if (c2, s2) == (c, s))
        cases += 1
        differ += run(c, s, 0x28) != first
    return cases, differ


def main(exe):
    d = load(exe)
    for title, table, count in (('Master League cups (0x%08x)' % CUP_TABLE, CUP_TABLE, CUP_ROWS),
                                ('game mode 0x28 (0x%08x)' % MODE28_TABLE, MODE28_TABLE, MODE28_ROWS)):
        print(title)
        for competition, stages in cups(d, table, count).items():
            name = NAMES.get(competition, '') if table == CUP_TABLE else ''
            print('  %3d %-22s %s' % (competition, name, ', '.join(
                '%d: %s' % (s, format(a, ',')) for s, a in sorted(stages.items()))))
    print('any other cup in Master League: ' + ', '.join(
        '%d: %s' % (s, format(a, ',')) for s, a in FALLBACK.items()))
    print('no prize: competitions ' + ', '.join(str(c) for c in sorted(NO_PRIZE)) + ', and stage 11')
    print('stages: ' + '; '.join('%d %s' % kv for kv in STAGES.items()))
    for name, amounts in league_lists(exe).items():
        last = max(i for i, a in enumerate(amounts) if a) if any(amounts) else 0
        print(name + ', place 1 to %d:' % last)
        print('  ' + ', '.join(format(a, ',') for a in amounts[1:last + 1]))


if __name__ == '__main__':
    if len(sys.argv) == 3 and sys.argv[2] == 'check':
        cases, differ = check(sys.argv[1])
        print('cup_prize run on %d pairs, %d differ from the tables' % (cases, differ))
        sys.exit(1 if differ else 0)
    if len(sys.argv) != 2:
        sys.exit(__doc__)
    main(sys.argv[1])
