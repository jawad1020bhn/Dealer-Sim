"""The year plan of the career modes (Master League, Become a Legend, League).

    python3 yearplan.py <PES2017.exe> [july|january]      # prints the Master League year

The exe holds one table of 169 rows (0x0216bc20, 0x14 bytes a row): month, day,
event number, two mode flags and the kind of season. On the first day of a
season the game walks the 365 days and writes the events of each day into the
mode's calendar (fcn_035d8b2e -> fcn_038b0b21). `events()` is fcn_038b0b21 in
Python; `check_findings.py` compares it with the game's code for every day.

The dates are checked against the game's code. The meanings in WHAT are not: they
are from the code that asks for each number, and "not read" marks the ones where
only the asking function is known.
"""
import struct
import sys

from layout import load, off

TABLE, ROWS, ROW = 0x0216bc20, 169, 0x14
ML, BL, LEAGUE = 0xc, 0xd, 0xb                       # mode kinds (table 0x0251d408)
DRAWS = (0x20, 0x21, 0x22, 0x23, 0x24, 0x25, 0x26, 0x27)

WHAT = {
    1: 'first day of the season: the year plan is written',
    3: 'first transfer window opens',
    4: 'day before the first window closes (the daily scout step is left out)',
    5: 'first transfer window closes',
    6: 'second transfer window opens',
    7: 'day before the second window closes (the daily scout step is left out)',
    8: 'second transfer window closes',
    9: 'window day: the daily negotiation and transfer steps run',
    10: 'asked by fcn_0364c065 and the staff report (not read)',
    11: 'asked by fcn_0364b81c (not read)',
    12: 'half-year step of fcn_036e1665 (not read)',
    13: 'half-year step of fcn_036e067a, fcn_036e1568 (not read)',
    14: 'half-year step of fcn_036e1665 (not read)',
    15: 'half-year step of fcn_036e067a, fcn_036e1568 (not read)',
    16: 'asked by the staff report and a transfer news function (not read)',
    17: 'asked by fcn_036f5728 (not read)',
    19: 'taken to be a national team day (six a year)',
    20: 'the day after event 19',
    22: 'asked by fcn_0314910f only (not read)',
    23: 'last day of the season: season-end processing',
    24: 'asked by fcn_03649f1f, 616 lines (taken to be the closing of the accounts)',
    25: 'money step fcn_03640d19; asked by process::ProcessCmnFinanceReportCheck',
    26: 'asked by fcn_0366f4bb and news functions (not read)',
    27: 'asked by fcn_0366f4bb and news functions (not read)',
    28: 'asked by fcn_0366f4bb and news functions (not read)',
    29: 'asked by fcn_0366f4bb and news functions (not read); only with a mode flag set',
    30: 'day after a window closes: computer clubs plan their squads (fcn_036602e5)',
    31: 'asked by fcn_03676016 (not read)',
    32: 'draw day (process::ProcessCmnLotCheck)', 33: 'draw day (process::ProcessCmnLotCheck)',
    34: 'draw day (process::ProcessCmnLotCheck)', 35: 'draw day (process::ProcessCmnLotCheck)',
    36: 'draw day (process::ProcessCmnLotCheck)', 37: 'draw day (process::ProcessCmnLotCheck)',
    38: 'draw day (process::ProcessCmnLotCheck)', 39: 'draw day (process::ProcessCmnLotCheck)',
    41: 'title step of fcn_0362eb70, fcn_036696e1 (process::SpecialTitle, not read)',
    42: 'title step of fcn_0362eb70 (process::SpecialTitleSetUEFA, not read)',
    43: 'title step of fcn_0362eb70, fcn_036696e1 (not read)',
    44: 'title step of fcn_0362eb70, fcn_036696e1 (not read)',
    45: 'asked by fcn_03676016 (not read)',
    48: 'report step fcn_0363beba (writes a staff report; not read)',
    49: 'money step fcn_03640d19',
}


def rows(d):
    """[(month, day, event, career only, Master League only, extra, season kind)]"""
    res = []
    for i in range(ROWS):
        o = off(TABLE) + i * ROW
        month, _, day, event, career, ml_only, _, extra, season = struct.unpack_from('<BBHIBBHII', d, o)
        res.append((month, day, event, career, ml_only, extra, season))
    return res


def events(table, mode, january_season, year, month, day, flag_29=0, no_draws=0, league_flag=0, flag_48=0):
    """Events of one day, in table order. january_season: False = the season starts on
    1 July, True = on 1 January (always True outside the three career modes).
    The four flags are bytes of the mode data (0xdcb686, 0xdc9d78 == 0x56, 0xdc9cbc, 0xddce71)."""
    season = 1 if mode not in (LEAGUE, ML, BL) or january_season else 0
    res = []
    for m, dd, event, career, ml_only, extra, kind in table:
        if m != month or dd != day or kind not in (3, season):
            continue
        if mode == BL:
            if ml_only:
                continue
        elif mode != ML and career:
            continue
        if event == 0x1d and not flag_29:
            continue
        if event in DRAWS and (no_draws or (mode not in (ML, BL) and league_flag >= 2)):
            continue
        if event in (0x13, 0x14) and year & 3 == 1 and month in (5, 6):
            continue
        if event == 0x30 and flag_48 and month in (2, 9):
            continue
        res.append(event)
    return res


def main(argv):
    if len(argv) < 2:
        sys.exit(__doc__)
    table = rows(load(argv[1]))
    january = len(argv) > 2 and argv[2].startswith('jan')
    order = list(range(1, 13)) if january else list(range(7, 13)) + list(range(1, 7))
    print('%s season, Master League. Event 9 (%s) is on every day of July, August and January.\n'
          % ('January' if january else 'July', WHAT[9]))
    for month in order:
        for day in range(1, 32):
            for e in events(table, ML, january, 2016, month, day):
                if e != 9:
                    print('%2d/%-2d  %2d  %s' % (day, month, e, WHAT.get(e, '?')))

if __name__ == '__main__':
    main(sys.argv)
