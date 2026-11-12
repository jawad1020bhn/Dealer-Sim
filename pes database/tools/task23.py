"""Task 23: playing styles, skills and COM styles from real matches of 2025-26 and 2026-27, for the club players of the
five leagues whose style PES 2017 never switches on where they play. On the output of task22.py.

The decisions are in task23.tsv (one row per player, with the figures that decided); task23_research.py wrote it from
FBref, Understat and EA FC 27 data and holds the rules. This script only applies the table:
  - `new style`: the playing style, always one PES 2017 switches on at the position he plays (`WORKS` of task22.py)
  - `skills added`, `COM styles added`: set on top of what he has; nothing is removed; at most 10 skills, 5 COM styles
A row without any of the three is a player the research left as he is.
Nothing else changes: no ability, position, overall, squad or line-up.
Usage: python3 task23.py <in data.dat> <out data.dat>          (ends with a report and a self-check of the written file)
"""
import os, sys, csv, collections
from lib import P17, POS, pack17, norm
import rate

STYLES = ['None', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man',
          'The Destroyer', 'Extra Frontman', 'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up',
          'Offensive Goalkeeper', 'Defensive Goalkeeper']
WORKS = {1: 'CF SS', 2: 'CF SS AMF', 3: 'CF', 13: 'CF', 14: 'LWF RWF SS', 4: 'LWF RWF', 5: 'AMF CMF', 6: 'AMF LMF RMF CMF', 7: 'AMF LMF RMF CMF',
         9: 'DMF CMF', 8: 'DMF', 15: 'DMF LB RB CB', 10: 'CB', 11: 'LB RB', 12: 'LB RB', 16: 'GK', 17: 'GK'}       # as in task22.py
WORKS = {k: v.split() for k, v in WORKS.items()}
def works(style, pos): return style in WORKS and pos in WORKS[style]
SK = ['Scissors Feint', 'Flip Flap', 'Marseille Turn', 'Sombrero', 'Cut Behind & Turn', 'Scotch Move', 'Heading', 'Long Range Drive', 'Knuckle Shot',
      'Acrobatic Finishing', 'Heel Trick', 'First-time Shot', 'One-touch Pass', 'Weighted Pass', 'Pinpoint Crossing', 'Outside Curler', 'Rabona',
      'Low Lofted Pass', 'Low Punt Trajectory', 'Long Throw', 'GK Long Throw', 'Malicia', 'Man Marking', 'Track Back', 'Acrobatic Clear', 'Captaincy',
      'Super-sub', 'Fighting Spirit']                                                    # bit order of the game (see task22.py)
COM = ['Trickster', 'Mazing Run', 'Speeding Bullet', 'Incisive Run', 'Long Ball Expert', 'Early Cross', 'Long Ranger']

SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d)
fielded = {}                                            # club starter -> position of his slot in the main formation
for t in pes.teams:
    if not pes.isclub(t): continue
    g = pes.plans[t]; r = pes.rosters[t]; pos = g['presets'][0]['forms'][0]['pos']
    for k in range(11):
        if r[g['xi'][k]][0] and pos[k] < len(POS): fielded[r[g['xi'][k]][0]] = POS[pos[k]]
def plays(i): return fielded.get(i, POS[P[i]['reg_pos']])
club = {i for t in pes.teams if pes.isclub(t) for i, _ in pes.squad(t)}
def nsk(p): return sum(p['sk%d' % k] for k in range(28))
def ncom(p): return sum(p['com%d' % k] for k in range(7))

rows = list(csv.DictReader(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task23.tsv'), encoding='utf-8'), delimiter='\t'))
def dead(X, ids): return sum(bool(X[i]['play_style']) and not works(X[i]['play_style'], plays(i)) for i in ids)
was = dead(P, club), dead(P, [int(r['id']) for r in rows])
log = collections.Counter(); changed = {}; listed = set()
for r in rows:
    i = int(r['id']); p = P[i]; old = dict(p); pos = plays(i); listed.add(i)
    assert i in club and norm(p['name']) == norm(r['name']) and r['plays (* = starter)'].rstrip('*') == pos, r['name']
    assert STYLES[p['play_style']] == r['style before'] and not works(p['play_style'], pos), r['name']
    if r['new style']:
        p['play_style'] = STYLES.index(r['new style']); assert works(p['play_style'], pos), r['name']
        log['style %-3s %s -> %s' % (pos, r['style before'], r['new style'])] += 1
    for s in filter(None, r['skills added'].split('; ')):
        assert not p['sk%d' % SK.index(s)], (r['name'], s)
        p['sk%d' % SK.index(s)] = 1; log['skill ' + s] += 1
    for s in filter(None, r['COM styles added'].split('; ')):
        assert not p['com%d' % COM.index(s)], (r['name'], s)
        p['com%d' % COM.index(s)] = 1; log['COM style ' + s] += 1
    assert nsk(p) <= 10 and ncom(p) <= 5, r['name']
    if pack17(p) != pack17(old):
        o = pes.P0 + p['i'] * pes.PSZ; d[o + 16:o + 51] = pack17(p); changed[i] = old
    else: log['left as he is: ' + ('no data' if r['evidence'].startswith('left alone') else 'the figures support no change')] += 1
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and new.porder == pes.porder
lo, hi = pes.P0, pes.P0 + pes.np * pes.PSZ
assert new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:], 'bytes outside the player table changed'
ALLOWED = {'play_style'} | {'sk%d' % k for k in range(28)} | {'com%d' % k for k in range(7)}
for i, p in N.items():
    old = changed.get(i)
    if old is None: assert p['raw'] == pes.players[i]['raw'], 'an unlisted record changed'; continue
    a, b = pes.players[i]['raw'], p['raw']
    assert a[:16] == b[:16] and a[51:] == b[51:], 'more than the ability block changed'
    diff = {k for k in p if k != 'raw' and p[k] != old[k]}
    assert diff and diff <= ALLOWED and rate.overall(p) == rate.overall(old), (p['name'], diff)
    assert all(p[k] == 1 and old[k] == 0 for k in diff - {'play_style'}), 'a skill or COM style was removed'
    assert nsk(p) <= 10 and ncom(p) <= 5 and p['play_style'] <= 17
    if 'play_style' in diff: assert works(p['play_style'], plays(i)) and not works(old['play_style'], plays(i)), p['name']
assert set(changed) <= listed

# ------------------------------------------------------------------ report
for k, v in sorted(log.items()): print('%-58s %d' % (k, v))
print('listed players (five leagues) with a style without effect: %d before, %d now' % (was[1], dead(N, listed)))
print('all club players with a style without effect: %d before, %d now' % (was[0], dead(N, club)))
print('players changed', len(changed), 'of', len(rows), 'listed | new styles', sum(N[i]['play_style'] != changed[i]['play_style'] for i in changed),
      '| skills added', sum(nsk(N[i]) - nsk(changed[i]) for i in changed), '| COM styles added', sum(ncom(N[i]) - ncom(changed[i]) for i in changed),
      '| bytes changed', sum(x != y for x, y in zip(pes.d, new.d)), '| self-check passed')
