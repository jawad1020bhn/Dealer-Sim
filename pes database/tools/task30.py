"""Task 30: squads as they are in November 2026, on the output of task29.py.
Source: the Wyscout league tables of 2026-27 (wyscout.py): who has minutes for which first team this season. A file
player is tied to a Wyscout player by full name, age, height and nationality (rate.match_cards); a club of the file is
the Wyscout team most of its squad has minutes for, or the one named in wyscout.NAMED (471 of 496 clubs; Colombia and
Iran are not covered).
  leaves   a) he has minutes for his club and for another team, and the tables say he is at the other one now
           b) he has minutes for other teams only; the match must be the full name, the nationality, age within a
              year and height within 3 cm, and no second Wyscout player may fit; if age or height differ at all,
              Football Life 27 must not list him at the club either. In the five leagues the FotMob squad list
              of the club overrules it.
           c) aged 38 or more, no minutes anywhere in 2026 and neither Football Life 27 nor EA FC 27 has him at the club
           d) the table GONE (web check)
           A second team of the same club (Freiburg II, Valencia Mestalla, Jong Ajax) is not another team.
           A squad keeps at least 16 players and a goalkeeper: beyond that the weakest leavers stay.
  joins    the team he is at now is a club of the file: he joins it as a reserve (free agents the same way). In a
           full squad he takes the place of the weakest reserve without minutes for the club who is weaker than he is.
  eleven   where a starter leaves, the reserve who fits the role best (then the best rated) steps in; takers and
           captain are replaced as in task15.py. task32.py sets the elevens from minutes afterwards. Where the
           bench is empty the place is filled after the joins.
No rating changes and nobody is removed from the file: who leaves without a club in the file is a free agent.
Usage: python3 task30.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
def _part(a, b): return _src[_src.index(a):_src.index(b)]
_bar = '# ------------------------------------------------------------------ '
exec(compile(_src[:_src.index(_bar + '1. transfers')], 'task15.py set-up', 'exec'))
exec(compile(_part('joined = set()', 'def join('), 'task15.py place', 'exec'))
exec(compile(_part('EAPOS = {', 'natof = '), 'task15.py EAPOS', 'exec'))
exec(compile(_part(_bar + 'line-up model', _bar + '3. Premier League'), 'task15.py line-up model', 'exec'))
import wyscout, fotmob

GONE = [  # club, -, name: not in the club's 2026/27 squad on Transfermarkt (13 Nov 2026), no minutes anywhere this season
    ('Leicester City FC', 0, 'Jamaal Lascelles'), ('Leicester City FC', 0, 'Ricardo Pereira'), ('Leicester City FC', 0, 'Jannik Vestergaard'),
    ('Leicester City FC', 0, 'Asmir Begović'), ('Leicester City FC', 0, 'Joe Aribo')]

W = wyscout.load()
mw = wyscout.link(W, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '', nation=p['nation'])
                      for i, p in P.items() if i not in leg]); ev = wyscout.link.ev
ALL = [t for t in CLUBS if t not in LEGENDS and pes.squad(t)]
wmap = wyscout.clubs({t: [i for i, _ in pes.squad(t)] for t in ALL}, mw)
for t in ALL:                                                          # squads too far behind to be recognised by their players
    if tname(t) in wyscout.NAMED: assert t not in wmap; wmap[t] = wyscout.NAMED[tname(t)]
winv = {v: t for t, v in wmap.items()}
assert len(winv) == len(wmap), 'two clubs share a Wyscout team'
listed = {i for ids in fotmob.match(pes, fotmob.squads(pes))[0].values() for i in ids}          # in his club's FotMob list (five leagues)
bytok = collections.defaultdict(list)
for w in W.values():
    for k in set(rate.toks(w['name']) + rate.toks(w['short'])): bytok[k].append(w)
def alone(i):
    """No second Wyscout player of about that age carries every word of the name."""
    w = mw[i]; t = [k for k in rate.toks(P[i]['name']) if len(k) > 1]
    return not any(x is not w and abs(x['age'] - P[i]['age']) <= 1 and set(t) <= set(rate.toks(x['name']) + rate.toks(x['short'])) for x in bytok.get(t[-1], []))
second = wyscout.second
def sure(i):
    lv, cm, nm, da, dh = ev[i]; return lv == 2 and nm and da <= 1 and dh <= 3 and alone(i)
def exact(i): return ev[i][3] == 0 and ev[i][4] <= 1

# ------------------------------------------------------------------ who leaves, and where to
leave = {}                                                             # player id -> (why, new team or None)
for t in ALL:
    n = wmap.get(t)
    for i, _ in pes.squad(t):
        w = mw.get(i)
        if n is None: continue
        if w is None:
            if P[i]['age'] >= 38 and not member(i, t): leave[i] = ('c', None)
            continue
        if any(second(n, x) for x in w['teams']) or w['now'] == n: continue
        if n in w['teams']:
            if w['now']: leave[i] = ('a', w['now'])
        elif sure(i) and (exact(i) or link.get(i) not in flsq.get(t, ())) and not (t in TOP5 and i in listed): leave[i] = ('b', w['now'])
for team, _, name in GONE:
    t, = [t for t in ALL if tname(t) == team]; i, = [i for i, _ in pes.squad(t) if P[i]['name'] == name]; leave[i] = ('d', None)
come = {}                                                              # player id -> club he joins
for i, (why, n) in leave.items():
    if n in winv: come[i] = winv[n]
for i, w in mw.items():
    if i not in club and i not in leg and w['now'] in winv and sure(i): come[i] = winv[w['now']]

gk = lambda i: POS[P[i]['reg_pos']] == 'GK'
for t in ALL:                                                          # a squad keeps 16 players and a goalkeeper: the weakest leavers stay
    ls = [i for i, _ in pes.squad(t) if i in leave]; n = len(pes.squad(t)) - len(ls) + sum(u == t for u in come.values())
    keep = sorted(ls, key=lambda i: (i in come, ovr(i), i))[:max(0, 16 - n)]
    if not any(gk(i) for i, _ in pes.squad(t) if i not in ls) and not any(gk(i) for i in keep): keep += sorted((i for i in ls if gk(i)), key=lambda i: -ovr(i))[:1]
    for i in keep: del leave[i]; come.pop(i, None); log['stays although he plays elsewhere: the squad would fall under 16 or lose its goalkeeper'] += 1; rep['kept'].append((tname(t), P[i]['name'], ovr(i)))

# ------------------------------------------------------------------ apply: leaves first, then joins (best first)
oldnum = {x[0]: x[1] for t in ALL for x in R[t] if x[0]}; was = dict(club); xi0 = {t: [x[0] for x in R[t][:11]] for t in ALL}
_member = member
def member(i, t): return _member(i, t) or (i in mw and wmap.get(t) in mw[i]['teams'])       # place(): minutes for the club count as listed
WHY = dict(a='minutes here, now at another team', b='minutes for other teams only', c='38 or older, no minutes, in no source', d='web check')
def fill(t, k):                                                        # the reserve who fits the role best steps into slot k
    r = R[t]; c = [j for j in range(11, 32) if r[j][0] and gk(r[j][0]) == (roles[t][k] == 'GK')]
    if not c: return False
    j = min(c, key=lambda j: (cost(r[j][0], roles[t][k]), -ovr(r[j][0]), j)); rep['in'].append((tname(t), P[r[j][0]]['name'], roles[t][k]))
    r[k] = r[j]; del r[j]; r.append([0, 0]); return True
for i in sorted(leave, key=lambda i: (not gk(i), i)):                  # the goalkeeper's place is filled first
    t = club.pop(i); r = R[t]; k = next(k for k in range(32) if r[k][0] == i); touched.add(t); log['leaves his club: ' + WHY[leave[i][0]]] += 1
    if k >= 11: del r[k]; r.append([0, 0])
    elif not fill(t, k): r[k] = [0, 0]                                 # nobody left on the bench: filled after the joins
freed = {}
for i in sorted(come, key=lambda i: (-ovr(i), i)):
    t = come[i]; k = next((k for k in range(11, 32) if not R[t][k][0]), None) if not all(x[0] for x in R[t][:11]) else place(t, ovr(i))
    if k is None: log['no room at the new club (free agent)'] += 1; rep['noroom'].append((P[i]['name'], ovr(i), tname(t))); continue
    r = R[t]; old = r[k][0]; used = {x[1] for x in r if x[0] and x[0] != old}
    fl = dict(A[fmap[t]]).get(link.get(i), 0) if t in fmap else 0
    # number: Football Life 27's, his old one, the released player's, 1 for a goalkeeper, the lowest free from 12, from 2
    n = next(x for x in (fl, oldnum.get(i, 0), r[k][1] if old else 0, int(gk(i)), *range(12, 100), *range(2, 12)) if 1 <= x <= 99 and x not in used and (x > 1 or gk(i)))
    r[k] = [i, n]; club[i] = t; joined.add(i); touched.add(t)
    if old: del club[old]; freed[old] = t; log['released to make room'] += 1
    log['joins a club: ' + ('from another club of the file' if i in leave else 'free agent')] += 1
    rep['join'].append((ovr(i), P[i]['name'], tname(was[i]) if i in was else 'free agent', tname(t), n, P[old]['name'] if old else ''))
for t in ALL:
    for k in sorted((k for k in range(11) if not R[t][k][0]), key=lambda k: roles[t][k] != 'GK'): assert fill(t, k), tname(t)
for i in freed: rep['freed'].append((ovr(i), P[i]['name'], tname(freed[i])))
for i in leave:
    if i not in club: rep['free'].append((ovr(i), P[i]['name'], tname(was[i]), leave[i][0], leave[i][1] or ''))

# ------------------------------------------------------------------ write rosters, takers and captains
plan_off = {u32(d, pes.G0 + k * pes.GSZ): pes.G0 + k * pes.GSZ for k in range(pes.nt)}
for t in CLUBS:
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    for k, (pid, n) in enumerate(R[t]): struct.pack_into('<I', d, o + 4 + 4 * k, pid); d[o + 132 + k] = n if pid else 0
    if t not in touched or t not in TK: continue
    xi = [x[0] for x in R[t][:11]]; out = [i for i in xi if POS[P[i]['reg_pos']] != 'GK']; tk = TK[t]
    kicker = max(out, key=lambda i: (P[i]['place_kick'], i))
    tk['takers'] = [i if i in xi else kicker for i in tk['takers']]
    if tk['captain'] not in xi:
        tk['captain'] = max(xi, key=lambda i: (P[i]['sk25'], ovr(i), P[i]['age'], i)); log['captains replaced (the old one no longer starts)'] += 1
        rep['captain'].append((tname(t), P[tk['captain']]['name']))
    q = plan_off[t] + 4 + 480
    for k, i in enumerate(tk['takers']): d[q + 32 + k] = xi.index(i)
    d[q + 41] = xi.index(tk['captain'])
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players; where = collections.Counter()
lo = pes.P0 + pes.np * pes.PSZ; assert len(new.d) == len(pes.d) and new.d[:lo] == pes.d[:lo], 'a player record or the header changed'
assert all(new.teams[t]['raw'] == pes.teams[t]['raw'] for t in pes.teams), 'team data changed'
for t in CLUBS:
    for i, _ in new.squad(t): where[i] += 1
assert all(n != 1 or gk(i) for i in joined for x, n in new.squad(club[i]) if x == i), 'number 1 on an outfield newcomer'
for t in pes.teams:
    a, b = pes.plans[t]['raw'], new.plans[t]['raw']
    assert a[:516] == b[:516] and a[526:] == b[526:], ('formation or line-up order changed', tname(t))       # only takers and captain may
    if t not in ALL: assert new.rosters[t] == pes.rosters[t] and a == b, ('a national or classic team changed', tname(t)); continue
    sq = new.squad(t); ids = [i for i, _ in sq]; nums = [n for _, n in sq]
    if t not in touched: assert new.rosters[t] == pes.rosters[t] and a == b, ('an untouched club changed', tname(t)); continue
    assert len(ids) == len(set(ids)) and 15 <= len(ids) <= 32 and all(x[0] for x in new.rosters[t][:len(ids)]), ('roster', tname(t))
    assert len(nums) == len(set(nums)) or len({n for _, n in pes.squad(t)}) < len(pes.squad(t)), ('shirt numbers', tname(t))
    assert all(1 <= n <= 99 for n in nums) or not all(1 <= n <= 99 for _, n in pes.squad(t)), ('shirt number range', tname(t))
    assert [i for i in ids[:11] if i in xi0[t]] == [i for i in xi0[t] if i not in leave], ('a starter who stays lost his place', tname(t))
    assert sum(POS[N[i]['reg_pos']] == 'GK' for i in ids[:11]) == 1 and sum(POS[N[i]['reg_pos']] == 'GK' for i in ids) >= 1, ('goalkeepers', tname(t))
    assert all(k < 11 for k in new.plans[t]['takers'] + [new.plans[t]['captain']]) or a == b, ('taker or captain outside the eleven', tname(t))
assert max(where.values()) == 1, 'a player is in two clubs'
for i in leave: assert where[i] == (i in club) and club.get(i) != was[i], ('still at his old club', P[i]['name'])
for i, t in come.items(): assert i not in club or (club[i] == t and i in [x for x, _ in new.squad(t)]), ('join', P[i]['name'])
for i in freed: assert where[i] == 0, ('released', P[i]['name'])
assert all(where[i] == 1 for i in was if i not in leave and i not in freed), 'somebody else lost his club'

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep=dict(rep), log=dict(log), leave=leave, come=come), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-60s %d' % (k, v))
print('-- joins (best 40 of %d): rating, player, from, to, number, released' % len(rep['join']))
for x in sorted(rep['join'], reverse=True)[:40]: print('  ', x)
print('-- now free agents (best 40 of %d): rating, player, old club, rule, new team' % len(rep['free']))
for x in sorted(rep['free'], reverse=True)[:40]: print('  ', x)
print('clubs changed', len(touched), '| smallest squads', sorted((len(new.squad(t)), tname(t)) for t in ALL)[:12])
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
