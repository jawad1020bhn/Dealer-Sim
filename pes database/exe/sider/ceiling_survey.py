#!/usr/bin/env python3
"""What the price ceilings of MLMoney.lua mean for the squads of an edit file.

    python3 ceiling_survey.py <PES2017.exe> <edit file> [ten ceilings, best clubs first, with commas]

Needs no game. The values are those of money_cave.py with the settings of MLMoney.lua and
SPREAD off. Two things are guessed, because the edit file does not hold them:
  - the club ranking of a career: the clubs are ranked here by the mean overall of their
    best eleven, and cut into the game's ten groups of places (money_cave.LEVEL_PLACES);
  - a player's popularity: 10 points per overall point above 50, plus the club part the
    game gives by club level (0 to 300). With FAME = 10 that moves a value by 0 to 8 percent.
Printed per group: the ceiling, the value of the most valuable and of the third most
valuable player of the middle club, and for all club players inside the group's rating
range the share above the ceiling. Then for the top three rating points of the range,
where a club looks first: the share above the ceiling (all of them passed over with
CEILING_STRETCH = 0), the share a club of the group passes over on average with the
settings of MLMoney.lua, in its usual search and when it is in need (players with a
contract who are not listed), the share no club of the group reaches even in need, and
the mean age of all and of those under the ceiling.
"""
import os
import statistics
import sys
import tempfile

HERE = os.path.dirname(os.path.abspath(__file__))
sys.path[:0] = [HERE, os.path.join(HERE, '..', 'tools'), os.path.join(HERE, '..', '..', 'tools')]
import clubai                                    # noqa: E402
import lib                                       # noqa: E402
import money_cave as mc                          # noqa: E402
import overall                                   # noqa: E402
import savefile                                  # noqa: E402
import test_money                                # noqa: E402

CLUB_PART = (0, 20, 40, 60, 80, 100, 150, 200, 250, 300)     # popularity by club level 0 to 9 (MASTER_LEAGUE.md 6.5)


def players(exe, edit):
    """Every player in a club squad: overall as the game computes it, age, position, club."""
    with tempfile.NamedTemporaryFile(suffix='.dat', delete=False) as f:
        f.write(savefile.read(edit)['data'])
    try:
        e = lib.P17(f.name)
    finally:
        os.unlink(f.name)
    tables = overall.Tables(exe)
    out = []
    for club, team in e.teams.items():
        if not e.isclub(club):
            continue
        for pid, _ in e.squad(club):
            p = e.players.get(pid)
            if p:
                v = overall.values(p)
                out.append(dict(name=p['name'], club=club, o=overall.overall(tables, v, v[0]), age=p['age'],
                                position=p['reg_pos']))
    return out


def main(exe, edit, ceilings=None):
    t = test_money.settings(test_money.two_modules())
    t.spread_low, t.spread_range = 1000, 0
    if ceilings is None:
        ceilings = [c / 10000.0 if c != mc.NO_CEILING else float('inf') for c in reversed(t.ceiling)]
    everyone = players(exe, edit)
    clubs = {}
    for p in everyone:
        clubs.setdefault(p['club'], []).append(p)
    ranked = sorted(clubs, key=lambda c: -sum(sorted((p['o'] for p in clubs[c]), reverse=True)[:11]))
    level_of = {c: mc.level_of_place(i + 1) for i, c in enumerate(ranked)}
    for p in everyone:
        popularity = CLUB_PART[level_of[p['club']]] + 10 * (max(p['o'], 50) - 50)
        p['value'] = mc.value(t, p['o'], p['age'], popularity, p['position']) / 10000.0       # millions on the screen
    print('%d players in %d clubs' % (len(everyone), len(ranked)))
    def passed_over(level, need, some):
        """per player: the share of the 256 steps of the club-and-player hash at which he is refused"""
        reach = sorted({mc.limit(t, level, (h, 0), 0, need) for h in range(4000)})   # every step turns up among these ids
        assert len(reach) in (1, 256)
        return [sum(p['value'] * 10000 > x for x in reach) / len(reach) for p in some]
    print('places    range  ceiling | middle club: best, third | in the range, above the ceiling | top 3 points of '
          'the range: above the ceiling, passed over in the usual search, in need, by every club | mean age of all, '
          'of those under the ceiling')
    for (first, last), level, ceiling in zip(mc.LEVEL_PLACES, range(9, -1, -1), ceilings):
        group = ranked[first - 1:last]
        best = [sorted((p['value'] for p in clubs[c]), reverse=True) for c in group]
        low, high = clubai.window(level)
        inside = [p for p in everyone if low <= p['o'] <= high]
        dear = [p for p in inside if p['value'] > ceiling]
        top = [p for p in inside if p['o'] >= min(high, 91) - 2]
        cheap = [p for p in top if p['value'] <= ceiling]
        t.ceiling[level] = int(ceiling * 10000) if ceiling != float('inf') else mc.NO_CEILING
        usual, need = ([0.0] * len(top),) * 2 if t.ceiling[level] == mc.NO_CEILING else (
            passed_over(level, False, top), passed_over(level, True, top))
        print('%3d-%-4s %2d-%2d  %7.1f | %6.1f %6.1f | %5d %5d (%4.1f %%) | %4.1f %% %4.1f %% %4.1f %% %4.1f %% | %.1f %.1f' % (
            first, last or len(ranked), low, high, ceiling, statistics.median(b[0] for b in best),
            statistics.median(b[2] for b in best if len(b) > 2), len(inside), len(dear),
            100.0 * len(dear) / len(inside), 100.0 * (len(top) - len(cheap)) / len(top), 100 * statistics.mean(usual),
            100 * statistics.mean(need), 100.0 * sum(x == 1 for x in need) / len(top),
            statistics.mean(p['age'] for p in top), statistics.mean(p['age'] for p in cheap) if cheap else 0))


if __name__ == '__main__':
    if len(sys.argv) < 3:
        sys.exit(__doc__)
    main(sys.argv[1], sys.argv[2], [float(x) for x in sys.argv[3].split(',')] if len(sys.argv) > 3 else None)
