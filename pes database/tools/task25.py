"""Task 25: shirt numbers of the five leagues as worn in 2026/27, on the output of task24.py.
The numbers of task 15 came from Football Life 27, a summer patch; the save "EDIT00000000 (another save i found online)"
showed they are out of date (Real Madrid: Asencio 2, Huijsen 4, Konaté 16 ...). Source of truth here: the FotMob squad
lists of 12 November 2026 (fotmob.py). Every squad member found in his club's list gets the number of the list. A squad
member who is not in the list keeps his number; if a listed team-mate now wears it, he takes the lowest free number
from 30 up. FotMob gives ten numbers to two players of one club: the one who wears it in the file keeps it, else the
better player gets it. Only the number bytes of the 93 club rosters change.
Usage: python3 task25.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys, collections
from lib import P17, u32
import fotmob, rate

SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d)
fm = fotmob.squads(pes); hit, _ = fotmob.match(pes, fm); want = {}; log = collections.Counter(); twice = set()
for t in fm:
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    r = pes.rosters[t]
    new = {}; used = set()
    listed = [(i, n, hit[t][i]['shirt']) for i, n in pes.squad(t) if i in hit[t] and 1 <= (hit[t][i]['shirt'] or 0) <= 99]
    for i, n, s in sorted(listed, key=lambda x: (x[1] != x[2], -rate.overall(P[x[0]]))):   # FotMob lists a few numbers twice:
        if s not in used: new[i] = s; used.add(s)                                          # the wearer in the file, else the better player
        else: twice.add(i)
    for i, n in pes.squad(t):                        # not in the list: keep the number if no listed team-mate wears it
        if i not in new and n not in used: new[i] = n; used.add(n)
    for i, n in pes.squad(t):
        if i not in new: new[i] = next(x for x in range(30, 100) if x not in used); used.add(new[i]); log['not in the list, number taken by a listed team-mate'] += 1
    for k, (i, n) in enumerate(r):
        if i and new[i] != n: d[o + 132 + k] = new[i]; want.setdefault('c', []).append((t, i, n, new[i]))
    want[t] = new
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); changed = want.pop('c', [])
assert len(new.d) == len(pes.d) and new.d[:pes.R0] == pes.d[:pes.R0], 'something before the rosters changed'
end = pes.R0 + len(pes.teams) * pes.RSZ; assert new.d[end:] == pes.d[end:], 'something after the rosters changed'
for t in pes.teams:
    a, b = pes.rosters[t], new.rosters[t]
    assert [i for i, _ in a] == [i for i, _ in b], ('a roster changed', pes.teams[t]['name'])
    if t not in want: assert a == b, ('another club changed', pes.teams[t]['name']); continue
    nums = [n for i, n in b if i]; assert len(set(nums)) == len(nums) and all(1 <= n <= 99 for n in nums), ('numbers', pes.teams[t]['name'])
    assert all(n == want[t][i] for i, n in b if i) and all(n == hit[t][i]['shirt'] for i, n in b if i in hit[t] and i not in twice and 1 <= (hit[t][i]['shirt'] or 0) <= 99)
for t in sorted({c[0] for c in changed}, key=lambda t: pes.teams[t]['name']):
    print('%-30s %s' % (pes.teams[t]['name'], ', '.join('%s %d>%d' % (P[i]['name'], n, m) for tt, i, n, m in changed if tt == t)))
print('squad members %d | found in the FotMob lists %d | numbers changed %d at %d clubs | moved aside %d | bytes changed %d | self-check passed' % (
    sum(len(pes.squad(t)) for t in fm), sum(len(hit[t]) for t in fm), len(changed), len({c[0] for c in changed}),
    log['not in the list, number taken by a listed team-mate'], sum(x != y for x, y in zip(pes.d, new.d))))
