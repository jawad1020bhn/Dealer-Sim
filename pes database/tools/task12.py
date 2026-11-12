"""Task 12: every player aged 23 or under gets the EA FC 27 rating and Football Life 27 info.
  rating: the rating in EA's complete FC 27 list (17,849 men, down to 47) where the player is in it, matched by name,
          age, height, club and nationality, up or down;
          otherwise, for players Football Life 27 knows, the FL 27 estimate (calibrated on the youngsters that do have
          an FC 27 rating), never below the FC 26 rating or the current one and at most +8 (19 or under) / +6 (21 or under) / +4 above it;
          players unknown to both sources are left alone.
  info:   age, height, weight, nationality, positions, playing style, feet, injury resistance and skills as in FL 27.
Usage: python3 task12.py <in data.dat> <out data.dat>
"""
import sys, collections, struct, pickle
from lib import *
import rate, fldb

SRC, OUT = sys.argv[1:3]
YOUNG = 23
def cap(age): return 8 if age <= 19 else 6 if age <= 21 else 4
pes = P17(SRC); P = pes.players; D, A, T = fldb.load()
d = bytearray(pes.d); log = collections.Counter(); rep = collections.defaultdict(list)

# ------------------------------------------------------------------ links: file player -> FL database id
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

# ------------------------------------------------------------------ cards
club = {pid: pes.teams[t]['name'] for t in pes.teams if pes.isclub(t) for pid, _ in pes.squad(t)}
def names(i):
    n = [P[i]['name']]
    if i in link and norm(D[link[i]]['name']) != norm(n[0]): n.append(D[link[i]]['name'])
    return n
pl = [dict(id=i, names=names(i), age=p['age'], height=p['height'], club=club.get(i, ''), nation=p['nation']) for i, p in P.items()]
C27 = rate.fc27full(); C26 = rate.fc26()
m27 = rate.match_cards(C27, pl); m26 = rate.match_cards(C26, pl)
# nicknames (Gavi = Pablo Martín Páez Gavira): an unmatched card of the same club, age and height whose name starts like the nickname
al = collections.defaultdict(collections.Counter)
for i, c in m27.items():
    if i in club: al[c['club']][club[i]] += 1
al = {k: v.most_common(1)[0][0] for k, v in al.items() if v.most_common(1)[0][1] >= 3}
squad = collections.defaultdict(list)
for i, t in club.items(): squad[t].append(i)
taken = {id(c) for c in m27.values()}; free27 = collections.defaultdict(list)
for c in C27:
    if id(c) not in taken and c['club'] in al: free27[al[c['club']]].append(c)
for t, cards in free27.items():
    for c in cards:
        full = set(c['t']) | set(c['ts'])
        hit = [i for i in squad[t] if i not in m27 and (abs(P[i]['age'] - c['age']) <= 1 and abs(P[i]['height'] - c['height']) <= 4 if c['height'] else P[i]['age'] == c['age'])
               and any(len(k) >= 4 and (f.startswith(k) or k.startswith(f)) for n in names(i) for k in rate.toks(n) for f in full if len(f) >= 4 and (c['height'] or f != c['t'][0]))]     # no height: a shared first name is not enough
        if len(hit) == 1: m27[hit[0]] = c; taken.add(id(c)); log['FC 27 players matched by nickname within the club'] += 1; rep['nick'].append(hit[0])
def same_rating_card(i, cur):
    """The current rating is that of an unmatched FC 27 card of the same club and age: it came from that card."""
    p = P[i]
    return any(c['ovr'] == cur and id(c) not in taken and c['height'] and abs(c['age'] - p['age']) <= 1 and abs(c['height'] - p['height']) <= 6 for c in free27.get(club.get(i, ''), []))
I27 = rate.Index(C27)

# ------------------------------------------------------------------ estimate from FL 27 abilities
raw = {i: rate.overall(fldb.to17(D[q])) for i, q in link.items()}
cal = collections.defaultdict(list)
for i in link:
    if i in m27 and P[i]['age'] <= YOUNG: cal[raw[i]].append(m27[i]['ovr'])
EST = rate.est_table(cal, 0)

# ------------------------------------------------------------------ youngsters
INFO = ['age', 'reg_pos', 'play_style', 'weak_use', 'weak_acc', 'injury', 'foot'] + ['sk%d' % k for k in range(28)] + ['com%d' % k for k in range(7)]
touched = set()
for i, p in P.items():
    if p['age'] > YOUNG: continue
    log['players aged %d or under' % YOUNG] += 1
    cur = rate.overall(p); o = pes.P0 + p['i'] * pes.PSZ; before = pack17(p)
    if i in link:                                           # --- info from FL 27
        q = D[link[i]]; f = fldb.to17(q); ch = [k for k in INFO if p[k] != f[k]]
        for k in INFO: p[k] = f[k]
        for n in POS:
            if f['pp_' + n] > p['pp_' + n]: p['pp_' + n] = f['pp_' + n]; ch.append('pp_' + n)       # keeps the wing positions added earlier
        if (p['nation'], p['height'], p['weight']) != (q['nation'], q['height'], q['weight']):
            struct.pack_into('<HBB', d, o + 10, q['nation'], q['height'], q['weight']); ch.append('body')
        if ch: log['info corrected from FL 27'] += 1; rep['info'].append((p['name'], sorted(set(ch))))
    # --- rating
    c = m27.get(i); est = EST[raw[i]] if i in link else None; b26 = m26[i]['ovr'] if i in m26 else None
    if c: tg, why = c['ovr'], 'FC27'
    elif I27.loose(p['name'], p['age'], p['height'], cur) or same_rating_card(i, cur): tg, why = cur, 'kept: equals an FC 27 rating'
    elif est is not None: base = max(cur, b26 or 0); tg, why = max(base, min(est, base + cap(p['age']))), 'FL27'
    else: tg, why = cur, 'kept: unknown to FL 27 and FC 27'
    log['rating source ' + why] += 1
    if rate.overall(p) != tg:
        assert rate.retarget(p, tg), (p['name'], tg)
    if tg != cur:
        log['rating changed'] += 1; log['rating changed, source ' + why] += 1
        rep['rating'].append((p['name'], club.get(i, 'free'), p['age'], cur, tg, why))
    if pack17(p) != before: d[o + 16:o + 51] = pack17(p); touched.add(i)

open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(d) == len(pes.d) and new.porder == pes.porder
lo, hi = pes.P0, pes.P0 + pes.np * pes.PSZ
assert d[:lo] == pes.d[:lo] and d[hi:] == pes.d[hi:], 'bytes outside the player table changed'
for i, p in pes.players.items():
    a, b = p['raw'], N[i]['raw']
    if a == b: continue
    assert p['age'] <= YOUNG, 'an older player changed'
    assert a[:10] == b[:10] and a[51:] == b[51:], 'more than nation, body and abilities changed'
    assert N[i]['pp_' + POS[N[i]['reg_pos']]] == 2
for name, cl, age, cur, tg, why in rep['rating']: assert why == 'FC27' or cur < tg <= max(cur, 99) and tg - cur <= 30, 'lowered without an FC 27 rating'
bad = [i for i in m27 if pes.players[i]['age'] <= YOUNG and rate.overall(N[i]) != m27[i]['ovr']]
assert not bad, [N[i]['name'] for i in bad]

# ------------------------------------------------------------------ report
for k, v in sorted(log.items()): print('%-58s %d' % (k, v))
ch = rep['rating']
print('changes by points', sorted(collections.Counter(tg - cur for *_, cur, tg, _ in ch).items()))
print('young FC 27 players with no player in the file', sum(1 for c in C27 if c['age'] <= YOUNG and id(c) not in taken))
print('bytes changed', sum(1 for k in range(len(d)) if d[k] != pes.d[k]), 'players changed', len(touched))
rep['match'] = {i: (c['name'], c['club'], c['age'], c['height'], c['ovr']) for i, c in m27.items()}; rep['est'] = EST
pickle.dump(dict(rep), open(OUT + '.log.pkl', 'wb'))
print('self-check passed')
