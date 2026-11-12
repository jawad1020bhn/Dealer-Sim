"""Task 14: realism pass on the output of `task12.py --older`.
  1. duplicates: a player stored twice keeps one record; the freed record becomes a real player the file lacks
  2. managers:   five national teams get back the newer manager that task 11 replaced with an older one
  3. squads:     national squads take Football Life 27 squad members that are in the file but not in the squad
  4. ratings:    club players aged 24 or over without an EA FC 27 or FC 26 rating move towards the estimate from their FL 27
                 abilities (only a gap of 4 or more, at most 5 points); players aged 23 or under are not lowered anywhere
  5. form:       the form value of every linked player as in FL 27
  6. nations:    three dual nationals set by hand (no source decides the others)
  7. positions:  a starter whose line-up role differs from his registered position is registered at the role when
                 EA FC 27 lists him there (LM / RM counts for LWF / RWF); the rating stays. Plus three named players.
  8. form rise:  Premier League 2026/27 (FPL points after the latest gameweek): the ten best of each position (three
                 keepers) rise towards the rating level of their rank, at most +3
  9. legends:    nine legends FL 27 does not have, built from the abilities of a similar legend of the file
Usage: python3 task14.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys, collections, struct, csv, unicodedata
from lib import P17, POS, pack17, norm, u32
import rate, fldb

SRC, OUT = sys.argv[1:3]
LEGENDS = (1458, 1459, 1460, 1462, 1463, 2703, 2704, 4971, 1386, 140, 2696, 2469)
NOTNATIONAL = LEGENDS + (4373, 5886)                      # FC Rouen 1899 and FC Versailles 78 sit in the national group
pes = P17(SRC); P = pes.players; D, A, T = fldb.load()
d = bytearray(pes.d); log = collections.Counter(); rep = collections.defaultdict(list)
leg = {i for t in LEGENDS for i, _ in pes.squad(t)}
club = {i: t for t in pes.teams if pes.isclub(t) for i, _ in pes.squad(t)}
before = {i: rate.overall(p) for i, p in P.items()}

def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
def put(i): d[off(i) + 16:off(i) + 51] = pack17(P[i])
def shirtname(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper().split()
    return (t[-1] if t else '')[:15]
def identity(i, name, nation, height, weight):
    o = off(i); P[i].update(name=name, nation=nation, height=height, weight=weight)
    struct.pack_into('<HBB', d, o + 10, nation, height, weight)
    d[o + 0x34:o + 0x34 + 46] = name.encode('utf8')[:45].ljust(46, b'\0')
    d[o + 0x62:o + 0x62 + 18] = shirtname(name).encode('latin1').ljust(18, b'\0')
def roster_off(t): o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t; return o
def squad_now(t): o = roster_off(t); return [u32(d, o + 4 + 4 * k) for k in range(32)]
def by_name(name, pool=None):
    hit = [i for i in (pool or P) if norm(P[i]['name']) == norm(name)]
    assert len(hit) == 1, (name, hit); return hit[0]

# ------------------------------------------------------------------ links to FL 27 and to EA FC 27 (as in task12.py)
link = {}
for i, p in P.items():            # ids 90000-96999 are other people in the FL database
    if i not in D or 90000 <= i < 97000: continue
    q = D[i]; da = abs(p['age'] - q['age'])
    if (da <= 1 and abs(p['height'] - q['height']) <= 2 and p['nation'] == q['nation']) or (norm(p['name']) == norm(q['name']) and da <= 3): link[i] = i
byname = collections.defaultdict(list); used = set(link.values())
for q in D.values(): byname[(norm(q['name']), q['age'], q['height'])].append(q['id'])
for i, p in P.items():
    if i in link: continue
    c = [x for x in byname.get((norm(p['name']), p['age'], p['height']), []) if x not in used]
    if len(c) == 1: link[i] = c[0]; used.add(c[0])
def names(i):
    n = [P[i]['name']]
    if i in link and norm(D[link[i]]['name']) != norm(n[0]): n.append(D[link[i]]['name'])
    return n
C27 = rate.fc27full(); I27 = rate.Index(C27)
m27 = rate.match_cards(C27, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=pes.teams[club[i]]['name'] if i in club else '',
                                  nation=p['nation']) for i, p in P.items() if i not in leg])
m26 = rate.match_cards(rate.fc26(), [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=pes.teams[club[i]]['name'] if i in club else '',
                                         nation=p['nation']) for i, p in P.items() if i not in leg and i not in m27])
raw = {i: rate.overall(fldb.to17(D[q])) for i, q in link.items()}
cal = collections.defaultdict(list)
for i in link:
    if i in m27 and P[i]['age'] > 23: cal[raw[i]].append(m27[i]['ovr'])
EST = rate.est_table(cal, 0)       # FL 27 overall -> expected EA rating, learned from the older players who have both

# ------------------------------------------------------------------ 1. duplicates
key = lambda s: frozenset(rate.toks(s))
def missing_free_agents():
    """FL 27 players without a squad whom the file lacks under any spelling, best first."""
    insq = {i for s in A.values() for i, _ in s}; known = collections.defaultdict(list)
    for p in P.values():
        t = rate.toks(p['name'])
        if t: known[t[-1]].append(p)
    out = []
    for i, q in D.items():
        t = rate.toks(q['name'])
        if i in insq or i in P or len(t) < 2 or q['age'] > 34: continue
        if any(abs(p['age'] - q['age']) <= 2 for k in t if len(k) > 3 for p in known.get(k, [])): continue    # a shared name of that age: maybe him
        c = I27.find(q['name'], q['age'], q['height'])
        out.append((c['ovr'] if c else EST[rate.overall(fldb.to17(q))], i))
    return [i for _, i in sorted(out, key=lambda x: (-x[0], x[1]))]
def become(i, q, target):
    """Record i becomes FL 27 player q; id, motions and appearance of the record stay."""
    old = P[i]['name']; P[i].update(fldb.to17(q)); identity(i, q['name'], q['nation'], q['height'], q['weight'])
    if rate.overall(P[i]) != target: assert rate.retarget(P[i], target), (q['name'], target)
    put(i); remade.add(i); rep['replaced'].append((old, q['name'], POS[P[i]['reg_pos']], target)); log['duplicate records turned into missing players'] += 1
inroster = {i for t in pes.teams for i, _ in pes.squad(t)}
freed = []; remade = set()
for dup, keep, name in ((71029, 174191, 'Johan Manzambi'), (71119, 181973, 'Ilyas Ansah'), (159269, 179126, 'Marcos Fernández'),
                        (142225, 146996, 'Jens Castrop'), (136274, 177103, 'Lamine Gueye')):       # free-agent copy of a club player
    assert norm(P[dup]['name']) == norm(P[keep]['name']) == norm(name) and dup not in inroster and keep in club, name
    freed.append(dup)
dup, keep = 91558, 161524                                   # Pablo Ganet: the club copy goes, the national-team record joins the club
assert norm(P[dup]['name']) == norm(P[keep]['name']) == norm('Pablo Ganet') and dup in club and keep not in club
o = roster_off(club[dup]); k = squad_now(club[dup]).index(dup); struct.pack_into('<I', d, o + 4 + 4 * k, keep)
club[keep] = club.pop(dup); freed.append(dup)
dup, keep = 71089, 181367                                   # Bazoumana Touré twice in one squad: the FL 27 record stays, with the EA rating
assert norm(P[dup]['name']) == norm(P[keep]['name']) == norm('Bazoumana Touré') and club[dup] == club[keep] and dup in m27
assert rate.retarget(P[keep], m27[dup]['ovr']); put(keep); m27[keep] = m27.pop(dup)
t = club[dup]; o = roster_off(t); sq = squad_now(t); k = sq.index(dup); last = max(x for x in range(32) if sq[x]); g = pes.plans[t]
# the squad has nobody missing to put there, so the copy leaves the roster: the last player takes his slot and shirt number stays with the player
assert g['xi'] + g['bench'] == list(range(32)) and k > 10 and not {k, last} & set(g['takers'] + g['join'] + [g['captain']]), 'line-up refers to the slot'
struct.pack_into('<I', d, o + 4 + 4 * k, sq[last]); d[o + 132 + k] = d[o + 132 + last]
struct.pack_into('<I', d, o + 4 + 4 * last, 0); d[o + 132 + last] = 0
dropped = {t: 1}; del club[dup]; freed.append(dup)
for i, j in zip(freed, missing_free_agents()):
    q = D[j]; c = I27.find(q['name'], q['age'], q['height'])
    become(i, q, c['ovr'] if c else EST[rate.overall(fldb.to17(q))]); link.pop(i, None); m27.pop(i, None)
log['duplicates removed'] = len(freed)

# ------------------------------------------------------------------ 2. managers
for team, (name, nat) in {'Indonesia': ('J. Herdman', 204), 'Cameroon': ('David Pagou', 50), 'Angola': ('P. Beaumelle', 208),
                          'Zimbabwe': ('Mario Marinică', 229), 'Zambia': ('Moses Sichone', 94)}.items():
    t = [t for t in pes.teams if pes.teams[t]['name'] == team]; assert len(t) == 1, team
    m = pes.managers[u32(pes.teams[t[0]]['raw'], 4)]; o = pes.M0 + m['i'] * 88; b = name.encode('utf8')
    n = max(len(b), len(m['name'].encode('utf8'))) + 1; assert n <= 60
    struct.pack_into('<H', d, o + 4, nat); d[o + 9:o + 9 + n] = b.ljust(n, b'\0')
    rep['manager'].append((team, m['name'], name)); log['managers restored'] += 1

# ------------------------------------------------------------------ 3. national squads
GROUP = {'GK': 0, 'CB': 1, 'LB': 1, 'RB': 1, 'DMF': 2, 'CMF': 2, 'LMF': 2, 'RMF': 2, 'AMF': 2, 'LWF': 3, 'RWF': 3, 'SS': 3, 'CF': 3}
for t in pes.teams:
    if pes.isclub(t) or t in NOTNATIONAL: continue
    sq = [i for i in squad_now(t) if i]; top = collections.Counter(P[i]['nation'] for i in sq).most_common(1)
    ft = max(A, key=lambda f: len({i for i, _ in A[f]} & set(sq))); fs = [i for i, _ in A[ft]]
    if len(set(fs) & set(sq)) < 8 or not top or 5 * top[0][1] < 3 * len(sq): continue       # no clear FL squad or no clear nation
    home = top[0][0]
    flnames = {norm(D[i]['name']) for i in fs if i in D}
    come = sorted((i for i in fs if i not in sq and link.get(i) == i and i not in leg and P[i]['nation'] == home
                   and norm(P[i]['name']) == norm(D[i]['name'])), key=lambda i: -before[i])               # no invented names into a squad
    go = sorted((i for i in sq if i not in fs and norm(P[i]['name']) not in flnames), key=lambda i: before[i])
    o = roster_off(t)
    for g in go:
        gp = POS[P[g]['reg_pos']]
        c = [i for i in come if P[i]['reg_pos'] == P[g]['reg_pos']] or [i for i in come if GROUP[POS[P[i]['reg_pos']]] == GROUP[gp] and gp != 'GK']
        if not c: continue
        i = c[0]; come.remove(i); struct.pack_into('<I', d, o + 4 + 4 * squad_now(t).index(g), i)      # same slot, same shirt number
        rep['squad'].append((pes.teams[t]['name'], P[g]['name'], P[i]['name'])); log['national squad places changed'] += 1

# ------------------------------------------------------------------ 4. estimate for older club players without an EA rating
for i, p in P.items():
    if p['age'] <= 23 or i in leg or i not in club or i not in link or i in m27 or i in m26: continue      # an EA rating of last year beats an estimate
    cur = rate.overall(p); est = EST[raw[i]]
    if abs(est - cur) < 4 or I27.loose(p['name'], p['age'], p['height'], cur): continue      # within the error of the estimate, or already an EA rating
    tg = cur + max(-5, min(5, est - cur))
    if rate.retarget(p, tg): put(i); log['older club players moved to the FL 27 estimate'] += 1; rep['est'].append((p['name'], pes.teams[club[i]]['name'], cur, tg))
    else: log['estimate not reachable'] += 1

# ------------------------------------------------------------------ 5. form, 6. nationality
for i, q in link.items():
    if i in leg or P[i]['form'] == D[q]['form']: continue
    P[i]['form'] = D[q]['form']; put(i); log['form value set as in FL 27'] += 1
for name, clubname, nat_of in (('Lucas Piton', 'Vasco', 'Brazil'), ('Igor Coronado', 'Sharjah', 'Brazil'), ('Ilgyu Park', '', 'Korea Republic')):
    hit = [i for i in P if norm(P[i]['name']) == norm(name) and i in link and i not in leg]; assert len(hit) == 1, (name, hit)
    i = hit[0]; t = [t for t in pes.teams if pes.teams[t]['name'] == nat_of]; assert len(t) == 1
    nat = collections.Counter(P[x]['nation'] for x, _ in pes.squad(t[0])).most_common(1)[0][0]
    assert D[link[i]]['nation'] == nat, (name, 'FL 27 disagrees')
    struct.pack_into('<H', d, off(i) + 10, nat); P[i]['nation'] = nat; log['nationality set by hand'] += 1

# ------------------------------------------------------------------ 7. registered positions
EAPOS = {'GK': 'GK', 'CB': 'CB', 'LB': 'LB', 'RB': 'RB', 'CDM': 'DMF', 'CM': 'CMF', 'LM': 'LMF', 'RM': 'RMF', 'CAM': 'AMF', 'LW': 'LWF', 'RW': 'RWF', 'ST': 'CF'}
WIDE = {'LMF': 'LWF', 'RMF': 'RWF'}
# playing styles that work at a position in PES 2017 (from the game's manual, not checked in the game); first = default
STYLE = {'CF': (1, 2, 3, 13), 'SS': (6, 2, 5, 14), 'LWF': (4, 14), 'RWF': (4, 14), 'AMF': (6, 2, 5, 14), 'LMF': (4, 6, 7, 14), 'RMF': (4, 6, 7, 14),
         'CMF': (6, 7, 9), 'DMF': (8, 7, 9, 15), 'CB': (15, 9, 10), 'LB': (11, 12), 'RB': (11, 12), 'GK': (17, 16)}
def move(i, role, target=None, why=''):
    p = P[i]; old = dict(p); cur = rate.overall(p); tg = target or cur
    p['reg_pos'] = POS.index(role); p['pp_' + role] = 2
    if p['play_style'] and p['play_style'] not in STYLE[role]:
        p['play_style'] = (12 if p['def'] > p['atk'] else 11) if role in ('LB', 'RB') else (7 if role == 'CMF' and p['def'] >= p['atk'] else STYLE[role][0])
    if rate.overall(p) != tg and not rate.retarget(p, tg): p.clear(); p.update(old); log['position change not possible'] += 1; return
    put(i); log['registered position changed' + why] += 1
    rep['pos'].append((p['name'], pes.teams[club[i]]['name'], POS[old['reg_pos']], role, cur, tg, old['play_style'], p['play_style']))
NAMED = {'Arda Güler': ('RWF', 85), 'Bernardo Silva': ('CMF', None), 'Denzel Dumfries': ('RB', None)}
named = {by_name(n, club): v for n, v in NAMED.items()}
for i, (role, tg) in named.items(): move(i, role, tg, ' (named)')
for t in pes.teams:
    if not pes.isclub(t): continue
    sq = squad_now(t); g = pes.plans[t]; roles = g['presets'][0]['forms'][0]['pos']
    for k, slot in enumerate(g['xi']):
        i = sq[slot] if slot < 32 else 0
        if not i or i in named or i not in m27: continue
        role = POS[roles[k]]; reg = POS[P[i]['reg_pos']]; ea = EAPOS.get(m27[i]['pos'])
        if role != reg and (ea == role or WIDE.get(ea) == role): move(i, role)

# ------------------------------------------------------------------ 8. Premier League form
F = fldb.W + 'src/fpl/data/2026-2027/'
rows = list(csv.DictReader(open(F + 'playerstats.csv', encoding='utf-8'))); gw = max(int(r['gw']) for r in rows)
fplp = {r['player_id']: r for r in csv.DictReader(open(F + 'players.csv', encoding='utf-8'))}
num = lambda x: float(x) if x not in ('', None) else 0.0
perf = collections.defaultdict(list); bycode = collections.defaultdict(list)
for r in rows:
    if int(r['gw']) == gw and r['id'] in fplp: bycode[fplp[r['id']]['team_code']].append(r)
for code, rs in bycode.items():                              # FPL team -> file club by shared surnames
    sur = {rate.toks(r['second_name'])[-1] for r in rs if rate.toks(r['second_name'])}
    t = max((t for t in pes.teams if pes.isclub(t)), key=lambda t: len(sur & {k for i in squad_now(t) if i for k in rate.toks(P[i]['name'])}))
    sq = [i for i in squad_now(t) if i]
    for r in rs:
        if num(r['minutes']) < 45 * gw: continue             # played at least half of the minutes
        want = [set(rate.toks(r['first_name'] + ' ' + r['second_name'])), set(rate.toks(r['web_name'].replace('.', ' ')))]
        hit = [i for i in sq if any(len(k) > 2 and k in w for w in want for k in rate.toks(P[i]['name'])[-1:])]
        if len(hit) > 1: hit = [i for i in hit if set(rate.toks(P[i]['name'])) <= want[0] or set(rate.toks(P[i]['name'])) & want[1] and len(set(rate.toks(P[i]['name'])) & want[0]) > 1]
        if len(hit) == 1: perf[fplp[r['id']]['position']].append((num(r['total_points']), hit[0]))
        else: log['FPL players not found in the file'] += 1
for posn, v in perf.items():
    v.sort(key=lambda x: (-x[0], x[1])); level = sorted((rate.overall(P[i]) for _, i in v), reverse=True)
    for rank, (pts, i) in enumerate(v[:3 if posn == 'Goalkeeper' else 10]):
        cur = rate.overall(P[i]); tg = min(cur + 3, level[rank])
        if tg > cur and i not in named and rate.retarget(P[i], tg):
            put(i); log['Premier League form rises'] += 1; rep['form'].append((P[i]['name'], pes.teams[club[i]]['name'], posn, rank + 1, int(pts), cur, tg))

# ------------------------------------------------------------------ 9. legends FL 27 does not have
# name, team, template (a legend of the file), position, also rated A, nation (national team name), age, height, weight, foot, rating
NEW = [('Jairzinho', 4971, 'Garrincha', 'RWF', ('RMF', 'SS'), 'Brazil', 25, 173, 72, 0, 90),
       ('Rivellino', 4971, 'Rivaldo', 'AMF', ('LMF', 'CMF'), 'Brazil', 24, 169, 68, 1, 90),
       ('Carlos Alberto', 4971, 'Cafu', 'RB', ('CB',), 'Brazil', 25, 182, 76, 0, 89),
       ('Bobby Moore', 4971, 'Franco Baresi', 'CB', (), 'England', 25, 178, 76, 0, 91),
       ('Emilio Butragueño', 4971, 'Gianfranco Zola', 'SS', ('CF',), 'Spain', 23, 170, 66, 0, 89),
       ('Jean-Pierre Papin', 4971, 'David Trézéguet', 'CF', (), 'France', 27, 176, 72, 0, 89),
       ('Rudi Völler', 4971, 'Jürgen Klinsmann', 'CF', (), 'Germany', 30, 180, 76, 0, 88),
       ('Gianluca Vialli', 4971, 'Hernán Crespo', 'CF', ('SS',), 'Italy', 26, 180, 77, 0, 88),
       ('David Ginola', 1386, 'Robert Pirès', 'LMF', ('LWF',), 'France', 28, 185, 80, 0, 87)]
inroster = {i for t in pes.teams for i in squad_now(t) if i}
real = {key(q['name']) for q in D.values()} | {key(c[k]) for c in C27 for k in ('name', 'short')} | {key(c['name']) for c in rate.fc26()}
spare = sorted((i for i, p in P.items() if i not in inroster and i not in m27 and i not in link and i not in remade and key(p['name']) not in real and before[i] <= 60),
               key=lambda i: (before[i], i))                  # unused free agents nobody knows, weakest first
legname = {norm(P[i]['name']): i for i in leg}
def template(name):
    hit = [i for n, i in legname.items() if n == norm(name) or norm(name) in n]; assert len(hit) == 1, (name, hit); return hit[0]
for name, team, tpl, pos, also, nation, age, h, w, foot, tg in NEW:
    assert key(name) not in {key(p['name']) for p in P.values()}, ('already in the file', name)
    nt = [t for t in pes.teams if pes.teams[t]['name'] == nation]; assert len(nt) == 1
    nat = collections.Counter(P[x]['nation'] for x in squad_now(nt[0]) if x).most_common(1)[0][0]
    i = next((x for x in spare if P[x]['nation'] == nat), spare[0]); spare.remove(i)      # a record of that country where there is one
    src = P[template(tpl)]; p = P[i]; old = p['name']
    for k in src:
        if k not in ('i', 'id', 'u4', 'name', 'shirt', 'app_id', 'raw', 'nation', 'height', 'weight', 'gc1', 'gc2') and not k.startswith('mo_'): p[k] = src[k]
    p.update(age=age, foot=foot, reg_pos=POS.index(pos))
    for k in (pos,) + also: p['pp_' + k] = 2
    assert rate.retarget(p, tg), (name, tg)
    identity(i, name, nat, h, w); put(i)
    sq = squad_now(team); k = sq.index(0); o = roster_off(team); usednum = {d[o + 132 + x] for x in range(32) if sq[x]}
    assert all(x == 0 for x in sq[k:]) and pes.plans[team]['xi'] + pes.plans[team]['bench'] == list(range(32)), 'roster or line-up not in order'
    struct.pack_into('<I', d, o + 4 + 4 * k, i); d[o + 132 + k] = next(x for x in range(1, 100) if x not in usednum)
    leg.add(i); rep['legend'].append((name, pes.teams[team]['name'], pos, tg, tpl, old)); log['legends built by hand'] += 1

open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players; now = {i: rate.overall(p) for i, p in N.items()}
assert len(new.d) == len(pes.d) and len(N) == len(P) and not new.dups and list(N) == list(P), 'file size, player count or ids changed'
lo, hi = pes.P0, pes.P0 + pes.np * pes.PSZ
assert new.d[:lo] == pes.d[:lo], 'header changed'
oldleg = {i for t in LEGENDS for i, _ in pes.squad(t)}
assert all(N[i]['raw'] == P[i]['raw'] if False else new.d[pes.P0 + N[i]['i'] * pes.PSZ:][:pes.PSZ] == pes.d[pes.P0 + N[i]['i'] * pes.PSZ:][:pes.PSZ] for i in oldleg), 'an existing legend changed'
for t in new.teams:
    sq = [i for i, _ in new.squad(t)]; nums = [x for _, x in new.squad(t)]
    assert len(sq) == len(set(sq)) and all(i in N for i in sq), ('roster', new.teams[t]['name'])
    assert len(sq) == len([i for i, _ in pes.squad(t)]) + sum(1 for x in NEW if x[1] == t) - dropped.get(t, 0), ('squad size', new.teams[t]['name'])
    assert t not in [x[1] for x in NEW] or len(nums) == len(set(nums)), ('shirt numbers', new.teams[t]['name'])
    assert new.plans[t]['raw'] == pes.plans[t]['raw'] and new.teams[t]['raw'] == pes.teams[t]['raw'], 'a line-up or team record changed'
    assert len(nums) == len(set(nums)) or len([x for _, x in pes.squad(t)]) != len({x for _, x in pes.squad(t)}), ('shirt numbers', new.teams[t]['name'])
young = [i for i in P if N[i]['age'] <= 23 and i not in leg and i not in remade]
low = [(N[i]['name'], before[i], now[i]) for i in young if now[i] < before[i]]
assert not low, ('a player aged 23 or under was lowered', low[:5])
for n, (role, tg) in NAMED.items():
    p = N[by_name(n, club)]; assert POS[p['reg_pos']] == role and (tg is None or rate.overall(p) == tg), n
moved = {x[0]: x for x in rep['pos']}; rose = {x[0] for x in rep['form']}
for name, team, a, b, cur, tg, s0, s1 in rep['pos']:
    i = [i for i in club if N[i]['name'] == name and new.teams[club[i]]['name'] == team][0]
    assert POS[N[i]['reg_pos']] == b and N[i]['pp_' + b] == 2 and (now[i] == tg or name in rose), ('position', name)
seen = collections.defaultdict(list)
for i, p in N.items():
    if i not in leg: seen[(norm(p['name']), p['nation'], p['age'])].append(i)
twice = [[N[i]['name'] for i in v] for v in seen.values() if len(v) > 1 and max(N[i]['height'] for i in v) - min(N[i]['height'] for i in v) <= 3
         and len({N[i]['reg_pos'] for i in v}) == 1 and N[v[0]]['name'] != 'FACE EDIT' and len({link.get(i) for i in v} - {None}) < len(v)]   # two FL 27 people are two people
assert not twice, ('still stored twice', twice)
assert all(N[i]['form'] == D[q]['form'] for i, q in link.items() if i not in leg), 'form differs from FL 27'
ea = [i for i, c in m27.items() if now[i] != c['ovr'] and N[i]['name'] not in rose and N[i]['name'] != 'Arda Güler' and before[i] == c['ovr']]
assert not ea, ('an EA rating was lost', [N[i]['name'] for i in ea[:5]])

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-58s %d' % (k, v))
for k in ('replaced', 'manager', 'squad', 'form', 'legend'):
    print('--', k)
    for x in rep[k][:60]: print('  ', x)
print('-- pos', len(rep['pos'])); [print('  ', x) for x in sorted(rep['pos'], key=lambda x: -x[4])[:40]]
print('-- est', collections.Counter(b - a for _, _, a, b in rep['est']).most_common()); [print('  ', x) for x in sorted(rep['est'], key=lambda x: -x[2])[:25]]
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
