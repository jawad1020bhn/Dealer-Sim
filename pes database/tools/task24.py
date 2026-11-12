"""Task 24: club managers as of 12 November 2026 (table `NAMED`: team id, club, manager, nationality code).
Source: the Transfermarkt 2026/27 manager lists of the Premier League, La Liga, Serie A, Bundesliga and Ligue 1 (all
clubs), checked against the "managerial changes" tables of the English and French Wikipedia season pages; plus the
second-division lists (Championship, 2. Bundesliga and the later parts of LaLiga2, Serie B and Ligue 2).
Only the clubs whose manager in the file differs are listed. A club without a head coach keeps the last one
(Manchester United and Crystal Palace are untouched, Lens gets the coach sacked on 10 November).
Usage: python3 task24.py <in data.dat> <out data.dat>          (ends with a self-check of the written file)
"""
import sys, struct
from lib import P17, u32

SRC, OUT = sys.argv[1:3]
ESP, ITA, GER, FRA, ENG, SCO, SUI, MEX, CMR = 236, 215, 210, 208, 204, 232, 238, 124, 50
NAMED = [
    # ---- the five leagues
    (110, 'Valencia', 'Javier Aguirre', MEX),                # Corberán out, September 2026
    (259, 'Espanyol', 'Eder Sarabia', ESP),                  # October 2026
    (263, 'Osasuna', 'Jagoba Arrasate', ESP),                # October 2026
    (123, 'Parma', 'Alberto Gilardino', ITA),                # September 2026
    (186, 'Bologna', 'Raffaele Palladino', ITA),             # September 2026
    (190, 'Udinese', 'Paolo Zanetti', ITA),                  # November 2026
    (4229, 'Venezia', 'Davide Nicola', ITA),                 # October 2026
    (1919, 'Sassuolo', "Roberto D'Aversa", ITA),             # November 2026
    (225, 'gladbach', 'Alexander Blessin', GER),             # September 2026
    (181, 'Lyonnais', 'Carlos Vicens', ESP),                 # 10 November 2026, Fonseca resigned
    (182, 'Lens', 'Yannick Cahuzac', FRA),                   # sacked 10 November 2026, post vacant
    (413, 'Havre', 'Jaïr Karam', FRA),                       # interim since 31 October 2026
    (213, 'Lille', 'Davide Ancelotti', ITA),                 # name was right, nationality said Brazil
    (178, 'Fulham', 'Álvaro Arbeloa', ESP),                  # spelling only
    # ---- second divisions
    (105, 'West Ham', 'Scott Parker', ENG),
    (378, 'Burnley', 'Fabio Celestini', SUI),
    (4192, 'Preston', 'Graham Alexander', SCO),
    (232, 'Wolfsburg', 'Tobias Strobl', GER),
    (4139, 'St. Pauli', 'Marcel Rapp', GER),
    (4260, 'Oviedo', 'Raúl González', ESP),
    (364, 'Las Palmas', 'Albert Sánchez', ESP),
    (4272, 'Leganés', 'Luis Carrión', ESP),
    (4308, 'Cádiz', 'Borja Jiménez', ESP),
    (4302, 'Albacete', 'Joseba Etxeberria', ESP),
    (5895, 'Ceuta', 'Sergio Lobera', ESP),
    (4220, 'Cremonese', 'Fabio Pecchia', ITA),
    (235, 'Empoli', 'Matteo Andreoletti', ITA),
    (4218, 'Carrarese', 'Guido Pagliuca', ITA),
    (240, 'Sampdoria', "Luca D'Angelo", ITA),
    (4233, 'Catanzaro', 'Michele Mignani', ITA),
    (4123, 'Metz', 'Grégory Proment', FRA),
    (4206, 'Dunkerque', 'Pierre Webó', CMR),
]

pes = P17(SRC); d = bytearray(pes.d); rep = []
assert len({t for t, *_ in NAMED}) == len(NAMED)
for t, club, name, nat in NAMED:
    X = pes.teams[t]; assert club in X['name'] and pes.isclub(t), (t, X['name'])
    m = pes.managers[u32(X['raw'], 4)]; o = pes.M0 + m['i'] * 88; b = name.encode('utf8')
    n = max(len(b), len(m['name'].encode('utf8'))) + 1; assert n <= 60
    struct.pack_into('<H', d, o + 4, nat); d[o + 9:o + 9 + n] = b.ljust(n, b'\0')
    if (m['name'], m['nat']) != (name, nat): rep.append((X['name'], m['name'], m['nat'], name, nat))
open(OUT, 'wb').write(d)

# ------------------------------------------------------------------ self-check of the written file
new = P17(OUT); want = {t: (name, nat) for t, _, name, nat in NAMED}; mine = set()
for t, (name, nat) in want.items():
    m = new.managers[u32(new.teams[t]['raw'], 4)]; mine.add(m['i'])
    assert (m['name'], m['nat']) == (name, nat), (t, m)
assert len(mine) == len(NAMED)                              # no two clubs share a record
lo, hi = pes.M0, pes.M0 + 88 * (max(m['i'] for m in pes.managers.values()) + 1)
assert len(new.d) == len(pes.d) and new.d[:lo] == pes.d[:lo] and new.d[hi:] == pes.d[hi:]
for i in range((hi - lo) // 88):                            # every other manager record is byte-identical
    o = lo + i * 88; assert i in mine or new.d[o:o + 88] == pes.d[o:o + 88], i
for i in mine:                                              # only nationality and name bytes moved
    o = lo + i * 88; assert new.d[o:o + 4] == pes.d[o:o + 4] and new.d[o + 6:o + 9] == pes.d[o + 6:o + 9]
for club, old, onat, name, nat in rep:
    print(f'{club:32} {old} ({onat})  ->  {name} ({nat})')
print(f'self-check passed: {len(rep)} of {len(NAMED)} listed managers changed, {sum(a != b for a, b in zip(new.d, pes.d))} bytes')
