"""Task 34: the classic players of task 13 and the nine hand-built legends of task 14 are removed.
The five team slots go back to what they held before task 13: "The Old Boys" (empty), "Pleasure Horn" and the three
Master League default teams with their own players. Each of the 139 records gets back its content of that time
(name, abilities, appearance, "edited" flags); the 32 that were unused free agents are unused free agents again.
The seven classic teams the save came with (Pes Classics ... World Classics) are not touched.
The old content comes from the file as it was before task 13 (commit d5341d7, decrypted):
  git show "d5341d7:pes database/EDIT00000000 (pes 2017 updated)" > before.bin && dec17 before.bin before
Usage: python3 task34.py <in data.dat> <before/data.dat> <out data.dat>     (ends with a self-check of the written file)
"""
import sys
from lib import P17

SRC, OLD, OUT = sys.argv[1:4]
TEAMS = (4971, 1386, 140, 2696, 2469)                         # World Cup Heroes, Modern Champions, FC Icons, UCL Legends, Cult Heroes
pes = P17(SRC); old = P17(OLD); d = bytearray(pes.d)
assert len(pes.d) == len(old.d) and list(pes.players) == list(old.players) and all(pes.teams[t]['i'] == old.teams[t]['i'] for t in TEAMS)
ids = [i for t in TEAMS for i, _ in pes.squad(t)]
elsewhere = {i for p in (pes, old) for t in p.teams if t not in TEAMS for i, _ in p.squad(t)}
assert not set(ids) & elsewhere, 'a classic player sits in another team as well'
assert {i for t in TEAMS for i, _ in old.squad(t)} <= set(ids), 'a player of the old squads is elsewhere now'

spans = [(pes.P0 + pes.players[i]['i'] * pes.PSZ, pes.PSZ) for i in ids]
assert all(pes.players[i]['i'] == old.players[i]['i'] for i in ids)
for t in TEAMS:
    k = pes.teams[t]['i']; spans += [(pes.R0 + k * pes.RSZ, pes.RSZ), (pes.G0 + k * pes.GSZ, pes.GSZ), (pes.T0 + k * pes.TSZ, pes.TSZ)]
for o, n in spans: d[o:o + n] = old.d[o:o + n]
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); mask = bytearray(len(d))
for o, n in spans: mask[o:o + n] = b'\1' * n
assert len(new.d) == len(pes.d) and all(m or a == b for m, a, b in zip(mask, new.d, pes.d)), 'something else changed'
for t in TEAMS:
    assert new.rosters[t] == old.rosters[t] and new.plans[t]['raw'] == old.plans[t]['raw'] and new.teams[t]['raw'] == old.teams[t]['raw'], t
assert all(new.players[i]['raw'] == old.players[i]['raw'] for i in ids) and not new.squad(4971)
seen = [i for t in new.teams for i, _ in new.squad(t) if not new.isclub(t)]
assert len(seen) == len(set(seen)), 'a player sits in two national or classic teams'
free = [i for i in ids if i not in set(seen)]
print('records restored %d (free agents again: %d) | bytes changed %d' % (len(ids), len(free), sum(a != b for a, b in zip(new.d, pes.d))))
for t in TEAMS: print('  %-18s -> %-24s %2d players' % (pes.teams[t]['name'], new.teams[t]['name'], len(new.squad(t))))
print('self-check passed')
