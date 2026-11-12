"""Task 19: registered positions set by hand, on the output of task18.py.
The player gets the new registered position rated A; his overall stays what it was (the abilities that count at the new
position are shifted, as in task14.py); a playing style that does not work at the new position becomes its default.
Usage: python3 task19.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys
from lib import P17, POS, pack17
import rate

NAMED = {('FC Bayern München', 'Serge Gnabry'): 'RMF', ('FC Bayern München', 'Lennart Karl'): 'RMF'}
# playing styles that work at a position in PES 2017 (table of task14.py); first = default
STYLE = {'CF': (1, 2, 3, 13), 'SS': (6, 2, 5, 14), 'LWF': (4, 14), 'RWF': (4, 14), 'AMF': (6, 2, 5, 14), 'LMF': (4, 6, 7, 14), 'RMF': (4, 6, 7, 14),
         'CMF': (6, 7, 9), 'DMF': (8, 7, 9, 15), 'CB': (15, 9, 10), 'LB': (11, 12), 'RB': (11, 12), 'GK': (17, 16)}
SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); done = {}
def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
for (team, name), role in NAMED.items():
    t = [t for t in pes.teams if pes.teams[t]['name'] == team]; assert len(t) == 1, team
    hit = [i for i, _ in pes.squad(t[0]) if P[i]['name'] == name]; assert len(hit) == 1, name
    i = hit[0]; p = P[i]; was = (POS[p['reg_pos']], rate.overall(p), p['play_style'])
    p['reg_pos'] = POS.index(role); p['pp_' + role] = 2
    if p['play_style'] and p['play_style'] not in STYLE[role]: p['play_style'] = STYLE[role][0]
    assert rate.overall(p) == was[1] or rate.retarget(p, was[1]), ('overall cannot be kept', name)
    d[off(i) + 16:off(i) + 51] = pack17(p); done[i] = (role, was)
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and new.rosters == pes.rosters
lo = pes.P0; hi = lo + pes.np * pes.PSZ; assert new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:], 'something outside the player records changed'
for i in P:
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    if i not in done: assert a == b, ('another player changed', P[i]['name']); continue
    role, was = done[i]
    assert a[:16] == b[:16] and a[51:] == b[51:] and POS[N[i]['reg_pos']] == role and N[i]['pp_' + role] == 2 and rate.overall(N[i]) == was[1], N[i]['name']
    print('%-16s %s %d (style %d) -> %s %d (style %d)' % (N[i]['name'], was[0], was[1], was[2], role, rate.overall(N[i]), N[i]['play_style']))
print('players changed', len(done), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
