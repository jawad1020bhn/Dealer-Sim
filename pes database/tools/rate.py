"""PES 2017 overall: the PES 2016 formula documented in the4chancup/unlimited-tool-works overall.rs, with three
changes fitted on this file (98% of 5,400 FC 27 matched players exact, the rest are wrong name matches): the
row weighted DMF 12 reads swerve, the row weighted LWF/RWF 5 reads kicking power, and the body row reads the
mean of body control and physical contact. Also the
EA FC 27 / FC 26 rating tables with a name + age + height match to file players."""
import csv, os, unicodedata, collections
from lib import POS, norm
W = os.environ.get('PES_WORK', '/home/user/pes-work/')
ROWS = [('atk', [0, 0, 6, 6, 7, 5, 7, 7, 14, 17, 17, 15, 31]), ('ball_ctrl', [0, 0, 10, 10, 18, 24, 15, 15, 24, 19, 19, 19, 24]),
        ('drib', [0, 0, 14, 14, 15, 24, 25, 25, 24, 22, 22, 19, 14]), ('lowpass', [0, 0, 0, 0, 18, 24, 7, 7, 22, 5, 5, 9, 0]),
        ('loftpass', [0, 0, 14, 14, 19, 21, 12, 12, 14, 9, 9, 9, 0]), ('finish', [0, 0, 0, 0, 0, 0, 0, 0, 17, 11, 11, 14, 36]),
        ('place_kick', [0] * 13), ('swerve', [0, 0, 0, 0, 12, 0, 4, 4, 0, 0, 0, 0, 0]), ('header', [0, 23, 0, 0, 0, 0, 0, 0, 0, 0, 0, 0, 3]),
        ('def', [0, 26, 14, 14, 8, 3, 0, 0, 0, 0, 0, 0, 0]), ('ball_win', [0, 26, 13, 13, 4, 0, 0, 0, 0, 0, 0, 0, 0]),
        ('kick_pwr', [0, 0, 0, 0, 0, 0, 0, 0, 0, 5, 5, 6, 3]), ('speed', [0, 10, 16, 16, 3, 4, 24, 24, 5, 15, 15, 9, 5]),
        ('exp_pwr', [0, 0, 14, 14, 3, 6, 22, 22, 7, 15, 15, 22, 5]), ('BODY', [11, 20, 12, 12, 13, 5, 0, 0, 5, 6, 6, 7, 9]),
        ('jump', [11, 20, 12, 12, 5, 0, 0, 0, 0, 0, 0, 0, 3]), ('GK1', [49] + [0] * 12), ('GK2', [49] + [0] * 12),
        ('stamina', [0, 9, 14, 14, 14, 17, 13, 13, 3, 6, 6, 4, 0]), ('ONE', [0, 24, 58, 58, 24, 24, 56, 56, 38, 47, 47, 38, 38])]
REGISTERED = [8, 8, 9, 9, 9, 8, 8, 8, 8, 10, 10, 9, 8]; RATED_A = [5, 5, 4, 4, 4, 5, 5, 5, 5, 4, 4, 5, 5]; RATED_B = [3, 3, 2, 2, 2, 3, 3, 3, 3, 2, 2, 3, 3]
BLEND = [0] * 40 + list(range(31, 53)) + [56, 59, 62, 65, 67, 70, 73, 75, 77, 79, 82, 83, 85, 87, 89, 90, 92, 93, 94, 95] + list(range(96, 114))
assert len(BLEND) == 100
def term(p, k):
    if k == 'BODY': return (p['body_ctrl'] + p['phys']) // 2
    if k == 'GK1': return (p['gk'] + p['cover']) // 2
    if k == 'GK2': return (p['catching'] + p['clearing'] + p['reflex']) // 3
    if k == 'ONE': return 1
    return p[k]
def overall(p, pos=None):
    reg = p['reg_pos']; col = reg if pos is None else pos
    s = sum(w[col] * max(1, term(p, k) - 25) for k, w in ROWS)
    if col == reg: bonus = REGISTERED[col]
    else: bonus = (0, RATED_B[col], RATED_A[col], RATED_A[col])[p['pp_' + POS[col]]]
    o = (s + 50) // 100 + bonus
    if col == reg and col != 0:
        mean = min(99, (sum(term(p, k) for k, _ in ROWS[:19]) * 100 // 19 + 50) // 100)
        o = (o * 60 + 50 + BLEND[mean] * 40) // 100
    return max(40, min(109, o))

# ---- EA FC tables
def toks(s):
    s = unicodedata.normalize('NFKD', s.replace('-', ' ').replace("'", ''))
    return [norm(t) for t in s.split() if norm(t)]
WOMEN = ('Women', 'Frauen', 'Liga F', 'Arkema', 'Femminile', 'Vrouwen', 'Feminino', 'Žen')
def fc27():
    """Base cards of men's players: list of dicts name, overall, club, age, height."""
    out = {}
    for r in csv.DictReader(open(W + 'src/fc27repo/fc27_players_database.csv', encoding='utf-8-sig')):
        if r['rarity'] != 'Rare' or not r['overall'] or any(w in r['league'] + r['club'] for w in WOMEN): continue
        out[r['eaId']] = dict(name=r['full_name'] or r['player_name'], short=r['player_name'], ovr=int(r['overall']), club=r['club'], league=r['league'],
                              age=int(r['age'] or 0), height=int(r['height'][:3]) if r['height'][:3].isdigit() else 0, pos=r['positions'])
    return list(out.values())
def fc26():
    out = []
    for r in csv.DictReader(open(W + 'src/fc26.csv', encoding='utf-8')):
        out.append(dict(name=r['long_name'], short=r['short_name'], ovr=int(r['overall']), club=r['club_name'], league=r['league_id'],
                        age=int(r['age']) + 1, height=int(r['height_cm']), pos=r['player_positions'], dob=r['dob']))   # +1: one season later
    return out
class Index:
    """Finds the card of a file player: surname token equal, first name or initial compatible, age within 1, height within 3."""
    def __init__(s, cards):
        s.by = collections.defaultdict(list)
        for c in cards:
            c['t'] = toks(c['name']); c['ts'] = toks(c['short'])
            for t in set(c['t'] + c['ts']): s.by[t].append(c)
    def find(s, name, age, height, club=''):
        t = toks(name)
        if not t: return None
        best = []
        for c in {id(c): c for k in t if len(k) > 1 for c in s.by.get(k, [])}.values():
            if abs(c['age'] - age) > 1 or (c['height'] and abs(c['height'] - height) > 3): continue
            full = set(c['t']) | set(c['ts'])
            hit = [k for k in t if len(k) > 1 and k in full]
            if not hit: continue
            rest = [k for k in t if k not in hit]
            ok = all(any(f.startswith(k) if len(k) == 1 else len(f) > 1 and (f.startswith(k) or k.startswith(f)) for f in full) for k in rest)   # initials, short first names
            if len(t) == 1: ok = len(c['ts']) == 1 or t[0] == c['t'][-1] or t[0] in c['ts']
            if not ok: continue
            sc = 2 * len(hit) + (c['age'] == age) + (c['height'] == height) + 2 * bool(club and (norm(club) in norm(c['club']) or norm(c['club']) in norm(club)))
            if len(t) >= 2 and len(hit) < 2 and not rest: continue
            best.append((sc, c))
        if not best: return None
        best.sort(key=lambda x: -x[0])
        if len(best) > 1 and best[0][0] == best[1][0] and best[0][1]['ovr'] != best[1][1]['ovr']: return None
        return best[0][1]
    def loose(s, name, age, height, ovr):
        """A card with this very rating, the same age and either two shared name tokens or one plus a similar height:
        the rating was taken from that card, even where find() is too strict."""
        t = set(toks(name))
        for c in {id(c): c for k in t if len(k) > 3 for c in s.by.get(k, [])}.values():
            if c['ovr'] != ovr or abs(c['age'] - age) > 1: continue
            if len(t & (set(c['t']) | set(c['ts']))) >= 2 or not c['height'] or abs(c['height'] - height) <= 6: return c

if __name__ == '__main__':      # self-check: python3 rate.py <decrypted data.dat> -> share of FC 27 matched players rated exactly
    import sys
    from lib import P17
    I = Index(fc27()); m = [(p, I.find(p['name'], p['age'], p['height'])) for p in P17(sys.argv[1]).players.values()]
    m = [(p, c) for p, c in m if c]; ok = sum(overall(p) == c['ovr'] for p, c in m)
    print('overall == FC 27 for %d of %d matched players' % (ok, len(m))); assert ok > 0.95 * len(m)
