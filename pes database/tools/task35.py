"""Task 35: ratings outside the five leagues, checked and corrected; on the output of task34.py.
1. cards     A club player outside England, Spain, Italy, Germany and France whose EA FC 27 card is his own gets the
             card's rating, as task 12 ruled. His own: full name, age within 2 years, and the card is at his club or
             at a club he has Wyscout minutes for this season (he moved after EA's list). The gaps came later: players
             built by task 31 at the median of their club although EA rates them, cards matched only since a move.
             Any other card at another club is left alone (a namesake).
2. check     Players without an EA FC 27 card against the Wyscout minutes of 2026-27: expected rating = level of the
             club + what his share of the club's minutes and his age are worth, fitted on the players outside the
             five leagues who do have a card (club level: its rated players; a club with fewer than 6 of them: its
             own squad). The fit misses a held-out rated player by 3.4 points (root mean square).
3. regulars  A player without a card who has 45 % of the minutes of the club's most-used player or more and is rated
             7 or more below the expectation rises to the lower edge of it (expectation - the miss of the fit,
             rounded down), but not above the Football Life 27 estimate where there is one, and by 5 points at most
             (the cap of task 14). Nobody is lowered: a highly rated player without minutes may be injured.
             A player with a card keeps EA's rating whatever he plays.
Usage: python3 task35.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os, statistics
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
exec(compile(_src[:_src.index('# ------------------------------------------------------------------ 1. transfers')], 'task15.py set-up', 'exec'))
import wyscout

OUT5 = [t for t in CLUBS if t not in TOP5 and t not in LEGENDS and pes.squad(t)]
squad = [i for t in OUT5 for i, _ in pes.squad(t)]; ev = rate.match_cards.ev          # (name level, club, nation, age gap, height gap)

W = wyscout.load(); mw = wyscout.link(W, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '', nation=p['nation'])
                                         for i, p in P.items() if i not in leg])
wmap = wyscout.clubs({t: [i for i, _ in pes.squad(t)] for t in CLUBS if t not in LEGENDS and pes.squad(t)}, mw)
for t in OUT5:
    if tname(t) in wyscout.NAMED: wmap[t] = wyscout.NAMED[tname(t)]

# ------------------------------------------------------------------ 1. the EA rating where the card is his own
def played(i, c):
    """He has Wyscout minutes this season for the club of the card."""
    k = norm(c['club']); return len(k) >= 5 and i in mw and any(len(norm(x['team'])) >= 5 and (norm(x['team']) in k or k in norm(x['team'])) for x in mw[i]['rows'])
changed = {}
for i in squad:
    c = m27.get(i)
    if c is None or ovr(i) == c['ovr']: continue
    if not (ev[i][0] == 2 and ev[i][3] <= 2 and (ev[i][1] or played(i, c))):
        rep['card elsewhere'].append((P[i]['name'], tname(club[i]), ovr(i), c['name'], c['club'], c['ovr'])); log['card differs, at a club he has no minutes for: left alone'] += 1; continue
    was = ovr(i); assert rate.retarget(P[i], c['ovr']), (P[i]['name'], c['ovr'])
    put(i); changed[i] = c['ovr']; rep['rating'].append((P[i]['name'], P[i]['age'], tname(club[i]), was, '->', c['ovr'])); log['rating set to the EA FC 27 card'] += 1
# ------------------------------------------------------------------ 2. check against Wyscout minutes
most = collections.Counter()                                                           # most minutes of one player per Wyscout team
for w in W.values():
    for tm in {x['team'] for x in w['rows']}: most[tm] = max(most[tm], wyscout.minutes(w, tm))
share = lambda i: (wyscout.minutes(mw[i], wmap[club[i]]) if i in mw else 0) / most[wmap[club[i]]]
SB = lambda s: 0 if s == 0 else 1 if s < .1 else 2 if s < .25 else 3 if s < .45 else 4 if s < .65 else 5 if s < .85 else 6
AB = lambda a: 0 if a <= 18 else 1 if a <= 20 else 2 if a <= 22 else 3 if a <= 25 else 4 if a <= 29 else 5 if a <= 32 else 6
rows = [(i, club[i], (SB(share(i)), AB(P[i]['age']), POS[P[i]['reg_pos']] == 'GK')) for i in squad if most[wmap.get(club[i])]]
rated = [r for r in rows if r[0] in m27 and ovr(r[0]) == m27[r[0]]['ovr']]
def fit(train):
    """Club level L and the worth H of (minutes share, age, goalkeeper), each the mean of what the other leaves over."""
    L = collections.defaultdict(float); H = collections.defaultdict(float)
    for _ in range(12):
        for tab, key, other in ((L, 1, 2), (H, 2, 1)):
            acc = collections.defaultdict(list)
            for r in train: acc[r[key]].append(ovr(r[0]) - (H if tab is L else L)[r[other]])
            tab.clear(); tab.update({k: statistics.mean(v) for k, v in acc.items()})
    return L, H, collections.Counter(r[1] for r in train), collections.Counter(r[2] for r in train)
rms = lambda v: (sum(x * x for x in v) / len(v)) ** .5
miss = []                                                                              # held out: a fifth of the rated players at a time
for f in range(5):
    L, H, nl, nh = fit([r for r in rated if r[0] % 5 != f])
    miss += [(ovr(i) - L[t] - H[k], k[0]) for i, t, k in rated if i % 5 == f and nl[t] >= 6 and nh[k] >= 15]
L, H, nl, nh = fit(rated)
own = collections.defaultdict(list)
for i, t, k in rows: own[t].append(ovr(i) - H[k])
level = {t: L[t] if nl[t] >= 6 else statistics.mean(v) for t, v in own.items() if nl[t] >= 6 or len(v) >= 12}
gap = [(ovr(i) - level[t] - H[k], i, k[0]) for i, t, k in rows if i not in m27 and t in level and nh[k] >= 15]
part = lambda v, f: '%d of %d (%.1f%%)' % (sum(map(f, v)), len(v), 100 * sum(map(f, v)) / len(v))

# ------------------------------------------------------------------ 3. regulars rated far below the expectation
MISS = rms([m for m, _ in miss])
for g, i, s in sorted(gap):
    if s < 4 or g > -7: continue
    fl = EST.get(rate.overall(fldb.to17(D[link[i]]))) if i in link else None; was = ovr(i)
    tg = min(int(was - g - MISS), was + 5, fl or 99)
    if tg <= was: log['regular far below, but the Football Life 27 estimate is no higher: left alone'] += 1; continue
    assert rate.retarget(P[i], tg), (P[i]['name'], tg)
    put(i); changed[i] = tg; rep['regular'].append((P[i]['name'], P[i]['age'], tname(club[i]), was, '->', tg, 'expected %.1f' % (was - g), 'FL %s' % fl)); log['regular raised'] += 1
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
lo = pes.P0 + pes.np * pes.PSZ; assert len(new.d) == len(pes.d) and new.d[:pes.P0] == pes.d[:pes.P0] and new.d[lo:] == pes.d[lo:], 'something outside the player records changed'
for i, p in N.items():
    if i in changed: assert rate.overall(p) == changed[i] and p['reg_pos'] == pes.players[i]['reg_pos'] and p['name'] == pes.players[i]['name'] and club[i] not in TOP5 and i not in leg, p['name']
    else: assert p['raw'] == pes.d[off(i):off(i) + pes.PSZ], ('a record outside the rule changed', p['name'])

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep=dict(rep), log=dict(log), gap=[(g, P[i]['name'], tname(club[i]), ovr(i), s) for g, i, s in gap]), open(OUT + '.log.pkl', 'wb'))
nocard = [i for i in squad if i not in m27]
print('players outside the five leagues: %d at %d clubs | EA FC 27 card: %d, rating equal before: %d' % (len(squad), len(OUT5), len(squad) - len(nocard), sum(ovr(i) == m27[i]['ovr'] for i in squad if i in m27) - log['rating set to the EA FC 27 card']))
print('no card: %d (Football Life 27 knows %d, no source %d) | at a club without a Wyscout team: %d' % (len(nocard), sum(i in link for i in nocard), sum(i not in link for i in nocard), len(squad) - len(rows)))
for k in sorted(log):
    if 'fantasy' not in k: print('%-60s %d' % (k, log[k]))
for k in ('rating', 'card elsewhere', 'regular'):
    for x in rep[k]: print('  ', x)
print('check: fitted on %d rated players; a held-out one is missed by %.2f (rms), within 5 points: %s' % (len(rated), rms([m for m, _ in miss]), part([m for m, _ in miss], lambda m: abs(m) <= 5)))
print('   players without a card judged: %d | mean gap (file - expected) %+.2f, rms %.2f' % (len(gap), statistics.mean(g for g, *_ in gap), rms([g for g, *_ in gap])))
print('   no source at all: mean gap %+.2f, rms %.2f' % (statistics.mean(g for g, i, _ in gap if i not in link), rms([g for g, i, _ in gap if i not in link])))
reg = [g for g, _, s in gap if s >= 4]; regr = [m for m, s in miss if s >= 4]
print('   regulars (45 %% of the minutes or more) rated 7+ below: %s; among rated players: %s' % (part(reg, lambda g: g <= -7), part(regr, lambda m: m <= -7)))
print('   regulars rated 7+ above: %s; among rated players: %s' % (part(reg, lambda g: g >= 7), part(regr, lambda m: m >= 7)))
idle = [g for g, _, s in gap if s == 0]; idler = [m for m, s in miss if s == 0]
print('   no minutes, rated 7+ above: %s; among rated players: %s' % (part(idle, lambda g: g >= 7), part(idler, lambda m: m >= 7)))
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
