"""Task 29: what is left to take from the save "EDIT00000000 (another save i found online)" in playable positions,
playing styles and shirt numbers, all leagues, on the output of task28.py. Outside the few players its author edited
that save is our first upload, so each difference was measured against a 2026/27 source first:

PLAY   A position only the other save has is listed by EA FC 27 or FotMob in 57 of 743 cases (8 %); one that only ours
       has in 479 of 1,115 (43 %). Taken: the listed ones, at the level of the other save (A or B). A wing-back
       position does not count as full-back.
STYLE  Ours has an effect where the player plays and the other save's has none for 1,799 players, the reverse for 86.
       Taken: club players whose style has no effect, where the other save's has and the rules of
       task23_research.py (on the EA FC 27 card) give that same style.
NUM    Outside the five leagues the other save's numbers are last season's: 801 of the 1,078 differences are numbers
       Football Life 27 confirms for us (checked on Fenerbahçe, AZ and Southampton: ours right 14 times of 14); the
       rest are players Football Life 27 no longer has at the club, and their old number is now on a team-mate (219
       of 224 looked at). Taken: two that 2026/27 squad lists confirm.
Nothing is removed; ratings, registered positions and line-ups stay.
Usage: python3 task29.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys
from lib import P17, POS, pack17, u32
import rate

STYLES = ['None', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man',
          'The Destroyer', 'Extra Frontman', 'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up',
          'Offensive Goalkeeper', 'Defensive Goalkeeper']
WORKS = {1: 'CF SS', 2: 'CF SS AMF', 3: 'CF', 13: 'CF', 14: 'LWF RWF SS', 4: 'LWF RWF', 5: 'AMF CMF', 6: 'AMF LMF RMF CMF', 7: 'AMF LMF RMF CMF',
         9: 'DMF CMF', 8: 'DMF', 15: 'DMF LB RB CB', 10: 'CB', 11: 'LB RB', 12: 'LB RB', 16: 'GK', 17: 'GK'}       # as in task22.py
def works(style, pos): return pos in WORKS.get(style, '').split()

PLAY = [  # id, name, positions added (A or B), where the position is listed
    (155214, 'Nico Paz', 'RWF:B', 'EA FC 27: CAM ST | FotMob: CAM ST RW'),
    (102719, 'Patrik Schick', 'AMF:B', 'EA FC 27: ST | FotMob: ST CAM'),
    (137990, 'Christos Tzolis', 'AMF:B', 'EA FC 27: LW LM | FotMob: LW CAM'),
    (113502, 'Yoane Wissa', 'AMF:B', 'EA FC 27: ST | FotMob: ST CAM'),
    (123999, 'Cameron Puertas', 'RMF:A', 'EA FC 27: CAM CM RM CDM'),
    (60565, 'Bruno Petković', 'AMF:B', 'EA FC 27: ST CAM'),
    (106635, 'Bernardo', 'CB:A', 'EA FC 27: LB CB | FotMob: LB CB'),
    (120929, 'Eric Smith', 'CMF:B', 'EA FC 27: CB CDM CM'),
    (138420, 'Jan Kuchta', 'LWF:B', 'EA FC 27: ST RW LW'),
    (70844, 'Derry Scherhant', 'AMF:B LMF:B', 'EA FC 27: LM ST LW CAM | FotMob: LW RW'),
    (70858, 'Linton Maina', 'LWF:A LMF:B', 'EA FC 27: LM ST LW CAM | FotMob: CAM LM RW'),
    (70888, 'Mert Kömür', 'DMF:A', 'EA FC 27: CAM ST CM | FotMob: CAM ST CDM'),
    (106764, 'Haris Hajradinović', 'DMF:B', 'EA FC 27: CM CAM CDM'),
    (116671, 'Carlo Holse', 'DMF:B', 'EA FC 27: CAM CM CDM'),
    (120411, 'Andreas Skov Olsen', 'CF:B', 'EA FC 27: RM RW CAM ST'),
    (71149, 'Hugo Bolin', 'CMF:A', 'EA FC 27: LM RM CM LW | FotMob: CAM LM RM LW CM'),
    (142228, 'Jan Thielmann', 'RMF:B', 'EA FC 27: RM RW RB | FotMob: RM RW ST CM RWB'),
    (143773, 'Kacper Kozłowski', 'DMF:B', 'EA FC 27: CM RM CAM CDM'),
    (70946, 'Benedikt Gimber', 'CMF:B', 'EA FC 27: CB CDM CM'),
    (107698, 'Stijn Spierings', 'CB:B', 'EA FC 27: CM CDM CB'),
    (112228, 'Sékou Koïta', 'CMF:B', 'EA FC 27: ST CAM RM CM'),
    (124349, 'Mark Brink', 'CB:B', 'EA FC 27: CDM CM CB'),
    (138496, 'Efkan Bekiroğlu', 'DMF:B', 'EA FC 27: CAM CM CDM'),
    (152207, 'Junnosuke Suzuki', 'CMF:B', 'EA FC 27: RB CB CM'),
    (75837, 'Ole Didrik Blomberg', 'LWF:B', 'EA FC 27: RW LW ST RM'),
    (117751, 'Elton Acolatse', 'CF:B', 'EA FC 27: LM LW ST'),
    (157324, 'Emmanuel Addai', 'CF:B', 'EA FC 27: LM ST LW'),
    (71121, 'Louis Oppie', 'LWF:B', 'EA FC 27: LB LM CM LW'),
    (109217, 'Pedro Pereira', 'RWF:B', 'EA FC 27: RB CB RM RW'),
    (173651, 'Relebohile Mofokeng', 'CF:A', 'EA FC 27: CAM LM ST LW'),
    (70861, 'Ben Bobzien', 'AMF:B LMF:B', 'EA FC 27: LM LW ST CAM'),
    (126767, 'Mikkel Kaufmann', 'LMF:B RMF:B', 'EA FC 27: ST LM RM LW'),
    (138407, 'Christian Conteh', 'AMF:B', 'EA FC 27: RM ST CAM RW'),
    (146965, 'Oleksiy Kashchuk', 'LMF:B', 'EA FC 27: RW RM LM'),
    (151584, 'Juan Córdoba', 'CF:A', 'EA FC 27: RW RM ST'),
    (75833, 'Sondre Auklend', 'DMF:B', 'EA FC 27: CM RW CDM RM'),
    (126342, 'Rabbi Matondo', 'AMF:B', 'EA FC 27: LM LW ST CAM'),
    (126544, 'William Balikwisha', 'DMF:B', 'EA FC 27: CAM CM CDM'),
    (132499, 'Oliver Villadsen', 'RWF:B', 'EA FC 27: RB RM RW'),
    (157690, 'Isak Määttä', 'RMF:A', 'EA FC 27: RW LW LB RM'),
    (162071, 'Valmir Matoshi', 'LMF:B', 'EA FC 27: CM CAM LM CDM'),
    (166167, 'Juho Lähteenmäki', 'CMF:B', 'EA FC 27: LB RB CM'),
    (140392, 'Gabriel Pirani', 'DMF:B', 'EA FC 27: CAM CM ST CDM'),
    (155248, 'Alexander Jensen', 'RWF:B', 'EA FC 27: RB RM RW'),
    (71124, 'Jannik Robatsch', 'DMF:A', 'EA FC 27: CB LB CDM'),
    (165679, 'Dal Varešanović', 'DMF:B', 'EA FC 27: CAM CM CDM'),
    (178002, 'Lucas Ferreira', 'AMF:A', 'EA FC 27: RW LM CAM RM'),
    (164659, 'Axel Kayombo', 'AMF:B CMF:B LMF:A', 'EA FC 27: ST CAM LM CM'),
    (170553, 'Ayodele Thomas', 'CF:B', 'EA FC 27: LW ST LM'),
    (71045, 'David Preu', 'CF:A', 'EA FC 27: LM CAM LW ST'),]
STYLE = [  # id, name, new style, EA FC 27 figures that decide under the task 23 rule
    (7511, 'Lionel Messi', 'Creative Playmaker', 'RWF: short passing 90, vision 88'),
    (59589, 'Alireza Jahanbakhsh', 'Hole Player', 'RMF: interceptions 45'),
    (75816, 'Youssoupha Sanyang', 'Hole Player', 'AMF: vision 65, short passing 65'),
    (75826, 'Odin Bjørtuft', 'Build Up', 'CB: PlayStyle Long Ball Pass, short passing 77, long passing 70'),
    (75837, 'Ole Didrik Blomberg', 'Prolific Winger', 'RWF: short passing 70, vision 67'),
    (76109, 'Marius Corbu', 'Hole Player', 'AMF: vision 70, short passing 73'),
    (104735, 'Steven Bergwijn', 'Prolific Winger', 'LWF: short passing 77, vision 77'),
    (118671, 'Nair Tiknizyan', 'Offensive Full-back', 'LB: crossing 73'),
    (139957, 'Jayden Oosterwolde', 'Defensive Full-back', 'LB: crossing 68'),
    (140228, 'Ahmetcan Kaplan', 'Build Up', 'CB: short passing 73, long passing 71'),
    (145056, 'Elijah Just', 'Prolific Winger', 'RWF: short passing 69, vision 71'),
    (148098, 'Joseph Rosales', 'Box-to-Box', 'CMF: no ball-winner, scorer or playmaker figures'),
    (151001, 'Facundo Lencioni', 'Hole Player', 'LMF: interceptions 40'),
    (154857, 'Lorenzo Scipioni', 'Anchor Man', 'DMF: short passing 67'),
    (170577, 'Julien Kouadio', 'Defensive Full-back', 'RB: crossing 56'),
    (174863, 'Nicolas Pays', 'Hole Player', 'AMF: vision 67, short passing 67')]
NUM = [  # club, id, name, number, evidence; whoever wears it takes his old one
    ('UD Las Palmas', 115656, 'Dinko Horkaš', 1, 'flashscore.es squad list (and the web check of task 21); it was on Jonathan Viera, a midfielder'),
    ('Wrexham AFC', 133576, 'Issa Kaboré', 12, 'ESPN and Wikipedia 2026-27 squad lists; he wore 1 as a full-back')]

SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); play, sty, num = {}, {}, {}
def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
fielded = {}                                            # club starter -> position of his slot in the main formation (as task23.py)
for t in pes.teams:
    if not pes.isclub(t): continue
    g = pes.plans[t]; r = pes.rosters[t]; pos = g['presets'][0]['forms'][0]['pos']
    for k in range(11):
        if r[g['xi'][k]][0] and pos[k] < len(POS): fielded[r[g['xi'][k]][0]] = POS[pos[k]]
for i, name, add, _ in PLAY:
    p = P[i]; assert p['name'] == name, name
    for x in add.split():
        r, lvl = x.split(':'); assert p['pp_' + r] == 0, (name, r); p['pp_' + r] = 'BA'.index(lvl) + 1
    play[i] = add
for i, name, style, _ in STYLE:
    p = P[i]; pos = fielded.get(i, POS[p['reg_pos']]); assert p['name'] == name and not works(p['play_style'], pos) and works(STYLES.index(style), pos), name
    sty[i] = (p['play_style'], STYLES.index(style), pos); p['play_style'] = STYLES.index(style)
for i in set(play) | set(sty): d[off(i) + 16:off(i) + 51] = pack17(P[i])
for team, i, name, n, _ in NUM:
    t, = [t for t in pes.teams if pes.teams[t]['name'] == team]; o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t and P[i]['name'] == name
    r = [(u32(d, o + 4 + 4 * k), d[o + 132 + k]) for k in range(32)]; k, = [k for k in range(32) if r[k][0] == i]
    for j in range(32):
        if r[j][0] and r[j][1] == n: d[o + 132 + j] = r[k][1]; num[r[j][0]] = (t, r[k][1])
    d[o + 132 + k] = n; num[i] = (t, n)
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players; old = P17(SRC)
lo = pes.P0; hi = lo + pes.np * pes.PSZ; assert len(new.d) == len(old.d) and new.d[:lo] == old.d[:lo] and new.d[hi:pes.R0] == old.d[hi:pes.R0]
end = pes.R0 + len(pes.teams) * pes.RSZ; assert new.d[end:] == old.d[end:], 'something after the rosters changed'
for i in P:
    a, b = old.players[i], N[i]; diff = {k for k in b if k != 'raw' and a[k] != b[k]}
    want = {'pp_' + x.split(':')[0] for x in play.get(i, '').split()} | ({'play_style'} if i in sty else set())
    assert diff == want, ('player', a['name'], diff ^ want)
    if diff: assert rate.overall(a) == rate.overall(b) and a['reg_pos'] == b['reg_pos']
    if i in sty: assert b['play_style'] == sty[i][1]
for t in pes.teams:
    a, b = old.rosters[t], new.rosters[t]
    assert [x[0] for x in a] == [x[0] for x in b] and all(x == y or num.get(y[0]) == (t, y[1]) for x, y in zip(a, b)), pes.teams[t]['name']
    nums = [n for i, n in b if i]; assert len(set(nums)) == len(nums) or a == b, ('numbers', pes.teams[t]['name'])
assert all(dict(new.squad(t))[i] == n for i, (t, n) in num.items())
for i, (was, now, pos) in sty.items(): print('%-22s %-3s %-20s -> %s' % (N[i]['name'], pos, STYLES[was], STYLES[now]))
for i, (t, n) in num.items(): print('%-22s %-18s #%d -> #%d' % (N[i]['name'], pes.teams[t]['name'], dict(old.squad(t))[i], n))
print('players with extra positions %d (%d positions) | styles %d | numbers %d | bytes changed %d | self-check passed' % (
    len(play), sum(len(x.split()) for x in play.values()), len(sty), len(num), sum(x != y for x, y in zip(old.d, new.d))))
