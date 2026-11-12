"""Task 13: five new classic teams built from the Football Life 27 classic players that the file lacks.
  World Cup Heroes   -> the empty slot "The Old Boys" (23 players written over unused free agents; team renamed)
  Modern Champions   -> the made-up team "Pleasure Horn" (its 23 records rewritten in place; team renamed)
  FC Icons           -> ML Default Europe       \\
  UCL Legends        -> ML Default Asia          > the 28 records of each rewritten in place: player ids, roster,
  Cult Heroes        -> ML Default Latinamerica /  shirt numbers, line-up and team name stay, so Master League finds
                                                   its default squad where it always was
  rating: the FL 27 classic (prime) value, raised to the EA FC 27 icon / hero rating or to PRIME where that is higher.
Usage: python3 task13.py <in data.dat> <out data.dat>     (input: the output of task12.py)
"""
import sys, csv, struct, collections, unicodedata
from lib import *
import rate, fldb

SRC, OUT = sys.argv[1:3]
CLASSIC = (1458, 1459, 1460, 1462, 1463, 2703, 2704)          # the seven classic teams already in the file
FLCLASSIC = range(900, 911)                                   # the eleven classic teams of Football Life 27
# first 11 = starting eleven in the order of the slot's formation, then the bench
TEAMS = {
 4971: ('World Cup Heroes', 'WCH', ['GK', 'CB', 'CB', 'RB', 'LB', 'DMF', 'RWF', 'LWF', 'AMF', 'CF', 'CF'], """
    Walter Zenga, Daniel Passarella, Jürgen Kohler, Berti Vogts, Andreas Brehme, Paul Breitner, Mané Garrincha, Rob Rensenbrink,
    Gheorghe Hagi, Gerd Muller, Giuseppe Meazza,
    Ubaldo Fillol, René Higuita, Marco Materazzi, Fabio Grosso, Dino Baggio, Maxi Rodríguez, Ahn Jung-Hwan, Claudio Caniggia,
    Careca, Jürgen Klinsmann, Roger Milla, Hakan Sükür"""),
 1386: ('Modern Champions', 'MCH', None, """
    Rui Patrício, Mats Hummels, Giorgio Chiellini, Jesús Navas, Aleksandar Kolarov, Miralem Pjanić, Marek Hamšík, Dries Mertens,
    Lukas Podolski, Gonzalo Higuaín, Mario Mandžukić,
    Sergio Romero, Antonis Nikopolidis, Leonardo Bonucci, Jérôme Boateng, Diego Godín, João Miranda, Fernandinho, Blaise Matuidi,
    Mesut Özil, Arda Turan, Mario Gómez, Diego Costa"""),
 140: ('FC Icons', None, None, """
    Samir Handanovič, Jamie Carragher, Ricardo Carvalho, Gianluca Zambrotta, Ashley Cole, Juan Sebastián Verón, Claudio Marchisio,
    Michael Laudrup, Ricardo Quaresma, Gianfranco Zola, Hugo Sánchez,
    Maarten Stekelenburg, Łukasz Fabiański, Alessandro Florenzi, John Arne Riise, Gabriel Heinze, Philippe Mexès, Phillip Cocu,
    Lucas Leiva, Joe Cole, John Barnes, Gary Lineker, Hernán Crespo, Antonio Di Natale, Carlos Tévez, Henrik Larsson,
    Christian Vieri, David Trézéguet"""),
 2696: ('UCL Legends', None, None, """
    Hans van Breukelen, Sergio Ramos, Gerard Piqué, Dani Alves, Marcelo, Demetrio Albertini, Ivan Rakitić, Kevin Keegan, Nani,
    Alfredo Di Stefano, Eusébio,
    Diego López, Helton da Silva, Ruud Krol, Raphaël Varane, Kakhaber Kaladze, Frank de Boer, Sami Hyypiä, Giacinto Facchetti,
    Nuno Maniche, Thiago Alcântara, Lars Ricken, Alessandro Mazzola, Uli Hoeneß, Karl-Heinz Riedle, Nicolas Anelka,
    Jon Dahl Tomasson, Goran Pandev"""),
 2469: ('Cult Heroes', None, None, """
    Joe Hart, Daniel Agger, Fabricio Coloccini, José Bosingwa, Fábio Coentrão, Lassana Diarra, Sebastian Deisler, Diego Ribas,
    Brian Laudrup, Damien Duff, Vincenzo Montella,
    Kasper Schmeichel, Marco Storari, Daniel Van Buyten, Robert Huth, Yuri Zhirkov, Gary Neville, Felipe Melo, Marouane Fellaini,
    Emre Belözoğlu, Dimitri Payet, Keisuke Honda, Theo Walcott, Florent Malouda, Ezequiel Lavezzi, Adrian Mutu, Alexandre Pato,
    Jimmy Hasselbaink"""),
}
# prime ratings where FL 27 is clearly below the player's peak and EA has no icon card for him (peak FIFA rating, or stature)
PRIME = {'Alfredo Di Stefano': 93, 'Sergio Ramos': 91, 'Giorgio Chiellini': 90, 'Kevin Keegan': 90, 'Diego Godín': 89, 'Samir Handanovič': 89,
         'Mesut Özil': 89, 'Gonzalo Higuaín': 89, 'Marcelo': 89, 'Paul Breitner': 88, 'Giacinto Facchetti': 88, 'Daniel Passarella': 88, 'Dani Alves': 87}
SPELL = {'Gerd Muller': 'Gerd Müller', 'Alfredo Di Stefano': 'Alfredo Di Stéfano', 'Hakan Sükür': 'Hakan Şükür'}

pes = P17(SRC); P = pes.players; D, A, T = fldb.load()
d = bytearray(pes.d); rep = []

# ------------------------------------------------------------------ pool: FL 27 classic players by name
pool = collections.defaultdict(list)
for t in FLCLASSIC:
    for pid, _ in A[t]: pool[D[pid]['name']].append(pid)
icon = {}                                                     # EA FC 27 icon / hero rating by normalised name
for r in csv.DictReader(open(fldb.W + 'src/fc27repo/fc27_players_database.csv', encoding='utf-8-sig')):
    if any(k in r['rarity'] for k in ('Icon', 'Hero', 'Hall of FUT', 'Heritage')):
        for n in (r['player_name'], r['full_name']): icon[norm(n)] = max(icon.get(norm(n), 0), int(r['overall']))
def icon_rating(name):
    """Exact name, or every token of the shorter name inside the longer one (Marcelo = Marcelo Vieira da Silva)."""
    t = set(rate.toks(name)); best = icon.get(norm(name), 0)
    for k, v in ICONTOK:
        if len(t) >= 2 and len(k) >= 2 and (t <= k or k <= t): best = max(best, v)
    return best
ICONTOK = []
for r in csv.DictReader(open(fldb.W + 'src/fc27repo/fc27_players_database.csv', encoding='utf-8-sig')):
    if any(k in r['rarity'] for k in ('Icon', 'Hero', 'Hall of FUT', 'Heritage')): ICONTOK.append((set(rate.toks(r['player_name'])), int(r['overall'])))

plan = {t: [n.strip() for n in txt.replace('\n', ' ').split(',')] for t, (_, _, _, txt) in TEAMS.items()}
flat = [n for names in plan.values() for n in names]
assert len(flat) == len(set(flat)), [n for n, c in collections.Counter(flat).items() if c > 1]
classic_now = {norm(P[i]['name']) for t in CLASSIC for i, _ in pes.squad(t)}
for n in flat:
    assert len(pool.get(n, [])) == 1, ('not exactly one FL classic player', n, pool.get(n))
    assert norm(n) not in classic_now, ('already in a classic team', n)

# ------------------------------------------------------------------ records to write into
inroster = {pid for t in pes.teams for pid, _ in pes.squad(t)}
key = lambda s: frozenset(rate.toks(s))                       # word order does not matter (Min Ji-Hoon = Ji Hoon Min)
real = {key(q['name']) for q in D.values()} | {key(c[k]) for c in rate.fc27full() for k in ('name', 'short')} | {key(c['name']) for c in rate.fc26()}
donors = sorted((i for i, p in P.items() if i not in inroster and key(p['name']) not in real and rate.overall(p) <= 60),
                key=lambda i: (rate.overall(P[i]), i))        # unused free agents unknown to FL 27, EA FC 27 and FC 26, weakest first
def shirtname(name):
    t = unicodedata.normalize('NFKD', name).encode('ascii', 'ignore').decode().upper().split()
    return (t[-1] if t else '')[:15]

def write(i, name, slotpos):
    """Rewrite record i as the FL classic player `name`; id, motions and appearance of the record stay."""
    q = D[pool[name][0]]; p = P[i]; old = (p['name'], rate.overall(p)); o = pes.P0 + p['i'] * pes.PSZ
    p.update(fldb.to17(q)); base = rate.overall(p)
    tg = max(base, icon_rating(name), PRIME.get(name, 0))
    if slotpos: p['pp_' + slotpos] = 2                         # a starter is rated A where the formation puts him
    if rate.overall(p) != tg: assert rate.retarget(p, tg), (name, tg)
    disp = SPELL.get(name, name)
    struct.pack_into('<HBB', d, o + 10, q['nation'], q['height'], q['weight'])
    d[o + 16:o + 51] = pack17(p)
    d[o + 0x34:o + 0x34 + 46] = disp.encode('utf8')[:45].ljust(46, b'\0')
    d[o + 0x62:o + 0x62 + 18] = shirtname(disp).encode('latin1').ljust(18, b'\0')
    return dict(id=i, name=disp, old=old, fl=base, target=tg, pos=POS[p['reg_pos']], age=p['age'])

changed = set()
for t, (title, abbr, form, _) in TEAMS.items():
    X = pes.teams[t]; g = pes.plans[t]; names = plan[t]; r = pes.rosters[t]
    form = form or [POS[x] for x in g['presets'][0]['forms'][0]['pos']]
    if pes.squad(t):                                          # in place: slot k of the roster becomes name k
        ids = [pid for pid, _ in r if pid]
        assert len(ids) == len(names) and g['xi'] == list(range(11)), (title, len(ids), len(names))
    else:                                                     # empty slot: free records, roster and line-up are written
        ids = donors[:len(names)]; assert len(ids) == len(names), 'not enough free records'
        ro = pes.R0 + X['i'] * pes.RSZ; assert u32(d, ro) == t
        for k in range(32):
            struct.pack_into('<I', d, ro + 4 + 4 * k, ids[k] if k < len(ids) else 0); d[ro + 132 + k] = k + 1 if k < len(ids) else 0
        q = pes.G0 + X['i'] * pes.GSZ + 4 + 480; assert u32(d, pes.G0 + X['i'] * pes.GSZ) == t
        d[q:q + 32] = bytes(range(32))                         # line-up = roster order, as in every other team of the file
        d[q + 32:q + 38] = bytes([8] * 6); d[q + 41] = 1       # set pieces: the no. 10 (slot 8); captain: slot 1
    assert [POS[x] for x in g['presets'][0]['forms'][0]['pos']] == form, (title, 'formation changed')
    for k, (i, n) in enumerate(zip(ids, names)):
        x = write(i, n, form[k] if k < 11 else None); x.update(team=title, slot=k); rep.append(x); changed.add(i)
    if abbr:                                                  # Master League default teams keep their name
        to = pes.T0 + X['i'] * pes.TSZ
        d[to + 0x98:to + 0x98 + 0x46] = title.encode('utf8').ljust(0x46, b'\0'); d[to + 0xDE:to + 0xE2] = abbr.encode('latin1').ljust(4, b'\0')

open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check on the written file
new = P17(OUT); N = new.players
assert len(d) == len(pes.d) and new.porder == pes.porder
for i, p in pes.players.items():
    if i not in changed: assert N[i]['raw'] == p['raw'], ('an unplanned player changed', p['name'])
    else: assert N[i]['raw'][:10] == p['raw'][:10] and N[i]['raw'][0x74:] == p['raw'][0x74:], 'id or appearance changed'
for t in pes.teams:
    if t == 4971: continue
    assert new.rosters[t] == pes.rosters[t] and new.plans[t]['raw'] == pes.plans[t]['raw'], ('roster or line-up changed', t)
    if t != 1386: assert new.teams[t]['raw'] == pes.teams[t]['raw'], ('team record changed', t)
for t in (4971, 1386):
    a, b = pes.teams[t]['raw'], new.teams[t]['raw']; assert a[:0x98] == b[:0x98] and a[0xE2:] == b[0xE2:] and new.teams[t]['name'] == TEAMS[t][0]
assert new.plans[4971]['raw'][:484] == pes.plans[4971]['raw'][:484], 'formation of the empty slot changed'
seen = collections.Counter()
for t, (title, abbr, form, _) in TEAMS.items():
    sq = new.squad(t); g = new.plans[t]; fpos = [POS[x] for x in g['presets'][0]['forms'][0]['pos']]
    assert [N[i]['name'] for i, _ in sq] == [SPELL.get(n, n) for n in plan[t]], title
    assert len({num for _, num in sq}) == len(sq) and all(1 <= num <= 99 for _, num in sq), (title, 'shirt numbers')
    assert g['xi'] == list(range(11)) and POS[N[sq[0][0]]['reg_pos']] == 'GK' and sum(POS[N[i]['reg_pos']] == 'GK' for i, _ in sq) >= 3
    for k in range(11): assert N[sq[k][0]]['pp_' + fpos[k]] == 2, (title, N[sq[k][0]]['name'], fpos[k])
for t in list(TEAMS) + list(CLASSIC):
    for i, _ in new.squad(t): seen[norm(N[i]['name'])] += 1
assert max(seen.values()) == 1, [n for n, c in seen.items() if c > 1]
for x in rep:
    p = N[x['id']]; assert rate.overall(p) == x['target'] >= x['fl'] and p['pp_' + POS[p['reg_pos']]] == 2, x
allr = collections.Counter(pid for t in new.teams if not new.isclub(t) for pid, _ in new.squad(t))
assert max(allr.values()) == 1, 'a player sits in two national or classic teams'

# ------------------------------------------------------------------ report
for t, (title, *_ ) in TEAMS.items():
    rs = [x for x in rep if x['team'] == title]; xi = rs[:11]
    print('\n%s (slot %d, %s): %d players, eleven %.1f, squad %.1f' % (title, t, pes.teams[t]['name'], len(rs), sum(x['target'] for x in xi) / 11, sum(x['target'] for x in rs) / len(rs)))
    print('  XI   : ' + ', '.join('%s %d' % (x['name'], x['target']) for x in xi))
    print('  bench: ' + ', '.join('%s %d' % (x['name'], x['target']) for x in rs[11:]))
up = [x for x in rep if x['target'] > x['fl']]
print('\nraised above the FL 27 value (%d): ' % len(up) + ', '.join('%s %d>%d' % (x['name'], x['fl'], x['target']) for x in up))
print('records over free agents: ' + ', '.join('%s %d' % x['old'] for x in rep if x['team'] == 'World Cup Heroes'))
print('free records left', len(donors) - 23)
print('bytes changed', sum(1 for k in range(len(d)) if d[k] != pes.d[k]), 'players written', len(rep))
print('self-check passed')
