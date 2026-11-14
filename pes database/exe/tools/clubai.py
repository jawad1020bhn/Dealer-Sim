"""Numbers of the transfer code of the computer clubs in PES 2017 Master League.

Overall window of the players a computer club looks for, by the club's level 0 to 9
(fcn_0365d12d lowest, fcn_0365d08d highest). A level outside 0 to 9 gives the window
of level 0. Checked against the game's machine code by check_findings.py (check 11).
What the level is (byte +0xe of the record fcn_031b1c34 returns for the club) is read,
not proven; MASTER_LEAGUE.md section 9.
"""
LEVEL_MIN = (47, 51, 55, 59, 63, 67, 70, 73, 76, 83)
LEVEL_MAX = (74, 75, 76, 77, 78, 79, 80, 83, 86, 99)
SQUAD_LIMIT = 32            # a club stops looking when squad + open slots reach this


def window(level):
    """(lowest, highest) overall a club of this level looks for."""
    if not 0 <= level <= 9:
        level = 0
    return LEVEL_MIN[level], LEVEL_MAX[level]
