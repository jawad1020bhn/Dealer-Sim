"""Task 15: squads and line-ups, on the output of task14.py. No rating of an existing player changes.
  1. transfers:  a free agent joins the club where a newer source has him:
                   a) Football Life 27 lists him in the squad of that club,
                   b) the Premier League fantasy data says "has joined <club>" and the club is in the file,
                   c) EA FC 27 lists him at a club whose squad FL 27 does not have.
                 A full squad (32) gives up a reserve: first one no source lists at the club, then the weakest member.
  2. missing:    real players the file lacks, written into unused records: FL 27 squad members of clubs in the file,
                 Premier League regulars only EA knows, and the best-rated players whose club is not in the file (free agents)
  3. line-ups:   Premier League clubs start the eleven with the most minutes (minutes per fit gameweek; a change needs
                 180 minutes more over the season so far and must put nobody new out of position)
  4. roles:      top-five clubs: a starter at a role that is neither his registered position nor the one EA lists is
                 moved inside the eleven; where that is not enough a reserve who fits comes in for another starter
                 (at most 3 points weaker; never for the misplaced player himself or the captain)
  5. set pieces: Premier League penalty, free-kick and corner takers in the fantasy data order
  6. numbers:    shirt numbers of every squad as in FL 27
Usage: python3 task15.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys, collections, struct, csv, unicodedata, difflib, re
from lib import P17, POS, pack17, norm, u32
import rate, fldb

# ------------------------------------------------------------------ line-up solver (with its own small test)
def feasible(costs, lim):
    """costs[k][j] = cost of player j at role k. True when every role can get its own player at a cost <= lim."""
    n = len(costs); owner = [-1] * n
    def tryrole(k, seen):
        for j in range(n):
            if costs[k][j] <= lim and j not in seen:
                seen.add(j)
                if owner[j] < 0 or tryrole(owner[j], seen): owner[j] = k; return True
        return False
    return all(tryrole(k, set()) for k in range(n))
def assign(costs):
    """Cheapest way to give every role one player (Hungarian method): list role -> player index.
    Ties keep a player at his own index."""
    n = len(costs); a = [[costs[k][j] * 100 + (j != k) for j in range(n)] for k in range(n)]; INF = 10 ** 9
    u = [0] * (n + 1); v = [0] * (n + 1); p = [0] * (n + 1); way = [0] * (n + 1)
    for i in range(1, n + 1):
        p[0] = i; j0 = 0; minv = [INF] * (n + 1); used = [False] * (n + 1)
        while True:
            used[j0] = True; i0 = p[j0]; delta = INF; j1 = 0
            for j in range(1, n + 1):
                if used[j]: continue
                cur = a[i0 - 1][j - 1] - u[i0] - v[j]
                if cur < minv[j]: minv[j] = cur; way[j] = j0
                if minv[j] < delta: delta = minv[j]; j1 = j
            for j in range(n + 1):
                if used[j]: u[p[j]] += delta; v[j] -= delta
                else: minv[j] -= delta
            j0 = j1
            if p[j0] == 0: break
        while j0: j1 = way[j0]; p[j0] = p[j1]; j0 = j1
    out = [0] * n
    for j in range(1, n + 1): out[p[j] - 1] = j - 1
    return out
assert assign([[0, 9, 9], [9, 0, 9], [9, 9, 0]]) == [0, 1, 2] and assign([[9, 0, 9], [0, 9, 9], [9, 9, 0]]) == [1, 0, 2]
assert assign([[1, 1], [1, 1]]) == [0, 1] and assign([[3, 0, 1], [0, 3, 0], [1, 1, 9]]) == [1, 2, 0]
assert feasible([[0, 9], [9, 0]], 1) and not feasible([[0, 9], [0, 9]], 1) and feasible([[0, 0, 9], [0, 9, 9], [9, 0, 0]], 0)

if __name__ != '__main__': sys.exit()
SRC, OUT = sys.argv[1:3]
LEGENDS = (1458, 1459, 1460, 1462, 1463, 2703, 2704, 4971, 1386, 140, 2696, 2469)
pes = P17(SRC); P = pes.players; D, A, T = fldb.load()
d = bytearray(pes.d); log = collections.Counter(); rep = collections.defaultdict(list)
leg = {i for t in LEGENDS for i, _ in pes.squad(t)}
CLUBS = [t for t in pes.teams if pes.isclub(t)]
R = {t: [list(x) for x in pes.rosters[t]] for t in CLUBS}              # per slot [player id, shirt number]; slots 0-10 start
club = {x[0]: t for t in CLUBS for x in R[t] if x[0]}
inroster0 = {i for t in pes.teams for i, _ in pes.squad(t)}
before = {i: rate.overall(p) for i, p in P.items()}
ovr = lambda i: rate.overall(P[i])
tname = lambda t: pes.teams[t]['name']
assert all(pes.plans[t]['xi'] + pes.plans[t]['bench'] == list(range(32)) for t in CLUBS), 'a line-up is not in roster order'

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

# ------------------------------------------------------------------ links to FL 27 and to EA FC 27 (as in task14.py)
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
rev = {q: i for i, q in link.items()}
def names(i):
    n = [P[i]['name']]
    if i in link and norm(D[link[i]]['name']) != norm(n[0]): n.append(D[link[i]]['name'])
    return n
C27 = rate.fc27full(); I27 = rate.Index(C27)
m27 = rate.match_cards(C27, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '',
                                  nation=p['nation']) for i, p in P.items() if i not in leg])
cal = collections.defaultdict(list)
for i, q in link.items():
    if i in m27 and P[i]['age'] > 23: cal[rate.overall(fldb.to17(D[q]))].append(m27[i]['ovr'])
EST = rate.est_table(cal, 0)       # FL 27 overall -> expected EA rating

# ------------------------------------------------------------------ which FL 27 team, EA club and EA league a file club is
def best_fl(t, pool):
    sq = {link.get(i) for i, _ in pes.squad(t)} - {None}
    f = max(pool, key=lambda f: (len({i for i, _ in A[f]} & sq), -f)); return f, len({i for i, _ in A[f]} & sq)
natfl = set()                                                          # FL teams that are national teams of the file
for t in pes.teams:
    if not pes.isclub(t) and t not in LEGENDS:
        f, n = best_fl(t, A)
        if n >= 8: natfl.add(f)
flclubs = [f for f in A if f not in natfl and not 900 <= f <= 910]
fmap = {}
for t in CLUBS:
    f, n = best_fl(t, flclubs)
    if n >= 6: fmap[t] = f
assert len(set(fmap.values())) == len(fmap), 'two clubs share an FL 27 team'
flsq = {t: {q for q, _ in A[f]} for t, f in fmap.items()}
cnt = collections.defaultdict(collections.Counter); lgc = collections.defaultdict(collections.Counter)
for i, c in m27.items():
    if i in club: cnt[c['club']][club[i]] += 1; lgc[club[i]][c['league']] += 1
eamap = {k: v.most_common(1)[0][0] for k, v in cnt.items() if v.most_common(1)[0][1] >= 3}
TOP5 = {t for t, v in lgc.items() if v.most_common(1)[0][1] >= 8 and v.most_common(1)[0][0] in
        ('Premier League', 'LALIGA EA SPORTS', 'Serie A Enilive', 'Bundesliga', "Ligue 1 McDonald's")}
def member(i, t):
    """A source lists the player at this club."""
    return link.get(i) in flsq.get(t, ()) or (i in m27 and eamap.get(m27[i]['club']) == t)

# ------------------------------------------------------------------ Premier League fantasy data (latest gameweek)
F = fldb.W + 'src/fpl/data/2026-2027/'
rows = list(csv.DictReader(open(F + 'playerstats.csv', encoding='utf-8'))); gw = max(int(r['gw']) for r in rows)
fplp = {r['player_id']: r for r in csv.DictReader(open(F + 'players.csv', encoding='utf-8'))}
num = lambda x: float(x) if x not in ('', None) else 0.0
bycode = collections.defaultdict(list)
for r in rows:
    if int(r['gw']) == gw and r['id'] in fplp: bycode[fplp[r['id']]['team_code']].append(r)
GONE = re.compile(r'has (?:joined|returned to)\s+(.+?)(?:\s+permanently|\s+on loan|\s+for the|\s+until|\.|$)', re.I)
left = lambda r: r['status'] == 'u' and bool(re.search(r'joined|returned to|departed', r['news'], re.I))
want = lambda r: set(rate.toks(r['first_name'] + ' ' + r['second_name'])) | set(rate.toks(r['web_name'].replace('.', ' ')))
PL = {}                                                               # file club -> its fantasy rows
for code, rs in bycode.items():
    sur = {rate.toks(r['second_name'])[-1] for r in rs if rate.toks(r['second_name']) and not left(r)}
    t = max(CLUBS, key=lambda t: len(sur & {k for x in R[t] if x[0] for k in rate.toks(P[x[0]]['name'])}))
    assert t not in PL; PL[t] = rs
assert len(PL) == 20 and PL.keys() <= TOP5, 'Premier League clubs not found'
free_by_tok = collections.defaultdict(set)
for i, p in P.items():
    if i not in club and i not in leg:
        for k in rate.toks(p['name']): free_by_tok[k].add(i)
def free_agent(r):
    """The free agent of the file a fantasy row means: all words of his name are in the row, two of them longer than two letters."""
    w = want(r); hit = [i for i in {i for k in w for i in free_by_tok.get(k, ())}
                        if len([k for k in rate.toks(P[i]['name']) if len(k) > 2]) >= 2 and set(rate.toks(P[i]['name'])) <= w]
    return hit[0] if len(hit) == 1 else None
gone_from = {}; news_move = {}
clubtoks = {t: set(rate.toks(tname(t))) for t in CLUBS}
ALIAS = {'wolves': 'Wolverhampton Wanderers FC', 'spurs': 'Tottenham Hotspur FC'}
GENERIC = {'fc', 'cf', 'afc', 'sc', 'ac', 'rc', 'cd', 'ud', 'sd', 'as', 'ss', 'sv', 'fk', 'bk', 'if', 'de', 'club', 'united', 'calcio'}   # 'York City' is not 'New York City FC'
for t, rs in PL.items():
    for r in rs:
        if not left(r): continue
        i = free_agent(r)
        if i is None: continue
        gone_from[i] = t; m = GONE.search(r['news'])
        if not m: continue
        w = set(rate.toks(m.group(1))); to = [x for x in CLUBS if w and (w <= clubtoks[x] and clubtoks[x] - w <= GENERIC or ALIAS.get(norm(m.group(1))) == tname(x))]
        if len(to) == 1 and to[0] != t: news_move[i] = (to[0], r['news'])
        else: log['fantasy move to a club the file lacks (stays a free agent)'] += 1

def in_fantasy(i, t): return any(set(rate.toks(P[i]['name'])) <= want(r) and not left(r) for r in PL[t])

# ------------------------------------------------------------------ 1. transfers
joined = set()
def place(t, rating):
    """Slot for a newcomer of that rating: an empty one, else a reserve no source lists here, else the weakest listed reserve."""
    r = R[t]; k = next((k for k in range(32) if not r[k][0]), None)
    if k is not None: return k
    res = [k for k in range(11, 32) if r[k][0] not in joined and not (t in PL and in_fantasy(r[k][0], t))]
    a = sorted((k for k in res if not member(r[k][0], t) and ovr(r[k][0]) <= rating), key=lambda k: (ovr(r[k][0]), r[k][0]))
    b = sorted((k for k in res if member(r[k][0], t) and ovr(r[k][0]) <= rating - 3), key=lambda k: (ovr(r[k][0]), r[k][0]))
    return (a or b or [None])[0]
def join(t, i, why, k=None):
    k = place(t, ovr(i)) if k is None else k
    if k is None: log['no room: ' + why] += 1; return False
    r = R[t]; out = r[k][0]; usednum = {x[1] for x in r if x[0] and x[0] != out}
    n = dict(A[fmap[t]]).get(link.get(i), 0) if t in fmap else 0
    if not 1 <= n <= 99 or n in usednum: n = r[k][1] if out and r[k][1] not in usednum else next(x for x in range(1, 100) if x not in usednum)
    r[k] = [i, n]; club[i] = t; joined.add(i)
    if out: del club[out]; log['released to make room'] += 1
    rep['join'].append((P[i]['name'], ovr(i), tname(t), why, P[out]['name'] if out else '', ovr(out) if out else 0)); log['joined a club: ' + why] += 1
    return True
todo = []
for t, f in fmap.items():
    for q, _ in A[f]:
        i = rev.get(q)
        if i is None or i in club or i in leg: continue
        if t in PL and not in_fantasy(i, t):
            log['FL 27 squad member not in the fantasy list of that club (stays a free agent)'] += 1; continue
        todo.append((-ovr(i), i, t, 'in the FL 27 squad'))
for i, (t, news) in news_move.items(): todo.append((-ovr(i), i, t, 'fantasy data: joined'))
flany = {q for f in flclubs for q, _ in A[f]}
for i, c in m27.items():
    t = eamap.get(c['club'])
    if i not in club and i not in leg and t is not None and t not in fmap and t not in PL and link.get(i) not in flany and i not in gone_from:
        todo.append((-ovr(i), i, t, 'EA FC 27, club unknown to FL 27'))
PRIO = {'fantasy data: joined': 0, 'in the FL 27 squad': 1, 'EA FC 27, club unknown to FL 27': 2}
for _, i, t, why in sorted(todo, key=lambda x: (PRIO[x[3]], x[0], x[1])):
    if i not in club: join(t, i, why)

# ------------------------------------------------------------------ 2. missing players
key = lambda s: frozenset(rate.toks(s))
real = {key(q['name']) for q in D.values()} | {key(c[k]) for c in C27 for k in ('name', 'short')} | {key(c['name']) for c in rate.fc26()}
spare = sorted((i for i, p in P.items() if i not in inroster0 and i not in club and i not in m27 and i not in link and i not in leg
                and key(p['name']) not in real and before[i] <= 60), key=lambda i: (before[i], i))      # unused records nobody knows
bytok = collections.defaultdict(list); bynat = collections.defaultdict(list)
def index(i):
    for k in rate.toks(P[i]['name']):
        if len(k) > 3: bytok[k].append(i)
    bynat[P[i]['nation']].append(i)
for i in P: index(i)
GROUP = {'GK': 0, 'CB': 1, 'LB': 1, 'RB': 1, 'DMF': 2, 'CMF': 2, 'LMF': 2, 'RMF': 2, 'AMF': 2, 'LWF': 3, 'RWF': 3, 'SS': 3, 'CF': 3}
def twin(name, age, height, nation, t=None, pos=None):
    """A file player who may be the same person: a shared name word at about that age with the same nation, height or
    club; a similar name with the same age, height and nation; an unlinked squad member of the same age, height and line."""
    here = {x[0] for x in R[t]} if t else ()
    for k in rate.toks(name):
        for i in bytok.get(k, []) if len(k) > 3 else []:
            p = P[i]
            if i in here or (abs(p['age'] - age) <= 2 and (p['nation'] == nation or abs(p['height'] - height) <= 3)): return i
    n = norm(name)
    for i in bynat.get(nation, []):
        p = P[i]
        if abs(p['age'] - age) <= 1 and abs(p['height'] - height) <= 2 and difflib.SequenceMatcher(None, norm(p['name']), n).ratio() >= 0.75: return i
    for i in here:
        p = P.get(i)
        if p and i not in link and abs(p['age'] - age) <= 1 and abs(p['height'] - height) <= 2 and GROUP[POS[p['reg_pos']]] == GROUP[pos]: return i
def take(nation):
    i = next((x for x in spare if P[x]['nation'] == nation), spare[0]); spare.remove(i); return i
built = set()
def become(i, q, target):
    """Record i becomes FL 27 player q; id, motions and appearance of the record stay."""
    old = P[i]['name']; P[i].update(fldb.to17(q)); identity(i, q['name'], q['nation'], q['height'], q['weight'])
    if rate.overall(P[i]) != target: assert rate.retarget(P[i], target), (q['name'], target)
    put(i); built.add(i); index(i); link[i] = q['id']; rev[q['id']] = i; return old

EAPOS = {'GK': 'GK', 'CB': 'CB', 'LB': 'LB', 'RB': 'RB', 'CDM': 'DMF', 'CM': 'CMF', 'LM': 'LMF', 'RM': 'RMF', 'CAM': 'AMF', 'LW': 'LWF', 'RW': 'RWF', 'ST': 'CF'}
natof = collections.defaultdict(collections.Counter)
for i, c in m27.items(): natof[c['nation']][P[i]['nation']] += 1
def alltoks(i): return {k for n in names(i) for k in rate.toks(n)} | ({k for n in (m27[i]['name'], m27[i]['short']) for k in rate.toks(n)} if i in m27 else set())

# a) Premier League players with minutes whom only EA knows: abilities of the most similar file player, EA rating
for t, rs in PL.items():
    sqt = {k for x in R[t] if x[0] for k in alltoks(x[0])}
    for r in rs:
        w = want(r)
        if left(r) or num(r['minutes']) < 45 or w & sqt: continue
        cs = [c for c in C27 if eamap.get(c['club']) == t and c['t'] and len(c['t'][-1]) > 4 and c['t'][-1] in w]        # the surname, at this club
        if len(cs) != 1: log['Premier League player with minutes not found anywhere'] += 1; rep['pl_missing'].append((r['web_name'], tname(t), int(num(r['minutes'])))); continue
        c = cs[0]; pos = EAPOS[c['pos']]; nat = natof[c['nation']].most_common(1)[0][0]
        tw = twin(c['name'], c['age'], c['height'] or 180, nat, t, pos)
        if tw is not None: rep['pl_twin'].append((r['web_name'], tname(t), P[tw]['name'])); continue
        k = place(t, c['ovr'])
        if k is None or not spare: log['Premier League player skipped: no room'] += 1; continue
        tpl = min((j for j in m27 if j not in leg and j not in built and POS[P[j]['reg_pos']] == pos and m27[j]['pos'] == c['pos'] and abs(ovr(j) - c['ovr']) <= 1),
                  key=lambda j: (abs(P[j]['age'] - c['age']), abs(P[j]['height'] - (c['height'] or P[j]['height'])), abs(ovr(j) - c['ovr']), j))
        i = take(nat); p = P[i]; old = p['name']; src = P[tpl]
        for f in src:
            if f not in ('i', 'id', 'u4', 'name', 'shirt', 'app_id', 'raw', 'nation', 'height', 'weight', 'gc1', 'gc2') and not f.startswith('mo_'): p[f] = src[f]
        p['age'] = c['age']; assert rate.retarget(p, c['ovr']), c['name']
        identity(i, c['name'], nat, c['height'] or src['height'], src['weight']); put(i); built.add(i); index(i); m27[i] = c
        join(t, i, 'new player', k); rep['built'].append((c['name'], pos, c['ovr'], 'EA, abilities like ' + src['name'], tname(t), old)); log['missing players built: Premier League, EA only'] += 1

# b) FL 27 squad members of clubs in the file, and c) FL 27 players EA rates 75 or more whose club is not in the file
#    (they become free agents). Best first, as long as unused records last.
cand = []; infile = {q for s in flsq.values() for q in s}; elsewhere = {q for f in flclubs for q, _ in A[f]} - infile
for t, f in fmap.items():
    for q, _ in A[f]:
        if q in rev or q not in D: continue
        x = D[q]
        if twin(x['name'], x['age'], x['height'], x['nation'], t, POS[x['reg_pos']]) is not None: log['FL 27 squad member skipped: maybe in the file under another spelling'] += 1; continue
        c = I27.find(x['name'], x['age'], x['height'], tname(t))
        cand.append((-(c['ovr'] if c else EST[rate.overall(fldb.to17(x))]), q, t, c))
for q in sorted(elsewhere):
    x = D.get(q)
    if x is None or q in rev or x['age'] > 37: continue
    c = I27.find(x['name'], x['age'], x['height'])
    if c is None or c['ovr'] < 75 or eamap.get(c['club']) is not None: continue
    if twin(x['name'], x['age'], x['height'], x['nation']) is not None: log['notable player skipped: maybe in the file under another spelling'] += 1; continue
    cand.append((-c['ovr'], q, None, c))
for tg, q, t, c in sorted(cand, key=lambda x: x[:2]):
    x = D[q]; what = 'FL 27 squad member' if t else 'notable, club not in the file'
    if not spare: log[what + ' skipped: no unused record left'] += 1; continue
    k = place(t, -tg) if t else None
    if t and k is None: log['FL 27 squad member skipped: no room in the squad'] += 1; continue
    if twin(x['name'], x['age'], x['height'], x['nation'], t, POS[x['reg_pos']]) is not None: continue        # built a moment ago for another club
    i = take(x['nation']); old = become(i, x, -tg)
    if c: m27[i] = c
    if t: join(t, i, 'new player', k)
    rep['built'].append((x['name'], POS[x['reg_pos']], -tg, 'EA' if c else 'estimate', tname(t) if t else 'free agent (' + c['club'] + ')', old))
    log['missing players built: ' + what] += 1

# ------------------------------------------------------------------ line-up model: takers and captain follow the player
TK = {t: dict(takers=[R[t][k][0] for k in pes.plans[t]['takers']], captain=R[t][pes.plans[t]['captain']][0]) for t in CLUBS
      if all(k < 11 for k in pes.plans[t]['takers'] + [pes.plans[t]['captain']])}
roles = {t: [POS[x] for x in pes.plans[t]['presets'][0]['forms'][0]['pos']] for t in CLUBS}
touched = set()
ALSO = {'LWF': ('LW', 'LM'), 'RWF': ('RW', 'RM'), 'LMF': ('LM', 'LW'), 'RMF': ('RM', 'RW'), 'SS': ('ST', 'CAM'), 'CMF': ('CM', 'CDM', 'CAM'), 'DMF': ('CDM', 'CM')}
def cost(i, r):
    """0 his registered position, 1 the position EA lists (or a neighbour of it he is rated A for), 2 rated A only,
    6 rated B, 20 not rated, 50 goalkeeper against outfield."""
    p = P[i]; reg = POS[p['reg_pos']]; a = p['pp_' + r]
    if (reg == 'GK') != (r == 'GK'): return 50
    if reg == r: return 0
    ea = m27[i]['pos'] if i in m27 else None
    if EAPOS.get(ea) == r or (a == 2 and ea in ALSO.get(r, ())): return 1
    return 2 if a == 2 else 6 if a == 1 else 20
def table(t, xi): return [[cost(i, r) for i in xi] for r in roles[t]]
def misfits(t, xi): return [i for i, r in zip(xi, roles[t]) if cost(i, r) >= (2 if i in m27 else 6)]     # EA lists another position, or not rated A
def arranged(t, xi): return [xi[j] for j in assign(table(t, xi))]
def settle(t, xi):
    """The eleven in its best order, unless that order puts more starters out of position than the given one."""
    c = arranged(t, xi); return c if len(misfits(t, c)) <= len(misfits(t, xi)) else xi
def lineup(t, xi):
    """Write a new eleven (player per role) into the roster: players leaving it take the slots of those coming in."""
    r = R[t]; cur = [x[0] for x in r[:11]]; nums = {x[0]: x[1] for x in r}; was = sorted(x[0] for x in r)
    if xi == cur: return
    out = [i for i in cur if i not in xi]
    for k in range(11, 32):
        if r[k][0] in xi: j = out.pop(0); r[k] = [j, nums[j]]
    for k, i in enumerate(xi): r[k] = [i, nums[i]]
    assert not out and sorted(x[0] for x in r) == was; touched.add(t)

# ------------------------------------------------------------------ 3. Premier League line-ups from minutes
def fpl_match(t):
    """Fantasy row -> squad player, best name agreement first, one row per player."""
    sq = [x[0] for x in R[t] if x[0]]; tk = {i: alltoks(i) for i in sq}; sc = []
    for r in PL[t]:
        if left(r): continue
        w = want(r); web = set(rate.toks(r['web_name'].replace('.', ' ')))
        for i in sq:
            hit = {k for k in tk[i] & w if len(k) > 1}
            if hit: sc.append((2 * len(hit) + 2 * (rate.toks(P[i]['name'])[-1] in w) + 3 * bool(web & tk[i]) + (set(rate.toks(P[i]['name'])) <= w), r['id'], i))
    sc.sort(key=lambda x: (-x[0], x[1], x[2])); m = {}; usedp = set(); byrow = collections.defaultdict(list)
    for s, rid, i in sc: byrow[rid].append((s, i))
    for s, rid, i in sc:
        if rid in m or i in usedp: continue
        if [x for x in byrow[rid] if x[0] == s and x[1] != i and x[1] not in usedp]: continue        # two players fit equally: leave it
        m[rid] = i; usedp.add(i)
    for r in PL[t]:                                                   # a short name against a nickname (Sávio / Savinho)
        if left(r) or r['id'] in m or num(r['minutes']) == 0: continue
        web = norm(r['web_name']); hit = [i for i in sq if i not in usedp and any(len(k) >= 4 and k[:4] == web[:4] for k in tk[i])]
        if len(web) >= 4 and len(hit) == 1: m[r['id']] = hit[0]; usedp.add(hit[0])
    return m
FP = {}                                                               # player id -> fantasy row
for t in PL:
    m = fpl_match(t); byid = {r['id']: r for r in PL[t]}
    for rid, i in m.items(): FP[i] = byid[rid]
    for r in PL[t]:
        if not left(r) and r['id'] not in m and num(r['minutes']) >= 90: rep['pl_unmatched'].append((r['web_name'], tname(t), int(num(r['minutes']))))
fit = collections.Counter()                                          # fantasy id -> gameweeks listed as fit or doubtful
for r in rows:
    if r['status'] in ('a', 'd'): fit[r['id']] += 1
hold = {i for i in FP if fit[FP[i]['id']] < 3}                        # injured nearly all season: minutes say nothing, he keeps his place
def mins(i):
    """Minutes scaled to a full season of fitness, so an injury spell does not cost a place."""
    return min(90.0 * gw, num(FP[i]['minutes']) * gw / max(fit[FP[i]['id']], 3)) if i in FP else 0.0
for t in sorted(PL):
    xi = [x[0] for x in R[t][:11]]; start = list(xi); rest = [x[0] for x in R[t][11:] if x[0]]
    for i in xi:
        if i not in FP: rep['pl_nodata'].append((P[i]['name'], tname(t)))
    while True:                                                      # most minutes gained first; nobody new out of position
        base = set(misfits(t, settle(t, xi)))
        for _, a, b in sorted((mins(b) - mins(a), a, b) for a in rest for b in xi if mins(a) - mins(b) >= 180 and not {a, b} & hold):
            new = settle(t, [a if x == b else x for x in xi])
            if set(misfits(t, new)) <= base: xi = new; rest = [b if x == a else x for x in rest]; break
        else: break
    if xi != start:
        for a in xi:
            if a not in start: rep['xi'].append((tname(t), P[a]['name'], int(mins(a)), roles[t][xi.index(a)])); log['Premier League starters changed'] += 1
        rep['xi_out'] += [(tname(t), P[b]['name'], int(mins(b))) for b in start if b not in xi]
        lineup(t, xi)

# ------------------------------------------------------------------ 4. starters out of position (top-five clubs)
for t in sorted(TOP5):
    xi = [x[0] for x in R[t][:11]]; bad = misfits(t, xi)
    if not bad: continue
    log['top-five starters out of position before'] += len(bad); start = list(xi)
    new = arranged(t, xi)
    if len(misfits(t, new)) < len(bad): xi = new
    for _ in range(2):                                               # a reserve who fits, for the smallest loss of rating (at most twice)
        n0 = len(misfits(t, xi))
        if not n0: break
        rest = [x[0] for x in R[t][11:] if x[0] and x[0] not in start]; opt = []
        for b in xi:
            if b in misfits(t, xi) or b == TK.get(t, {}).get('captain'): continue      # never the misplaced player himself, never the captain
            for a in rest:
                if ovr(b) - ovr(a) > 3 or (t in PL and (mins(a) < mins(b) - 180 or {a, b} & hold)): continue
                c = settle(t, [a if x == b else x for x in xi]); n1 = len(misfits(t, c))
                if n1 < n0 and set(misfits(t, c)) <= set(misfits(t, xi)): opt.append((n1, ovr(b) - ovr(a), -ovr(a), a, b, c))
        if not opt: break
        _, _, _, a, b, xi = min(opt, key=lambda x: x[:5])
        rep['role_in'].append((tname(t), P[a]['name'], ovr(a), 'for', P[b]['name'], ovr(b))); log['reserve brought in for a role'] += 1
    left_bad = misfits(t, xi); log['top-five starters out of position after'] += len(left_bad)
    for i in bad:
        if i in xi and i not in left_bad: rep['role'].append((tname(t), P[i]['name'], roles[t][start.index(i)], roles[t][xi.index(i)]))
    for i in left_bad: rep['role_left'].append((tname(t), P[i]['name'], POS[P[i]['reg_pos']], m27[i]['pos'] if i in m27 else '', roles[t][xi.index(i)]))
    lineup(t, xi)

# ------------------------------------------------------------------ 5. Premier League set pieces
for t in sorted(PL):
    if t not in TK: continue
    xi = [x[0] for x in R[t][:11]]; tk = TK[t]; old = list(tk['takers'])
    def order(col): return [i for _, i in sorted((num(FP[i][col]), i) for i in xi if i in FP and num(FP[i][col]) > 0)]
    pk, fk, ck = order('penalties_order'), order('direct_freekicks_order'), order('corners_and_indirect_freekicks_order')
    if fk: tk['takers'][0] = tk['takers'][1] = fk[0]                 # long and short free kick
    if len(fk) > 1: tk['takers'][2] = fk[1]                           # second free-kick taker
    if ck:
        l = r = ck[0]
        if len(ck) > 1 and P[ck[0]]['foot'] != P[ck[1]]['foot']:     # two feet: both corners swing in (right foot from the left)
            l, r = (ck[0], ck[1]) if P[ck[0]]['foot'] == 0 else (ck[1], ck[0])
        tk['takers'][3], tk['takers'][4] = l, r
    if pk: tk['takers'][5] = pk[0]
    if tk['takers'] != old:
        touched.add(t); log['Premier League set-piece roles changed'] += sum(a != b for a, b in zip(old, tk['takers']))
        rep['takers'].append((tname(t),) + tuple(P[i]['name'] if i in P else '?' for i in (tk['takers'][0], tk['takers'][2], tk['takers'][3], tk['takers'][4], tk['takers'][5])))

# ------------------------------------------------------------------ 6. shirt numbers as in FL 27
for t, f in fmap.items():
    r = R[t]; fn = dict(A[f]); wantn = {}
    for x in r:
        n = fn.get(link.get(x[0]), 0) if x[0] else 0
        if 1 <= n <= 99 and n not in wantn.values(): wantn[x[0]] = n
    if all(x[1] == wantn.get(x[0], x[1]) for x in r) and len({x[1] for x in r if x[0]}) == sum(1 for x in r if x[0]): continue
    taken = set(wantn.values()); keep = {}
    for x in r:                                                       # everybody else keeps his number unless an FL 27 number needs it
        if x[0] and x[0] not in wantn and 1 <= x[1] <= 99 and x[1] not in taken: keep[x[0]] = x[1]; taken.add(x[1])
    for x in r:
        if not x[0]: continue
        n = wantn.get(x[0]) or keep.get(x[0])
        if n is None: n = next(k for k in range(2, 100) if k not in taken); taken.add(n)
        if n != x[1]: rep['number'].append((tname(t), P[x[0]]['name'], x[1], n)); log['shirt numbers changed'] += x[0] not in joined; x[1] = n

# ------------------------------------------------------------------ write rosters, takers and captains
plan_off = {u32(d, pes.G0 + k * pes.GSZ): pes.G0 + k * pes.GSZ for k in range(pes.nt)}
for t in CLUBS:
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    for k, (pid, n) in enumerate(R[t]): struct.pack_into('<I', d, o + 4 + 4 * k, pid); d[o + 132 + k] = n if pid else 0
    if t not in touched or t not in TK: continue
    xi = [x[0] for x in R[t][:11]]; out = [i for i in xi if POS[P[i]['reg_pos']] != 'GK']; tk = TK[t]
    kicker = max(out, key=lambda i: (P[i]['place_kick'], i))
    tk['takers'] = [i if i in xi else kicker for i in tk['takers']]
    if tk['captain'] not in xi:
        tk['captain'] = max(xi, key=lambda i: (P[i]['sk25'], ovr(i), P[i]['age'], i)); log['captains replaced (the old one no longer starts)'] += 1
        rep['captain'].append((tname(t), P[tk['captain']]['name']))
    q = plan_off[t] + 4 + 480
    for k, i in enumerate(tk['takers']): d[q + 32 + k] = xi.index(i)
    d[q + 41] = xi.index(tk['captain'])
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and not new.dups, 'file size, player count or ids changed'
assert new.d[:pes.P0] == pes.d[:pes.P0], 'header changed'
same = lambda i: new.d[off(i):off(i) + pes.PSZ] == pes.d[off(i):off(i) + pes.PSZ]
assert all(same(i) for i in P if i not in built), 'a player record outside the newly built ones changed'
assert built.isdisjoint(inroster0) and built.isdisjoint(leg) and not any(i in before and before[i] > 60 for i in built), 'a record in use was overwritten'
where = collections.Counter()
for t in new.teams:
    sq = new.squad(t); ids = [i for i, _ in sq]; nums = [n for _, n in sq]; g = new.plans[t]; old = pes.plans[t]
    assert new.teams[t]['raw'] == pes.teams[t]['raw'], 'a team record changed'
    if not new.isclub(t):
        assert new.rosters[t] == pes.rosters[t] and g['raw'] == old['raw'], ('a national or classic team changed', tname(t)); continue
    for i in ids: where[i] += 1
    assert len(ids) == len(set(ids)) and all(i in N for i in ids) and 16 <= len(ids) <= 32, ('roster', tname(t))
    assert all(x[0] for x in new.rosters[t][:len(ids)]), ('gap in a roster', tname(t))
    assert len(ids) >= len(pes.squad(t)), ('a squad shrank', tname(t))
    assert len(nums) == len(set(nums)) or len({n for _, n in pes.squad(t)}) < len(pes.squad(t)), ('shirt numbers', tname(t))
    assert all(1 <= n <= 99 for n in nums) or not all(1 <= n <= 99 for _, n in pes.squad(t)), ('shirt number range', tname(t))
    xi = ids[:11]; rl = [POS[x] for x in g['presets'][0]['forms'][0]['pos']]
    assert g['raw'][:4 + 480 + 32] == old['raw'][:4 + 480 + 32] and g['raw'][4 + 480 + 42:] == old['raw'][4 + 480 + 42:], ('formation data changed', tname(t))
    assert all(k < 11 for k in g['takers'] + [g['captain']]) or g['raw'] == old['raw'], ('taker outside the eleven', tname(t))
    if t in touched or ids[:11] != [i for i, _ in pes.squad(t)][:11]:
        assert [POS[N[i]['reg_pos']] == 'GK' for i in xi] == [r == 'GK' for r in rl], ('goalkeeper', tname(t))
        assert all(POS[N[xi[k]]['reg_pos']] != 'GK' for k in g['takers']), ('a goalkeeper takes set pieces', tname(t))
    if t in PL:
        assert sum(mins(i) for i in xi) >= sum(mins(i) for i, _ in pes.squad(t)[:11]), ('fewer minutes in the eleven', tname(t))
    if t in TOP5:
        assert len(misfits(t, xi)) <= len(misfits(t, [i for i, _ in pes.squad(t)][:11])), ('more starters out of position', tname(t))
    if t not in touched: assert g['raw'] == old['raw'], ('line-up data of an untouched club changed', tname(t))
assert max(where.values()) == 1, 'a player is in two clubs'
assert all(where[i] == 1 for i in joined), 'a transferred player is not in a squad'
gonecheck = [P[i]['name'] for i, t in gone_from.items() if club.get(i) == t]; assert not gonecheck, ('back at the club he left', gonecheck)
seen = collections.defaultdict(list)
for i, p in N.items():
    if i not in leg: seen[(norm(p['name']), p['nation'], p['age'])].append(i)
twice = [N[v[0]]['name'] for v in seen.values() if len(v) > 1 and set(v) & built]
assert not twice, ('a built player is in the file twice', twice)
assert all(rate.overall(N[i]) == (m27[i]['ovr'] if i in m27 else rate.overall(N[i])) for i in built), 'a built player misses his EA rating'
for t in fmap:                                                        # FL 27 numbers hold wherever FL 27 gives one
    fn = dict(A[fmap[t]]); got = {}
    for i, n in new.squad(t):
        w = fn.get(link.get(i), 0)
        if 1 <= w <= 99 and w not in got.values(): got[i] = w; assert n == w, ('number differs from FL 27', tname(t), N[i]['name'], n, w)

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-72s %d' % (k, v))
for k, n in (('join', 70), ('built', 200), ('pl_missing', 20), ('pl_twin', 20), ('pl_unmatched', 30), ('pl_nodata', 40), ('xi', 80), ('xi_out', 80), ('role', 80), ('role_in', 40),
             ('role_left', 40), ('takers', 20), ('captain', 20), ('number', 40)):
    print('--', k, len(rep[k]))
    for x in rep[k][:n]: print('  ', x)
print('unused records left', len(spare))
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
