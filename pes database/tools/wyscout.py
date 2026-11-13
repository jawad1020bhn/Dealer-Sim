"""Wyscout league tables of 2026-27 and 2026 (btgriff/Wyscout_Data under $PES_WORK/src/wyscout, state of 12 November
2026): every player with minutes in one of 202 men's first-team competitions, with the team he played for, minutes,
positions and set-piece figures. Colombia and Iran are not covered.
  load()                 -> {wyscout id: player}; player['rows'] = one dict per team and competition
  link(players)          -> {file player id: wyscout player} (rate.match_cards on name, age, height, nation, club)
  clubs(squads, m)       -> {file team id: wyscout team name}, learned from the matched squad members
player['teams'] = the teams he has minutes for; player['now'] = the team he is at: his only team in the running
competitions, or the one their 'Team' columns agree on; None when they disagree.
"""
import csv, glob, os, re, collections, unicodedata
import rate
D = os.environ.get('PES_WORK', '/home/user/pes-work/') + 'src/wyscout/Main App/'
SKIP = re.compile(r'U1[5-9]|U2[0-3]|NCAA|NAIA|NJCAA|NCCA|Reserve|Next Pro|J[uú]niores|Sub 23|Primavera|Tineret|Premier League 2 ')
def num(x):
    try: return float(x)
    except ValueError: return 0.0
def load(seasons=('26-27', '2026')):
    out = {}
    for f in sorted(glob.glob(D + '*.csv')):
        comp = os.path.basename(f)[:-4]
        if comp.split(' Fall')[0].split()[-1] not in seasons or SKIP.search(comp): continue
        key = unicodedata.normalize('NFKD', comp).encode('ascii', 'ignore').decode()      # "Süper Lig" and "Super Lig" are one table
        for r in csv.DictReader(open(f, encoding='utf-8-sig')):
            if not r['Wyscout id'] or not r['Birthday'][:4].isdigit(): continue
            p = out.setdefault(r['Wyscout id'], dict(id=r['Wyscout id'], short=r['Player'], name=' '.join((r['Full name'] or r['Player']).split()), team=r['Team'].strip(),
                               age=2026 - int(r['Birthday'][:4]), height=int(num(r['Height'])), loan=r['On loan'],
                               nation=(re.findall(r"'([^']+)'", r['Passport country']) or [r['Birth country']])[0], rows=[]))
            row = dict(key=key, comp=comp, team=r['Team within selected timeframe'].strip(), min=int(num(r['Minutes played'])), r=r)
            old = [x for x in p['rows'] if (x['key'], x['team']) == (key, row['team'])]
            if old and old[0]['min'] >= row['min']: continue
            if old: p['rows'].remove(old[0])
            p['rows'].append(row)
    who = collections.defaultdict(lambda: collections.defaultdict(set))       # one name, two clubs (Everton of England and of Chile)
    for p in out.values():
        for x in p['rows']: who[x['team']][x['key']].add(p['id'])
    ren = {}
    for name, comps in who.items():
        ks = sorted(comps, key=lambda k: -len(comps[k])); main = set(comps[ks[0]])
        for k in ks[1:]:
            if comps[k] & main: main |= comps[k]
            else: ren[(name, k)] = name + ' (' + k + ')'
    for p in out.values():
        for x in p['rows']: x['team'] = ren.get((x['team'], x['key']), x['team'])
    for p in out.values():
        p['teams'] = {x['team'] for x in p['rows']}
        live = [x for x in p['rows'] if '100 Year Vision' not in x['comp']] or p['rows']      # Japan's spring league ended in June
        ts = {x['team'] for x in live}; col = {x['r']['Team'].strip() for x in live}
        p['now'] = next(iter(ts)) if len(ts) == 1 else next(iter(col)) if len(col) == 1 and col <= ts else None
    return out
def minutes(w, team): return sum(x['min'] for x in w['rows'] if x['team'] == team)
def link(W, players):
    cards = [dict(id=w['id'], name=w['name'], short=w['short'], ovr=int(w['id']), club=w['now'] or w['team'], league=w['rows'][0]['comp'], age=w['age'],
                  height=w['height'], pos='', nation=w['nation'], w=w) for w in W.values()]
    m = rate.match_cards(cards, players); link.ev = dict(rate.match_cards.ev)
    return {i: c['w'] for i, c in m.items()}
def second(n, other):
    """`other` is a second team of the club n (Freiburg II, Barcelona Atlètic, Jong Ajax, Melbourne City U21)."""
    n = n.split(' (')[0]
    return other != n and (other.startswith(n + ' ') or other == 'Jong ' + n or (n in other and other.split()[-1] in ('II', 'B', 'U21', 'U23'))
                           or other in SECOND.get(n, ()))
SECOND = {'Deportivo La Coruña': ('Deportivo Fabril',), 'Real Betis': ('Betis Deportivo',), 'Athletic Club': ('Athletic Bilbao',)}
NAMED = {'Spezia Calcio': 'Spezia', 'Mondihome Kayserispor': 'Kayserispor', 'SD Huesca': 'Huesca', 'CD Mirandés': 'Mirandés', 'Amiens SC': 'Amiens SC',
         'Cultural y Deportiva Leonesa': 'Cultural Leonesa', 'Nakhonratchasima FC': 'Nakhon Ratchasima', 'Kanchanaburi Power FC': 'Kanchanaburi Power'}
def clubs(squads, m):
    """squads: {team id: [player ids]}. A club is the Wyscout team most of its matched members have minutes for (5 or
    more); if that is a second team and the first team has 5 too, the first team."""
    out = {}
    for t, ids in squads.items():
        c = collections.Counter(x for i in ids if i in m for x in m[i]['teams']); top = c.most_common(1)
        if top and top[0][1] >= 5: out[t] = next((n for n in c if c[n] >= 5 and second(n, top[0][0]) and top[0][0].split()[-1] != 'B'), top[0][0])
    return out
