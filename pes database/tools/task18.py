"""Task 18: lopsided back-three formations, on the output of task17.py.
In 22 clubs the main formation has three centre-backs with a full-back on one side and a winger on the other (the two
wing-backs of the Football Life 27 formation, each given the role of his registered position by an earlier task).
  - Football Life 27 plays three centre-backs with wide midfielders: both become RMF / LMF
  - Football Life 27 plays three centre-backs with full-backs:       both become RB / LB at (15, 88) / (15, 16)
  - no Football Life 27 formation for the club:                      RMF / LMF at (25, 88) / (25, 16), the most common
    wing-back spot of back-three formations in the original save
  - RMF / LMF depth and width are those of Football Life 27, moved to the nearest spot the original 2017 save uses
    (depth 23, 25 ... 33; width 12, 16, 20 from the touchline), the same depth and width on both sides
  - the starter in such a slot who is not rated A for the new role is raised to A
Nothing else changes: the other eight roles, the second and third preset, clubs with four defenders, line-ups.
The set-up (links, club maps) is that of task15.py, run from its source.
Usage: python3 task18.py <in data.dat> <out data.dat> <FL save data.dat>      (ends with a self-check of the written file)
"""
import os
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
exec(compile(_src[:_src.index('# ------------------------------------------------------------------ 1. transfers')], 'task15.py set-up', 'exec'))
from lib import FL
fl = FL(sys.argv[3]); WIDE = ('LB', 'RB', 'LMF', 'RMF', 'LWF', 'RWF')
def form(t, f=0): return pes.plans[t]['presets'][0]['forms'][f]
def roles(t): return [POS[x] for x in form(t)['pos']]
def lopsided(r): return r.count('CB') == 3 and r.count('LB') != r.count('RB')
def snap(v, grid): return min(grid, key=lambda g: (abs(g - v), g))
assert snap(24, (23, 25, 27)) == 23 and snap(9, (12, 16, 20)) == 12 and lopsided(['CB'] * 3 + ['LB', 'RWF']) and not lopsided(['CB'] * 3 + ['LB', 'RB'])

plan_off = {u32(d, pes.G0 + k * pes.GSZ): pes.G0 + k * pes.GSZ for k in range(pes.nt)}
todo = [t for t in CLUBS if lopsided(roles(t))]; changed = {}; raised = {}
for t in todo:
    f0 = form(t); w = [k for k in range(11) if POS[f0['pos'][k]] in WIDE]
    assert len(w) == 2 and all(form(t, j)['pos'] == f0['pos'] and form(t, j)['yx'] == f0['yx'] for j in (1, 2)), ('unexpected formation', tname(t))
    rk, lk = sorted(w, key=lambda k: -f0['yx'][k][1]); assert f0['yx'][rk][1] > 52 > f0['yx'][lk][1], ('wide men on one side', tname(t))
    src = fl.plans.get(fmap.get(t)); fr = [POS[x] for x in src['presets'][0]['pos']] if src else []; fyx = src['presets'][0]['yx'] if src else []
    if fr.count('CB') == 3 and 'RMF' in fr and 'LMF' in fr:
        (ry, rx), (ly, lx) = fyx[fr.index('RMF')], fyx[fr.index('LMF')]; y = snap((ry + ly) / 2, (23, 25, 27, 29, 31, 33))
        x = snap((104 - rx + lx) / 2, (12, 16, 20)); new = {rk: ('RMF', (y, 104 - x)), lk: ('LMF', (y, x))}; how = 'FL 27: wide midfielders'
    elif fr.count('CB') == 3 and 'RB' in fr and 'LB' in fr: new = {rk: ('RB', (15, 88)), lk: ('LB', (15, 16))}; how = 'FL 27: full-backs'
    else: new = {rk: ('RMF', (25, 88)), lk: ('LMF', (25, 16))}; how = 'no FL 27 back three' if src else 'no FL 27 team'
    log[how] += 1; o = plan_off[t] + 4; ro = pes.rosters[t]; xi = pes.plans[t]['xi']; line = []
    for k, (role, (y, x)) in new.items():
        for j in range(3): d[o + j * 33 + k] = POS.index(role); d[o + j * 33 + 11 + 2 * k] = y; d[o + j * 33 + 12 + 2 * k] = x
        i = ro[xi[k]][0]; was = 'CBA'[P[i]['pp_' + role]]
        if was != 'A': P[i]['pp_' + role] = 2; put(i); raised[i] = role; log['starter raised to A for the new role (from %s)' % was] += 1
        line.append('%s %s %s -> %s %s%s' % (P[i]['name'], POS[f0['pos'][k]], f0['yx'][k], role, (y, x), '' if was == 'A' else ', rated %s -> A' % was))
    changed[t] = new; rep['club'].append((tname(t), how, '; '.join(line)))
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and new.rosters == pes.rosters, 'file size, players or squads changed'
for i in P:
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    if i not in raised: assert a == b, ('a player outside the raised ones changed', P[i]['name']); continue
    assert a[:16] == b[:16] and a[51:] == b[51:] and N[i]['pp_' + raised[i]] == 2 and rate.overall(N[i]) == before[i], ('raised player', P[i]['name'])
    assert all(N[i][k] == pes.players[i][k] for k in N[i] if k not in ('raw', 'pp_' + raised[i])), ('more than one position rating changed', P[i]['name'])
for t in new.teams:
    a, b = pes.plans[t], new.plans[t]
    assert new.teams[t]['raw'] == pes.teams[t]['raw']
    if t not in changed: assert a['raw'] == b['raw'], ('a club outside the 22 changed', tname(t)); continue
    assert a['raw'][4 + 99:] == b['raw'][4 + 99:], ('second or third preset, line-up or settings changed', tname(t))
    for j in range(3):
        fa, fb = a['presets'][0]['forms'][j], b['presets'][0]['forms'][j]; r = [POS[x] for x in fb['pos']]
        for k in range(11):
            if k not in changed[t]: assert fa['pos'][k] == fb['pos'][k] and fa['yx'][k] == fb['yx'][k], ('another role changed', tname(t)); continue
            assert (r[k], fb['yx'][k]) == changed[t][k] and N[new.rosters[t][b['xi'][k]][0]]['pp_' + r[k]] == 2, ('wide role', tname(t))
        wide = sorted(x for x in r if x in WIDE); assert r.count('CB') == 3 and wide in (['LMF', 'RMF'], ['LB', 'RB']), ('still lopsided', tname(t))
        (y1, x1), (y2, x2) = [fb['yx'][k] for k in changed[t]]; assert y1 == y2 and x1 + x2 == 104, ('wide men not level', tname(t))
assert len(changed) == len(todo) and not any(lopsided([POS[x] for x in new.plans[t]['presets'][0]['forms'][0]['pos']]) for t in CLUBS), 'a lopsided club is left'

# ------------------------------------------------------------------ report
for k, v in sorted(log.items()):
    if 'fantasy' not in k: print('%-60s %d' % (k, v))
for x in rep['club']: print('  ', x)
print('clubs changed', len(changed), '| players raised', len(raised), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
