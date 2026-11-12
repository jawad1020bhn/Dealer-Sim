"""Task 21: free agents whose real 2026/27 club is in the file join it, on the output of task20.py.
The table is the result of a web check (November 2026) of the best-rated free agents: Wikipedia, Transfermarkt, club news.
Each joins as a reserve. In a full squad (32) he takes the slot of the weakest reserve, who becomes a free agent; a
goalkeeper is released only if the club keeps three. Shirt number: his real one if free, else the released player's, else
the lowest free one from 2 up.
Usage: python3 task21.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import struct, sys
from lib import P17, POS, u32
import rate

NAMED = [  # club, player id, name (checked against the record), real shirt number (0 = unknown), evidence
    ('Getafe CF', 57353, 'Dani Carvajal', 14, 'signed 13 Oct 2026'),
    ('Al Hilal SFC', 8944, 'Karim Benzema', 9, 'there since Feb 2026, contract to 2027'),
    ('S.S. Lazio', 102481, 'Samuel Gigot', 2, 'contract to 2027'),
    ('UD Las Palmas', 115656, 'Dinko Horkaš', 1, 'contract to 2028'),
    ('Servette FC', 120787, 'Jesper Karlsson', 21, 'on loan from Bologna since 8 Sep 2026'),
    ('N.E.C. Nijmegen', 122011, 'Mitchel Bakker', 5, 'signed 8 Oct 2026'),
    ('AS Monaco', 45023, 'Paul Pogba', 8, 'contract to 2027'),
    ('Bologna FC 1909', 37140, 'Matteo Darmian', 36, 'signed 8 Oct 2026'),
    ('Paris FC', 41066, 'Ciro Immobile', 36, 'contract to 2027'),
    ('RSC Anderlecht', 147783, 'César Huerta', 21, 'contract to 2029')]
SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); done = {}; out = {}
clubs = [t for t in pes.teams if pes.isclub(t)]
taken = {i for t in clubs for i, _ in pes.squad(t)}
gk = lambda i: POS[P[i]['reg_pos']] == 'GK'
for team, i, name, want, _ in NAMED:
    t = [t for t in clubs if pes.teams[t]['name'] == team]; assert len(t) == 1, team
    t = t[0]; assert P[i]['name'] == name and i not in taken, ('not that free agent', name)
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    r = [(u32(d, o + 4 + 4 * k), d[o + 132 + k]) for k in range(32)]
    k = next((k for k in range(32) if not r[k][0]), None); old = 0
    if k is None:                                   # full squad: the weakest reserve leaves
        keepers = sum(gk(x[0]) for x in r)
        k = min((k for k in range(11, 32) if not (gk(r[k][0]) and keepers <= 3)), key=lambda k: (rate.overall(P[r[k][0]]), k))
        old = r[k][1]; out[r[k][0]] = t; taken.discard(r[k][0])
    assert k >= 11, ('no reserve slot', team)
    used = {n for j, (pid, n) in enumerate(r) if pid and j != k}
    n = want if want and want not in used else old if old else next(x for x in range(2, 100) if x not in used)
    struct.pack_into('<I', d, o + 4 + 4 * k, i); d[o + 132 + k] = n; taken.add(i); done[i] = (t, k, n)
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); touched = {t for t, _, _ in done.values()}
assert len(new.d) == len(pes.d) and new.d[:pes.R0] == pes.d[:pes.R0], 'something before the rosters changed'
end = pes.R0 + len(pes.teams) * pes.RSZ; assert new.d[end:] == pes.d[end:], 'something after the rosters changed'
for t in pes.teams:
    if t not in touched: assert new.rosters[t] == pes.rosters[t], ('another roster changed', pes.teams[t]['name']); continue
    (i, (_, k, n)), = [(i, v) for i, v in done.items() if v[0] == t]
    a, b = pes.rosters[t], new.rosters[t]
    assert b[k] == (i, n) and all(a[j] == b[j] for j in range(32) if j != k) and k >= 11, ('roster', pes.teams[t]['name'])
    nums = [x for pid, x in b if pid]; assert len(set(nums)) == len(nums) and all(1 <= x <= 99 for x in nums), ('numbers', pes.teams[t]['name'])
    assert sum(POS[P[pid]['reg_pos']] == 'GK' for pid, _ in b if pid) >= 2, ('goalkeepers', pes.teams[t]['name'])
    left = P[a[k][0]] if a[k][0] else None
    print('%-18s %d -> %d   %-16s %s %d  #%d%s' % (pes.teams[t]['name'], len(pes.squad(t)), len(new.squad(t)), P[i]['name'], POS[P[i]['reg_pos']],
          rate.overall(P[i]), n, '   released: %s (%s %d)' % (left['name'], POS[left['reg_pos']], rate.overall(left)) if left else ''))
now = {i for t in new.teams if new.isclub(t) for i, _ in new.squad(t)}
assert set(done) <= now and not set(out) & now and len(done) == len(NAMED), 'placement'
print('players placed', len(done), '| released', len(out), '| bytes changed', sum(x != y for x, y in zip(pes.d, new.d)), '| self-check passed')
