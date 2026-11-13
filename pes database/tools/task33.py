"""Task 33: playing styles outside the five leagues, on the output of task32.py.
Who: squad members of clubs outside England, Spain, Italy, Germany and France whose playing style is None or one that
PES 2017 never switches on where they play (WORKS of task22.py; position: the one in the club's formation for a
starter, else the registered one). Goalkeepers are left alone.
Rules: style() of task23_research.py, unchanged. Evidence:
  match figures   Wyscout 2026-27 / 2026 (wyscout.py), all his league rows added up, 450 minutes or more:
                  non-penalty goals, xG without penalties (0.76 a penalty), shots, shot assists (what Understat calls
                  key passes; Wyscout's own "key passes" are something rarer), xA, crosses per 90. The rules were
                  written for FBref and Understat figures and Wyscout counts lower (more minutes per match, fewer
                  events), so each figure is multiplied by a factor fitted on the five-league players both sources
                  have (least squares through the origin; SCALE below, printed by the run).
                  tackles + interceptions: Wyscout's "successful defensive actions per 90", put on the FBref scale
                  through the two thresholds the rules use (2.2 and 2.7): the Wyscout values that the same share of
                  five-league midfielders reaches (FBref 2026-27 against Wyscout 2026-27, 450 minutes or more)
  abilities       his EA FC 27 card (passing, vision, interceptions ..., PlayStyles), else the file's own abilities
Wyscout has no xG build-up: a centre-back is judged on passing alone. A player with neither 450 Wyscout minutes nor an
EA card is left alone (no evidence), as in task 23.
Usage: python3 task33.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os
_dir = os.path.dirname(os.path.abspath(__file__))
_src = open(os.path.join(_dir, 'task15.py'), encoding='utf-8').read(); _r23 = open(os.path.join(_dir, 'task23_research.py'), encoding='utf-8').read()
def _part(s, a, b): return s[s.index(a):s.index(b)]
_bar = '# ------------------------------------------------------------------ '
exec(compile(_src[:_src.index(_bar + '1. transfers')], 'task15.py set-up', 'exec'))
for a, b in (('STYLES = [', _bar + 'sources'), ('def rows(f)', 'def index(rs)'), ('fielded = {}', 'def evidence(i)'), ('def ge(f, k, x)', 'def extras(')):
    exec(compile(_part(_r23, a, b), 'task23_research.py', 'exec'))
import wyscout, csv

W = wyscout.load()
mw = wyscout.link(W, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '', nation=p['nation'])
                      for i, p in P.items() if i not in leg])
ALL = [t for t in CLUBS if t not in LEGENDS and pes.squad(t)]

# ------------------------------------------------------------------ tackles + interceptions: Wyscout value -> FBref scale
MID = ('DMF', 'LDMF', 'RDMF', 'LCMF', 'RCMF', 'LCMF3', 'RCMF3', 'AMF', 'LAMF', 'RAMF')
BIG5 = ('Premier League 26-27', 'La Liga 26-27', 'Serie A 26-27', 'Bundesliga 26-27', 'Ligue 1 26-27')
fb = sorted(90 * (num(r['TklW']) + num(r['Int'])) / num(r['Min']) for r in rows('optiscout-football-dss/data/players_data_light-2026_2027.csv') if num(r['Min']) >= 450 and 'MF' in r['Pos'])
wy = sorted(num(x['r']['Successful defensive actions per 90']) for w in W.values() for x in w['rows']
            if x['comp'] in BIG5 and x['min'] >= 450 and x['r']['Position'].split(',')[0].strip() in MID)
assert len(fb) > 300 and len(wy) > 300, (len(fb), len(wy))
def same_share(x): return wy[min(len(wy) - 1, round(sum(v < x for v in fb) / len(fb) * len(wy)))]
T22, T27 = same_share(2.2), same_share(2.7); assert T22 < T27
def fbref(v): return 2.2 + (v - T22) * 0.5 / (T27 - T22)

# ------------------------------------------------------------------ the other figures: factor Wyscout -> source of the rules
def _wy5(season):
    """Five-league Wyscout rows of a season by name (full and short, tokens joined)."""
    out = collections.defaultdict(dict)
    for lg in ('Premier League', 'La Liga', 'Serie A', 'Bundesliga', 'Ligue 1'):
        for r in csv.DictReader(open(os.path.join(wyscout.D, '%s %s.csv' % (lg, season)), encoding='utf-8-sig')):
            for k in {''.join(rate.toks(r.get('Full name') or '')), ''.join(rate.toks(r['Player']))} - {''}: out[k][r['Wyscout id'], r['Team']] = r
    return out
def _both(rs, wy, least):
    """(source row, Wyscout row) where the name is unique on both sides and the minutes agree within 10 %."""
    n = collections.Counter(''.join(rate.toks(r['name'])) for r in rs); out = []
    for r in sorted(rs, key=lambda r: r['name']):
        c = list(wy.get(''.join(rate.toks(r['name'])), {}).values())
        if n[''.join(rate.toks(r['name']))] == 1 and len(c) == 1 and r['min'] >= least and abs(num(c[0]['Minutes played']) - r['min']) <= 0.1 * r['min']: out.append((r, c[0]))
    return out
def npxg(xg, pens, m): return max(0.0, xg - 0.76 * pens) * 90 / m             # xG per 90 without penalties
def _factor(pairs, src, wy):
    x = [wy(w) for r, w in pairs]; y = [90 * src(r) / r['min'] for r, w in pairs]; return sum(a * b for a, b in zip(x, y)) / sum(a * a for a in x)
_u = _both(us26, _wy5('25-26'), 900)                                       # Understat 2025-26 against Wyscout 25-26
_f = _both(fb27, _wy5('26-27'), 450)                                            # FBref 2026-27 against Wyscout 26-27
assert len(_u) > 300 and len(_f) > 60, (len(_u), len(_f))
_us = {r['name']: r for r in merge([r for r in rows('asta-fantacalcio/understat_full.csv') if r['season'] == '2526'], 'player', None, dict(min='minutes', sh='shots'))}
SCALE = dict(kp90=_factor(_u, lambda r: r['kp'], lambda w: num(w['Shot assists per 90'])),
             xa90=_factor(_u, lambda r: r['xa'], lambda w: num(w['xA per 90'])),
             xg90=_factor(_u, lambda r: r['xg'], lambda w: npxg(num(w['xG per 90']) * num(w['Minutes played']) / 90, num(w['Penalties taken']), num(w['Minutes played']))),
             sh90=_factor(_u, lambda r: _us[r['name']]['sh'], lambda w: num(w['Shots per 90'])),
             g90=_factor(_f, lambda r: r['g'] - r['pk'], lambda w: num(w['Non-penalty goals per 90'])),
             crs90=_factor(_f, lambda r: r['crs'], lambda w: num(w['Crosses per 90'])))
assert all(1.0 <= v <= 1.5 for v in SCALE.values()), SCALE

def evidence(i):
    p = P[i]; c = ea27.get(m27[i]['id']) if i in m27 else None; w = mw.get(i); m = sum(x['min'] for x in w['rows']) if w else 0
    f = {'ps': {x.strip().rstrip('+') for x in (c['playstyles'] if c else '').split(',') if x.strip()}, 'ea': c is not None, 'stats': m >= 450, 'min': m}
    if m >= 450:
        per = lambda col: sum(num(x['r'].get(col)) * x['min'] for x in w['rows']) / m
        f.update(g90=per('Non-penalty goals per 90'), sh90=per('Shots per 90'), kp90=per('Shot assists per 90'), xa90=per('xA per 90'), crs90=per('Crosses per 90'),
                 xg90=npxg(per('xG per 90') * m / 90, sum(num(x['r'].get('Penalties taken')) for x in w['rows']), m))
        for k in SCALE: f[k] *= SCALE[k]
        f['def90'] = fbref(per('Successful defensive actions per 90'))
    for k in EA: f[k] = num(c[EA[k]]) if c else float(p[OWN[k]])
    f['height'] = num(c['height_cm']) if c and num(c['height_cm']) else p['height']
    f['fin'] = num(c['attacking_finishing']) if c else float(p['finish'])
    return f

works = lambda i: P[i]['play_style'] in WORKS and plays(i) in WORKS[P[i]['play_style']]
todo = [i for t in ALL if t not in TOP5 for i, _ in pes.squad(t) if i not in leg and plays(i) != 'GK' and not works(i)]
changed = {}; was = {i: dict(P[i]) for i in todo}
for i in todo:
    f = evidence(i); pos = plays(i); old = P[i]['play_style']
    if not (f['stats'] or f['ea']): log['left alone: no evidence (under 450 minutes, no EA card)'] += 1; continue
    why = []; s = style(pos, f, why)
    if s is None: log['left alone: the rules give no style at ' + pos] += 1; continue
    assert pos in WORKS[s] and s != old
    P[i]['play_style'] = s; put(i); changed[i] = s; log['style given: ' + STYLES[s]] += 1; log['style given, evidence: ' + ('match figures' if f['stats'] else 'EA card only')] += 1
    rep['style'].append((tname(club[i]), P[i]['name'], pos, STYLES[old] if old < len(STYLES) else str(old), '->', STYLES[s], '; '.join(why)))
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P), 'file size or player ids changed'
lo = pes.P0 + pes.np * pes.PSZ; assert new.d[:pes.P0] == pes.d[:pes.P0] and new.d[lo:] == pes.d[lo:], 'something outside the player records changed'
for i, p in N.items():
    if i in changed: diff = {k for k in p if k != 'raw' and p[k] != was[i][k]}; assert diff == {'play_style'} and p['play_style'] == changed[i] and POS[p['reg_pos']] != 'GK' and plays(i) in WORKS[p['play_style']], ('style', p['name'], diff)
    else: assert p['raw'] == pes.players[i]['raw'], ('a record outside the rule changed', p['name'])
assert set(changed) <= set(todo) and all(club[i] not in TOP5 for i in changed)

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep=dict(rep), log=dict(log)), open(OUT + '.log.pkl', 'wb'))
print('players without a working style outside the five leagues:', len(todo), '| Wyscout thresholds for 2.2 / 2.7: %.2f / %.2f' % (T22, T27))
print('factors Wyscout -> FBref / Understat (%d and %d players in both):' % (len(_u), len(_f)), ', '.join('%s %.3f' % kv for kv in sorted(SCALE.items())))
for k, v in sorted(log.items()): print('%-60s %d' % (k, v))
for x in rep['style'][:120]: print('  ', x)
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
