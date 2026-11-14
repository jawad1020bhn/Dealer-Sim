"""Task 36: mark the renamed players and managers as edited; on the output of task35.py.
The game takes a player's name from the edit file only when the record's "edited player" flag is 1 (or its own
database has no name for him); a manager's name likewise, flag = bit 0 of byte 8 of the manager record. Read from
PES2017.exe and run in an emulator: ../exe/NOTES.md, "Names and the edited flags". Task 17 set the player flags;
the players built later (task 31 and after) and all renamed managers lack them, so the game would show the old name
with the new abilities.
  players   name differs from the user's upload and the flag is 0 -> the nine edited flags are set, as task 17 did
  managers  name differs from the upload and the flag is 0        -> the flag is set
Nothing else changes.
Usage: python3 task36.py <in data.dat> <upload data.dat> <out data.dat>          (ends with a self-check)
"""
import sys
from lib import P17, u32

SRC, ORIG, OUT = sys.argv[1:4]
pes, org = P17(SRC), P17(ORIG); d = bytearray(pes.d)
PBITS = (191, 223, 255, 349, 350, 351, 366, 367, 368)      # fields 1-9 of the exe's player table, bit in the record
EFLAGS = ('e_player', 'e_basic', 'e_regpos', 'e_playpos', 'e_ability', 'e_skill', 'e_style', 'e_com', 'e_motion')
MSZ, MFLAG, MNAME = 88, 8, 9

players = [i for i, p in pes.players.items() if not p['e_player'] and (i not in org.players or org.players[i]['name'] != p['name'])]
for i in players:
    o = pes.P0 + pes.players[i]['i'] * pes.PSZ
    for b in PBITS: d[o + b // 8] |= 1 << (b % 8)


def mname(buf, o): return bytes(buf[o + MNAME:o + MSZ]).split(b'\0')[0]


old = {u32(org.d, o): mname(org.d, o) for o in range(org.M0, org.M0 + 850 * MSZ, MSZ) if any(org.d[o:o + MSZ])}
managers = []
for o in range(pes.M0, pes.M0 + 850 * MSZ, MSZ):
    if any(d[o:o + MSZ]) and not d[o + MFLAG] & 1 and old.get(u32(d, o)) != mname(d, o):
        d[o + MFLAG] |= 1; managers.append(u32(d, o))
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check
new = P17(OUT); a, b = pes.d, new.d
assert len(a) == len(b) and len(players) == len(set(players)) and len(managers) == len(set(managers))
want = {pes.P0 + pes.players[i]['i'] * pes.PSZ + bit // 8 for i in players for bit in PBITS} | \
       {pes.M0 + new.managers[m]['i'] * MSZ + MFLAG for m in managers}
assert {k for k in range(len(a)) if a[k] != b[k]} == want, 'bytes changed outside the flags'
for i, p in new.players.items():
    q = pes.players[i]
    assert all(p[k] == q[k] for k in p if k not in EFLAGS + ('raw',)), ('player changed', i)
    if i in players: assert all(p[f] == 1 for f in EFLAGS) and q['e_player'] == 0
    else: assert p['raw'] == q['raw']
    assert p['e_player'] == 1 or (i in org.players and org.players[i]['name'] == p['name']), ('renamed without the flag', i)
for o in range(new.M0, new.M0 + 850 * MSZ, MSZ):
    if any(b[o:o + MSZ]): assert b[o + MFLAG] & 1 or old.get(u32(b, o)) == mname(b, o), ('manager renamed without the flag', u32(b, o))
assert all(new.managers[m]['name'] == pes.managers[m]['name'] for m in managers)
print('players marked as edited: %d; managers marked as edited: %d; self-check ok' % (len(players), len(managers)))
for i in players[:5]: print('  player  %6d %-22s was %s' % (i, new.players[i]['name'], org.players[i]['name'] if i in org.players else '-'))
for m in managers[:5]: print('  manager %6d %-22s was %s' % (m, new.managers[m]['name'], old.get(m, b'-').decode('utf8', 'replace')))
