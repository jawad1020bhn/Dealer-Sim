"""Task 32: line-ups, set-piece takers and captains outside the Premier League, on the output of task31.py.
(The Premier League has them from the fantasy data, task15.py.) Clubs: those with a Wyscout team (wyscout.py).
  eleven    a reserve comes in for a starter if he has 180 minutes more for the club this season, is rated at most
            3 points lower (goalkeepers: any rating; a starter kept by his rating may be injured) and puts nobody new
            out of position. Most minutes gained first. Keeping their place: a starter Wyscout does not know or has
            no minutes for at the club (injured all season, or tied to a namesake), and the captain of the table.
            A reserve who came in stays in, a starter who went out stays out.
  takers    from the starters' Wyscout counts for the club (per 90 x minutes): direct free kicks (2 or more: first and
            second taker), corners (5 or more; with a left and a right foot both corners swing in), penalties taken.
  captain   the table CAPTAIN (club announcements collected by the press, August and September 2026), if he starts.
            Otherwise as before: a captain or taker who no longer starts is replaced as in task15.py.
Usage: python3 task32.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
def _part(a, b): return _src[_src.index(a):_src.index(b)]
_bar = '# ------------------------------------------------------------------ '
exec(compile(_src[:_src.index(_bar + '1. transfers')], 'task15.py set-up', 'exec'))
exec(compile(_part('EAPOS = {', 'natof = '), 'task15.py EAPOS', 'exec'))
exec(compile(_part(_bar + 'line-up model', _bar + '3. Premier League'), 'task15.py line-up model', 'exec'))
import wyscout

CAPTAIN = [  # club, captain. Sources: bundesliga.com 26 Aug and 7 Aug 2026 (1. and 2. Bundesliga), sport.sky.it 22 Aug 2026 (Serie A),
             # news.bet365.es 22 Sep 2026 and transfermarkt (La Liga), foot-actu.com (Ligue 1). Left out where two sources disagree (Barcelona, Betis).
    ('FC Bayern München', 'Manuel Neuer'), ('Borussia Dortmund', 'Emre Can'), ('RB Leipzig', 'David Raum'), ('VfB Stuttgart', 'Deniz Undav'),
    ('Hoffenheim', 'Oliver Baumann'), ('Leverkusen', 'Edmond Tapsoba'), ('Freiburg', 'Christian Günter'), ('Eintracht Frankfurt', 'Robin Koch'),
    ('FC Augsburg', 'Jeffrey Gouweleeuw'), ('Mainz', 'Silvan Widmer'), ('Union Berlin', 'Christopher Trimmel'), ('M’gladbach', 'Tim Kleindienst'),
    ('Hamburger SV', 'Nicolai Remberg'), ('1. FC Köln', 'Marvin Schwäbe'), ('Werder Bremen', 'Marco Friedl'),
    ('VfL Wolfsburg', 'Maximilian Arnold'), ('Heidenheim', 'Patrick Mainka'),
    ('Atalanta', 'Marten de Roon'), ('Bologna', 'Lorenzo De Silvestri'), ('Cagliari', 'Alessandro Deiola'), ('Como', 'Lucas Da Cunha'),
    ('Fiorentina', 'David de Gea'), ('Frosinone', 'Ilario Monterisi'), ('Genoa', 'Johan Vásquez'), ('Internazionale', 'Lautaro Martínez'),
    ('Juventus', 'Manuel Locatelli'), ('Lazio', 'Mattia Zaccagni'), ('Lecce', 'Wladimiro Falcone'), ('AC Milan', 'Mike Maignan'), ('Monza', 'Matteo Pessina'),
    ('Napoli', 'Giovanni Di Lorenzo'), ('Parma', 'Enrico Delprato'), ('AS Roma', 'Bryan Cristante'), ('Torino', 'Duván Zapata'),
    ('Udinese', 'Jesper Karlström'), ('Venezia', 'Gianluca Busio'),
    ('Atlético de Madrid', 'Koke'), ('Getafe', 'Djené'), ('Rayo Vallecano', 'Óscar Valentín'), ('Deportivo La Coruña', 'Ximo Navarro'),
    ('Real Madrid', 'Federico Valverde'), ('Valencia CF', 'José Gayà'), ('Villarreal', 'Gerard Moreno'), ('Osasuna', 'Kike Barja'), ('Sevilla', 'Gabriel Suazo'),
    ('Athletic Club', 'Iñaki Williams'), ('Racing Club de Santander', 'Íñigo Sainz-Maza'), ('Real Sociedad de Fútbol', 'Mikel Oyarzabal'), ('Espanyol', 'Javi Puado'),
    ('Angers SCO', 'Haris Belkebla'), ('Auxerre', 'Elisha Owusu'), ('Brest', 'Brendan Chardonnet'), ('Havre', 'Arouna Sangante'), ('Le Mans', 'Edwin Quarshie'),
    ('RC Lens', 'Florian Thauvin'), ('Lille', 'Benjamin André'), ('Lorient', 'Laurent Abergel'), ('Olympique Lyonnais', 'Corentin Tolisso'),
    ('Olympique de Marseille', 'Leonardo Balerdi'), ('AS Monaco', 'Denis Zakaria'), ('OGC Nice', 'Melvin Bard'), ('Paris FC', 'Maxime Lopez'),
    ('Paris Saint-Germain', 'Marquinhos'), ('Rennais', 'Valentin Rongier'), ('Strasbourg', 'Mamadou Sarr'), ('Toulouse', 'Rasmus Nicolaisen'), ('Troyes', 'Adrien Monfray')]

W = wyscout.load()
mw = wyscout.link(W, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '', nation=p['nation'])
                      for i, p in P.items() if i not in leg])
ALL = [t for t in CLUBS if t not in LEGENDS and pes.squad(t)]
wmap = wyscout.clubs({t: [i for i, _ in pes.squad(t)] for t in ALL}, mw)
for t in ALL:
    if tname(t) in wyscout.NAMED: wmap[t] = wyscout.NAMED[tname(t)]
gk = lambda i: POS[P[i]['reg_pos']] == 'GK'
xi0 = {t: [x[0] for x in R[t][:11]] for t in CLUBS}

want = {}; named = {}                                                 # club -> the table's captain, if he is in the squad
for cl, who in CAPTAIN:
    ts = [t for t in ALL if cl.lower() in tname(t).lower()]; ts = [t for t in ts if tname(t) == cl] or ts
    assert len(ts) == 1 and ts[0] in TK and ts[0] not in PL, (cl, [tname(t) for t in ts]); t = ts[0]; w = rate.toks(who)
    c = [x[0] for x in R[t] if x[0] and any(set(w) <= set(rate.toks(n)) or ''.join(rate.toks(n)) == ''.join(w) for n in names(x[0]))]
    c = [i for i in c if any(sorted(rate.toks(n)) == sorted(w) for n in names(i))] or c
    if len(c) == 1: want[t] = c[0]
    else: log['captain not in the squad (he left after the announcement): no change'] += 1; rep['cap_missing'].append((tname(t), who))

# ------------------------------------------------------------------ 1. line-ups from minutes
def mins(i, t): return wyscout.minutes(mw[i], wmap[t])
for t in sorted(wmap):
    if t in PL or t not in TK: continue
    xi = [x[0] for x in R[t][:11]]; start = list(xi); rest = [x[0] for x in R[t][11:] if x[0] and x[0] in mw]
    while True:
        base = set(misfits(t, settle(t, xi)))
        for _, a, b in sorted((mins(b, t) - mins(a, t), a, b) for a in rest for b in xi
                              if b in mw and mins(b, t) > 0 and b != want.get(t) and b in start and a not in start and gk(a) == gk(b) and mins(a, t) - mins(b, t) >= 180 and (gk(a) or ovr(b) - ovr(a) <= 3)):
            new = settle(t, [a if x == b else x for x in xi])
            if set(misfits(t, new)) <= base: xi = new; rest = [b if x == a else x for x in rest]; break
        else: break
    if xi != start:
        for a in xi:
            if a not in start: rep['xi'].append((tname(t), P[a]['name'], ovr(a), mins(a, t), roles[t][xi.index(a)])); log['starters changed'] += 1
        rep['xi_out'] += [(tname(t), P[b]['name'], ovr(b), mins(b, t)) for b in start if b not in xi]; log['clubs with a new eleven'] += 1
        lineup(t, xi)

# ------------------------------------------------------------------ 2. set pieces
def count(i, t, col, per90=True):
    # per-90 figures have two decimals: round back to whole kicks (0.22 per 90 over 812 minutes is 2, not 1.98)
    return round(sum(num(x['r'].get(col) or 0) * (x['min'] / 90.0 if per90 else 1) for x in mw[i]['rows'] if x['team'] == wmap[t]))
for t in sorted(wmap):
    if t in PL or t not in TK: continue
    xi = [x[0] for x in R[t][:11] if x[0] in mw and not gk(x[0])]; tk = TK[t]; old = list(tk['takers'])
    def order(col, least, per90=True): return [i for n, i in sorted(((-count(i, t, col, per90), i) for i in xi)) if -n >= least]
    fk, ck, pk = order('Direct free kicks per 90', 2), order('Corners per 90', 5), order('Penalties taken', 1, False)
    if fk: tk['takers'][0] = tk['takers'][1] = fk[0]
    if len(fk) > 1: tk['takers'][2] = fk[1]
    if ck:
        l = r = ck[0]
        if len(ck) > 1 and P[ck[0]]['foot'] != P[ck[1]]['foot']: l, r = (ck[0], ck[1]) if P[ck[0]]['foot'] == 0 else (ck[1], ck[0])
        tk['takers'][3], tk['takers'][4] = l, r
    if pk: tk['takers'][5] = pk[0]
    if tk['takers'] != old:
        touched.add(t); log['set-piece roles changed'] += sum(a != b for a, b in zip(old, tk['takers'])); log['clubs with new takers'] += 1
        rep['takers'].append((tname(t),) + tuple(P[i]['name'] if i in P else '?' for i in (tk['takers'][0], tk['takers'][2], tk['takers'][3], tk['takers'][4], tk['takers'][5])))

# ------------------------------------------------------------------ 3. captains
for t, i in sorted(want.items()):
    if i not in [x[0] for x in R[t][:11]]: log['captain is not in the eleven: no change'] += 1; rep['cap_bench'].append((tname(t), P[i]['name'])); continue
    named[t] = i
    if TK[t]['captain'] == i: log['captain already right'] += 1; continue
    rep['cap'].append((tname(t), P[i]['name'], 'was', P[TK[t]['captain']]['name'] if TK[t]['captain'] in P else '?')); TK[t]['captain'] = i; touched.add(t); log['captain set from the table'] += 1

exec(compile(_part(_bar + 'write rosters', _bar + 'self-check'), 'task15.py write', 'exec'))

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
lo = pes.P0 + pes.np * pes.PSZ; assert len(new.d) == len(pes.d) and new.d[:lo] == pes.d[:lo], 'a player record or the header changed'
for t in pes.teams:
    a, b = pes.plans[t]['raw'], new.plans[t]['raw']; sq = new.squad(t); ids = [i for i, _ in sq]; g = new.plans[t]
    assert new.teams[t]['raw'] == pes.teams[t]['raw'] and a[:516] == b[:516] and a[526:] == b[526:], ('team or formation data changed', tname(t))
    if t not in wmap or t in PL or t not in TK: assert new.rosters[t] == pes.rosters[t] and a == b, ('a club outside the rule changed', tname(t)); continue
    assert sorted(sq) == sorted(pes.squad(t)), ('squad or shirt numbers changed', tname(t))
    xi = ids[:11]; old = xi0[t]
    assert [gk(i) for i in xi] == [r == 'GK' for r in roles[t]], ('goalkeeper', tname(t))
    was = {old[k] for k in pes.plans[t]['takers']}
    assert all(k < 11 and (not gk(xi[k]) or xi[k] in was) for k in g['takers']) and g['captain'] < 11, ('taker or captain', tname(t))
    assert all(i in xi for i in old if i not in mw or not mins(i, t) or i == want.get(t)), ('a starter who must stay lost his place', tname(t))
    assert sum(mins(i, t) for i in xi if i in mw) >= sum(mins(i, t) for i in old if i in mw), ('fewer minutes in the eleven', tname(t))
    assert all(gk(i) or ovr(i) >= min(ovr(j) for j in old if j not in xi and not gk(j)) - 3 for i in xi if i not in old), ('a newcomer is rated too low', tname(t))
    assert len(misfits(t, xi)) <= len(misfits(t, old)), ('more starters out of position', tname(t))
    if t in named: assert xi[g['captain']] == named[t], ('captain', tname(t))
    if t not in touched: assert a == b and ids == [i for i, _ in pes.squad(t)], ('an untouched club changed', tname(t))

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep=dict(rep), log=dict(log)), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-60s %d' % (k, v))
for k, n in (('xi', 60), ('xi_out', 30), ('takers', 40), ('cap', 80), ('cap_bench', 80), ('cap_missing', 80), ('captain', 30)):
    print('--', k, len(rep[k]))
    for x in rep[k][:n]: print('  ', x)
print('clubs changed', len(touched), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
