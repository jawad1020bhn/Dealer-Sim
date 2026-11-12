"""Task 16: more missing players, on the output of task15.py.
A real player the file lacks is written into an unused record. New rule for which record may be overwritten:
  - it is a free agent, and no source knows its name (FL 27, EA FC 27, FC 26)       (as in task 15)
  - it is rated 69 or lower                                                          (task 15: 60 or lower)
  - the player written into it is rated 70 or higher                                 (new)
Who is built (abilities, positions, styles, age, height from the FL 27 database; overall set to the rating):
  a) FL 27 squad members of clubs in the file: EA FC 27 rating, or the estimate from the FL 27 abilities if EA has no card.
     He joins that club: an empty slot, else the slot of a reserve no source lists there, else of the weakest listed
     reserve (3 points weaker or more); if there is no such slot he becomes a free agent. Starting elevens do not change.
  b) other FL 27 players with an EA FC 27 card of 70 or more: free agents, unless EA lists them at a club of the file
     whose squad FL 27 does not have (then they join it as in a)
Not built: a player who may be in the file already. task15.py dropped everybody who shared any name word with a file
player of about that age (1,004 of 1,316). Here a file player who is linked to another FL 27 player, or matched to another
EA card, counts as another person; the rest are compared by surname, full name, club, age, height and nation.
The set-up (links, club maps, fantasy data) and place / join / become are those of task15.py, run from its source.
Usage: python3 task16.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import os
_src = open(os.path.join(os.path.dirname(os.path.abspath(__file__)), 'task15.py'), encoding='utf-8').read()
def _part(a, b): return _src[_src.index(a):_src.index(b)]
exec(compile(_src[:_src.index('# ------------------------------------------------------------------ 1. transfers')], 'task15.py set-up', 'exec'))
exec(compile(_part('joined = set()', 'todo = []'), 'task15.py place, join', 'exec'))
_p = _part('# ------------------------------------------------------------------ 2. missing players', 'EAPOS = {')
assert _p.count('before[i] <= 60') == 1
exec(compile(_p.replace('before[i] <= 60', 'before[i] <= 69'), 'task15.py spare records, become', 'exec'))
MIN = 70; spare0 = set(spare); xi0 = {t: [x[0] for x in R[t][:11]] for t in CLUBS}
assert all(before[i] <= 69 and i not in club and i not in link and i not in m27 for i in spare0)

owner = {id(c): i for i, c in m27.items()}
def last(n):
    k = [w for w in rate.toks(n) if len(w) > 1]; return k[-1] if k else ''
def dup(q, c, t):
    """The file player who may be FL 27 player q (EA card c, FL 27 club t in the file), or None."""
    if c is not None and id(c) in owner: return owner[id(c)]
    x = D[q]; n = norm(x['name']); here = {a[0] for a in R[t]} if t else (); g = GROUP[POS[x['reg_pos']]]
    for nm in [x['name']] + ([c['short']] if c else []):
        tx = {k for k in rate.toks(nm) if len(k) > 1}
        for i in {i for k in tx if len(k) > 3 for i in bytok.get(k, [])}:
            p = P[i]; tp = {w for w in rate.toks(p['name']) if len(w) > 1}
            da = abs(p['age'] - x['age']); close = da <= 1 and abs(p['height'] - x['height']) <= 2
            if (i in link and link[i] != q) or (c is not None and i in m27):          # known to be somebody else
                if norm(p['name']) == n and close: return i
                continue
            if i in here and close: return i
            if tp <= tx or tx <= tp:
                if min(len(tp), len(tx)) >= 2 and da <= 3 and abs(p['height'] - x['height']) <= 4: return i
                if close and p['nation'] == x['nation'] and GROUP[POS[p['reg_pos']]] == g: return i
            if last(p['name']) == last(nm) and close and p['nation'] == x['nation']: return i
    for i in bynat.get(x['nation'], []):
        p = P[i]
        if i in link and link[i] != q: continue
        if abs(p['age'] - x['age']) <= 1 and abs(p['height'] - x['height']) <= 2 and difflib.SequenceMatcher(None, norm(p['name']), n).ratio() >= 0.75: return i
    for i in here:
        p = P.get(i)
        if p and i not in link and i not in m27 and p['nation'] == x['nation'] and abs(p['age'] - x['age']) <= 1 and abs(p['height'] - x['height']) <= 2 \
           and GROUP[POS[p['reg_pos']]] == g: return i

# ------------------------------------------------------------------ candidates, best first
cand = {}; classic = {q for f in A if 900 <= f <= 910 for q, _ in A[f]}; usedcard = set()
for t, f in sorted(fmap.items()):
    for q, _ in A[f]:
        if q in rev or q not in D or q in cand: continue
        x = D[q]; c = I27.find(x['name'], x['age'], x['height'], tname(t))
        cand[q] = (c['ovr'] if c else EST[rate.overall(fldb.to17(x))], t, c)
for q, x in sorted(D.items()):
    if q in rev or q in cand or q in classic or x['age'] > 40: continue
    c = I27.find(x['name'], x['age'], x['height'])
    if c is None: continue
    t = eamap.get(c['club'])                                          # his EA club, where FL 27 has no squad for it (Wolfsburg, Sunderland ...)
    cand[q] = (c['ovr'], t if t is not None and t not in fmap else None, c)
for q, (r, t, c) in sorted(cand.items(), key=lambda kv: (-kv[1][0], kv[0])):
    x = D[q]
    if r < MIN: log['missing player below 70: not built'] += 1; continue
    if c is not None and id(c) in usedcard: log['skipped: his EA card went to another FL 27 player'] += 1; continue
    i = dup(q, c, t)
    if i is not None: log['skipped: may be in the file already'] += 1; rep['dup'].append((r, x['name'], x['age'], P[i]['name'], P[i]['age'], tname(club[i]) if i in club else 'free')); continue
    if not spare: log['skipped: no unused record left'] += 1; continue
    k = place(t, r) if t else None
    i = take(x['nation']); old = become(i, x, r)
    if c: m27[i] = c; owner[id(c)] = i; usedcard.add(id(c))
    if k is not None: join(t, i, 'new player', k)
    where = tname(t) if k is not None else 'free agent (' + (tname(t) + ', squad full' if t else 'EA: ' + c['club']) + ')'
    rep['built'].append((r, x['name'], x['age'], POS[x['reg_pos']], 'EA' if c else 'estimate', where, old, before[i]))
    log['built: ' + ('joins his club' if k is not None else 'free agent, squad full' if t else 'free agent, club not in the file')] += 1
    log['built: rating ' + ('80+' if r >= 80 else '75-79' if r >= 75 else '70-74') + (', EA' if c else ', estimate')] += 1

# ------------------------------------------------------------------ write
for t in CLUBS:
    o = pes.R0 + pes.teams[t]['i'] * pes.RSZ; assert u32(d, o) == t
    for k, (pid, n) in enumerate(R[t]): struct.pack_into('<I', d, o + 4 + 4 * k, pid); d[o + 132 + k] = n if pid else 0
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P) and not new.dups, 'file size, player count or ids changed'
assert new.d[:pes.P0] == pes.d[:pes.P0], 'header changed'
assert all(new.d[off(i):off(i) + pes.PSZ] == pes.d[off(i):off(i) + pes.PSZ] for i in P if i not in built), 'a record outside the built ones changed'
assert built <= spare0 and built.isdisjoint(inroster0) and built.isdisjoint(leg), 'a record in use was overwritten'
for i in built:
    q = D[link[i]]; r = cand[link[i]][0]
    assert before[i] <= 69 and r >= MIN and rate.overall(N[i]) == r, ('rule or rating', N[i]['name'])
    assert (N[i]['name'], N[i]['nation'], N[i]['height'], N[i]['age']) == (q['name'][:45], q['nation'], q['height'], q['age']), ('identity', q['name'])
    assert N[i]['pp_' + POS[N[i]['reg_pos']]] == 2, ('registered position not rated A', q['name'])
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    assert a[:10] == b[:10] and a[0x74:] == b[0x74:], ('id or appearance block changed', q['name'])
where = collections.Counter()
for t in new.teams:
    assert new.teams[t]['raw'] == pes.teams[t]['raw'] and new.plans[t]['raw'] == pes.plans[t]['raw'], ('team or line-up data changed', tname(t))
    if not new.isclub(t): assert new.rosters[t] == pes.rosters[t], ('a national or classic team changed', tname(t)); continue
    sq = new.squad(t); ids = [i for i, _ in sq]; nums = [n for _, n in sq]
    for i in ids: where[i] += 1
    assert ids[:11] == xi0[t], ('a starting eleven changed', tname(t))
    assert len(ids) == len(set(ids)) and all(i in N for i in ids) and 16 <= len(ids) <= 32 and len(ids) >= len(pes.squad(t)), ('roster', tname(t))
    assert all(x[0] for x in new.rosters[t][:len(ids)]), ('gap in a roster', tname(t))
    assert len(nums) == len(set(nums)) or len({n for _, n in pes.squad(t)}) < len(pes.squad(t)), ('shirt numbers', tname(t))
    assert all(1 <= n <= 99 for n in nums) or not all(1 <= n <= 99 for _, n in pes.squad(t)), ('shirt number range', tname(t))
assert max(where.values()) == 1 and all(where[i] == 1 for i in joined) and all(where[i] == 0 for i in built - joined), 'a player is in two clubs, or a new squad member in none'
seen = collections.defaultdict(list)
for i, p in N.items():
    if i not in leg: seen[(norm(p['name']), p['nation'], p['age'])].append(i)
twice = [N[v[0]]['name'] for v in seen.values() if len(v) > 1 and set(v) & built]
assert not twice, ('a built player is in the file twice', twice)

# ------------------------------------------------------------------ report
import pickle
pickle.dump(dict(rep), open(OUT + '.log.pkl', 'wb'))
for k, v in sorted(log.items()): print('%-72s %d' % (k, v))
for k, n in (('built', 400), ('dup', 60), ('join', 400)):
    print('--', k, len(rep[k]))
    for x in rep[k][:n]: print('  ', x)
print('unused records left (rated 69 or lower)', len(spare))
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
