"""Task 17: appearance of the players that were written into another player's record (tasks 11 to 16).
Such a record kept the look of the invented player it replaced. Here it gets the appearance Football Life 27 stores
for the real player: skin colour, face shape, eyes, nose, mouth, facial hair, hairstyle and colours, build, accessories.

  - which records: neither surname is part of the other name (the name now, the name in the original save), and
    nation, height, weight and age are not all the same (so a mere renaming does not count)
  - layout: bytes 12-67 of the appearance block of a PES 2017 record (record offset +0x74) are bytes 4-59 of a
    PlayerAppearance.bin record of PES 2021 / FL 27. Checked on 14,945 players who are the same person with the same id
    in both: 644 blocks are identical byte for byte, skin colour agrees for 72% (20% by chance).
  - FL 27 stores no hairstyle for some players (hair colour only): they get the most common hairstyle of the 2017
    players with the same skin colour; the 'undershorts' value (always 0 in the 2017 file) stays 0
  - the "edited" flags of these records are set (name and abilities, face, hair, physique, strip style), so the game
    takes the record of the edit file instead of the invented player of its own database
  - nine legends built by hand have no FL 27 record: only their skin colour is set, from a table
Scanned faces are files of the game or patch tied to the player id; the edit file cannot supply them.
Usage: python3 task17.py <in data.dat> <original data.dat> <out data.dat>     (ends with a self-check of the written file)
"""
import sys, collections
from lib import P17, pack17, norm
import rate, fldb, pesdb

SRC, ORIG, OUT = sys.argv[1:4]
pes = P17(SRC); P = pes.players; O = P17(ORIG).players; D, A, T = fldb.load()
d = bytearray(pes.d); log = collections.Counter(); rep = collections.defaultdict(list)
app = pesdb.AppearanceTable(pesdb.table_blob(fldb.CPK, 'PlayerAppearance'))
PA = {app.pid(k): bytes(app.records[k]) for k in range(len(app.records))}
FIELD = {lab: (bit, w) for lab, bit, w, _ in pesdb.APPEARANCE}
SHIFT = 64                                                            # a field at bit b of the FL record is at bit b + 64 of the 2017 block
EFLAGS = ('e_player', 'e_basic', 'e_regpos', 'e_playpos', 'e_ability', 'e_skill', 'e_style', 'e_com', 'e_motion')
def off(i): return pes.P0 + P[i]['i'] * pes.PSZ
def block(buf, i): return bytes(buf[off(i) + 0x74:off(i) + 0xBC])
def get(rec, lab, shift=0): bit, w = FIELD[lab]; return (int.from_bytes(rec, 'little') >> (bit + shift)) & ((1 << w) - 1)
def put(rec, lab, v, shift=0):
    bit, w = FIELD[lab]; n = int.from_bytes(rec, 'little'); m = ((1 << w) - 1) << (bit + shift)
    assert 0 <= v < 1 << w; return ((n & ~m) | (v << (bit + shift))).to_bytes(len(rec), 'little')
assert get(put(bytes(60), 'Skin Colour', 5), 'Skin Colour') == 5 and put(put(bytes(60), 'Hair Red', 33), 'Hair Red', 0) == bytes(60)

# ------------------------------------------------------------------ links to FL 27 (as in task15.py)
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

# ------------------------------------------------------------------ records that hold another person than in the original save
def last(n):
    k = [w for w in rate.toks(n) if len(w) > 1]; return k[-1] if k else ''
def rebuilt(i):
    a, b = O.get(i), P[i]
    if a is None or norm(a['name']) == norm(b['name']): return False
    if last(a['name']) in rate.toks(b['name']) or last(b['name']) in rate.toks(a['name']): return False
    return (a['nation'], a['height'], a['weight'], a['age']) != (b['nation'], b['height'], b['weight'], b['age'])

# ------------------------------------------------------------------ the format check the layout rests on
same = [i for i in P if i in O and link.get(i) == i and i in PA and set(rate.toks(O[i]['name'])) & set(rate.toks(P[i]['name'])) and not rebuilt(i)]
eq = sum(get(block(pes.d, i), 'Skin Colour', SHIFT) == get(PA[i], 'Skin Colour') for i in same)
ident = sum(block(pes.d, i)[12:68] == PA[i][4:60] for i in same)
assert len(same) > 10000 and eq > 0.6 * len(same) and ident > 300, ('appearance layouts do not agree', len(same), eq, ident)

# skin colour 1 (lightest) to 6 (darkest), as the file uses it: Messi 1, Son 2, Salah 3, Vinícius Júnior 6
LEGEND_SKIN = {'Jairzinho': 6, 'Carlos Alberto': 5, 'Rivellino': 2, 'Bobby Moore': 1, 'Emilio Butragueño': 1, 'Jean-Pierre Papin': 1,
               'Rudi Völler': 1, 'Gianluca Vialli': 2, 'David Ginola': 1}

todo = [i for i in P if rebuilt(i)]
# ------------------------------------------------------------------ hairstyles
# FL 27 stores no hairstyle for about 6,800 players (style fields 0, colour set): they get the most common hairstyle
# of the 2017 players with the same skin colour. A style / variation pair the 2017 file never uses gets the nearest one.
HAIR = ('Overall Style', 'Overall Length', 'Overall Wave Level', 'Overall Hair Variation', 'Front Style', 'Front Parted', 'Front Hairline',
        'Front Forehead Width', 'Side Back Style', 'Side Back Cropped')
keep = [i for i in O if not rebuilt(i)]
seen = collections.Counter(tuple(get(block(pes.d, i), f, SHIFT) for f in HAIR[:4]) for i in keep)
common = collections.defaultdict(collections.Counter)
for i in keep:
    b = block(pes.d, i); h = tuple(get(b, f, SHIFT) for f in HAIR)
    if h[1] and h[4]: common[get(b, 'Skin Colour', SHIFT)][h] += 1
def nohair(rec): return get(rec, 'Overall Style') == 1 and get(rec, 'Overall Length') == 0 and get(rec, 'Front Style') == 0
def hair(rec):
    if nohair(rec):
        for f, v in zip(HAIR, common[get(rec, 'Skin Colour')].most_common(1)[0][0]): rec = put(rec, f, v)
        log['  of these: no hairstyle in FL 27, common one for the skin colour'] += 1; return rec
    h = tuple(get(rec, f) for f in HAIR[:4])
    if seen[h]: return rec
    ok = list(seen)
    alt = [k for k in ok if k[:3] == h[:3]] or [k for k in ok if k[:2] == h[:2]] or [k for k in ok if k[0] == h[0]]
    for f, v in zip(HAIR, max(alt, key=lambda k: seen[k])): rec = put(rec, f, v)
    log['  of these: hairstyle variation unknown to the 2017 file, nearest one'] += 1; return rec

# ------------------------------------------------------------------ write
written = {}; skinonly = {}
for i in todo:
    o = off(i) + 0x74; was = get(block(pes.d, i), 'Skin Colour', SHIFT)
    if link.get(i) in PA:
        rec = put(hair(PA[link[i]]), 'Undershorts', 0)
        d[o + 12:o + 68] = rec[4:60]; d[o + 4] |= 0x0F                 # edited face, hair, physique, strip style
        written[i] = rec; now = get(rec, 'Skin Colour')
        log['appearance written from FL 27'] += 1; log['  of these: skin colour changed'] += was != now; log['  of these: skin colour changed by 2 steps or more'] += abs(was - now) >= 2
    elif P[i]['name'] in LEGEND_SKIN:
        b = put(block(d, i), 'Skin Colour', LEGEND_SKIN[P[i]['name']], SHIFT); d[o:o + 72] = b; d[o + 4] |= 0x01
        skinonly[i] = LEGEND_SKIN[P[i]['name']]; log['legend built by hand: skin colour only'] += 1
    else: log['no FL 27 record: left as it is'] += 1; rep['left'].append(P[i]['name']); continue
    for f in EFLAGS: P[i][f] = 1
    d[off(i) + 16:off(i) + 51] = pack17(P[i]); rep['done'].append((P[i]['name'], O[i]['name'], was, get(block(d, i), 'Skin Colour', SHIFT)))
assert len(skinonly) == len(LEGEND_SKIN), 'a hand-built legend was not found'
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(new.d) == len(pes.d) and list(N) == list(P), 'file size or players changed'
lo, hi = pes.P0, pes.P0 + pes.np * pes.PSZ
assert new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:], 'something outside the player records changed'
for i in P:
    a, b = pes.d[off(i):off(i) + pes.PSZ], new.d[off(i):off(i) + pes.PSZ]
    if i not in written and i not in skinonly: assert a == b, ('an untouched record changed', P[i]['name']); continue
    assert a[:16] == b[:16] and a[51:0x74 + 4] == b[51:0x74 + 4] and a[0x74 + 5:0x74 + 12] == b[0x74 + 5:0x74 + 12] and a[0x74 + 68:] == b[0x74 + 68:], ('identity changed', P[i]['name'])
    assert all(N[i][f] == 1 for f in EFLAGS) and all(N[i][k] == P[i][k] for k in P[i] if k not in EFLAGS + ('raw',)), ('abilities changed', P[i]['name'])
    blk = block(new.d, i)
    if i in skinonly: assert get(blk, 'Skin Colour', SHIFT) == skinonly[i] and blk[4] & 1; continue
    src = PA[link[i]]; assert blk[4] & 15 == 15
    for lab in FIELD:
        v = get(blk, lab, SHIFT)
        if lab == 'Undershorts': assert v == 0
        elif lab in HAIR: assert v == get(written[i], lab)
        else: assert v == get(src, lab), ('field differs from FL 27', P[i]['name'], lab)
    assert seen[tuple(get(blk, f, SHIFT) for f in HAIR[:4])] and not nohair(blk[8:]), ('hairstyle unknown to the 2017 file', P[i]['name'])
assert all(new.rosters[t] == pes.rosters[t] for t in pes.teams), 'a squad changed'

# ------------------------------------------------------------------ report
for k, v in log.items(): print('%-62s %d' % (k, v))
print('format check: %d same players, skin colour equal for %d, block identical for %d' % (len(same), eq, ident))
print('records holding another person than in the original save:', len(todo))
print('-- left', rep['left'])
print('-- sample (player, record was, skin before, skin now)'); [print('  ', x) for x in rep['done'][:25]]
print('bytes changed', sum(a != b for a, b in zip(pes.d, new.d)), '| self-check passed')
