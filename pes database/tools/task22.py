"""Task 22: check of player skills, playing styles and COM playing styles, with two corrections. On the output of task21.py.

Bit order and style table: Rigged Wiki, "Pro Evolution Soccer 2017/Edit file" and ".../Tactical" (the 4ccEditor source and
the skill list of the game agree with the bit order).

  1. goalkeeper skills: skill bit 18 is Low Punt Trajectory and bit 20 is GK Long Throw. The source save and `fldb.SKILL`
     had the two the other way round, so every record held the wrong one of the two. Both bits are swapped on every record.
  2. playing styles that PES 2017 never switches on. A style works only at the positions of `WORKS`; the position that
     counts is the one the club fields a starter at, else the registered position.
       - Orchestrator (FL 27 style 20, unknown to PES 2017) was stored as Anchor Man, which works at DMF only. On a
         player who plays CMF or AMF it becomes Classic No. 10, the static playmaker of PES 2017. A starter fielded at
         DMF keeps Anchor Man, and so does a player FL 27 itself calls Anchor Man.
       - Creative Playmaker works for wing forwards and second strikers only. On a player who plays AMF or CMF it
         becomes Classic No. 10 as well (chosen by the user).
       - a style number above 17 (unknown to PES 2017) is converted with the table of `fldb.to17`.
     Other styles without effect (The Destroyer on a centre-back, Box-to-Box on a DMF, Prolific Winger on a wide
     midfielder, ...) stay: PES 2017 has no style that means the same there.
Nothing else changes: no ability, position, overall, squad or line-up.
Usage: python3 task22.py <in data.dat> <out data.dat>          (ends with a report and a self-check of the written file)
"""
import sys, collections
from lib import P17, POS, pack17, norm
import rate, fldb

STYLES = ['None', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man',
          'The Destroyer', 'Extra Frontman', 'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up',
          'Offensive Goalkeeper', 'Defensive Goalkeeper', 'Roaming Flank', 'Cross Specialist', 'Orchestrator', 'Full-back Finisher']
WORKS = {1: 'CF SS', 2: 'CF SS AMF', 3: 'CF', 13: 'CF', 14: 'LWF RWF SS', 4: 'LWF RWF', 5: 'AMF CMF', 6: 'AMF LMF RMF CMF', 7: 'AMF LMF RMF CMF',
         9: 'DMF CMF', 8: 'DMF', 15: 'DMF LB RB CB', 10: 'CB', 11: 'LB RB', 12: 'LB RB', 16: 'GK', 17: 'GK'}
WORKS = {k: v.split() for k, v in WORKS.items()}
def works(style, pos): return style in WORKS and pos in WORKS[style]
def convert(style, pos, fl_style=None):
    """Playing style to store for a player who plays at `pos`. fl_style: his style in FL 27 when FL 27 knows him."""
    if style > 17: style = {18: 4, 19: 4, 20: 8, 21: 11}[style]
    if style == 8 and pos in ('CMF', 'AMF') and fl_style != 8: return 5
    if style == 14 and pos in ('CMF', 'AMF'): return 5
    return style
assert convert(8, 'CMF') == 5 and convert(8, 'CMF', 20) == 5 and convert(8, 'CMF', 8) == 8 and convert(8, 'DMF', 20) == 8
assert convert(20, 'CMF') == 5 and convert(20, 'CB') == 8 and convert(19, 'RMF') == 4 and convert(14, 'AMF') == 5 and convert(14, 'RWF') == 14 and convert(14, 'RMF') == 14 and convert(0, 'CMF') == 0
assert works(5, 'CMF') and works(8, 'DMF') and not works(8, 'CMF') and not works(0, 'CF') and not works(20, 'CMF')

if __name__ != '__main__': sys.exit()
SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); D, A, T = fldb.load()
SK = ['sk%d' % k for k in range(28)]; CM = ['com%d' % k for k in range(7)]
fielded = {}                                            # club starter -> position of his slot in the main formation
for t in pes.teams:
    if not pes.isclub(t): continue
    g = pes.plans[t]; r = pes.rosters[t]; pos = g['presets'][0]['forms'][0]['pos']
    for k in range(11):
        if r[g['xi'][k]][0] and pos[k] < len(POS): fielded[r[g['xi'][k]][0]] = POS[pos[k]]
def plays(i): return fielded.get(i, POS[P[i]['reg_pos']])
def fl(i):
    """His FL 27 record when the id is the same person there (same name)."""
    q = D.get(i); return q if q and not 90000 <= i < 97000 and norm(q['name']) == norm(P[i]['name']) else None

same = [i for i in P if P[i]['name'] and fl(i)]                                  # the two goalkeeper skills against FL 27
def agree(X): return sum((X[i]['sk18'], X[i]['sk20']) == ('GK Low Punt' in D[i]['skills'], 'GK Long Throw' in D[i]['skills']) for i in same)
before = agree(P)
log = collections.Counter(); changed = {}
for i, p in P.items():
    old = dict(p)
    p['sk18'], p['sk20'] = p['sk20'], p['sk18']                                   # 1. goalkeeper skills
    if p['name']:                                                               # 2. styles PES 2017 never switches on
        q = fl(i); p['play_style'] = convert(p['play_style'], plays(i), q['play_style'] if q else None)
    if p['sk18'] != old['sk18']: log['goalkeeper skill bits swapped'] += 1
    if p['play_style'] != old['play_style']:
        log['style: %s -> %s' % (STYLES[old['play_style']], STYLES[p['play_style']])] += 1
    if pack17(p) != pack17(old):
        o = pes.P0 + p['i'] * pes.PSZ; d[o + 16:o + 51] = pack17(p); changed[i] = old
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and new.porder == pes.porder
lo, hi = pes.P0, pes.P0 + pes.np * pes.PSZ
assert new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:], 'bytes outside the player table changed'
for i, p in N.items():
    old = changed.get(i)
    if old is None: assert p['raw'] == pes.players[i]['raw'], 'an unlisted record changed'; continue
    a, b = pes.players[i]['raw'], p['raw']
    assert a[:16] == b[:16] and a[51:] == b[51:], 'more than the ability block changed'
    diff = {k for k in p if k not in ('raw',) and p[k] != old[k]}
    assert diff <= {'sk18', 'sk20', 'play_style'}, (p['name'], diff)
    assert (p['sk18'], p['sk20']) == (old['sk20'], old['sk18']) and rate.overall(p) == rate.overall(old)
    if 'play_style' in diff:
        assert p['name'] and not works(old['play_style'], plays(i)) and (works(p['play_style'], plays(i)) or old['play_style'] > 17), p['name']
assert all(p['play_style'] <= 17 for p in N.values() if p['name']), 'a style PES 2017 does not know is left'
assert not any(p['play_style'] == 8 and plays(i) in ('CMF', 'AMF') and not (fl(i) and fl(i)['play_style'] == 8) for i, p in N.items() if p['name'])
assert not any(p['play_style'] == 14 and plays(i) in ('CMF', 'AMF') for i, p in N.items() if p['name'])
keepers = [i for i in same if (N[i]['sk18'], N[i]['sk20']) != (0, 0) or D[i]['skills'] & {'GK Low Punt', 'GK Long Throw'}]
assert agree(N) > before and agree(N) >= 0.99 * len(same), (agree(N), before, len(same))

# ------------------------------------------------------------------ report
for k, v in sorted(log.items()): print('%-52s %d' % (k, v))
print('the two goalkeeper skills as in FL 27: %d of %d players FL 27 knows, before %d (%d of them have either skill)'
      % (agree(N), len(same), before, len(keepers)))
club = {i for t in new.teams if new.isclub(t) for i, _ in new.squad(t)}
rep = collections.Counter(); pairs = collections.Counter()
for i in same:
    p = N[i]; f = fldb.to17(D[i], fixed=True); g = 'club players' if i in club else 'others'
    rep[g, 'known to FL 27'] += 1
    rep[g, 'skills as in FL 27'] += all(p[k] == f[k] for k in SK); rep[g, 'COM styles as in FL 27'] += all(p[k] == f[k] for k in CM)
    rep[g, 'style as in FL 27'] += p['play_style'] == convert(D[i]['play_style'], plays(i), D[i]['play_style'])
for i, p in N.items():
    if not p['name']: continue
    g = 'club players' if i in club else 'others'; rep[g, 'all'] += 1
    rep[g, 'more than 10 skills'] += sum(p[k] for k in SK) > 10; rep[g, 'more than 5 COM styles'] += sum(p[k] for k in CM) > 5
    rep[g, 'no style'] += p['play_style'] == 0
    if p['play_style'] and not works(p['play_style'], plays(i)):
        rep[g, 'style that does not work where he plays'] += 1
        if i in club: pairs[plays(i), STYLES[p['play_style']]] += 1
for g in ('club players', 'others'):
    print(g + ':', ', '.join('%s %d' % (k, v) for (gg, k), v in rep.items() if gg == g))
print('club players, style without effect (position, style):', ', '.join('%s %s %d' % (a, b, v) for (a, b), v in pairs.most_common(12)))
print('players changed', len(changed), '| bytes changed', sum(x != y for x, y in zip(pes.d, new.d)), '| self-check passed')
