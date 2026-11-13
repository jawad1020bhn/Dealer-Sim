"""FotMob first-team squads of the five leagues, 2026/27: `data/cache/squads_<league>_2026-27.json` of Savowai/xr-football
(commit 13dbadf, 12 Nov 2026), cloned to $PES_WORK/src/xr-football. Each row: name, shirt, position (the positions he
plays, most used first), age, country. Schalke, Elversberg and Paderborn are not in the edit file."""
import os, json
from lib import norm
W = os.environ.get('PES_WORK', '/home/user/pes-work/')
ALIAS = {'Brighton': 'Brighton & Hove Albion FC', 'Bournemouth': 'AFC Bournemouth', 'Deportivo A Coruña': 'Deportivo La Coruña',
         'Atlético Madrid': 'Club Atlético de Madrid', 'Athletic Club': 'Athletic Club de Bilbao', 'Racing Santander': 'Real Racing Club de Santander',
         'Rayo Vallecano': 'Rayo Vallecano de Madrid', 'Real Sociedad': 'Real Sociedad de Fútbol', 'Celta Vigo': 'RC Celta de Vigo',
         'Real Betis': 'Real Betis Balompié', 'Inter': 'Internazionale Milano', 'Milan': 'AC Milan', 'Roma': 'AS Roma', 'Lazio': 'S.S. Lazio',
         'Napoli': 'SSC Napoli', 'Monza': 'AC Monza', 'Mainz 05': '1. FSV Mainz 05', 'Bayer Leverkusen': 'Bayer 04 Leverkusen',
         'Werder Bremen': 'SV Werder Bremen', 'Union Berlin': '1. FC Union Berlin', 'Hoffenheim': 'TSG 1899 Hoffenheim',
         'Borussia Mönchengladbach': 'VfL Borussia M’gladbach', 'Lyon': 'Olympique Lyonnais', 'Marseille': 'Olympique de Marseille',
         'Rennes': 'Stade Rennais FC', 'Brest': 'Stade Brestois 29', 'Troyes': 'ESTAC Troyes', 'Lens': 'RC Lens', 'Nice': 'OGC Nice',
         'Le Havre': 'Havre AC', 'Strasbourg': 'RC Strasbourg Alsace', 'Lille': 'LOSC Lille', 'Monaco': 'AS Monaco', 'Auxerre': 'AJ Auxerre',
         'Angers': 'Angers SCO', 'Everton': 'Everton FC', 'Sunderland': 'Sunderland ΑFC', 'Manchester United': 'Manchester United'}
ABSENT = {'Schalke 04', 'Elversberg', 'Paderborn'}
TO17 = {'GK': 'GK', 'CB': 'CB', 'LB': 'LB', 'LWB': 'LB', 'RB': 'RB', 'RWB': 'RB', 'CDM': 'DMF', 'CM': 'CMF', 'CAM': 'AMF', 'LM': 'LMF', 'RM': 'RMF',
        'LW': 'LWF', 'RW': 'RWF', 'ST': 'CF'}

def squads(pes):
    """{team id of the edit file: [FotMob rows]} for the 93 clubs of the five leagues that the file has."""
    by = {}
    for t, x in pes.teams.items():
        if pes.isclub(t): by.setdefault(norm(x['name']), []).append(t)
    out = {}
    for lg in ('epl', 'laliga', 'seriea', 'bundesliga', 'ligue1'):
        for club, rows in json.load(open(W + 'src/xr-football/data/cache/squads_%s_2026-27.json' % lg, encoding='utf-8')).items():
            if club in ABSENT: continue
            if club in ALIAS: hit = by[norm(ALIAS[club])]
            else: k = norm(club); hit = [t for n, ts in by.items() if k in n for t in ts]
            assert len(hit) == 1, (club, [pes.teams[t]['name'] for t in hit])
            out[hit[0]] = [dict(r, pos17=list(dict.fromkeys(TO17[p] for p in (r['position'] or '').replace(' ', '').split(',') if p))) for r in rows]
    assert len(out) == 93 and len(set(out)) == 93
    return out

FOLD = str.maketrans({'ı': 'i', 'ł': 'l', 'ð': 'd', 'đ': 'dj', 'ß': 'ss', 'ø': 'o', 'æ': 'ae', 'Đ': 'Dj', 'Ł': 'L', 'Ø': 'O'})
def toks(name): return [norm(x.translate(FOLD)) for x in name.replace('.', '. ').replace('-', ' ').split()]

def same(name, age, row, level):
    """Is the record `name` (age of the file) the FotMob player `row`? Ages within one year, and
    level 0: the same words in any order ("Lee Kang-In" / "Kang-In Lee");
    level 1: one name is a run of the other's words ("Junior Kroupi" in "Éli Junior Kroupi"), a one-word name is one of
             his names, or the same family name with the same initial ("Joe Gomez" / "Joseph Gomez");
    level 2: the same family name (match() takes it only if nobody else at the club has it)."""
    if row['age'] is not None and abs(row['age'] - age) > 1: return False
    a, b = toks(name), toks(row['name'])
    if sorted(a) == sorted(b) or ''.join(a) == ''.join(b): return True
    if level == 0: return False
    s, l = sorted((a, b), key=len)
    if any(l[k:k + len(s)] == s for k in range(len(l) - len(s) + 1)) and (len(s) > 1 or len(s[0]) > 3): return True
    if len(a) > 1 and len(b) > 1 and a[0][0] == b[0][0] and (a[-1] == b[-1] or a[1:] == b[1:len(a)] or b[1:] == a[1:len(b)]): return True
    return level == 2 and len(a[-1]) > 3 and (a[-1] == b[-1] or (len(b) > 2 and a[-1] == b[-2]) or (len(a) > 2 and a[-2] == b[-1]))

def match(pes, fm):
    """{team: {player id: row}} for squad members found in the club's FotMob squad (one to one), and the rows left over.
    Three passes, strictest first; a pair is taken only if it is the only candidate on both sides."""
    hit, rest = {}, {}
    for t, rows in fm.items():
        m = {}; left = list(rows); P = pes.players
        for level in (0, 1, 2):
            ours = [i for i, _ in pes.squad(t) if i not in m]
            c = {i: [r for r in left if same(P[i]['name'], P[i]['age'], r, level)] for i in ours}
            for i in ours:
                if len(c[i]) == 1 and sum(c[i][0] in c[j] for j in ours) == 1: m[i] = c[i][0]; left.remove(c[i][0])
        hit[t] = m; rest[t] = left
    return hit, rest
