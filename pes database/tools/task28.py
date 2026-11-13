"""Task 28: free agents back in their 2026/27 squads, on the output of task27.py.
Taken from the save "EDIT00000000 (another save i found online)": players it has at a club of the five leagues who are
free agents in ours, kept only where FotMob's squad list of 12 November 2026 (fotmob.py) has them at that club. Its other
squad differences are older than ours or not confirmed. Plus one of our own mistakes: Kendry Páez was left without a
club; he is on loan at River Plate for 2026.
Each joins as a reserve with his real number. In a full squad (32) he takes the slot of the weakest reserve that the
club's FotMob list does not have, who becomes a free agent (a goalkeeper only if the club keeps three). A team-mate
outside the list who wears his number takes the lowest free one from 30 up.
Left out, although listed, because the squad is full and no reserve outside the list is rated below them: Akintola and
Ömür (Hull), Harvey Davies (Liverpool), Jack Fletcher (Manchester United), Dani Martínez (Atlético), Torriani (Milan),
Furlanetto and Farcomeni (Lazio), Nyarko (Sassuolo), Gorter (Lecce), Becker (Strasbourg), Sierralta (Auxerre).
Usage: python3 task28.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import struct, sys
from lib import P17, POS, u32
import fotmob, rate

NAMED = [  # club, player id, name (checked against the record), shirt number (0 = FotMob gives none)
    ('Manchester United', 177107, 'Shea Lacey', 31), ('Manchester United', 177109, 'Tyler Fletcher', 39),
    ('Real Madrid CF', 181417, 'Jorge Cestero', 29), ('Como 1907', 182314, 'Adrian Lahdo', 15), ('S.S. Lazio', 61397, 'Patric', 4),
    ('Atalanta BC', 115038, 'Francesco Rossi', 0), ('Genoa CFC', 175974, 'Joi Nuredini', 19), ('ACF Fiorentina', 182257, 'Edoardo Sadotti', 67),
    ('FC Augsburg', 139727, 'Kristijan Jakić', 17), ('RB Leipzig', 71148, 'Samba Konate', 45),
    ('Olympique Lyonnais', 176301, 'Mathys De Carvalho', 39), ('Havre AC', 168595, 'Paul Argney', 50), ('AJ Auxerre', 138467, 'Josué Casimir', 7),
    ('CA River Plate', 165874, 'Kendry Páez', 19)]   # on loan from Chelsea for 2026 (BBC); number 19 (soydelmillo.com, 4 Feb 2026)
SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); done = {}; out = {}; aside = {}
clubs = [t for t in pes.teams if pes.isclub(t)]
taken = {i for t in clubs for i, _ in pes.squad(t)}
fm = fotmob.squads(pes); listed, rest = fotmob.match(pes, fm)
gk = lambda i: POS[P[i]['reg_pos']] == 'GK'
for team, i, name, want in NAMED:
    t = [t for t in clubs if pes.teams[t]['name'] == team]; assert len(t) == 1, team
    t = t[0]; assert P[i]['name'] == name and i not in taken, ('not that free agent', name)
    if t in fm: assert any(fotmob.same(name, P[i]['age'], r, 1) and (r['shirt'] or 0) == want for r in rest[t]), ('not in the FotMob list', name)
    keep = set(listed.get(t, {})) | {x for x, v in done.items() if v[0] == t}
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    r = [(u32(d, o + 4 + 4 * k), d[o + 132 + k]) for k in range(32)]
    k = next((k for k in range(32) if not r[k][0]), None)
    if k is None:                                   # full squad: the weakest reserve outside the list leaves
        keepers = sum(gk(x[0]) for x in r)
        k = min((k for k in range(11, 32) if r[k][0] not in keep and not (gk(r[k][0]) and keepers <= 3 and not gk(i))), key=lambda k: (rate.overall(P[r[k][0]]), k), default=None)
        assert k is not None and rate.overall(P[r[k][0]]) <= rate.overall(P[i]), ('no weaker reserve outside the list', name)
        out[r[k][0]] = t; taken.discard(r[k][0])
    assert k >= 11, ('no reserve slot', team)
    used = {n: j for j, (pid, n) in enumerate(r) if pid and j != k}
    free = lambda: next(x for x in range(30, 100) if x not in used and x != want)
    if want in used:                                # his number is on a team-mate outside the list
        j = used.pop(want); assert r[j][0] not in keep, ('number worn by a listed player', name)
        n = free(); d[o + 132 + j] = n; used[n] = j; aside[r[j][0]] = (t, j, n)
    n = want or free()
    struct.pack_into('<I', d, o + 4 + 4 * k, i); d[o + 132 + k] = n; taken.add(i); done[i] = (t, k, n)
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); touched = {t for t, _, _ in done.values()}
assert len(new.d) == len(pes.d) and new.d[:pes.R0] == pes.d[:pes.R0], 'something before the rosters changed'
end = pes.R0 + len(pes.teams) * pes.RSZ; assert new.d[end:] == pes.d[end:], 'something after the rosters changed'
for t in pes.teams:
    a, b = pes.rosters[t], new.rosters[t]
    if t not in touched: assert a == b, ('another roster changed', pes.teams[t]['name']); continue
    slot = {k: (i, n) for i, (tt, k, n) in done.items() if tt == t}; moved = {k: n for tt, k, n in aside.values() if tt == t}
    for j in range(32):
        if j in slot: assert b[j] == slot[j] and j >= 11
        elif j in moved: assert b[j] == (a[j][0], moved[j])
        else: assert a[j] == b[j], ('roster', pes.teams[t]['name'])
    nums = [x for pid, x in b if pid]; assert len(set(nums)) == len(nums) and all(1 <= x <= 99 for x in nums), ('numbers', pes.teams[t]['name'])
    assert sum(POS[P[pid]['reg_pos']] == 'GK' for pid, _ in b if pid) >= 2 and len(new.squad(t)) >= len(pes.squad(t)), pes.teams[t]['name']
    for k, (i, n) in sorted(slot.items()):
        left = P[a[k][0]] if a[k][0] else None; away = [P[x]['name'] + ' now #%d' % v[2] for x, v in aside.items() if v[0] == t]
        print('%-24s %-20s %-3s %d  #%d%s' % (pes.teams[t]['name'], P[i]['name'], POS[P[i]['reg_pos']], rate.overall(P[i]), n,
              '   released: %s (%s %d)' % (left['name'], POS[left['reg_pos']], rate.overall(left)) if left else ''))
    if moved: print('%-24s moved aside: %s' % ('', ', '.join(P[x]['name'] + ' #%d' % v[2] for x, v in aside.items() if v[0] == t)))
now = [i for t in new.teams if new.isclub(t) for i, _ in new.squad(t)]
assert len(now) == len(set(now)) and set(done) <= set(now) and not set(out) & set(now) and len(done) == len(NAMED), 'placement: a row of NAMED stayed out'
hit2, _ = fotmob.match(new, fm)
assert all(set(listed[t]) <= set(hit2[t]) for t in fm), 'a player of a FotMob list was released'
print('players placed', len(done), '| released', len(out), '| numbers moved aside', len(aside), '| bytes changed', sum(x != y for x, y in zip(pes.d, new.d)), '| self-check passed')
