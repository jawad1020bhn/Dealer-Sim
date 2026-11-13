"""Task 31: missing goalkeepers and short squads, on the output of task30.py.
A club of the file gets players until it has two goalkeepers and 20 players. Who, in this order:
  1) Wyscout 2026-27: players the tables put at the club now, most minutes first (wyscout.py; needs minutes this season)
  2) EA FC 27 cards at the club, best first        3) the Football Life 27 squad of the club, best first
Goalkeepers come first, then the smallest squads. Nobody is built who may be in the file already: a file player of
about that age (2 years; any age inside the club) with the same surname and a fitting first name, or with a similar
full name, or an untied squad member of the same age, height and position. A file player tied to another person of
the same source is somebody else.
The player is written into an unused record: a free agent with one of the game's made-up names (all lower case), else
a free agent no source knows who is rated 60 or lower. Name, age, height, nation, position are the source's (Wyscout:
first name and the surname of the short name). Abilities:
  Football Life 27 player: his own (become() of task15.py), rated as EA rates him, else the estimate of task15.py
  otherwise: those of the file player of the same position nearest in rating, age and height, shifted to the rating:
             EA's, or for a Wyscout-only player the median of the club's squad (3 less under 450 minutes)
He joins as a reserve; number: Football Life 27's if free, else 1 for a goalkeeper, else the lowest free from 12.
Usage: python3 task31.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os, statistics
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
def _part(a, b): return _src[_src.index(a):_src.index(b)]
_bar = '# ------------------------------------------------------------------ '
exec(compile(_src[:_src.index(_bar + '1. transfers')], 'task15.py set-up', 'exec'))
exec(compile(_part('joined = set()', 'todo = []'), 'task15.py place, join', 'exec'))
exec(compile(_part(_bar + '2. missing players', '# a) Premier League'), 'task15.py spare records, twin, become', 'exec'))
import wyscout

W = wyscout.load()
mw = wyscout.link(W, [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=tname(club[i]) if i in club else '', nation=p['nation'])
                      for i, p in P.items() if i not in leg])
ALL = [t for t in CLUBS if t not in LEGENDS and pes.squad(t)]
wmap = wyscout.clubs({t: [i for i, _ in pes.squad(t)] for t in ALL}, mw)
for t in ALL:
    if tname(t) in wyscout.NAMED: wmap[t] = wyscout.NAMED[tname(t)]
fake = lambda i: P[i]['name'] == P[i]['name'].lower() and any(c.isalpha() for c in P[i]['name'])
spare[:] = sorted(i for i in P if fake(i) and i not in inroster0 and i not in leg and i not in mw and i not in m27 and i not in link) + [i for i in spare if i not in mw and not fake(i)]
spare0 = set(spare); P0name = {i: P[i]['name'] for i in spare}; xi0 = {t: [x[0] for x in R[t][:11]] for t in CLUBS}
taken = {w['id'] for w in mw.values()}; owned = {id(c) for c in m27.values()}
natw = collections.defaultdict(collections.Counter)                    # Wyscout country -> nation id of the file
for i, w in mw.items(): natw[w['nation']][P[i]['nation']] += 1
WPOS = dict(GK='GK', CB='CB', RCB='CB', LCB='CB', RCB3='CB', LCB3='CB', RB='RB', RB5='RB', RWB='RB', LB='LB', LB5='LB', LWB='LB', DMF='DMF', LDMF='DMF', RDMF='DMF',
            RCMF='CMF', LCMF='CMF', RCMF3='CMF', LCMF3='CMF', AMF='AMF', RAMF='RMF', LAMF='LMF', RW='RWF', RWF='RWF', LW='LWF', LWF='LWF', CF='CF')
gk = lambda i: POS[P[i]['reg_pos']] == 'GK'
def need(t):
    ids = [x[0] for x in R[t] if x[0]]; return (sum(map(gk, ids)) < 2, len(ids) < 20)

def wname(w):
    a = w['short'].split(); f = w['name'].split()
    return ' '.join(f[:1] + a[1:]) if len(a) > 1 and len(a[0]) == 2 and a[0][1] == '.' and f else w['short']
def candidates(t):
    """(source, name, full name, age, height, nation id, position, rating, foot, FL 27 record) in the order of the rule."""
    med = round(statistics.median(ovr(x[0]) for x in R[t] if x[0])); out = []
    ws = [w for w in W.values() if w['now'] == wmap.get(t) and w['id'] not in taken and w['nation'] in natw]
    for w in sorted(ws, key=lambda w: (-wyscout.minutes(w, wmap[t]), w['id'])):
        r = max(w['rows'], key=lambda x: x['min'])['r']; pos = WPOS.get(r['Position'].split(',')[0].strip()); mins = wyscout.minutes(w, wmap[t])
        if pos and w['height']: out.append(('Wyscout, %d minutes' % mins, wname(w), w['name'], w['age'], w['height'], natw[w['nation']].most_common(1)[0][0], pos, med - 3 * (mins < 450), r['Foot'], None))
    for c in sorted((c for c in C27 if eamap.get(c['club']) == t and id(c) not in owned and c['nation'] in natof), key=lambda c: (-c['ovr'], c['name'])):
        out.append(('EA FC 27', c['short'] if len(c['name']) > 30 else c['name'], c['name'], c['age'], c['height'] or 180, natof[c['nation']].most_common(1)[0][0], EAPOS[c['pos']], c['ovr'], '', None))
    fl = []
    for q, _ in A[fmap[t]] if t in fmap else ():
        if q in rev or q not in D: continue
        x = D[q]; c = I27.find(x['name'], x['age'], x['height'], tname(t))
        fl.append(('Football Life 27', x['name'], x['name'], x['age'], x['height'], x['nation'], POS[x['reg_pos']], c['ovr'] if c else EST[rate.overall(fldb.to17(x, True))], '', x))
    return out + sorted(fl, key=lambda x: (-x[7], x[1]))
def same(src, name, full, age, height, nat, pos, t):
    """The file player who may be this person, or None."""
    tied = mw if src[0] == 'W' else m27 if src[0] == 'E' else link; here = {x[0] for x in R[t]}
    tf = {k for k in rate.toks(full) + rate.toks(name) if len(k) > 1}; ts = {k for k in rate.toks(name)[1:] if len(k) > 1} or tf; n = norm(name)
    for i in {i for k in tf if len(k) > 3 for i in bytok.get(k, [])}:
        p = P[i]; tp = {k for k in rate.toks(p['name']) if len(k) > 1}
        if (i in tied and i not in built) or not (abs(p['age'] - age) <= 2 or i in here): continue
        if tp <= tf or (ts <= tp and (len(tp) == len(ts) or any(k[0] == norm(full)[0] for k in tp - ts))): return i
        if difflib.SequenceMatcher(None, norm(p['name']), n).ratio() >= 0.85: return i
    for i in here:
        p = P.get(i)
        if p and i not in tied and i not in built and p['age'] == age and abs(p['height'] - height) <= 1 and POS[p['reg_pos']] == pos: return i
EAPOS = {'GK': 'GK', 'CB': 'CB', 'LB': 'LB', 'RB': 'RB', 'CDM': 'DMF', 'CM': 'CMF', 'LM': 'LMF', 'RM': 'RMF', 'CAM': 'AMF', 'LW': 'LWF', 'RW': 'RWF', 'ST': 'CF'}
natof = collections.defaultdict(collections.Counter)
for i, c in m27.items(): natof[c['nation']][P[i]['nation']] += 1
known = [j for j in P if j not in leg and not fake(j) and (j in m27 or j in link or j in mw)]
made = {}; cands = {}
def build(t, only_gk):
    for cnd in cands.setdefault(t, candidates(t)):
        src, name, full, age, height, nat, pos, r, foot, x = cnd; g, s = need(t)
        if not ((g and pos == 'GK') if only_gk else s): continue
        if not spare: log['skipped: no unused record left'] += 1; return
        tw = same(src, name, full, age, height, nat, pos, t)
        if tw is not None:
            if (name, tw) not in seen: seen.add((name, tw)); log['skipped: may be in the file already'] += 1; rep['dup'].append((tname(t), name, age, P[tw]['name'], P[tw]['age'], tname(club[tw]) if tw in club else 'free agent'))
            continue
        r = max(45, min(r, 90)); i = take(nat); old = P[i]['name']
        if x is not None: P[i].update(fldb.to17(x, True)); identity(i, name, nat, height, x['weight']); like = 'his own'; link[i] = x['id']; rev[x['id']] = i
        else:
            for w in (1, 3, 6, 12):
                c = [j for j in known if j not in built and P[j]['reg_pos'] == POS.index(pos) and abs(ovr(j) - r) <= w]
                if c: break
            tpl = min(c, key=lambda j: (abs(P[j]['age'] - age) > 2, abs(P[j]['height'] - height) > 4, abs(ovr(j) - r), abs(P[j]['age'] - age), abs(P[j]['height'] - height), j)); q = P[tpl]
            for f in q:
                if f not in ('i', 'id', 'u4', 'name', 'shirt', 'app_id', 'raw', 'nation', 'height', 'weight', 'gc1', 'gc2') and not f.startswith('mo_'): P[i][f] = q[f]
            P[i]['age'] = age
            if foot in ('left', 'right'): P[i]['foot'] = int(foot == 'left')
            identity(i, name, nat, height, max(50, min(110, q['weight'] + round(0.9 * (height - q['height']))))); like = q['name']
        assert rate.retarget(P[i], r), (name, r)
        put(i); built.add(i); index(i); k = place(t, r); assert k is not None and not R[t][k][0]; join(t, i, 'new player', k)
        if x is None or R[t][k][1] != dict(A[fmap[t]]).get(x['id']):      # no Football Life 27 number: 1 for a goalkeeper, the lowest free from 12, from 2
            used = {y[1] for y in R[t] if y[0] and y[0] != i}; R[t][k][1] = next(n for n in (int(pos == 'GK'), *range(12, 100), *range(2, 12)) if n and n not in used)
        made[i] = (name[:45], nat, height, age, pos, r, t)
        rep['built'].append((tname(t), name, age, pos, r, src, 'abilities: ' + like, 'record of ' + old, R[t][k][1]))
        log['built: ' + src.split(',')[0]] += 1; log['built: ' + ('goalkeeper' if pos == 'GK' else 'outfield player')] += 1
seen = set()
for t in sorted(ALL):
    if need(t)[0]: build(t, True)
for t in sorted(ALL, key=lambda t: (sum(1 for x in R[t] if x[0]), t)):
    if need(t)[1]: build(t, False)
for t in ALL:
    g, s = need(t)
    if g: log['still under two goalkeepers'] += 1; rep['short'].append((tname(t), 'goalkeepers', sum(gk(x[0]) for x in R[t] if x[0])))
    if s: log['still under 20 players'] += 1; rep['short'].append((tname(t), 'players', sum(1 for x in R[t] if x[0])))

# ------------------------------------------------------------------ write
for t in CLUBS:
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    for k, (pid, n) in enumerate(R[t]): struct.pack_into('<I', d, o + 4 + 4 * k, pid); d[o + 132 + k] = n if pid else 0
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and not new.dups and new.d[:pes.P0] == pes.d[:pes.P0], 'file size, player count, ids or header changed'
assert all(new.d[off(i):off(i) + pes.PSZ] == pes.d[off(i):off(i) + pes.PSZ] for i in P if i not in built), 'a record outside the built ones changed'
assert built == set(made) and built <= spare0 and built.isdisjoint(inroster0) and built.isdisjoint(leg) and built.isdisjoint(mw), 'a record in use was overwritten'
for i, (name, nat, height, age, pos, r, t) in made.items():
    assert (before[i] <= 60 or P0name[i] == P0name[i].lower()) and rate.overall(N[i]) == r, ('rule or rating', name)
    assert (N[i]['name'], N[i]['nation'], N[i]['height'], N[i]['age'], POS[N[i]['reg_pos']]) == (name, nat, height, age, pos), ('identity', name)
    assert N[i]['pp_' + pos] == 2, ('registered position not rated A', name)
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    assert a[:10] == b[:10] and a[0x74:] == b[0x74:], ('id or appearance block changed', name)
    assert i in [x for x, _ in new.squad(t)][11:], ('not a reserve of his club', name)
where = collections.Counter()
for t in new.teams:
    assert new.teams[t]['raw'] == pes.teams[t]['raw'] and new.plans[t]['raw'] == pes.plans[t]['raw'], ('team or line-up data changed', tname(t))
    old = pes.squad(t); sq = new.squad(t); ids = [i for i, _ in sq]; nums = [n for _, n in sq]
    for i in ids: where[i] += 1
    assert sq[:len(old)] == old and set(ids[len(old):]) <= built and len(ids) <= 32, ('somebody moved, left or changed number', tname(t))
    add = ids[len(old):]; g0 = sum(POS[P[i]['reg_pos']] == 'GK' for i, _ in old); g1 = sum(POS[N[i]['reg_pos']] == 'GK' for i in add); room = max(0, 20 - len(old))
    assert not add or (new.isclub(t) and len(add) - g1 <= room and g1 <= max(room, 2 - g0)), ('a squad grew against the rule', tname(t))
    assert len(nums) == len(set(nums)) or len({n for _, n in old}) < len(old), ('shirt numbers', tname(t))
    assert all(n != 1 or POS[N[i]['reg_pos']] == 'GK' for i, n in sq[len(old):]), ('number 1 on an outfield player', tname(t))
assert all(where[i] == 1 for i in built), 'a built player is in no club or in two'
byname = collections.defaultdict(list)
for i, p in N.items():
    if i not in leg: byname[norm(p['name'])].append(i)
twice = [N[i]['name'] for i in built for j in byname[norm(N[i]['name'])] if j != i and (club.get(j) == club[i] or (abs(N[j]['age'] - N[i]['age']) <= 1 and j not in mw))]       # tied to another Wyscout player: a namesake
assert not twice, ('a built player is in the file twice', twice)

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep=dict(rep), log=dict(log)), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-60s %d' % (k, v))
for k in ('built', 'dup', 'short'):
    print('--', k, len(rep[k]))
    for x in rep[k][:300]: print('  ', x)
print('unused records left', len(spare), '| bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
