"""Task 23, research step: writes task23.tsv, the table that task23.py applies. Run on the output of task22.py.

Who: club players of the five leagues (England, Spain, Italy, Germany, France; the 93 clubs of task 15's `TOP5`) whose
playing style PES 2017 never switches on where they play (`WORKS` / `plays` of task22.py).

Evidence (real matches of 2025-26 and 2026-27, files under $PES_WORK/src, see README):
  fb26   FBref 2025-26, five leagues: minutes, goals, assists, shots        asta-fantacalcio/big5_stats_full.csv, big5_shooting.csv
  fb27   FBref 2026-27 up to mid November 2026: the same plus crosses,       optiscout-football-dss/data/players_data_light-2026_2027.csv
         tackles won, interceptions, fouls drawn
  us26   Understat 2025-26: xG, xA, key passes, xG build-up                  asta-fantacalcio/understat_full.csv
  ea     EA FC 27 card (scouted on 2025-26): attributes and PlayStyles       mouhbnms_football-player-scouting/Data/players.csv
A player without an EA card is judged on the abilities the file holds for him (Konami's numbers) instead of EA's.
Rates per 90 minutes need 900 minutes over both seasons (also for Understat), 450 for the figures that only 2026-27 has.
Players are matched by name and birth year (Understat, which has no birth year: by name and the minutes of FBref).

Playing style: only styles PES 2017 switches on at the position are given.
  CB       Build Up when he really builds play, measured against the 306 centre-backs of these leagues that Konami calls
           Build Up (xG build-up per 90: quartiles 0.19 / 0.27 / 0.37; short passing 66 / 71 / 76; long passing 61 / 67 / 73):
             xG build-up >= 0.27 with short passing >= 66 and long passing >= 61, or
             short passing >= 71 and long passing >= 67 (xG build-up >= 0.19 if he has the minutes), or
             a passing PlayStyle (Long Ball Pass, Pinged Pass, Incisive Pass, Tiki Taka) with short passing >= 71.
           Otherwise the style stays: PES 2017 has no stopper style at CB (sources differ on whether The Destroyer
           works there), and Extra Frontman (a centre-back who runs upfield in open play) is given to nobody.
  DMF      1. short passing >= 82 and a passing PlayStyle                                           -> Build Up
           2. tackles won + interceptions >= 2.7 per 90, or interceptions >= 80, standing tackle >= 78
              and aggression >= 78                                                                  -> The Destroyer
           3. short passing >= 80 with key passes >= 1.2, xG build-up >= 0.35, a passing PlayStyle
              or long passing >= 80; or shots >= 1.5 per 90                                         -> Build Up
           4. otherwise                                                                             -> Anchor Man
  CMF      ball winner as in DMF 2 -> The Destroyer; goals or xG >= 0.25 per 90 -> Hole Player;
           key passes >= 1.5 and short passing >= 78 -> Classic No. 10; otherwise Box-to-Box
  LMF RMF  interceptions >= 65 (a wing-back or full-back by trade), or tackles + interceptions >= 2.2 per 90 with
           interceptions >= 55                                                                      -> Box-to-Box
           otherwise (an attacker)                                                                  -> Hole Player
  AMF      key passes >= 1.5, short passing >= 78 and fewer than 2 shots per 90 -> Classic No. 10; otherwise Hole Player
           (under 900 minutes: vision and short passing >= 75 and vision above finishing -> Classic No. 10)
  SS       goals or xG >= 0.35 per 90 -> Goal Poacher; key passes >= 1.5 or xA >= 0.17 -> Creative Playmaker;
           otherwise Dummy Runner (under 900 minutes: finishing >= 75 and not below vision -> Goal Poacher;
           vision >= 75 -> Creative Playmaker)
  LWF RWF  key passes >= 1.8, or short passing >= 78 and vision >= 78 (not a full-back) -> Creative Playmaker;
           otherwise Prolific Winger
  CF       190 cm or taller -> Target Man; goals or xG >= 0.4 per 90 -> Goal Poacher; otherwise Dummy Runner
  LB RB    crosses >= 2.5 per 90, xA >= 0.1 or crossing >= 72 -> Offensive Full-back; otherwise Defensive Full-back
A player with fewer than 900 minutes over the two seasons and no EA card is left alone (no evidence).

Skills and COM styles are only added, never removed, up to the limits of the game (10 skills, 5 COM styles).
  from EA PlayStyles (pairs that Konami's own data confirms: share of holders who have the PES skill, against the
  share among all 8,835 players known to both):
    Precision Header, Aerial Fortress -> Heading (62 %, 63 % / 20 %)      Finesse Shot -> Long Range Drive (38 / 11)
    Acrobatic -> Acrobatic Finishing (44 / 10)                            Tiki Taka -> One-touch Pass (59 / 17)
    Incisive Pass, Pinged Pass -> Weighted Pass (33, 36 / 11)             Whipped Pass -> Pinpoint Crossing (46 / 11)
    Long Throw -> Long Throw (37 / 5)                                     Block -> Acrobatic Clear (42 / 14)
    Jockey -> Man Marking (33 / 10)                                       Relentless -> Fighting Spirit (35 / 18)
    Technical, Trickster -> Cut Behind & Turn (44, 51 / 17)               Trickster -> Scissors Feint (38 / 8)
    COM: Trickster -> Trickster (70 / 13); Technical, Trickster -> Mazing Run (69, 79 / 24);
         Rapid, Quick Step -> Speeding Bullet (76, 78 / 23); Quick Step (forwards, wide players) -> Incisive Run (64 / 21);
         Long Ball Pass, Pinged Pass -> Long Ball Expert (62, 56 / 24); Whipped Pass -> Early Cross (58 / 17);
         Power Shot -> Long Ranger (71 / 27)
  from the match figures:
    crosses >= 3.6 per 90 (top 15 %) with xA or assists >= 0.15 per 90 -> Pinpoint Crossing; a wide player also gets
    COM Early Cross (Early Cross is given to wide players only: the crosses of a central player are set pieces)
    fouls drawn >= 2.2 per 90 -> Malicia
    an attacker with tackles won + interceptions >= 2.0 per 90 -> Track Back
    a centre-back with 4 or more goals over the two seasons -> Heading
    15 or more matches, 60 % of them from the bench, goals + assists >= 0.45 per 90 -> Super-sub

Usage: python3 task23_research.py <task22 data.dat> <out tsv>
"""
import os, sys, csv, collections
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
_out = sys.argv[2]; sys.argv[2] = os.devnull
exec(compile(_src[:_src.index('# ------------------------------------------------------------------ 1. transfers')], 'task15.py set-up', 'exec'))

STYLES = ['None', 'Goal Poacher', 'Dummy Runner', 'Fox in the Box', 'Prolific Winger', 'Classic No. 10', 'Hole Player', 'Box-to-Box', 'Anchor Man',
          'The Destroyer', 'Extra Frontman', 'Offensive Full-back', 'Defensive Full-back', 'Target Man', 'Creative Playmaker', 'Build Up',
          'Offensive Goalkeeper', 'Defensive Goalkeeper']
WORKS = {1: 'CF SS', 2: 'CF SS AMF', 3: 'CF', 13: 'CF', 14: 'LWF RWF SS', 4: 'LWF RWF', 5: 'AMF CMF', 6: 'AMF LMF RMF CMF', 7: 'AMF LMF RMF CMF',
         9: 'DMF CMF', 8: 'DMF', 15: 'DMF LB RB CB', 10: 'CB', 11: 'LB RB', 12: 'LB RB', 16: 'GK', 17: 'GK'}       # as in task22.py
WORKS = {k: v.split() for k, v in WORKS.items()}

SRC = os.path.join(os.environ.get('PES_WORK', '/home/user/pes-work/'), 'src')
SK = ['Scissors Feint', 'Flip Flap', 'Marseille Turn', 'Sombrero', 'Cut Behind & Turn', 'Scotch Move', 'Heading', 'Long Range Drive', 'Knuckle Shot',
      'Acrobatic Finishing', 'Heel Trick', 'First-time Shot', 'One-touch Pass', 'Weighted Pass', 'Pinpoint Crossing', 'Outside Curler', 'Rabona',
      'Low Lofted Pass', 'Low Punt Trajectory', 'Long Throw', 'GK Long Throw', 'Malicia', 'Man Marking', 'Track Back', 'Acrobatic Clear', 'Captaincy',
      'Super-sub', 'Fighting Spirit']
COM = ['Trickster', 'Mazing Run', 'Speeding Bullet', 'Incisive Run', 'Long Ball Expert', 'Early Cross', 'Long Ranger']
PS_SKILL = {'Precision Header': ['Heading'], 'Aerial Fortress': ['Heading'], 'Finesse Shot': ['Long Range Drive'], 'Acrobatic': ['Acrobatic Finishing'],
            'Tiki Taka': ['One-touch Pass'], 'Incisive Pass': ['Weighted Pass'], 'Pinged Pass': ['Weighted Pass'], 'Whipped Pass': ['Pinpoint Crossing'],
            'Long Throw': ['Long Throw'], 'Block': ['Acrobatic Clear'], 'Jockey': ['Man Marking'], 'Relentless': ['Fighting Spirit'],
            'Technical': ['Cut Behind & Turn'], 'Trickster': ['Cut Behind & Turn', 'Scissors Feint']}
PS_COM = {'Trickster': ['Trickster', 'Mazing Run'], 'Technical': ['Mazing Run'], 'Rapid': ['Speeding Bullet'], 'Quick Step': ['Speeding Bullet'],
          'Long Ball Pass': ['Long Ball Expert'], 'Pinged Pass': ['Long Ball Expert'], 'Whipped Pass': ['Early Cross'], 'Power Shot': ['Long Ranger']}
PASSING = {'Long Ball Pass', 'Pinged Pass', 'Incisive Pass', 'Tiki Taka'}
ATTACK = ('CF', 'SS', 'LWF', 'RWF', 'AMF')
WIDE = ('LWF', 'RWF', 'LMF', 'RMF', 'LB', 'RB')

# ------------------------------------------------------------------ sources
def rows(f): return list(csv.DictReader(open(os.path.join(SRC, f), encoding='utf-8-sig')))
def num(x):
    try: return float(x)
    except (TypeError, ValueError): return 0.0
def merge(rs, name, born, cols):
    """One row per person: the rows of a player who changed club are added up."""
    out = {}
    for r in rs:
        o = out.setdefault((r[name], r.get(born) if born else r.get('player_id')), {'name': r[name], 'born': int(num(r.get(born))) if born else 0, 'sq': set()})
        o['sq'].add(r.get('Squad') or r.get('team') or '')
        for a, b in cols.items(): o[a] = o.get(a, 0.0) + num(r.get(b))
    return list(out.values())
fb27 = merge(rows('optiscout-football-dss/data/players_data_light-2026_2027.csv'), 'Player', 'Born',
             dict(min='Min', mp='MP', st='Starts', g='Gls', a='Ast', sh='Sh', crs='Crs', tkl='TklW', int='Int', fld='Fld', pk='PK'))
fb26 = merge([r for r in rows('asta-fantacalcio/big5_stats_full.csv') if r['season'] == '2526'], 'player', 'born',
             dict(min='Playing Time_Min', mp='Playing Time_MP', st='Playing Time_Starts', g='Performance_Gls', a='Performance_Ast', pk='Performance_PK'))
_sh = {(r['name'], r['born']): r['sh'] for r in merge([r for r in rows('asta-fantacalcio/big5_shooting.csv') if r['season'] == '2526'],
                                                      'player', 'born', dict(sh='Standard_Sh'))}
for r in fb26: r['sh'] = _sh.get((r['name'], r['born']), 0.0)
us26 = merge([r for r in rows('asta-fantacalcio/understat_full.csv') if r['season'] == '2526'], 'player', None,
             dict(min='minutes', xg='np_xg', xa='xa', kp='key_passes', bu='xg_buildup'))
ea27 = {r['player_id']: r for r in rows('mouhbnms_football-player-scouting/Data/players.csv')}
def index(rs):
    ix = collections.defaultdict(list)
    for r in rs:
        r['_t'] = rate.toks(r['name'])
        for t in set(r['_t']): ix[t].append(r)
    return ix
I27, I26, IU = index(fb27), index(fb26), index(us26)
def find(ix, names, ok, clubname):
    """The one row that carries the same name: equal words, else one name inside the other, else surname + initial.
    A one-word name that is only the first name of the other ("Lucas" for Lucas Bretelle) needs the same club as well."""
    best = collections.defaultdict(dict); cl = {w for w in rate.toks(clubname) if len(w) >= 4}
    for nm in names:
        t = rate.toks(nm or '')
        if not t: continue
        for r in ix.get(t[-1], []) + ix.get(t[0], []):
            if not r['_t'] or not ok(r): continue
            a, b = set(t), set(r['_t'])
            s = 3 if a == b else 2 if a <= b or b <= a else 1 if (t[-1] == r['_t'][-1] and t[0][0] == r['_t'][0][0]) else 0
            if s == 2 and min(len(a), len(b)) == 1 and t[-1] != r['_t'][-1] and not (cl & {w for q in r['sq'] for w in rate.toks(q)}): s = 0
            if s: best[s][id(r)] = r
    for s in (3, 2, 1):
        if len(best[s]) == 1: return list(best[s].values())[0]
        if best[s]: return None
    return None

fielded = {}
for t in CLUBS:
    g = pes.plans[t]; r = pes.rosters[t]; pos = g['presets'][0]['forms'][0]['pos']
    for k in range(11):
        if r[g['xi'][k]][0] and pos[k] < len(POS): fielded[r[g['xi'][k]][0]] = POS[pos[k]]
plays = lambda i: fielded.get(i, POS[P[i]['reg_pos']])

EA = dict(sp='attacking_short_passing', lp='skill_long_passing', ic='mentality_interceptions', ag='mentality_aggression', vi='mentality_vision',
          cr='attacking_crossing', st='defending_standing_tackle')
OWN = dict(sp='lowpass', lp='loftpass', ic='def', ag='ball_win', vi='lowpass', cr='loftpass', st='ball_win')     # no EA card: the file's abilities

def evidence(i):
    p = P[i]; born = 2026 - p['age']; c = ea27.get(m27[i]['id']) if i in m27 else None
    names = [p['name']] + ([c['first_name'] + ' ' + c['last_name'], c['common_name']] if c else [])
    a = find(I27, names, lambda r: abs(r['born'] - born) <= 1 or not r['born'], tname(club[i]))
    b = find(I26, names, lambda r: abs(r['born'] - born) <= 1 or not r['born'], tname(club[i]))
    u = find(IU, names, lambda r: abs(r['min'] - b['min']) <= max(60, 0.1 * b['min']), tname(club[i])) if b else None     # Understat has no birth year
    f = {'ps': {x.strip().rstrip('+') for x in (c['playstyles'] if c else '').split(',') if x.strip()}, 'ea': c is not None, 'src': []}
    ma = a['min'] if a else 0; mb = b['min'] if b else 0; f['min26'], f['min27'] = mb, ma
    tot = lambda k: (a[k] if a else 0) + (b[k] if b else 0)
    f['g'], f['a'], f['mp'], f['sub'] = tot('g'), tot('a'), tot('mp'), tot('mp') - tot('st')
    if ma + mb >= 900:
        f['g90'] = 90 * (tot('g') - tot('pk')) / (ma + mb); f['a90'] = 90 * tot('a') / (ma + mb); f['sh90'] = 90 * tot('sh') / (ma + mb)
    if ma >= 450:
        f['def90'] = 90 * (a['tkl'] + a['int']) / ma; f['crs90'] = 90 * a['crs'] / ma; f['fld90'] = 90 * a['fld'] / ma
    if u and u['min'] >= 900:
        for k in ('xg', 'xa', 'kp', 'bu'): f[k + '90'] = 90 * u[k] / u['min']
    for k in EA: f[k] = num(c[EA[k]]) if c else float(p[OWN[k]])
    f['height'] = num(c['height_cm']) if c and num(c['height_cm']) else p['height']
    f['stats'] = ma + mb >= 900
    f['fin'] = num(c['attacking_finishing']) if c else float(p['finish'])
    return f

def ge(f, k, x): return k in f and f[k] >= x
def style(pos, f, why):
    """The style for a player at `pos`, or None to leave him. `why` collects the figures that decided."""
    def note(*ks):
        why.extend('%s %s' % (k, ('%.2f' % f[k]) if k.endswith('90') else ('%d' % f[k])) for k in ks if k in f)
    winner = ge(f, 'def90', 2.7) or (f['ic'] >= 80 and f['st'] >= 78 and f['ag'] >= 78)
    passer = bool(f['ps'] & PASSING)
    if passer: why.append('PlayStyle ' + ', '.join(sorted(f['ps'] & PASSING)))
    if pos == 'CB':
        note('bu90', 'sp', 'lp')
        if (ge(f, 'bu90', 0.27) and f['sp'] >= 66 and f['lp'] >= 61) or (f['sp'] >= 71 and f['lp'] >= 67 and f.get('bu90', 1) >= 0.19) or (passer and f['sp'] >= 71): return 15
        return None
    if pos == 'DMF':
        if f['sp'] >= 82 and passer: note('sp'); return 15
        if winner: note('def90', 'ic', 'st', 'ag'); return 9
        if (f['sp'] >= 80 and (ge(f, 'kp90', 1.2) or ge(f, 'bu90', 0.35) or passer or f['lp'] >= 80)) or ge(f, 'sh90', 1.5):
            note('sp', 'lp', 'kp90', 'bu90', 'sh90'); return 15
        note('def90', 'sp', 'kp90', 'sh90'); return 8
    if pos == 'CMF':
        if winner: note('def90', 'ic', 'st', 'ag'); return 9
        if ge(f, 'g90', 0.25) or ge(f, 'xg90', 0.25): note('g90', 'xg90'); return 6
        if ge(f, 'kp90', 1.5) and f['sp'] >= 78: note('kp90', 'sp'); return 5
        note('def90', 'g90', 'kp90'); return 7
    if pos in ('LMF', 'RMF'):
        if f['ic'] >= 65 or (ge(f, 'def90', 2.2) and f['ic'] >= 55): note('ic', 'def90'); return 7
        note('ic', 'def90', 'g90', 'sh90'); return 6
    if pos == 'AMF':
        if not f['stats']: note('vi', 'sp', 'fin'); return 5 if f['vi'] >= 75 and f['sp'] >= 75 and f['vi'] > f['fin'] else 6
        if ge(f, 'kp90', 1.5) and f['sp'] >= 78 and not ge(f, 'sh90', 2.0): note('kp90', 'sp', 'sh90'); return 5
        note('g90', 'xg90', 'sh90', 'kp90'); return 6
    if pos == 'SS':
        if not f['stats']: note('fin', 'vi'); return 1 if f['fin'] >= 75 and f['fin'] >= f['vi'] else 14 if f['vi'] >= 75 else 2
        if ge(f, 'g90', 0.35) or ge(f, 'xg90', 0.35): note('g90', 'xg90'); return 1
        if ge(f, 'kp90', 1.5) or ge(f, 'xa90', 0.17): note('kp90', 'xa90'); return 14
        note('g90', 'xg90', 'kp90', 'xa90'); return 2
    if pos in ('LWF', 'RWF'):
        if f['ic'] < 65 and (ge(f, 'kp90', 1.8) or (f['sp'] >= 78 and f['vi'] >= 78)): note('kp90', 'sp', 'vi'); return 14
        note('kp90', 'sp', 'vi', 'crs90'); return 4
    if pos == 'CF':
        if f['height'] >= 190: note('height'); return 13
        if ge(f, 'g90', 0.4) or ge(f, 'xg90', 0.4): note('g90', 'xg90'); return 1
        note('g90', 'xg90', 'height'); return 2
    if pos in ('LB', 'RB'):
        if ge(f, 'crs90', 2.5) or ge(f, 'xa90', 0.1) or f['cr'] >= 72: note('crs90', 'xa90', 'cr'); return 11
        note('crs90', 'xa90', 'cr'); return 12
    return None

def extras(pos, f):
    """Skills and COM styles the evidence supports: [(name, reason)], most telling first."""
    sk, com = [], []
    if ge(f, 'crs90', 3.6):
        if pos in WIDE: com.append(('Early Cross', 'crosses %.1f per 90' % f['crs90']))
        if ge(f, 'xa90', 0.15) or ge(f, 'a90', 0.15): sk.append(('Pinpoint Crossing', 'crosses %.1f per 90 with assists' % f['crs90']))
    if ge(f, 'fld90', 2.2): sk.append(('Malicia', 'fouled %.1f times per 90' % f['fld90']))
    if (pos in ATTACK or (pos in ('LMF', 'RMF') and f['ic'] < 65)) and ge(f, 'def90', 2.0):
        sk.append(('Track Back', 'tackles + interceptions %.1f per 90' % f['def90']))
    if pos == 'CB' and f['g'] >= 4: sk.append(('Heading', '%d goals as a centre-back' % f['g']))
    if f['mp'] >= 15 and f['sub'] >= 0.6 * f['mp'] and f['min26'] + f['min27'] >= 900 and 90 * (f['g'] + f['a']) / (f['min26'] + f['min27']) >= 0.45:
        sk.append(('Super-sub', '%d of %d matches from the bench, %d goals + assists' % (f['sub'], f['mp'], f['g'] + f['a'])))
    for x in sorted(f['ps']):
        for s in PS_SKILL.get(x, []):
            if s in ('Man Marking', 'Acrobatic Clear') and pos in ATTACK: continue
            sk.append((s, 'PlayStyle ' + x))
        for s in PS_COM.get(x, []):
            if s != 'Early Cross' or pos in WIDE: com.append((s, 'PlayStyle ' + x))
        if x == 'Quick Step' and pos in ATTACK + ('LMF', 'RMF'): com.append(('Incisive Run', 'PlayStyle Quick Step'))
    return sk, com

# ------------------------------------------------------------------ the table
out = []; cnt = collections.Counter()
for i in sorted(club, key=lambda i: (tname(club[i]), -before[i], P[i]['name'])):
    p = P[i]; t = club[i]; pos = plays(i)
    if t not in TOP5 or not p['play_style'] or pos in WORKS[p['play_style']]: continue
    f = evidence(i); why = []; new = None; add, addc = [], []
    basis = ', '.join(x for x in ("2025-26 %d'" % f['min26'] if f['min26'] else '', "2026-27 %d'" % f['min27'] if f['min27'] else '',
                                  'EA FC 27' if f['ea'] else '') if x)
    if not f['stats'] and not f['ea']:
        note = 'left alone: fewer than 900 minutes and no EA card'; cnt[note] += 1
    else:
        new = style(pos, f, why)
        assert new is None or pos in WORKS[new]
        sk, com = extras(pos, f)
        have = [k for k in range(28) if p['sk%d' % k]]; hcom = [k for k in range(7) if p['com%d' % k]]
        for s, r in sk:
            k = SK.index(s)
            if k not in have and k not in [x[0] for x in add] and len(have) + len(add) < 10: add.append((k, r))
        for s, r in com:
            k = COM.index(s)
            if k not in hcom and k not in [x[0] for x in addc] and len(hcom) + len(addc) < 5: addc.append((k, r))
        note = ' | '.join(['style: ' + ', '.join(why)] * bool(why) + ['%s: %s' % (SK[k], r) for k, r in add] + ['COM %s: %s' % (COM[k], r) for k, r in addc])
        if new is None and not add and not addc: note = 'no change: ' + ', '.join(why); cnt['no change: the figures do not support one'] += 1
        else: cnt['players changed'] += 1
        cnt['style %s %s -> %s' % (pos, STYLES[p['play_style']], STYLES[new] if new else '(kept)')] += 1
        cnt['skills added'] += len(add); cnt['COM styles added'] += len(addc); cnt['new style'] += new is not None
    out.append([i, p['name'], tname(t), pos + ('*' if i in fielded else ''), before[i], STYLES[p['play_style']], STYLES[new] if new else '',
                '; '.join(SK[k] for k, _ in add), '; '.join(COM[k] for k, _ in addc), basis, note])
with open(_out, 'w', encoding='utf-8', newline='') as fh:
    w = csv.writer(fh, delimiter='\t', lineterminator='\n')
    w.writerow(['id', 'name', 'club', 'plays (* = starter)', 'overall', 'style before', 'new style', 'skills added', 'COM styles added', 'based on', 'evidence'])
    w.writerows(out)
print('%5d  players whose style has no effect where they play (five leagues)' % len(out))
for k, v in sorted(cnt.items(), key=lambda x: (-x[1], x[0])): print('%5d  %s' % (v, k))
