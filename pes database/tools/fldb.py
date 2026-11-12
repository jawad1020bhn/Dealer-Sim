"""Football Life 27 game database (Player.bin, PlayerAssignment.bin, Team.bin, Coach.bin in data_s26271.cpk of
choepd/FL27-player-names-ko), read with Binz120/pesforge's pesdb.py. Field names follow lib.F17."""
import sys, csv, os
W = os.environ.get('PES_WORK', '/home/user/pes-work/')
sys.path.insert(0, W + 'src/pesforge')
import pesdb
SRC = W + 'src/flko/'; CPK = SRC + 'data_s26271.cpk'
KEY = {'Offensive Awareness': 'atk', 'Ball Control': 'ball_ctrl', 'Dribbling': 'drib', 'Tight Possession': 'tight', 'Low Pass': 'lowpass',
       'Lofted Pass': 'loftpass', 'Finishing': 'finish', 'Place Kicking': 'place_kick', 'Curl': 'swerve', 'Heading': 'header',
       'Defensive Awareness': 'def', 'Ball Winning': 'ball_win', 'Aggression': 'aggr', 'GK Awareness': 'gk', 'GK Catching': 'catching',
       'GK Clearing': 'clearing', 'GK Reflexes': 'reflex', 'GK Reach': 'cover', 'Speed': 'speed', 'Acceleration': 'exp_pwr',
       'Kicking Power': 'kick_pwr', 'Jump': 'jump', 'Physical Contact': 'phys', 'Balance': 'body_ctrl', 'Stamina': 'stamina',
       'Age': 'age', 'Height (cm)': 'height', 'Weight (kg)': 'weight', 'Nationality': 'nation', 'Playing Style': 'play_style',
       'Registered Position': 'reg_pos', 'Form': 'form', 'Weak Foot Usage': 'weak_use', 'Weak Foot Accuracy': 'weak_acc',
       'Injury Resistance': 'injury', 'Stronger Foot': 'foot'}
from lib import POS, STATS17
def to17(q):
    """FL database record -> PES 2017 ability fields."""
    o = {k: q[k] for k in ['age', 'reg_pos', 'form', 'weak_use', 'weak_acc', 'injury', 'foot'] + STATS17}
    o['play_style'] = {18: 4, 19: 4, 20: 8, 21: 11}.get(q['play_style'], q['play_style'])
    for n in POS: o['pp_' + n] = q['pp_' + n]
    o['pp_' + POS[q['reg_pos']]] = 2
    for bit, lab in SKILL.items(): o[bit] = int(lab in q['skills'])
    return o
SKILL = dict(zip(['sk%d' % i for i in range(28)] + ['com%d' % i for i in range(7)],
    ['Scissors Feint', 'Flip Flap', 'Marseille Turn', 'Sombrero', 'Cut Behind & Turn', 'Scotch Move', 'Heading', 'Long Range Drive', 'Knuckle Shot',
     'Acrobatic Finishing', 'Heel Trick', 'First-time Shot', 'One-touch Pass', 'Weighted Pass', 'Pinpoint Crossing', 'Outside Curler', 'Rabona',
     'Low Lofted Pass', 'GK Long Throw', 'Long Throw', 'GK Low Punt', 'Gamesmanship', 'Man Marking', 'Track Back', 'Acrobatic Clear', 'Captaincy',
     'Super-Sub', 'Fighting Spirit', 'Trickster', 'Mazing Run', 'Speeding Bullet', 'Incisive Run', 'Long Ball Expert', 'Early Cross', 'Long Ranger']))
def load():
    """-> players by id, squads {team: [(player, shirt number)]}, team names {team: name}."""
    t = pesdb.PlayerTable(pesdb.table_blob(CPK, 'Player')); en = {}
    for r in csv.DictReader(open(SRC + '선수명단 한글 변환용 파일_v11.csv', encoding='utf-8-sig')): en[int(r['id'])] = r['english_name']
    for l in open(SRC + 'FL2710_players.txt', encoding='utf-8-sig'):
        a, _, b = l.strip().partition(' - ')
        if a.isdigit(): en.setdefault(int(a), b)
    P = {}
    for i in range(len(t.records)):
        p = {v: t.get(i, k) for k, v in KEY.items()}
        for k in ('form', 'weak_use', 'weak_acc', 'injury'): p[k] -= 1        # back to the stored 0-based value
        for n in pesdb.POS_NAMES: p['pp_' + n] = t.get(i, 'Pos ' + n)
        p['skills'] = {l for l, _ in pesdb.SKILLS if t.get(i, 'Skill ' + l)}
        p['id'] = t.pid(i); p['name'] = en.get(p['id'], ''); p['slots'] = [t.slot(i, n) for n in range(4)]
        P[p['id']] = p
    pa = pesdb.AssignmentTable(pesdb.table_blob(CPK, 'PlayerAssignment')); A = {}
    for i in range(len(pa.records)): A.setdefault(pa.team(i), []).append((pa.pid(i), pa.shirt_number(i)))
    tt = pesdb.TeamTable(pesdb.table_blob(CPK, 'Team')); T = {tt.tid(i): tt.name(i) for i in range(len(tt.records))}
    return P, A, T
