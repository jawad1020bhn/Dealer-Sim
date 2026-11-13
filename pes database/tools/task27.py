"""Task 27: skills and goal celebrations from the save "EDIT00000000 (another save i found online)", on the output of
task26.py. That save gives 51 players of the five leagues 196 skills ours lack. None of them is in Konami's own current
data (Football Life 27, where our skills come from), so a skill is taken only where it passes the rules of
task23_research.py: the EA FC 27 PlayStyle that Konami's data pairs with it, or the match figure. That leaves 23; the
other 173 (Flip Flap 19 times, Fighting Spirit 21, One-touch Pass 20, Low Lofted Pass 21, Knuckle Shot 11 ...) are left
out. Skills are only added, nobody goes above 10.
Goal celebrations: the two that save changed, Mbappé's second and both of Vinícius Júnior (bytes 14 and 15 of the record).
Usage: python3 task27.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys
from lib import P17, pack17

SK = ['Scissors Feint', 'Flip Flap', 'Marseille Turn', 'Sombrero', 'Cut Behind & Turn', 'Scotch Move', 'Heading', 'Long Range Drive', 'Knuckle Shot',
      'Acrobatic Finishing', 'Heel Trick', 'First-time Shot', 'One-touch Pass', 'Weighted Pass', 'Pinpoint Crossing', 'Outside Curler', 'Rabona',
      'Low Lofted Pass', 'Low Punt Trajectory', 'Long Throw', 'GK Long Throw', 'Malicia', 'Man Marking', 'Track Back', 'Acrobatic Clear', 'Captaincy',
      'Super-sub', 'Fighting Spirit']                                                    # bit order of the game (see task22.py)
SKILLS = [  # id, name, skills added, evidence (EA FC 27 PlayStyle or FBref 2026/27)
    (60512, 'Bruno Fernandes', ['Weighted Pass', 'Fighting Spirit'], 'PlayStyle Incisive Pass; PlayStyle Relentless'),
    (104226, 'Bernardo Silva', ['One-touch Pass'], 'PlayStyle Tiki Taka'),
    (110626, 'Ousmane Dembélé', ['Long Range Drive'], 'PlayStyle Finesse Shot'),
    (110718, 'Kylian Mbappé', ['Long Range Drive'], 'PlayStyle Finesse Shot'),
    (116575, 'Marc Cucurella', ['Man Marking', 'Acrobatic Clear', 'Fighting Spirit'], 'PlayStyle Block; PlayStyle Jockey; PlayStyle Relentless'),
    (116751, 'Ferran Torres', ['Long Range Drive'], 'PlayStyle Finesse Shot'),
    (119782, 'Aurélien Tchouaméni', ['Man Marking'], 'PlayStyle Jockey'),
    (128281, 'Enzo Fernández', ['Pinpoint Crossing'], 'crosses 4.1 per 90 with assists'),
    (128720, 'K. Kvaratskhelia', ['Fighting Spirit'], 'PlayStyle Relentless'),
    (129369, 'Michael Olise', ['One-touch Pass', 'Weighted Pass'], 'PlayStyle Incisive Pass; PlayStyle Tiki Taka'),
    (132756, 'Nuno Mendes', ['Weighted Pass'], 'PlayStyle Pinged Pass'),
    (141578, 'Arda Güler', ['Weighted Pass'], 'PlayStyle Incisive Pass'),
    (143196, 'Moisés Caicedo', ['Weighted Pass'], 'PlayStyle Pinged Pass'),
    (154986, 'Álvaro Carreras', ['Long Throw'], 'PlayStyle Long Throw'),
    (155214, 'Nico Paz', ['Weighted Pass'], 'PlayStyle Incisive Pass'),
    (166254, 'Ayyoub Bouaddi', ['Man Marking'], 'PlayStyle Jockey'),
    (168465, 'Carlos Espí', ['Heading'], 'PlayStyle Precision Header'),
    (173989, 'Víctor Muñoz', ['Fighting Spirit'], 'PlayStyle Relentless'),
    (176104, 'Yan Diomande', ['Cut Behind & Turn'], 'PlayStyle Technical')]
CELEB = [(110718, 'Kylian Mbappé', 73, 38), (117047, 'Vinícius Júnior', 30, 69)]      # id, name, celebration 1, celebration 2

SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d)
def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
def nsk(p): return sum(p['sk%d' % k] for k in range(28))
for i, name, add, _ in SKILLS:
    p = P[i]; assert p['name'] == name and not any(p['sk%d' % SK.index(s)] for s in add), name
    for s in add: p['sk%d' % SK.index(s)] = 1
    assert nsk(p) <= 10, name
    d[off(i) + 16:off(i) + 51] = pack17(p)
for i, name, a, b in CELEB:
    assert P[i]['name'] == name; d[off(i) + 14] = a; d[off(i) + 15] = b
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players; old = P17(SRC).players
want = {i: add for i, _, add, _ in SKILLS}; cel = {i: (a, b) for i, _, a, b in CELEB}
lo = pes.P0; hi = lo + pes.np * pes.PSZ; assert len(new.d) == len(pes.d) and new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:]
for i in P:
    if i not in want and i not in cel: assert pes.d[off(i):off(i) + pes.PSZ] == new.d[off(i):off(i) + pes.PSZ], ('another player changed', P[i]['name']); continue
    diff = {k for k in N[i] if k != 'raw' and N[i][k] != old[i][k]}
    assert diff == {'sk%d' % SK.index(s) for s in want.get(i, [])} | {k for k, v in zip(('gc1', 'gc2'), cel.get(i, ())) if old[i][k] != v}, N[i]['name']
    assert all(N[i]['sk%d' % SK.index(s)] for s in want.get(i, [])) and nsk(N[i]) == nsk(old[i]) + len(want.get(i, [])) <= 10
    if i in cel: assert (N[i]['gc1'], N[i]['gc2']) == cel[i]
    print('%-20s %2d -> %2d skills  %s%s' % (N[i]['name'], nsk(old[i]), nsk(N[i]), ', '.join(want.get(i, [])),
          '  celebrations %d/%d -> %d/%d' % (old[i]['gc1'], old[i]['gc2'], N[i]['gc1'], N[i]['gc2']) if i in cel else ''))
print('players', len(set(want) | set(cel)), '| skills added', sum(map(len, want.values())), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
