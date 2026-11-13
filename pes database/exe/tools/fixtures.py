"""League fixture plan of PES 2017 (process::LeagueCreation, fcn_03774725 and fcn_037741b4), in Python.

    python3 fixtures.py <number of teams>        print the rounds of a home-and-away league

`plan(n)` returns the table the game builds for a league of n teams that play each other
twice: cell [a][b] is the round (from 0) in which team a is the first team of the match
against team b; a and b are places in the competition's team list. `rounds(n)` turns the
table into a list of rounds, each a list of (first team, second team).
Checked against the game's machine code by check_findings.py (check 10).
The first team is written into the match record before the second; that it is the home
side is read from the code, not tested in the game.
"""
import sys

# Leagues of four teams do not use the rule below; the game writes this table (fcn_03773791).
FOUR = ((-1, 4, 1, 2),
        (0, -1, 2, 5),
        (5, 3, -1, 0),
        (3, 1, 4, -1))

def half_rounds(n):
    """Rounds in one half of the season: n - 1, or n when the number of teams is odd."""
    return n - 1 + (n & 1)


def raw(n):
    """Step 1: the circle method. Two rows of teams; each round pairs the teams that stand
    above each other, then all but the first place move one step round the ring. With an odd
    number of teams the first place of the top row is empty and the team below it rests."""
    odd = n & 1
    half = n // 2 + odd
    top = list(range(-odd, half - odd))
    bottom = list(range(half - odd, n))
    count = half_rounds(n)
    table = [[-1] * n for _ in range(n)]
    for r in range(count):
        for k in range(odd, half):
            a, b = top[k], bottom[k]
            table[a][b] = r                 # first half of the season
            table[b][a] = count + r         # second half: the same match, sides changed
        if half > 1:
            moved = top[1]
            top[1:] = top[2:] + [bottom[-1]]
            bottom[:] = [moved] + bottom[:-1]
    return table


def plan(n):
    """Step 2: every third and every seventh round (counted from 1) changes place with the
    same round of the second half, so no team stays first team for a whole half."""
    if n == 4:
        return [list(row) for row in FOUR]
    table = raw(n)
    count = half_rounds(n)
    for r in range(count):
        if (r + 1) % 3 == 0 or (r + 1) % 7 == 0:
            for row in table:
                for i, v in enumerate(row):
                    if v == r:
                        row[i] = count + r
                    elif v == count + r:
                        row[i] = r
    return table


def rounds(n):
    table = plan(n)
    out = [[] for _ in range(2 * half_rounds(n))]
    for a in range(n):
        for b in range(n):
            if table[a][b] >= 0:
                out[table[a][b]].append((a, b))
    return out


if __name__ == '__main__':
    for number, matches in enumerate(rounds(int(sys.argv[1])), 1):
        print('round %2d: %s' % (number, '  '.join('%d-%d' % (a + 1, b + 1) for a, b in matches)))
