"""Task 20: free agents go back to the club they last belonged to, on the output of task19.py.
Eight clubs were left with 18 or 19 players because Football Life 27 and EA FC 27 no longer carry them. The table lists
the free agents that FC 26 or Transfermarkt (both September 2025) have under contract at one of those clubs (not on loan
there) and that neither Football Life 27 nor EA FC 27 lists at another club. Each takes the first empty roster slot (a
reserve) and his FC 26 shirt number, or the lowest free one from 2 up if that number is taken or unknown.
Usage: python3 task20.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import struct, sys
from lib import P17, u32

NAMED = [  # club, player id, name (checked against the record), FC 26 shirt number (0 = unknown)
    ('Real Zaragoza', 131069, 'Paulino De La Fuente', 18), ('Real Zaragoza', 160312, 'Pau Sans', 29),
    ('Real Zaragoza', 169899, 'Sebastián Kóša', 22), ('Real Zaragoza', 168606, 'Lucas Terrer', 25),
    ('Real Zaragoza', 151463, 'Carlos Calavia', 40), ('Real Zaragoza', 168418, 'Hugo Barrachina', 32),
    ('SSC Bari', 108206, 'Gaetano Castrovilli', 4), ('SSC Bari', 178030, 'Indrit Mavraj', 0),
    ('Spezia Calcio', 110467, 'Edoardo Soleri', 27), ('Spezia Calcio', 160158, 'Pietro Candelari', 36),
    ('Amiens SC', 167656, 'Mactar Tine', 58), ('Amiens SC', 155278, 'Ange Chibozo', 17), ('Amiens SC', 176620, 'Nathan Talbot', 59),
    ('AVS Futebol', 115169, 'Rafael Barbosa', 10), ('AVS Futebol', 131287, 'Bruno Lourenço', 17)]
SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); done = {}
clubs = [t for t in pes.teams if pes.isclub(t)]
taken = {i for t in clubs for i, _ in pes.squad(t)}
for team, i, name, want in NAMED:
    t = [t for t in clubs if pes.teams[t]['name'] == team]; assert len(t) == 1, team
    t = t[0]; assert P[i]['name'] == name and i not in taken, ('not that free agent', name)
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    r = [(u32(d, o + 4 + 4 * k), d[o + 132 + k]) for k in range(32)]
    k = next(k for k in range(32) if not r[k][0]); assert k >= 11 and all(x[0] for x in r[:k]) and not any(x[0] for x in r[k:]), ('roster', team)
    used = {n for pid, n in r if pid}
    n = want if want and want not in used else next(x for x in range(2, 100) if x not in used)
    struct.pack_into('<I', d, o + 4 + 4 * k, i); d[o + 132 + k] = n; taken.add(i); done[i] = (t, k, n)
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); touched = {t for t, _, _ in done.values()}
assert len(new.d) == len(pes.d) and new.d[:pes.R0] == pes.d[:pes.R0], 'something before the rosters changed'
end = pes.R0 + len(pes.teams) * pes.RSZ; assert new.d[end:] == pes.d[end:], 'something after the rosters changed'
for t in pes.teams:
    if t not in touched: assert new.rosters[t] == pes.rosters[t], ('another roster changed', pes.teams[t]['name']); continue
    add = [(i, n) for i, (c, k, n) in done.items() if c == t]; sq = new.squad(t)
    assert sq == pes.squad(t) + add and len(sq) <= 32, ('roster', pes.teams[t]['name'])
    nums = [n for _, n in sq]; assert len(set(nums)) == len(nums) and all(1 <= n <= 99 for n in nums), ('numbers', pes.teams[t]['name'])
    print('%-14s %d -> %d   %s' % (pes.teams[t]['name'], len(pes.squad(t)), len(sq), ', '.join('%s #%d' % (P[i]['name'], n) for i, n in add)))
home = [t for t in new.teams if new.isclub(t) for i, _ in new.squad(t) if i in done]
assert len(home) == len(done) == len(NAMED), 'a player is in two clubs'
print('players placed', len(done), '| clubs', len(touched), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
