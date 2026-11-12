"""Task 11 on the PES 2017 edit file (decrypted data.dat in, data.dat out):
  1. add top-five Football Life 27 squad members that the file lacks, by overwriting unlinked free agents,
  2. lift top-five youngsters (age <= 23, no FC 27 card) to the FL 27 estimate, capped above last year's rating,
  3. rate every LWF/RWF starter A at that position,
  4. take manager names and tactical settings from the FL 27 save.
Usage: python3 task11.py <in data.dat> <FL data.dat> <out data.dat>
"""
import sys, collections, unicodedata, struct
from lib import *
import rate, fldb

SRC, FLP, OUT = sys.argv[1:4]
pes = P17(SRC); fl = FL(FLP); P = pes.players; D, A, T = fldb.load()
d = bytearray(pes.d)
log = collections.Counter(); notes = []

# ------------------------------------------------------------------ links: file player -> FL database id
def compat(a, b): return norm(a) == norm(b) or bool(set(rate.toks(a)) & set(rate.toks(b)))
link = {}; byname = collections.defaultdict(list)
for q in D.values(): byname[(norm(q['name']), q['age'], q['height'])].append(q['id'])
for i, p in P.items():      # ids 90000-96999 are other people in the FL database
    if i not in D or 90000 <= i < 97000: continue
    q = D[i]; da = abs(p['age'] - q['age'])
    if (compat(p['name'], q['name']) and da <= 3) or (da <= 1 and abs(p['height'] - q['height']) <= 2 and p['nation'] == q['nation']): link[i] = i
used = set(link.values())
for i, p in P.items():
    if i in link: continue
    c = [x for x in byname.get((norm(p['name']), p['age'], p['height']), []) if x not in used]
    if len(c) == 1: link[i] = c[0]; used.add(c[0])
def same_person(n1, n2):
    """Names of one person in two spellings: same surname (or near-identical full name) and compatible first names."""
    import difflib
    a, b = rate.toks(n1), rate.toks(n2)
    if not a or not b: return False
    if a == b or a[-len(b):] == b or b[-len(a):] == a: return True
    if a[-1] != b[-1] and difflib.SequenceMatcher(None, ''.join(a), ''.join(b)).ratio() < 0.85: return False
    return len(a) == 1 or len(b) == 1 or a[0] == b[0] or a[0].startswith(b[0]) or b[0].startswith(a[0])
bytok = collections.defaultdict(list)
for q in D.values():
    for k in set(rate.toks(q['name'])):
        if len(k) > 2: bytok[k].append(q['id'])
strict = set(link)
for i, p in P.items():
    if i in link: continue
    c = [x for x in {x for k in rate.toks(p['name']) for x in bytok.get(k, [])} if x not in used and abs(D[x]['age'] - p['age']) <= 1
         and abs(D[x]['height'] - p['height']) <= 2 and D[x]['nation'] == p['nation'] and same_person(p['name'], D[x]['name'])]
    if len(c) == 1: link[i] = c[0]; used.add(c[0])
    elif c: link[i] = None                       # ambiguous: a real player, but not safe to use
loose = {i for i in link if i not in strict and link[i] is not None}
real = set(link)                                 # everybody the FL database knows
link = {i: v for i, v in link.items() if v is not None}
rev = {v: k for k, v in link.items()}

# ------------------------------------------------------------------ teams: file team -> FL team by squad overlap
inv = collections.defaultdict(set)
for t in fl.teams:
    for pid, _ in fl.squad(t): inv[pid].add(t)
tmatch = {}
for t in pes.teams:
    sq = [pid for pid, _ in pes.squad(t)]; c = collections.Counter()
    for pid in sq:
        for ft in inv.get(link.get(pid, -1), ()): c[ft] += 1
    if c and c.most_common(1)[0][1] >= max(8, len(sq) // 2): tmatch[t] = c.most_common(1)[0][0]
assert len(set(tmatch.values())) == len(tmatch)
classic = lambda t: any(w in (pes.teams[t]['name'] + fl.teams[tmatch[t]]['name']).lower() for w in ('classic', 'old boys'))

# ------------------------------------------------------------------ FC cards, top-five clubs
I27 = rate.Index(rate.fc27()); I26 = rate.Index(rate.fc26())
club = {pid: t for t in pes.teams if pes.isclub(t) for pid, _ in pes.squad(t)}
cname = lambda i: pes.teams[club[i]]['name'] if i in club else ''
def card(I, i):
    p = P[i]; c = I.find(p['name'], p['age'], p['height'], cname(i))
    if not c and i in link: c = I.find(D[link[i]]['name'], p['age'], p['height'], cname(i))     # FL spelling, e.g. Savinho / Savio
    return c
c27 = {i: card(I27, i) for i in P}; c26 = {i: card(I26, i) for i in P}
TOP27 = {'Premier League', 'LALIGA EA SPORTS', 'Serie A Enilive', 'Bundesliga', "Ligue 1 McDonald's"}
TOP26 = {'13.0', '53.0', '31.0', '19.0', '16.0'}
top = []
for t in pes.teams:
    if not pes.isclub(t): continue
    a = collections.Counter(c27[i]['league'] for i, _ in pes.squad(t) if c27[i]).most_common(1)
    b = collections.Counter(c26[i]['league'] for i, _ in pes.squad(t) if c26[i]).most_common(1)
    if (a and a[0][0] in TOP27 and a[0][1] >= 8) or (b and b[0][0] in TOP26 and b[0][1] >= 8): top.append(t)

# ------------------------------------------------------------------ ratings
fromdb = fldb.to17
retarget = rate.retarget

# estimate: FL 27 abilities read with the 2017 formula run about 3 above EA; map through the median FC 27 rating
cal = collections.defaultdict(list)
for i, q in link.items():
    if c27[i] and rate.overall(P[i]) == c27[i]['ovr']: cal[rate.overall(fromdb(D[q]))].append(c27[i]['ovr'])
EST = rate.est_table(cal)
CAP = lambda age: 8 if age <= 19 else 6 if age <= 21 else 4
def target_for(card27, card26, age, est, cur=None):
    """FC 27, else (age <= 23) the estimate held between last year's rating and that + cap, else FC 26, else estimate."""
    if card27: return card27['ovr'], 'FC27'
    base = card26['ovr'] if card26 else cur
    if age <= 23:
        if base is None: return est, 'YOUNG'
        return min(max(est, base), (cur if cur is not None else base) + CAP(age)), 'YOUNG'
    if card26: return card26['ovr'], 'FC26'
    return est, 'EST'

def put_abilities(i):
    p = P[i]; o = pes.P0 + p['i'] * pes.PSZ; d[o + 16:o + 51] = pack17(p)

# ------------------------------------------------------------------ 1. missing players
rosters = {t: [list(x) for x in pes.rosters[t]] for t in pes.teams}       # [player id, number] per slot
inroster = {pid for r in rosters.values() for pid, _ in r if pid}
donors = collections.defaultdict(list)                                     # nation -> free agents unknown to FL and EA, worst first
pool = sorted((i for i in P if i not in inroster and i not in real and not c27[i] and not c26[i] and rate.overall(P[i]) <= 66), key=lambda i: rate.overall(P[i]))
for i in pool: donors[P[i]['nation']].append(i)
anydonor = pool
taken = set()
def donor(nation):
    for i in donors.get(nation, []) + anydonor:
        if i not in taken: taken.add(i); return i
def shirtname(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper().split()
    return (t[-1] if t else '')[:15]
existing = collections.defaultdict(list)
for i, p in P.items():
    for k in rate.toks(p['name']): existing[k].append(i)
def twin(q):
    """A file player who is probably the same person under another spelling."""
    for i in {i for k in rate.toks(q['name']) if len(k) > 2 for i in existing.get(k, [])}:
        p = P[i]
        if i not in link and abs(p['age'] - q['age']) <= 1 and abs(p['height'] - q['height']) <= 2 and p['nation'] == q['nation'] and same_person(p['name'], q['name']): return i
added = []; newids = set()
for t in top:
    if t not in tmatch: continue
    ft = tmatch[t]; g = fl.plans[ft]; fr = fl.rosters[ft]; r = rosters[t]; plan = pes.plans[t]
    assert plan['xi'] + plan['bench'] == list(range(32)), t
    order = [fr[k][0] for k in g['order'] if k < 40 and fr[k][0]]
    rank = {rev[pid]: n for n, pid in enumerate(order) if pid in rev}
    flnum = dict(A.get(ft, []))
    for n, pid in enumerate(order):
        if pid in rev or pid not in D: continue
        q = D[pid]
        tw = twin(q)
        if tw is None:                               # same name in this very squad, whatever age and height the two sources give
            tw = next((x[0] for x in r if x[0] and x[0] not in rank and same_person(P[x[0]]['name'], q['name'])), None)
        if tw is not None: log['skipped: probably in the file under another spelling'] += 1; notes.append('twin %s ~ %s' % (q['name'], P[tw]['name'])); continue
        size = sum(1 for x in r if x[0])
        if size < 32: slot = next(k for k, x in enumerate(r) if not x[0]); victim = None
        else:
            bench = [k for k in range(11, 32) if r[k][0] not in newids]
            fills = sorted((k for k in bench if r[k][0] not in rank), key=lambda k: rate.overall(P[r[k][0]]))
            later = sorted((k for k in bench if rank.get(r[k][0], -1) > n), key=lambda k: -rank[r[k][0]])
            if n < 11 and r[n][0] not in rank and r[n][0] not in newids: slot = n
            elif fills: slot = fills[0]
            elif later: slot = later[0]
            else: log['skipped: squad full of higher-ranked FL players'] += 1; continue
            victim = r[slot][0]
        i = donor(q['nation'])
        if i is None: log['skipped: no free record'] += 1; continue
        # --- write the record: nation, height, weight, abilities, names; id, motions and appearance stay the donor's
        old = (P[i]['name'], rate.overall(P[i]))
        p = P[i]; p.update(fromdb(q)); est = EST[rate.overall(p)]
        k27 = I27.find(q['name'], q['age'], q['height'], pes.teams[t]['name']); k26 = I26.find(q['name'], q['age'], q['height'], pes.teams[t]['name'])
        tg, why = target_for(k27, k26, q['age'], est)
        assert retarget(p, tg), (q['name'], tg)
        o = pes.P0 + p['i'] * pes.PSZ
        struct.pack_into('<HBB', d, o + 10, q['nation'], q['height'], q['weight'])
        put_abilities(i)
        nm = q['name'].encode('utf8')[:45]; d[o + 0x34:o + 0x34 + 46] = nm.ljust(46, b'\0')
        sn = shirtname(q['name']).encode('latin1'); d[o + 0x62:o + 0x62 + 18] = sn.ljust(18, b'\0')
        p['name'] = q['name']; p['nation'] = q['nation']; p['height'] = q['height']; link[i] = pid; rev[pid] = i; rank[i] = n; newids.add(i)
        # --- roster and line-up
        usednum = {x[1] for x in r if x[0] and x[0] != victim}
        num = flnum.get(pid, 0)
        if not 1 <= num <= 99 or num in usednum: num = next(k for k in range(1, 100) if k not in usednum)
        if n < 11 and slot != n:                       # FL starter: takes his slot, the stand-in moves to the free slot
            r[slot] = r[n]; slot = n
        r[slot] = [i, num]
        added.append((t, n, i, q['name'], tg, why, old, victim))
        log['added'] += 1; log['added, rating from ' + why] += 1; log['added as starter'] += n < 11
        if victim: log['released to make room'] += 1
for t, r in rosters.items():
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ
    for k, (pid, num) in enumerate(r): struct.pack_into('<I', d, o + 4 + 4 * k, pid); d[o + 132 + k] = num

# ------------------------------------------------------------------ 2. top-five youngsters
lifted = []
for t in top:
    for pid, _ in rosters[t]:
        if not pid or pid in newids: continue
        p = P[pid]
        if p['age'] > 23 or c27[pid] or pid not in link: continue
        cur = rate.overall(p)
        if I27.loose(p['name'], p['age'], p['height'], cur) or I27.loose(D[link[pid]]['name'], p['age'], p['height'], cur): log['youngsters skipped: rating equals a loosely matching FC 27 card'] += 1; continue
        k26 = c26[pid] if c26[pid] and c26[pid]['ovr'] == cur else I26.loose(p['name'], p['age'], p['height'], cur) or I26.loose(D[link[pid]]['name'], p['age'], p['height'], cur)
        if not k26: log['youngsters skipped: rating is not last year\'s FC 26 rating'] += 1; continue
        est = EST[rate.overall(fromdb(D[link[pid]]))]
        tg, _ = target_for(None, k26, p['age'], est, cur)
        log['youngsters checked'] += 1
        if tg > cur:
            assert retarget(p, tg), p['name']
            put_abilities(pid); lifted.append((p['name'], pes.teams[t]['name'], p['age'], cur, tg))

# ------------------------------------------------------------------ 3. wing starters
wing = []
for t, g in pes.plans.items():
    for k, pc in enumerate(g['presets'][0]['forms'][0]['pos']):
        pid = rosters[t][g['xi'][k]][0] if g['xi'][k] < 32 else 0
        if pc in (9, 10) and pid in P and P[pid]['pp_' + POS[pc]] != 2:
            P[pid]['pp_' + POS[pc]] = 2; put_abilities(pid); wing.append((pes.teams[t]['name'], P[pid]['name'], POS[pc]))

# ------------------------------------------------------------------ 4. managers and tactical settings
ADV = {1, 2, 4, 5, 6, 7, 9, 11, 12, 13, 16}           # advanced instruction ids already used by this 2017 file
mgr = []
for t, ft in tmatch.items():
    if classic(t): continue
    X = pes.teams[t]; m = fl.managers.get(fl.teams[ft]['mgr']); mid = u32(X['raw'], 4)
    if m and mid in pes.managers:
        o = pes.M0 + pes.managers[mid]['i'] * 88; nm = m['name'].encode('utf8')[:59]
        if pes.managers[mid]['name'] != m['name']: mgr.append((X['name'], pes.managers[mid]['name'], m['name']))
        struct.pack_into('<H', d, o + 4, m['nat']); d[o + 9:o + 69] = nm.ljust(60, b'\0')
    o = pes.G0 + X['i'] * pes.GSZ; src = fl.plans[ft]['raw']; before = bytes(d[o:o + pes.GSZ])
    for k in range(3):
        po = 4 + k * 160
        d[o + po + 99:o + po + 106] = src[po + 99:po + 106]                # the seven attack / defence style switches
        for b in (108, 116, 124, 132):                                    # advanced instructions: attack 1, 2, defence 1, 2
            v = src[po + b]
            if v in ADV: d[o + po + b:o + po + b + 8] = bytes([v]) + bytes(7)
            else: d[o + po + b] = 0; log['advanced instruction unknown to 2017 dropped'] += v != 0
        for b in (140, 142, 143): d[o + po + b] = src[po + b]              # support range, defensive line, compactness
    log['teams with tactics from FL'] += 1; log['teams whose tactic bytes changed'] += bytes(d[o:o + pes.GSZ]) != before

open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(d) == len(pes.d) and new.porder == pes.porder and list(new.teams) == list(pes.teams)
seen = collections.Counter(pid for t in new.teams if new.isclub(t) for pid, _ in new.squad(t))
assert max(seen.values()) == 1, 'a player in two clubs'
for t in new.teams:
    sq = new.squad(t); nums = [n for _, n in sq]
    assert all(pid in N for pid, _ in sq) and len(set(nums)) == len(nums) and all(1 <= n <= 99 for n in nums), new.teams[t]['name']
    assert len(sq) == len(pes.squad(t)) or t in top, new.teams[t]['name']
    if new.isclub(t) and t in top: assert 16 <= len(sq) <= 32
    g = new.plans[t]
    for pr in g['presets']:
        for f in pr['forms']: assert 6 not in f['pos'] and 7 not in f['pos']
    for k, pc in enumerate(g['presets'][0]['forms'][0]['pos']):
        pid = new.rosters[t][g['xi'][k]][0] if g['xi'][k] < 32 else 0
        if pid: assert pc not in (9, 10) or N[pid]['pp_' + POS[pc]] == 2
for t, n, i, name, tg, why, old, victim in added:
    assert N[i]['name'] == name and rate.overall(N[i]) == tg and any(pid == i for pid, _ in new.squad(t))
for name, team, age, cur, tg in lifted: pass
changed = {i for i in P if new.players[i]['raw'] != pes.players[i]['raw']}
assert changed == newids | {i for i in P if pack17(P[i]) != pes.players[i]['raw'][16:51]}
for i in changed - newids:                            # everyone else: only the ability block moved
    a, b = pes.players[i]['raw'], N[i]['raw']; assert a[:16] == b[:16] and a[51:] == b[51:]
for i in newids: assert pes.players[i]['raw'][0x74:] == N[i]['raw'][0x74:] and pes.players[i]['raw'][:10] == N[i]['raw'][:10]
lo, hi = pes.T0, pes.T0 + pes.nt * pes.TSZ; assert d[lo:hi] == pes.d[lo:hi], 'team records changed'
regions = [(pes.P0, pes.P0 + pes.np * pes.PSZ), (pes.M0, pes.M0 + 636 * 88), (pes.R0, pes.R0 + pes.nt * pes.RSZ), (pes.G0, pes.G0 + pes.nt * pes.GSZ)]
out = sum(1 for k in range(len(d)) if d[k] != pes.d[k] and not any(a <= k < b for a, b in regions)); assert out == 0, out
for t in new.teams:                                   # line-up tail (XI, bench, takers, captain) untouched
    assert new.plans[t]['raw'][484:] == pes.plans[t]['raw'][484:]

# ------------------------------------------------------------------ report
print('links %d, teams matched %d, top-five clubs %d (%d with an FL team)' % (len(link), len(tmatch), len(top), sum(t in tmatch for t in top)))
for k, v in sorted(log.items()): print('%-55s %d' % (k, v))
print('youngsters lifted %d, by points %s' % (len(lifted), sorted(collections.Counter(tg - cur for *_, cur, tg in lifted).items())))
print('wing starters given the position %d (LWF %d, RWF %d)' % (len(wing), sum(w[2] == 'LWF' for w in wing), sum(w[2] == 'RWF' for w in wing)))
print('manager names changed %d of %d teams' % (len(mgr), sum(not classic(t) for t in tmatch)))
print('bytes changed %d' % sum(1 for k in range(len(d)) if d[k] != pes.d[k]))
import pickle; pickle.dump(dict(added=added, lifted=lifted, wing=wing, mgr=mgr, notes=notes, top=top), open(OUT + '.log.pkl', 'wb'))
print('self-check passed')
