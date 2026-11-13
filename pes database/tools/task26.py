"""Task 26: positions of the five leagues, on the output of task25.py. Both lists come from the save "EDIT00000000
(another save i found online)" and are kept only where the 2026/27 sources agree: FotMob's positions played this season
(fotmob.py, most used first) and the EA FC 27 card (main position + alternatives).

REG   new registered position of a reserve: both sources list the position and at least one has it as his main one.
      As in task19.py the new position is rated A and his overall stays what it was; the old position stays A.
      A playing style that PES 2017 does not switch on at the new position is replaced by the one the rules of
      task23_research.py give there (`style`; '' = the rule leaves him, or his style works there).
      Starters are not moved: that would be a change of line-up.
PLAY  extra playable positions (rated A): one of the two sources lists the position.
Usage: python3 task26.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys
from lib import P17, POS, pack17
import rate

STYLES = ['None', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man',
          'The Destroyer', 'Extra Frontman', 'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up',
          'Offensive Goalkeeper', 'Defensive Goalkeeper']
WORKS = {1: 'CF SS', 2: 'CF SS AMF', 3: 'CF', 13: 'CF', 14: 'LWF RWF SS', 4: 'LWF RWF', 5: 'AMF CMF', 6: 'AMF LMF RMF CMF', 7: 'AMF LMF RMF CMF',
         9: 'DMF CMF', 8: 'DMF', 15: 'DMF LB RB CB', 10: 'CB', 11: 'LB RB', 12: 'LB RB', 16: 'GK', 17: 'GK'}       # as in task22.py
def works(style, pos): return pos in WORKS.get(style, '').split()

REG = [  # id, name, position, new style, FotMob 2026/27 | EA FC 27
    (45134, 'Ben Davies', 'CB', 'Build Up', 'CB, LB | CB'),
    (104717, 'Lucas Hernández', 'LB', 'Offensive Full-back', 'LB, CB | CB, LB, LM'),
    (106987, 'Josan', 'RWF', 'Prolific Winger', 'RW, RB | RM, RB, RW'),
    (119131, 'Sergio Gómez', 'LB', 'Offensive Full-back', 'LB | LB, LM, CM'),
    (121813, 'Takehiro Tomiyasu', 'CB', 'Build Up', 'CB, LB | LB, RB, CB, CM'),
    (127577, 'Robert Navarro', 'RWF', 'Prolific Winger', 'LW, RW | RW, RM, LW, LM'),
    (131334, 'Rodrigo Riquelme', 'LWF', 'Prolific Winger', 'LW | no card'),
    (138047, 'Filippo Terracciano', 'CB', '', 'CB, RB | CB, LB, RB'),
    (142217, 'Hugo Novoa', 'RB', 'Defensive Full-back', 'RB, RWB, RM | RM, RB'),
    (143567, 'Andrey Santos', 'DMF', 'Build Up', 'CDM, CM | CM, CDM'),
    (154218, 'Giovane', 'CF', 'Dummy Runner', 'ST, RW | ST, CAM'),
    (164591, 'Santiago Mouriño', 'RB', '', 'RB | RB, CB'),
    (165637, 'Pau Navarro', 'CB', 'Build Up', 'CB, RB | CB, RB, CM'),
    (166254, 'Ayyoub Bouaddi', 'DMF', 'Build Up', 'CDM, CM, RB | CDM, CM'),
    (167060, 'Trey Nyoni', 'CMF', '', 'CDM, CM | CM, CAM, CDM'),
    (168813, 'Josh Acheampong', 'CB', 'Build Up', 'CB, RB | CB, RB'),
    (170229, 'Rafita', 'RB', 'Defensive Full-back', 'LB, RB | RB, LB, RM, LM'),
    (172317, 'Jorge Salinas', 'LB', '', 'LB, CB | LB, CB'),
    (178082, 'Max Dowman', 'RWF', 'Prolific Winger', 'RW, CM, CAM | no card')]
PLAY = [  # id, name, positions added
    (104226, 'Bernardo Silva', 'DMF'), (110439, 'Pablo Fornals', 'CMF'), (110644, 'Raphinha', 'CF LMF'), (113911, 'Federico Valverde', 'DMF'),
    (117289, 'Tete Morente', 'LWF'), (118977, 'Rodrygo', 'LMF RMF'), (130727, 'Pathé Ciss', 'CB'), (132933, 'Jude Bellingham', 'CF'),
    (147955, 'Bradley Barcola', 'CF'), (179264, 'Thiago Pitarch', 'DMF')]

SRC, OUT = sys.argv[1:3]
pes = P17(SRC); P = pes.players; d = bytearray(pes.d); done = {}
def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
starters = {pes.rosters[t][k][0] for t in pes.teams if pes.isclub(t) for k in pes.plans[t]['xi'][:11]}
for i, name, role, style, _ in REG:
    p = P[i]; assert p['name'] == name and i not in starters, name
    was = (POS[p['reg_pos']], rate.overall(p), p['play_style'])
    p['reg_pos'] = POS.index(role); p['pp_' + role] = 2
    if style: assert not works(was[2], role) and works(STYLES.index(style), role), name; p['play_style'] = STYLES.index(style)
    assert rate.overall(p) == was[1] or rate.retarget(p, was[1]), ('overall cannot be kept', name)
    d[off(i) + 16:off(i) + 51] = pack17(p); done[i] = (role, was)
for i, name, roles in PLAY:
    p = P[i]; assert p['name'] == name and all(p['pp_' + r] < 2 for r in roles.split()), name
    for r in roles.split(): p['pp_' + r] = 2
    d[off(i) + 16:off(i) + 51] = pack17(p); done[i] = roles
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and new.rosters == pes.rosters
lo = pes.P0; hi = lo + pes.np * pes.PSZ; assert new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:], 'something outside the player records changed'
old = P17(SRC).players
for i in P:
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    if i not in done: assert a == b, ('another player changed', P[i]['name']); continue
    assert a[:16] == b[:16] and a[51:] == b[51:] and all(N[i]['pp_' + r] >= old[i]['pp_' + r] for r in POS), N[i]['name']
    if isinstance(done[i], str):
        same = {k: v for k, v in N[i].items() if k != 'raw' and not (k.startswith('pp_') and k[3:] in done[i].split())}
        assert all(N[i]['pp_' + r] == 2 for r in done[i].split()) and all(old[i][k] == v for k, v in same.items()), N[i]['name']
        print('%-20s %-3s also plays %s' % (N[i]['name'], POS[N[i]['reg_pos']], done[i])); continue
    role, was = done[i]
    assert POS[N[i]['reg_pos']] == role and N[i]['pp_' + role] == 2 and N[i]['pp_' + was[0]] == 2 and rate.overall(N[i]) == was[1], N[i]['name']
    assert all(N[i][k] == old[i][k] for k in N[i] if k.startswith(('sk', 'com')) or k in ('age', 'height', 'foot', 'form', 'injury')), N[i]['name']
    print('%-20s %-3s %d (%s) -> %-3s %d (%s)' % (N[i]['name'], was[0], was[1], STYLES[was[2]], role, rate.overall(N[i]), STYLES[N[i]['play_style']]))
print('registered positions', len(REG), '| players with extra positions', len(PLAY), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
