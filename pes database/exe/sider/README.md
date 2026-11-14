# Sider Lua modules for Master League

Modules for the Sider that ships in `pes.7z` (`sider.dll` of 20 February 2022, Lua
enabled in `sider.ini`). They work on the running game; `PES2017.exe` is not edited.

| file | what it does |
|---|---|
| `MLCheck.lua` | **read-only test.** Reads the overall window of computer clubs by level (section 9.4 of `../MASTER_LEAGUE.md`) and four numbers of the transfer fee formula (section 6.2) from the running game and writes them to `sider.log`. It writes nothing to the game |
| `test_module.py <PES2017.exe>` | runs `MLCheck.lua` outside the game against the bytes of the exe file (needs `pip install lupa`) |
| `MLMoney.lua` | **changes the game.** Player values by rating, age, talent, position and popularity, salaries, the transfer budget of a new career, the yearly income of the club, cup and league prizes, from tables at the top of the file. Checks the game's code first and writes nothing if it differs. Version 2 ran in the game and version 5 was played by hand (no log); versions 3, 4, 6 and 7 have run in the emulator only |
| `MLTransfers.lua` | **changes the game.** The transfers between computer clubs; version 1 holds the price ceiling, which was a part of `MLMoney.lua` up to its version 6. Needs `MLMoney.lua` (version 7) in the line above its own in `sider.ini`. Has run in the emulator only |
| `money_cave.py` | what the two modules write (13 small routines, with their source) and the same arithmetic as Python |
| `test_money.py <PES2017.exe>` | runs `MLMoney.lua` and then `MLTransfers.lua` on the exe in the emulator, then runs the game's salary, fee, budget, prize and income code with the changes in and compares it with `money_cave.py` (needs `pip install lupa unicorn`) |

## Install and run `MLCheck.lua`

1. Copy `MLCheck.lua` into the `modules` folder next to `sider.exe`.
2. Add this line to `sider.ini`, below the other `lua.module` lines:
   `lua.module = "MLCheck.lua"`
3. Start the game with Sider as usual, wait for the title screen, quit.
4. Open `sider.log` (next to `sider.exe`) and look for the lines with `MLCheck`.

Expected, on the exe of this repository:

```
MLCheck 1: read-only test, nothing is written to the game
club level       0  1  2  3  4  5  6  7  8  9
lowest overall  47 51 55 59 63 67 70 73 76 83   as expected
highest overall 74 75 76 77 78 79 80 83 86 99   as expected
fee: rating step 68             at 038ab8db = 83f844   as expected
fee: 9,000 per rating point     at 038ab8e6 = 69ff28230000   as expected
fee: factor 0.00027             at 0216ba48 = 00000020d9b1313f   as expected
fee: factor 2.2                 at 01f0f2b8 = 000000a099990140   as expected
RESULT: 6 of 6 as expected. The running game has the code the notes describe, at the same addresses.
```

To remove it, delete the line from `sider.ini`.

What the result means:

- **6 of 6**: the running game holds the same code at the same addresses as the exe
  file that was analysed. A module that changes these numbers can be tried next.
- **`DIFFERENT` or `??`**: the game that runs is not this exe, or its code is changed
  in memory. No tuning module made from these notes should be used.
- **No `MLCheck` line at all**: look for `MLCheck.lua` in `sider.log`. Sider writes
  there why it skipped the module (file not found, error in `init`).

## Result in the game (14 November 2026)

`MLCheck.lua` ran on the user's PC under Sider 3.6.0: **6 of 6 as expected**, with the
same nine lines as above. So the running game holds the analysed code at the analysed
addresses, and a Sider module reads it without trouble.

What else the same `sider.log` shows:

- `luajit.ext.enabled = 0`: modules have no `ffi`, `bit` or `require`. Modules here must
  not need them.
- Sider itself uses `0x026503E0` (`_tid_addr1`), the pointer `MASTER_LEAGUE.md` calls the
  mode object, and `0x04062701`, the competition id table function. Two addresses of the
  notes confirmed from another side.
- Sider changes code at 31 places of the running game (hooks and small patches). None of
  them lies in one of the 133 functions that `../names.tsv` named when this was checked,
  so the salary, fee, fixture and computer-club code runs as analysed. The eight names
  added later (prize money, account lines) were not checked against the 31 places, and
  the 31 addresses are not kept here. `MLMoney.lua` settles it at run time: it compares
  every piece of code it relies on with the exe file before it writes, so a place Sider
  had changed would show as `DIFFERENT` and nothing would be written.
- Sider's gameplay settings point at the constants `0x01F0F2A8` and `0x01F0F2C0`, the
  neighbours of the shared 2.2 at `0x01f0f2b8`. One more reason not to change that
  constant in place.
- Three other modules of that install are not active, for reasons of their own:
  `Script_Stadiums.lua` (file `map_teams.txt` missing), `PlayerDump.lua` (calls
  `memory.search_process`, which this Sider does not have) and `GrowthBridge.lua` (asks
  for events this Sider does not know: `key_down`, `overlay_on`, `set_teams`,
  `gamepad_input`).

## `MLMoney.lua`, version 7, and `MLTransfers.lua`, version 1: values, salaries, budgets, income, prize money, and what a computer club can afford

**Two files since version 7.** `MLMoney.lua` holds the money: values, salaries,
budgets, income, prizes. `MLTransfers.lua` holds the transfers between computer clubs:
today the price ceiling (every setting whose name starts with `CEILING`), moved out of
`MLMoney.lua` without a change. The bytes written to the game and their addresses are
those of version 6, except for the four letters of the mark (`MLM7`). The reasons for
the second file: the money settings are finished and are not touched by the coming
transfer work, a fault in one file does not stop the other, and the transfers can be
switched off by taking one line out of `sider.ini`. Both run once, when the game
starts, and cost nothing during play.

`MLTransfers.lua` needs `MLMoney.lua`: its routine calls the value routine of
`MLMoney.lua` to price a player. Sider runs the modules in the order of their
`lua.module` lines, so the line of `MLMoney.lua` must stand above. `MLTransfers.lua`
looks for the mark of `MLMoney.lua` in the memory and compares the value routine
(1,376 bytes) and the number 100 it uses with what version 7 writes; if they are not
there, or differ, it writes nothing and says so. `MLMoney.lua` alone works as before.
A setting `WRITE` stands in both files; each rules its own file.

### What the game does without it

`../MASTER_LEAGUE.md` section 6. The value of a player is
`salary x (2.2 to 3.3) + 9,000 x (rating - 68)`, and the screens show 100 times the
stored amount. There is no age and no position in it, and it rises in a straight line
with the rating. From the formula, for a club high in the ranking: rating 80 about 16
million, 85 about 23 million, 94 about 40 million. The one player measured in the user's
career, Bruno Fernandes (rating 89, captain's bonus in his salary), showed 36,743,200.

When a career starts, the transfer budget of the user's club is twice the mean value of
its 16 best players, and the salary budget is the wage bill plus twice the mean salary
of its 16 best paid players (section 6.4).

A cup pays once, when the club is out or has won: 8 million for winning the Champions
League, half a million for going out in its group stage. A first division pays 15
million for place 1 down to 0.3 million. The money goes to the club's balance; neither
budget gets any of it (section 6.7). The first club of the game's club ranking pays twice
the salary of a club outside the first 250. A player of 23 or younger signs for 3 years
at most (section 7.3).

On the first day of a season the club gets two amounts: one by its place in the club
ranking (201 million for the first club, 76.5 million at place 250, almost nothing
at place 400) and one by the popularity of the club and its players (30 to 85 million
for the squads of the edit file). Neither depends on what the club pays its players. On 28 and on 30 June the two budgets get a grant; both
grants are fractions of the wage bill and of the fees of the ten most valuable players
(section 6.7).

The game keeps no number for a player's potential. Players grow by age and by playing
time with fixed steps (section 12), and nothing of that enters the value.

### What the module does

- **Value** = `VALUE[rating] x AGE[age]`, plus the talent bonus, times
  `POSITION[registered position]`, times the player's own fixed factor (`SPREAD`), plus
  `FAME` percent of that for every 1,000 popularity points of the player (section 6.5).
  The salary no longer enters the value.
  The rest of the game's fee function is untouched: figures handed in by a deal, the
  random change of up to 20 or 49 percent, the limit.
- **The player's own factor**: without it, two players of the same rating, age and
  position cost exactly the same. Each player gets one of 256 steps between
  `100 - SPREAD` and `100 + SPREAD` percent, chosen by his id, so it is the same every
  time the game asks.
- **Salary**: the rating part (`30 x rating - 500` plus the steps at 65, 75, 85) becomes
  `SALARY[rating] x SALARY_AGE[age]`. The popularity part is the game's own.
- **Transfer budget** at the start of a career: `BUDGET_TRANSFER` times the mean value
  of the 16 best players, in place of 2 times. `BUDGET_SALARY` does the same for the
  salary budget and is off by default.

New in version 3, each with its own switch:

- **Cup prizes** (`CUP`): the amounts of the game's cup table are replaced for the
  competitions and stages named in the setting. The game's table is not written; the
  three instructions that read it are pointed to a copy.
- **League prizes** (`LEAGUE`, `LEAGUE_2`): the game's two main lists by place, for
  first and second divisions. Leagues played in two halves still get half per half.
- **Prizes into the transfer budget** (`PRIZE_TO_BUDGET`): on the day a prize is paid,
  that percent of it is added to the transfer budget as well. The balance gets the whole
  prize as before. Only in Master League (game mode `0x13`).
- **Pay gap** (`PAY_GAP`): the first club of the ranking pays this many times the
  salary of a club outside the first 250, in place of 2 times. `SALARY` is what the
  first club pays, so a higher gap lowers the salaries at small clubs.
- **Salary bonuses** (`BONUS`): the game's bonuses for the team role, the age band and
  the awards are multiplied by this percent. They are fixed amounts (1,000 to 15,000 a
  year stored, 100,000 to 1.5 million on the screen) that the larger salaries of the
  module would otherwise dwarf.
- **Contract years** (`YOUNG_YEARS`): the limit of 3 years for a player of 23 or
  younger becomes this number. The game still picks the years itself below the limit
  (section 7.3), so not every young player is offered the full length.

New in version 4, each with its own switch:

- **Talent** (`TALENT`, `TALENT_STEP`, `TALENT_MAX`, `TALENT_CAP`): a young player who
  is already good for his age costs more. Because the game has no potential to read,
  the rating a player has at his age stands for it: `TALENT` gives the rating that is
  ordinary at each age up to 23, and every point above it adds `TALENT_STEP` percent
  to the value, up to `TALENT_MAX` percent and `TALENT_CAP` millions. This is a
  stand-in. It cannot tell a late developer from a finished player, and it gives a
  17-year-old of rating 60 nothing even if he would grow fast.
- **Yearly income** (`INCOME_WAGES`): `INCOME_WAGES` percent of the club's wage bill is
  added to the popularity amount of every 1 July. The game's own code already works
  out the wage bill at that point and throws it away; the module keeps it. With 60 the
  income less the wages comes out close to what the game alone gives, for strong and
  for weak squads (table below). `INCOME` is a second, blunt tool, off by default: it
  multiplies both of the game's amounts, and the first of them at the start of a
  career, by a percent.
- **Prize lists by league** (`LEAGUE_BY_ID`): up to 12 first divisions get a list of
  their own, or a percent of `LEAGUE`. The routine looks at the league number the
  game's function already holds.
- **National cups** (`CUP_NATIONAL`): the six amounts the game pays for every cup that
  has no row in its cup table.
- **Television money of the big cups** (`CUP_TV`): an amount per competition that is
  added to every amount of `CUP` for it.

New in version 5, changed in version 6, in `MLTransfers.lua` since version 7:

- **Price ceiling of the computer clubs** (`CEILING`, `CEILING_RATING`). This is the
  first part that changes the transfers between computer clubs.

  *The game.* A computer club has no money (section 9 of `MASTER_LEAGUE.md`). For each
  open position it goes through lists of players sorted by overall, from the top of a
  rating range down, and notes the first three who pass its tests; one of them is
  signed. The range goes by the club's place in the club ranking, in ten groups: the
  clubs outside the first 300 look from 74 down to 47, the first ten from 99 down to
  83. No test looks at a price. If nobody fits, the club looks a second time among
  all players from 99 down to 40, whatever its size. In that second search the game
  leaves out the stars of other clubs (players of the highest status bands who are not
  listed for sale), but not the players it sorted into its first set of lists: those
  without a club and those who are more than 3 points above the range of the club
  they play for.

  *The module.* One more test at the point where a player has passed all the others:
  his value (the value this module computes, with his own factor and popularity,
  before the game's random change) is compared with the ceiling of the club's group.
  A player the club cannot reach is passed over and the search goes on with the next
  one, so the three players it notes are the best three it can afford.
  With `CEILING_RATING` the second search also stops at the top of the club's own
  rating range: it looks further down, not further up.

  What it does not do: no money is booked. A computer club still has no account, the
  ceiling is the same for a club every time, and a club that sold a player for 100
  million can spend no more than before. Your own club is not touched: your players
  are not in these lists (offers for them go another way), and what you can buy is a
  matter of your budget.

  *Version 6: the ceiling gives way.* Version 5 refused every player above the
  ceiling. Played by hand it gave fewer transfers than the game alone. Between two
  computer clubs the game has no offer and no price, so a club cannot "bid less" or
  "bid more"; what the module can decide is how far above its ceiling a club still
  reaches. Four settings:

  - `CEILING_STRETCH` (50): above the ceiling the chance falls evenly, to none at 50
    percent above it. A player 10 percent above is within reach of four clubs in five
    of the group, 25 percent above of every second one. No dice: which club reaches
    how far for which player comes from the player's id and the club's id, so the
    same club gives the same answer every day and two clubs of one group differ.
  - `CEILING_NEED` (30): a club in need counts its ceiling 30 percent higher. In need
    is a club in its second search (it found nobody for the position) and a club that
    asks for a player of a certain standing, which is how the game's plan marks the
    key player a club wants on the last day of a window. The stretch comes on top:
    1.3 x 1.5, so never beyond 1.95 times the ceiling.
  - `CEILING_LISTED` (70): of a player his club has listed for sale, 70 percent of
    the value count.
  - `CEILING_FREE` (50): of a player without a contract, 50 percent. No fee is due
    for him; what is left stands for his wages.

  With 0, 0, 100, 100 the module chooses exactly as version 5 did.

The **yearly budget step** of 28 and 30 June is not changed, and needs no change: its
two grants are fractions of the wage bill and of the fees of the ten most valuable
players, so they grow with the module's salaries and values by themselves. The test
runs that code for both days and compares it with `money_cave.june_grants`.

Not changed: the second salary formula (`fcn_038ab5ea`, used for clubs of the league
numbers 60 to 62 and for some players in one mode), the lists of the league numbers 60
and 61, the list for second divisions unless `LEAGUE_2` is set, the cup table of game
mode `0x28`, the growth of players, the rest of the way computer clubs choose players
(positions, ages, the three candidates and the pick among them, section 9).

### Settings (top of the file; amounts in millions as on the screen)

| setting | default |
|---|---|
| `VALUE` | rating 60: 0.3, 65: 0.8, 70: 2.5, 75: 8, 80: 25, 85: 65, 88: 110, 90: 150, 92: 185, 94: 215, 99: 260 |
| `AGE` (percent) | up to 19: 130, falling to 100 at 25 and 26, then 27: 97, 28: 90, 29: 80, 30: 65, 31: 50, 32: 36, 33: 26, 34: 18, 35: 12, 36: 8, 37: 6, from 38: 5 |
| `POSITION` (percent) | GK 45, CB 85, LB and RB 75, DMF 95, CMF 100, LMF and RMF 95, AMF 105, LWF and RWF 110, SS 105, CF 110 |
| `SPREAD` | 12 percent up and down; 0 switches it off |
| `FAME` | 10 percent per 1,000 points |
| `TALENT` (age, ordinary rating) | 16: 62, 18: 66, 20: 70, 22: 74, 23: 76; no bonus from 24 on; `false` = no talent bonus |
| `TALENT_STEP`, `TALENT_MAX`, `TALENT_CAP` | 6 percent per rating point above the ordinary rating, at most 60 percent and 40 million (before position, spread and popularity) |
| `SALARY` (first club of the ranking; a club outside the first 250 pays this divided by `PAY_GAP`) | rating 60: 0.2, 65: 0.5, 70: 1.2, 75: 2.6, 80: 5.5, 85: 10, 88: 15, 90: 20, 92: 25, 94: 30, 99: 36; `false` leaves salaries alone |
| `SALARY_AGE` (percent) | 16: 45, 18: 50, 20: 62, 22: 76, 24: 90, 26 to 31: 100, 33: 92, 35: 80, 37: 65, 39: 50 |
| `BUDGET_TRANSFER` | 3 (the game: 2); `false` leaves the game's code |
| `BUDGET_SALARY` | `false` = the game's own 2 |
| `INCOME_WAGES` | 60 percent of the wage bill added to the yearly income; `false` = nothing added |
| `INCOME` | `false`; a number is the percent of the game's two yearly amounts (10 to 1000) |
| `CUP` (competition, stage, millions) | Champions League (2): winner 82.12, runner-up 75.62, semi-final 57.12, quarter-final 42.12, first knock-out round 29.62, group stage 18.62. Europa League (3): 26.06, 20.06, 13.06, 8.86, round of 16 6.36, first knock-out round 4.61, group 4.31. UEFA Super Cup (4): 5 and 4. Libertadores (5): 32.25, 15.25, 8.25, 5.95, 4.25, 3. Sudamericana (6): 9.5, 5, 3, 2.2, 1.5, 0.9. AFC Champions League (8): 12, 6, 2, 1.4, 1, 0.8. Club World Cup (1): 5 and 4. `false` leaves the game's amounts |
| `LEAGUE` (place 1 to 22) | 53.1, 50.4, 47.7, 45.0, 42.4, 39.8, 37.1, 34.5, 31.9, 29.1, 26.5, 23.8, 21.2, 18.6, 15.9, 13.3, 10.7, 7.9, 5.3, 2.6, 2.6, 2.6; `false` leaves the game's list |
| `CUP_TV` (competition, millions) | Champions League (2): 23.7; Europa League (3): 5.5; `false` = nothing added |
| `CUP_NATIONAL` | winner 3.91, runner-up 2.91, semi-final 1.41, quarter-final 0.46, round of 16 0.235, round before 0.115 (the game: 2, 1, 0.5, 0.1, 0.05, 0.03); `false` leaves the game's amounts |
| `LEAGUE_BY_ID` (league number, list or percent of `LEAGUE`) | 19 Spain: 58.4 down to 0.9. 50 Germany: 71.1 down to 6.6. 18 Italy: 74.2 down to 3.0. 21 Netherlands: 14.73 down to 3.37. 29 Brazil: 8.0 down to 2.7, places 17 to 20 nothing. 20 France: 9 percent. 22 Portugal, 30 Argentina, 51, 52, 67 Chile: 5 percent. Every other first division: `LEAGUE`. `false` = `LEAGUE` for all |
| `LEAGUE_2` (place 1 to 24) | `false` = the game's list (2 million down to 25,000) |
| `PRIZE_TO_BUDGET` | 75 percent; `false` = prizes go to the balance only |
| `PAY_GAP` | 3 (the game: 2); `false` leaves the game's code |
| `BONUS` | 300 percent; `false` leaves the game's code |
| `YOUNG_YEARS` | 5 (the game: 3); `false` leaves the game's code |
| `WRITE` | `true`; `false` = check and report only |
| **in `MLTransfers.lua`:** | |
| `WRITE` | the same, for this file |
| `CEILING` (ranking places 1-10, 11-20, 21-50, 51-80, 81-120, 121-170, 171-220, 221-260, 261-300, others) | 200, 100, 50, 28, 18, 12, 8, 6, 4.5, 3: the highest value a computer club of that group signs; 0 in a place = no ceiling for the group; `false` = computer clubs choose as in the game |
| `CEILING_STRETCH` (0 to 300) | 50: a club reaches a player up to 50 percent above its ceiling, the further above the less often; 0 = nothing above the ceiling, as in version 5 |
| `CEILING_NEED` (0 to 300) | 30: the ceiling of a club in need (second search, or a slot that asks for a player of a certain standing) counts 30 percent higher; 0 = need changes nothing |
| `CEILING_LISTED` (0 to 100) | 70: percent of the value that counts for a player listed for sale; 100 = he counts like any other |
| `CEILING_FREE` (0 to 100) | 50: the same for a player without a contract |
| `CEILING_RATING` | `true`: in its second search a computer club takes nobody rated above the top of its own rating range; `false`: from 99 down, as in the game. Used only with `CEILING` |

Where the prize defaults come from. Cups: the fixed payments per stage of 2025/26
(Champions League, Europa League, UEFA Super Cup), of 2025 (Libertadores, Sudamericana,
Intercontinental Cup for the Club World Cup) and of 2024/25 (AFC Champions League), as
published in the press, added up to the stage where the run ends, because the game pays
a cup once. The payments per win and the television shares are not in them; with those
a Champions League winner got about 140 million in 2024/25, so the defaults are on the
low side for the big cups. Euros and dollars are taken as the same. League: the Premier
League's payments by place of 2024/25 (pounds); the equal share every club gets is not
in it.

Version 4 adds, from press figures as well: `CUP_TV` is UEFA's "value" share of 2024/25
divided evenly by the 36 clubs; a real club gets between a few million and about 45.
`CUP_NATIONAL` is the FA Cup of 2024/25 from the third round on, added up. One list
serves every country, so the Copa del Rey, the Coppa Italia and the others pay FA Cup
money. `LEAGUE_BY_ID` holds figures of different kinds, because the leagues publish
different things:

| league | what the numbers are |
|---|---|
| 19 Spain | the part of LaLiga's television money that is shared by place, 2023/24 |
| 50 (Germany in the usual patches) | a club's television money of 2024/25 less about 26 million, roughly what every club gets. It is shared by the results of several years, not by this year's place |
| 18 Italy | the same for 2023/24 less the equal share of 26.8 million. Ten amounts are published figures; places 11 to 20 are filled in evenly |
| 21 Netherlands | all of a club's media money of 2026/27, also by the results of several years |
| 29 Brazil | the prize by place of 2024 at 6 reais to the euro |
| 20 France | 9 percent of `LEAGUE`, the size of the television deal of 2025/26 |
| 22, 30, 51, 52, 67 | 5 percent of `LEAGUE`. **An estimate**; no published list is behind it |

Not found, and so not in the defaults: Portugal, Argentina and Chile by place, every
second division (the Championship pays about 10 million to every club whatever its
place), the Copa del Rey, the Coppa Italia, the Coupe de France. The league numbers
are the game's own (`../MASTER_LEAGUE.md`, appendix D); a list applies to a league
only if the game hands that number to its prize function, which was run in the
emulator with made-up numbers and not seen in a career.

The competition numbers 1 and 5 match names of the edit file. The numbers 2, 3, 4, 6
and 8 are **inferred** from the shape of the game's table (which stages have a prize),
and so are the stage names. If one of them is another competition, that one gets the
amounts meant for the first. `python3 ../tools/prize.py <exe>` prints the game's table.

The defaults were set by hand against published figures of 2026: the most valuable
players at 200 to 220 million, the 25th at 100 million; Bruno Fernandes at about 42
million and 300,000 pounds a week; Manchester United's summer of 145 million pounds
spent and 99 million net. They are a starting point, not a fit to a data set.

What the defaults give for the players and squads of the edit file in this repository
(worked with `money_cave.py`, `SPREAD` left out, every club taken with club part 300 of
the popularity; not read from a career):

| | with the talent bonus (version 4) | without (`TALENT = false`, as in version 3) |
|---|---|---|
| most valuable | Lamine Yamal 287 million, Jude Bellingham 239, Erling Haaland 204, João Neves 185, Michael Olise 183, Kylian Mbappé 183, Pedri 175, Vitinha 167 | Lamine Yamal 238, Erling Haaland 204, Jude Bellingham 193, Michael Olise 183, Kylian Mbappé 183, Pedri 175, Vitinha 167 |
| 25th, 50th, 100th, 200th player | 111, 79, 53, 35 million | 93, 70, 51, 33 million |
| transfer budget of a new career | Manchester United 120 million, Manchester City 228, Real Madrid 265, Paris Saint-Germain 282, Liverpool 159, Juventus 96, Brentford 61, Sevilla 29, Burnley 19 | Manchester United 107 (72 with the factor 2, 39 with the game's own formulas), Manchester City 208, Real Madrid 232, Paris Saint-Germain 254, Liverpool 147, Juventus 88, Brentford 59, Sevilla 29, Burnley 19 |

398 of the 13,760 club players get a talent bonus. The largest: Lamine Yamal (rating
90, age 19) 238 to 287 million, Arda Güler (85, 21) 94 to 142, Désiré Doué (86, 21)
112 to 160, Jude Bellingham (90, 23) 193 to 239, Florian Wirtz (86, 23) 98 to 143,
Jamal Musiala (87, 23) 116 to 162, João Neves (88, 22) 141 to 185. These are above
the published values of 2026 for some of them; lower `TALENT_STEP` or `TALENT_CAP`
if they look too high in the game.

Income and wages of one season, in millions, before prizes and transfers. Squads from
the edit file; **the ranking places are guesses**, so the columns show the size of the
effect and not what a career will read:

| club | place taken | wages, game | wages, module | income, game | income with `INCOME_WAGES = 60` | income less wages: game | module, no income setting | with `INCOME_WAGES = 60` | with `INCOME = 150` instead |
|---|---|---|---|---|---|---|---|---|---|
| Real Madrid | 1 | 93 | 235 | 278 | 419 | 185 | 43 | 184 | 182 |
| Paris Saint-Germain | 2 | 89 | 222 | 282 | 415 | 193 | 60 | 193 | 201 |
| Manchester City | 3 | 78 | 193 | 275 | 391 | 197 | 83 | 198 | 220 |
| Bayern München | 4 | 80 | 195 | 277 | 394 | 197 | 82 | 199 | 220 |
| Manchester United | 12 | 65 | 143 | 266 | 352 | 201 | 123 | 209 | 256 |
| Juventus | 20 | 59 | 128 | 221 | 298 | 162 | 93 | 170 | 203 |
| Porto | 35 | 49 | 92 | 214 | 269 | 165 | 122 | 177 | 228 |
| Ajax | 40 | 39 | 68 | 211 | 252 | 172 | 144 | 184 | 249 |
| Sevilla | 60 | 33 | 54 | 201 | 233 | 168 | 148 | 180 | 248 |
| Brentford | 90 | 39 | 69 | 186 | 227 | 147 | 117 | 159 | 210 |
| Leeds United | 110 | 36 | 65 | 176 | 215 | 141 | 111 | 150 | 199 |
| Burnley | 120 | 29 | 39 | 171 | 195 | 142 | 132 | 155 | 218 |
| Blackburn Rovers | 200 | 13 | 12 | 131 | 138 | 118 | 119 | 126 | 185 |

The module's salaries cost the strongest squads about 140 million a year more than the
game's and a weak squad nothing more. A share of the wage bill follows that; one
percent for every club does not, which is why `INCOME` is off. The side effect of
`INCOME_WAGES`: of every salary the club adds, 60 percent comes back on 1 July, so a
large wage bill hurts the balance less than its size says. The salary budget still
limits it.

`CEILING` and the club ranking. The ten amounts are for the ten groups of ranking
places the game uses. `python3 ceiling_survey.py <exe> <edit file>` prints what they
mean for the squads of the edit file, with the default settings and `SPREAD` off, in
millions:

| places | rating range | `CEILING` | middle club: most valuable player | third most valuable | players in the range above the ceiling | mean age at the top of the range: all / under the ceiling |
|---|---|---|---|---|---|---|
| 1-10 | 83-99 | 200 | 158.3 | 93.3 | 1.0 % | 27.8 / 28.5 |
| 11-20 | 76-86 | 100 | 59.4 | 40.2 | 0.6 % | 27.9 / 28.5 |
| 21-50 | 73-83 | 50 | 46.4 | 27.1 | 0.7 % | 28.8 / 29.3 |
| 51-80 | 70-80 | 28 | 22.5 | 13.9 | 1.1 % | 27.9 / 28.5 |
| 81-120 | 67-79 | 18 | 14.4 | 9.9 | 1.8 % | 27.8 / 28.9 |
| 121-170 | 63-78 | 12 | 10.1 | 5.7 | 3.1 % | 27.7 / 29.8 |
| 171-220 | 59-77 | 8 | 7.1 | 4.3 | 4.2 % | 27.8 / 30.4 |
| 221-260 | 55-76 | 6 | 5.5 | 3.4 | 5.6 % | 27.8 / 31.1 |
| 261-300 | 51-75 | 4.5 | 4.7 | 2.4 | 7.5 % | 27.8 / 31.4 |
| others | 47-74 | 3 | 2.2 | 1.4 | 11.4 % | 27.9 / 32.1 |

A club looks from the top of its range down, so what counts is the top. The same
survey for the three highest rating points of each range (players with a contract who
are not listed):

| places | above the ceiling: passed over by version 5 | version 6, passed over in the usual search | version 6, club in need | version 6, out of reach of every club of the group |
|---|---|---|---|---|
| 1-10 | 10.0 % | 5.4 % | 0.6 % | 0.0 % |
| 11-20 | 8.2 % | 4.7 % | 0.7 % | 0.0 % |
| 21-50 | 6.8 % | 3.4 % | 1.1 % | 0.0 % |
| 51-80 | 9.6 % | 4.2 % | 1.6 % | 0.4 % |
| 81-120 | 19.1 % | 9.5 % | 2.8 % | 0.6 % |
| 121-170 | 37.1 % | 20.2 % | 7.8 % | 2.7 % |
| 171-220 | 48.1 % | 30.6 % | 13.2 % | 4.2 % |
| 221-260 | 53.7 % | 35.1 % | 15.8 % | 5.4 % |
| 261-300 | 57.9 % | 41.2 % | 19.8 % | 8.1 % |
| others | 63.5 % | 50.4 % | 30.7 % | 15.9 % |

"Passed over" in the two middle columns is the mean over the clubs of the group: each
club reaches a different part of the players above the ceiling.

Two things in this table are guessed, because the edit file does not hold them: the
club ranking (the clubs are ranked by the mean rating of their best eleven; the game
has its own table) and each player's popularity (which moves a value by a few
percent).

So a ceiling is about what the middle club of a group has in its most valuable
player, with more room at the top. Over the whole rating range it turns away few
players. At the top of the range, where the search begins, version 5 turned away more
than half at the small clubs: the young ones, so the best players a small club could
still sign were a few years older (last column of the first table). Version 6 leaves
about a third of that for a club in need. In the second search the range is gone and
the ceiling, with `CEILING_RATING`, is what keeps a small club from the best players. A stricter set (15, 8,
4.5, 2.5, 1.5, 1 for the six lower groups) turned away 42 percent of the range at the
smallest clubs and left them players of 35 at its top; it was dropped. If you change
`VALUE` much, change `CEILING` with it. `0` in a place of the list means no ceiling
for that group.

### Install

1. Copy `MLMoney.lua` and `MLTransfers.lua` into the `modules` folder next to
   `sider.exe`. `MLMoney.lua` goes over the older version; an `MLMoney.lua` of version 5
   or 6 must not stay, because it holds a ceiling of its own.
2. `sider.ini` needs these two lines, once and in this order:

   ```
   lua.module = "MLMoney.lua"
   lua.module = "MLTransfers.lua"
   ```
3. Start the game. `sider.log` must show, from `MLMoney.lua`: "MLMoney 7: ...", twenty
   `check:` lines "as expected", the line "free memory ... empty", twenty-one
   `written:` lines "ok", the tables, and `RESULT: installed. Changed: values, salaries,
   transfer budget, cup prizes, league prizes, prizes into the transfer budget, pay gap,
   salary bonuses, contract years, yearly income, national cup prizes.`
4. Below it, from `MLTransfers.lua`:

   ```
   MLTransfers 1: the price ceiling of the computer clubs from the settings in MLTransfers.lua
   check: MLMoney.lua   at 047b065c  installed, version 7
   check: value routine at 047b0c90  as expected
   check: number 100    at 047b0654  as expected
   check: choose        at 0365f5c2  as expected
   check: pick          at 03660c52  as expected
   check: range         at 0365d08d  as expected
   check: rating        at 03853b42  as expected
   check: take          at 041293c0  as expected
   check: free memory   at 047d3c40  empty
   written: ceiling  at 0365fb0d  ok
   ```

   then the ceilings with the line "above the ceiling: the chance falls to none at 50
   percent above it; a club in need counts its ceiling 30 percent higher; a listed
   player counts at 70 percent of his value, a player without a contract at 50
   percent", and `RESULT: installed. Changed: price ceiling of the computer clubs.`

What `MLTransfers.lua` says when it writes nothing:

| line in `sider.log` | cause | what to do |
|---|---|---|
| `RESULT: nothing written. MLMoney.lua is not installed ...` | no line for `MLMoney.lua` in `sider.ini`, or it stands below, or `MLMoney.lua` itself wrote nothing | put its line above; read the `RESULT` line of `MLMoney.lua` |
| `... The MLMoney.lua that is installed is not the version this module was made for` | another version of `MLMoney.lua` | take both files from the same folder of this repository |
| `... The price ceiling is in the game already` | an `MLMoney.lua` of version 6 is still in use, or `MLTransfers.lua` stands twice in `sider.ini` | replace the old file; one line only |
| `... This game does not hold what the module expects` | one of the five `check:` lines of the transfer code says `DIFFERENT`, or "free memory" says `NOT EMPTY` | send the log |
| `... CEILING = false` | the setting | |

In each of these cases the money part stays in. The "free memory" line of
`MLTransfers.lua` is the place new in version 6 (`0x047d3c40`): the file of the game
holds zeros there, but whether the running game leaves it alone has not been seen yet,
which is why this line of the log matters.

To undo: remove the two lines from `sider.ini` (the line of `MLTransfers.lua` alone: the
transfers of the game come back and the money stays). No file of the game is changed.

**A running career.** Salaries are stored in the contracts and the budgets were made
from the old numbers. With the module on, values change at once, salaries only at a new
contract, and the budgets stay as they are. Prizes, the share for the transfer budget,
the yearly income and the contract limit work in a running career from the day the
module is on. For a running career set `SALARY = false`, `PAY_GAP = false`,
`BONUS = false` and `INCOME_WAGES = false` (its 60 percent is sized for the module's
salaries), or start a new career. The price ceiling needs no new career: it works from
the next time the computer clubs choose players. Deals they have already chosen are
kept.

### Version 2 in the game (November 2026)

The user ran version 2 with `SPREAD = 0`: all checks "as expected", three places
written, `RESULT: installed. Changed: values, salaries, transfer budget.` In a new
career with Manchester United:

- Bruno Fernandes (rating 89, AMF, age 32) showed a value of **52,973,200**. The
  module's formula gives exactly that for popularity 910, and for no other popularity
  from 0 to 3,000 (`test_money.py`, ok 5). In the older career his popularity was 955,
  which would give 53,191,700; a new career starts him lower.
- The transfer budget was **106,925,700**. The estimate made from the edit file, with
  every player's popularity guessed, was 107 million.

So the value routine runs in the game and reads rating, age, position and popularity
from the right places, the budget routine runs, and the budget field is the one the
screen shows. Not seen yet: salaries of new contracts, `SPREAD` above 0, a season.

### What to look at with versions 3, 4 and 5

Nothing of the parts added since version 2 has run in the game. In the order of effort:

1. `sider.log` as under Install. If a `check:` line says `DIFFERENT`, nothing is written;
   send the log.
2. A new career with Manchester United and the same edit file started with a transfer
   budget of 106,925,700 under version 2. With `TALENT = false` it must be the same
   again, which shows that the larger module did not disturb the old part. With the
   talent bonus on it is higher; the estimate is 120 million.
3. The value of a young player before and after: one of 21 or younger with a rating
   of 80 or more must read higher than with `TALENT = false`, a player of 24 or older
   the same.
4. Note the salary of two players in the new career, with their rating, age and team
   role: one star and one captain or leader. From these the pay gap and the bonus can
   be checked against `money_cave.py`.
5. Offer a new contract to a player of 23 or younger. Lengths of 4 or 5 years must now
   be possible; the game never offered more than 3 before.
6. Note the transfer budget on the day before and the day after your club goes out of
   a cup or wins one, and at the end of the league. It must rise by 75 percent of the
   prize. Premier League (league 17), place 1: 53,100,000, so 39,825,000 more budget.
   Spain (19), place 1: 58,400,000. A national cup: winner 3,910,000, so 2,932,500
   more budget. If a league pays the amounts of `LEAGUE` although `LEAGUE_BY_ID`
   names it, the league number in the setting is not the one the game uses.
7. The balance on 30 June and on 2 July. The rise is the two yearly amounts, each
   changed by up to 10 percent by the game; with `INCOME_WAGES = 60` the second one
   holds 60 percent of the wage bill.
8. The price ceiling can only be seen in the transfer news. Play through the first
   transfer window of a new career and note three or four signings of computer clubs:
   player, his value on the screen, the buying club. A club outside the first 300 of
   the ranking must not sign a player valued above 3,000,000, one of the places 51 to
   80 none above 28,000,000. The value on a screen can differ from the one the test
   uses by the game's random change of up to 20 percent, so a signing a little above
   a ceiling is no fault, and with version 6 a signing up to 1.5 times the ceiling
   (1.95 times for a club in need) is as intended.
9. The number of signings. Version 5 gave fewer than the game alone, by a test played
   by hand. Count the signings of computer clubs in one window with version 6 and, if
   you can, in the same window of the same save with `CEILING = false`. If version 6
   is still clearly lower, set `CEILING_RATING = false` and count once more: that
   tells whether the price or the rating limit of the second search holds the clubs
   back. Why version 5 lost transfers was not found out; see "Not shown by the test".

### How it works

Up to 26 places of the game's code are changed and two pieces of unused memory are
filled (`money_cave.py` has the layout and the source of the 14 routines):

| where | before | after | setting |
|---|---|---|---|
| `0x038ab8db`, 17 bytes, fee function | `9,000 x max(0, rating - 68)` into `edi` | call to the value routine; it also sets the factor of the salary part to 0 | always |
| `0x038ac875`, 7 bytes, salary function | start of the 98 bytes that compute the rating part | call to the salary routine, jump over the rest | `SALARY` |
| `0x038adc47`, 5 bytes, budget function | the mean value of the best 16, doubled | call to a routine that multiplies by `BUDGET_TRANSFER` | `BUDGET_TRANSFER` |
| `0x038add08`, 8 bytes, budget function | wage bill + twice the mean salary of the best 16 | call to a routine that uses `BUDGET_SALARY` in place of the 2 | `BUDGET_SALARY` |
| `0x038aa400`, `0x038aa408`, `0x038aa423`, 4 bytes each, `cup_prize` | address of the game's cup table (`0x0216b178`) in three instructions | address of the module's copy of the table | `CUP` |
| `0x038aa2dd`, 7 bytes, `league_prize` | `mov eax, [ebp + eax*4 - 0x17c]`: the first list, built on the stack | call to a routine: if the league number in `edi` is one of `LEAGUE_BY_ID`, the amount of its list, else of the module's first list | `LEAGUE` (and `LEAGUE_BY_ID`) |
| `0x038aa2c6`, 7 bytes, `league_prize` | the same for the second list | the same | `LEAGUE_2` |
| `0x03640ac5` and `0x03640b78`, 5 bytes each, `prize_step` | `call balance_add` for a league and for a cup prize | call to a routine that calls `balance_add` and then, in Master League, `transfer_budget_add` with the share | `PRIZE_TO_BUDGET` |
| `0x038aca1b`, 4 bytes, salary function | address of the shared 0.004 in `fmul qword [0x01f2fe88]` | address of a number of the module, `(PAY_GAP - 1) / 250` | `PAY_GAP` |
| `0x038aca2b`, 6 bytes, salary function | `add esi, [ebp - 0x50]`: role bonus + popularity part | call to a routine that first multiplies the role bonus by `BONUS` | `BONUS` |
| `0x038acd96`, 12 bytes, salary function | award bonuses + band bonus into `eax` | call to a routine that multiplies their sum by `BONUS` | `BONUS` |
| `0x03887fc1`, 5 bytes, contract limit | `mov eax, 3` | `mov eax, YOUNG_YEARS` | `YOUNG_YEARS` |
| `0x038adeaa`, 9 bytes, `season_income` | `mov eax, [ebp + 8]; push eax; call club_popularity`, right after the call that works out the wage bill | call to a routine that keeps the wage bill in the function's own local and goes on to `club_popularity` with the same argument | `INCOME_WAGES` |
| `0x038adeee`, 6 bytes, `season_income` | `lea eax, [esi - 3451330]`: the last step of the amount | call to a routine that does the same, applies `INCOME` and adds the share of the wage bill | `INCOME_WAGES` or `INCOME` |
| `0x038a9e9c`, 6 bytes, amount by rank | `imul eax, eax, 5000` | call to a routine that does the same and applies `INCOME` | `INCOME` |
| `0x038ae025`, 6 bytes, `club_money_setup` | `add esi, 15000` | call to a routine that does the same and applies `INCOME` | `INCOME` |
| `0x038aa43a`, `...446`, `...452`, `...45e`, `...46a`, `...476`, 4 bytes each, `cup_prize` | the six amounts for a cup without a row: 20000, 10000, 5000, 1000, 500, 300 (the numbers in six `mov edi`) | the six amounts of `CUP_NATIONAL` | `CUP_NATIONAL` |
| `0x047b0200`, 3,568 bytes | zero | the tables (value, salary, two by age, position, talent), the cup table, two league lists, 12 lists by league, the single numbers, 13 routines of 226, 53, 26, 22, 53, 24, 21, 31, 8, 19, 18, 50 and 13 bytes | always |
| `0x0365fb0d`, 9 bytes, `ai_candidates` | `mov ecx, [ebp + 0x24]; push esi; call 0x041293c0`: the player who passed every test is added to the list of candidates | call to the ceiling routine, which goes on to that function or to the game's "next player" at `0x0365fb28` | `CEILING` |
| `0x047d3c40`, 384 bytes | zero | ten ceilings, ten highest ratings for the second search, the four numbers of the stretch, the ceiling routine of 313 bytes | `CEILING` |

**The ceiling routine.** `ai_candidates` is not handed the club's level. Its only
caller, `ai_pick_candidate`, has it as an argument, so the routine reads it from that
function's stack frame (the saved `ebp`), and the byte there that says "second
search". The buying club is the first number of the plan record and the standing the
slot asks for is behind the last argument, both among `ai_candidates`' own arguments
(`[ebp + 0x18]`, `[ebp + 0x30]`). It does so only if `ai_candidates` is about to return to one of its two calls
in `ai_pick_candidate` (`0x03660d58`, `0x03660db9`; a scan of the exe found no other
call) and the level is 0 to 9. In every other case the player is taken as in the game:
when something is not as expected the routine changes nothing. The rating is fetched
with the same call the fee function uses, the value with the module's own value
routine. A refused player leaves the routine by a jump to the place the game's own
failed tests jump to. `ebx`, `edi`, `esi` and `ebp` come back as they were.

The limit, in whole numbers (each division drops the remainder):

```
limit = ceiling of the level
in need (second search, or the slot asks for a standing):  limit = limit * (100 + CEILING_NEED) / 100
h     = ((player id, 16 bits) ^ (player id, 32 bits) * 0x01000193 ^ club id * 0x9e3779b1) * 0x85ebca6b >> 24      0 to 255
limit = limit + limit * (h * CEILING_STRETCH) / 25600
price = value * CEILING_FREE / 100      status 1 or 2 (+0xb4, bits 0-3)
        value * CEILING_LISTED / 100    else, with bit 29 or 30 of +0xb8
        value                           else
refused if price > limit
```

The rating limit of the second search comes before this and is not moved by it.

The memory is the end of the code section `.trace`: its content ends at `0x047b005d` and
its last page runs to `0x047b0fff`; the file holds zeros from `0x047b005e` on. That page
is full (version 5 had its ceiling routine below the tables, at `0x047b0130`; version 6
leaves that piece unused). The second piece is the end of the next section, `.xcode`:
its content ends at `0x047d3a42`, the file holds zeros up to `0x047d3dff`, the next
section begins at `0x047d4000`, and a scan found no call, jump or stored address into
`0x047d3000`-`0x047d3fff`. Both sections are readable, writable and executable in
the exe's header, so the routines can run there whatever Sider does with the page
protection. No call or jump of the exe goes into that range. For the changed places a
scan of the exe found no call or jump into the inside of any of them; for the three
address operands in `cup_prize` this was read from the listing of the function, not
scanned.

No shared constant is changed: the 0.004 of the club factor has five other users in the
exe, so the salary function is given a number of its own.

After each changed place the game's code was read for what it still needs. The league
routine uses `ecx` and `edx`; the game loads both anew before it reads them. The income
routines change the flags; a `test eax, eax` follows two of them and the third is
followed by code that reads no flag. `[ebp - 4]` of `season_income`, where the wage
bill is kept, holds a flag byte for the wage bill function that nothing reads after
that call.

What the routines read of a player record: the age (6 bits at `+0x1c`, bit 7) and the
registered position (4 bits at `+0x04`, bit 28), which is where the game's own getter
`fcn_038278b0` reads fields `0x2b` and `0x00`; the popularity (`+0xb4`, bit 11) as the
fee function itself does; the id (`+0x2c`, `+0x30`) as the rating function does.

Order of the module's work: check the settings; build the tables; compare 5,120 bytes
of the game, in twenty pieces, with what the exe file has (the code around every
changed place, whole functions where they are short: `cup_prize`, `league_prize`,
`balance_add`, `transfer_budget_add`, the contract limit, `season_income`, the amount
by rank; the game's cup table), and in `MLTransfers.lua` 2,110 bytes more in five pieces
(`ai_candidates` whole, `ai_pick_candidate` up to its two calls, the function with the
rating ranges, the rating call, the function that adds a candidate); see
that the memory is all zero; write tables and routines; read them back; only then
change the places one by one and read each back. If a comparison fails, nothing more is
written. `MLTransfers.lua` works in the same order on its own piece of memory and its
one place, after it has found `MLMoney.lua`. The part of each file that holds the
routines, the places and the compared bytes is made by `python3 money_cave.py lua <exe>`
(`MLMoney.lua`) and `python3 money_cave.py lua <exe> transfers` (`MLTransfers.lua`);
the test fails if a file differs from it.

### What the test shows

```
python3 test_money.py ~/pes-work/game/PES2017.exe
ok 0: without the module the emulated game gives the amounts of ../tools/money.py (salary with role, age band and award bonuses at every place of the club ranking; fee); its budget function adds twice the mean of the 16 highest fees and the wage bill plus twice the mean of the 16 highest salaries; cup_prize and league_prize give the game's lists (2626 and 6720 cases); a prize goes to the balance only; the contract limit is 3 years up to age 23; the three amounts of yearly income are 25 x popularity - 670 x the club's number - 3,451,330 (whatever the wage bill), (403 - rank) x 5,000 and 15,000 + 165,000 x club level; on 28 and on 30 June the yearly budget step gives the two grants of money_cave.june_grants for 2,000 cases each (to within 2); ai_candidates, the code that lists the players a computer club may sign, run whole through its two calls in ai_pick_candidate and, for three cases in eight, with ai_pick_candidate itself run from its first instruction to the end of its two searches, lists the first three players of the lists from the highest overall down who pass its tests (in a deal, on loan, the status band a slot asks for), whatever their value; ai_pick_candidate searches the first set of lists and then the second, a plan of kind 1 or 4 the second only, in the rating range of the club level, or from 99 down to 41 when the lowest overall handed in is 0
ok 1: MLMoney.lua and then MLTransfers.lua pass their checks, write only their own memory and the places they report, and what they wrote is what money_cave.py builds from the same settings
ok 2: with the changes in, the game's code gives the amounts of money_cave.py: salary and fee for 3000 + 3000 random players (ratings 40 to 255, ages 0 to 63, every position, with and without awards and the random change) and for every place of the club ranking; the budgets of 150 squads of 0 to 40 players; cup_prize for 2626 cases (competitions 0 to 100, stages 0 to 12, two game modes; mode 0x28 keeps its own table); league_prize for 11648 cases (every list, place and half); the two places that pay a prize, in Master League and four other modes: balance, transfer budget, account line, registers and stack; the two bonus routines leave every other register as it was; the contract limit for every age; the three amounts of yearly income for 600 cases each, with wage bills from 0 to the largest number; ai_candidates run whole for 750 random sets of lists (club levels 0 to 9 and six numbers that are no level, both searches, both sets of lists, any buying club, slots that ask for a status band, players without a contract, listed, in a deal and on loan among them, the ceiling put where one player is just within the club's limit for him and 1 below that; three cases in eight with ai_pick_candidate itself run up to the end of its two searches, so that level, range and the mark of the second search are where the game puts them): it lists the players of money_cave.candidates, passes over the others and goes on, leaves stack, registers, player records and plan as the game does, and entered from anywhere else it lists as the game
ok 3: with every optional part switched off only the fee place is written and salary, prizes and contract limit are the game's own; each of the 17 optional parts switched on alone changes its own places and nothing else; BUDGET_SALARY changes the salary budget; with spread, position and salary age switched off the value is VALUE x AGE plus popularity; PAY_GAP = 1, 1.5, 2, 2.75, 7.3, 10 give the club factor of money_cave.py at every place of the ranking; with every setting at its limit the code and money_cave.py still agree; the ceiling without the rating rule, with groups without a ceiling, with none at all (the rating rule alone) and with the lowest amount everywhere; the hard ceiling of version 5 (CEILING_STRETCH = 0, CEILING_NEED = 0, CEILING_LISTED = CEILING_FREE = 100), each of the four alone, and all four at their limits
ok 4: WRITE = false, one changed byte at 60 places of the checked code and data, memory not empty, 57 kinds of faulty settings: MLMoney.lua writes nothing, and MLTransfers.lua after it writes nothing either; a write to its memory that does not stick: the code is not touched. MLTransfers.lua: WRITE = false, one changed byte at 15 places of the transfer code, its memory not empty, 11 kinds of faulty settings, a write that does not stick: it writes no place of the code and MLMoney.lua is installed as without it; run without MLMoney.lua, before it, with a mark that is not MLMoney.lua's, with a changed byte at 6 places of the value routine and the 100 it uses, or a second time: it writes nothing; with another version number in the mark and the same value routine it installs; with CEILING = false it does not look at the game at all
ok 5: Bruno Fernandes as the user saw him without a module (rating 89, salary 7,259,700, value 36,743,200): the game's formula gives exactly that value from that salary with popularity 955, and with no other rating from 60 to 99
      as the user saw him with version 2 and SPREAD = 0 in a new career (age 32, value 52,973,200): the module's formula gives exactly that for an AMF of rating 89 with popularity 910, and with no other popularity
```

About 110 seconds. The prize, budget, salary and income code of the game runs as machine
code in the emulator, with the module's changes in it. For the two places that pay a
prize the piece of `prize_step` around each call is run on its own, with a made-up
stack frame; `prize_step` as a whole (the walk over the competitions of the club) was
not run. The same holds for the yearly budget step: the piece of the money step from
the grade to the transfer grant is run for 28 June and for 30 June, not the whole
step, and for the piece of `club_money_setup` that makes the starting amount.
`season_income` and the amount by rank run as whole functions; the test also sees that
`season_income` hands the club to `club_popularity` and gives back `ebx`, `esi` and
`edi` as it got them.

The price ceiling: `ai_candidates` runs as a whole function with made-up lists of 1 to
14 players. Of eight cases, four start it at one of its two call instructions in
`ai_pick_candidate` with a made-up frame of that function (level, "second search"
byte); three run `ai_pick_candidate` itself from its first instruction to the end of
its two searches (`0x03660dce`), so that the level, the range, the search byte and the
order of the two sets are the game's; one calls it from somewhere else. The players
have a contract or none, a quarter are listed, the slot asks for a standing or for
none, the buying club is any number. Five things it asks are
answered by the test: the record of a player, his club, the date, and the two tests
taken to be the foreign-player and squad rules (always "yes"); the rating is a number
kept in the made-up record. Everything else is the game's code, with the changed place
and the routine in it. The list it returns is compared with `money_cave.candidates`:
without the module (the first three who pass, whatever they cost), with it, with the
ceiling of the level put where one player is exactly at the club's limit for him and 1
below it, with players the game's own tests refuse mixed in, with a number that is no
level, and entered from somewhere else (then it must list as the game does). After
each run the stack pointer, `ebp`, `ebx`, `esi`, `edi`, the player records and the
plan record must be as the game leaves them. The four numbers of version 6 are also
set to 0, 0, 100, 100 (the list must be version 5's), each alone, and to their
limits. The second half of `ai_pick_candidate` (which of the three is taken),
`ai_fill_slots` and the steps above them were not run.

The test was tried against planted faults. Version 2: ten in the routines and the
changed places (wrong shift for the position, wrong mask for the age, the id read with
its unused upper half, wrong table for the salary age, wrong step of the spread, wrong
divisor of the popularity bonus, wrong number slot or wrong sum in the budget routines,
a call one byte off). Nine made it fail. The tenth, leaving out the `test esi, esi` at
the end of the transfer budget routine, cannot be seen in the emulator: the jump after
it reads the zero flag, which a real processor leaves undefined after a division and
the emulator does not. The instruction is there for the real processor.

Version 3: twenty more (the prize routine without the mode test, with the stack off by
4, with an unsigned division, without the call to `balance_add`; the bonus routines
without the popularity part, without the awards, with a register not restored; the two
league lists swapped; a cup operand pointing to the stage column; the pay gap operand
one byte off; the contract limit written to the wrong instruction; two faults in
`money_cave.py`'s own arithmetic; six in the Lua: a cup amount in the wrong row, a
wrongly built floating-point number, league places shifted, the contract years setting
ignored, a place written although switched off, one piece of code not compared). All
twenty made it fail; two of them (a register not restored in a bonus routine) only
after a check of the routines' registers was added, because the game does not use
those registers afterwards.

Version 4: thirty-two more, run together with the twenty of version 3 (52 runs). In the
routines: the talent bonus without its zero below the ordinary rating, without the
limit in money, replacing the value instead of adding to it, with the percent limit
one step late; income scaled below zero, without the 5,000 per place, with the 15,000
added after the percent, with two places swapped; the wage bill kept in the slot of a
saved register, `club_popularity` reached without its argument or with the wrong one,
the wage share not added or added before the percent, the place one byte late; the
league routine with rows of the wrong width, without the unit of 100, comparing unused
slots; two national cup amounts swapped. In `money_cave.py`'s arithmetic: a wrong
stage for the national cups, the talent bonus after the position, the constant of 30
June used on 28 June, the wage share added after the floor of 1,000. In the Lua: the
talent table one year late, the television money of one cup given to every cup, the
national amounts in reverse, the income percent or the wage percent not written, a
short league list filled with zeros, the count of leagues one short, three places
written although switched off or not written although needed. All 52 made the test
fail. Two of the new ones (the argument of `club_popularity`, the saved register) are
seen only by a check of `season_income`'s argument and registers that was written for
them: the result of the function is right with either fault. One planted
fault was dropped as no fault at all: comparing the league number in 16 bits, which is
all the game keeps of it. The wage share added after the floor of 1,000 is seen only
with a wage bill near the largest number, because the game's amount never reaches
that floor.

Versions 5 and 6 (`python3 planted_faults.py <exe> routine` and `files`): every one of
the 2,504 bits of the ceiling routine of version 6 was flipped in turn. 2,497 flips
made the cases fail (version 5: 1,169 of 1,176). Six of the other seven turn the
`push ebx` or `push edi` at its start into the push of another register, so a wrong
value comes back in `ebx` or `edi`; the game loads both anew right after
(`0x0365fb28`) or returns, so no result changes, and the routine restores them all the
same. The seventh turns `sub esp, 0x1c` into `and esp, 0x1c`; the emulator has memory
at address 0 and the test answers the rating call itself, so the routine still works
there, while the real game would stop. Then 32
faults in the files, each with a whole run of the test: in the Lua the ceilings or the
ratings in reverse order, the place not written, the comparison of the transfer code or
the test for empty memory left out, "no ceiling" written as 0, wrong limits, the rating
rule always on, the second piece of memory not written or not read back, a wrong size
or address of it, a faulty setting let through; in `money_cave.py` a value equal to the
ceiling or a rating equal to the top refused, the rating rule in both searches, the
lowest list searched too, the ceilings in reverse; and for version 6, in the Lua the
need written without its 100, the two discounts swapped, a negative number let
through, in `money_cave.py` need counted in only one of its two cases, a wrong divisor
of the stretch, the club left out of the hash, the discount for only one of the two
statuses, both discounts for a listed player without a contract. All 32 made the test
fail.

Not shown by the test: for the price ceiling, anything above the two searches of
`ai_pick_candidate` (how the game calls it in a transfer window, how often the first
search finds nobody, whether squads stay full over seasons), and that the club level
the routine reads is the one the club's rating range was made from in a running game
(read in the disassembly, not run). That the status 1 and 2 of `CEILING_FREE` are the
players without a contract is taken from how the game closes their deals
(`MASTER_LEAGUE.md` 9.7), not seen in a game. **Why version 5 gave fewer transfers is
not known**, so it is not known either how much of them version 6 brings back. What
the code says (`MASTER_LEAGUE.md` 9.6): the game notes only the first three players
who pass and then takes one of them only if his club lets him go; if none of the three
can go, the position stays open and, unless the slot asks for a standing, the club
searches a second time. Without the module that second search starts at rating 99 and
finds other players. With `CEILING_RATING` it starts at the top of the club's own
range again, so it can meet the same three and fail again; version 6 changes that
only as far as the need raise lets dearer players in ahead of them. How often this
happens was not measured. The setting to try if signings stay low is therefore
`CEILING_RATING = false`. Sider's `memory.write` on the real game, the memory being empty
in the running game (the module checks it), that the game's cup table and code are in
the running game as in the exe file (the module checks it), which competition each
number of the cup table is, which league number the game hands to `league_prize` for
each league of a career (the lists by league rest on the numbers of appendix D), when
and how often the game calls the prize and income code in a season, what the screens
show of a prize, and the play of a season with the new numbers. The 30 June budget step
grades the year's result against the year before (section 6.7); larger prizes and the
wage share enter that result, and what this does over several seasons is not known.
The table of income and wages above is worked from the edit file with guessed ranking
places; no season was played. The emulator computes the club factor with 80-bit
floating point; if the game runs with a lower precision setting, a salary can differ by
1 (100 on the screen).

## What was looked at in `sider.dll`

Read from the DLL's code and strings, not run:

- A module must return a table with an `init(ctx)` function. It gets these names:
  `log`, `memory` (`read`, `write`, `search`, `pack`, `unpack`), `string`, `table`,
  `math`, `pairs`, `ipairs`, `tostring`, `tonumber`, `type`, `unpack`, `assert`,
  `error`, `os` (`time`, `clock`, `date`), `audio`; with `luajit.ext.enabled` also
  `ffi`, `bit`, `require`. There is **no `pcall`**: an error in `init` makes Sider skip
  the module and log the error.
- `memory.read(address, count)` makes the pages readable and writable
  (`VirtualProtect`), copies the bytes, and asks for the old protection back with a
  call that Windows refuses (no place for the old value is passed). So **a read leaves
  the touched pages marked writable**. No byte changes. Every Sider module that reads
  memory does the same.
- `memory.write(address, bytes)` does the same and copies the other way, so it can
  change code. That is the route for the tuning modules. It gives the pages the
  protection "read, write, execute" (`0x40`) before the copy; if Windows refuses that,
  the module stops with an error and Sider skips it.

## Notes for the next module

- The exe has a fixed load address (no relocation table, no dynamic base), so the
  addresses of `MASTER_LEAGUE.md` are valid in the running game. `MLCheck.lua` tests
  exactly this.
- The level values are single bytes inside `mov eax, value` instructions; 68 and 9,000
  of the fee formula are numbers inside two instructions; 0.00027 is a constant with
  one user. All four can be changed in place.
- **The 2.2 of the fee formula is a shared constant** (`0x01f0f2b8`, 16 references in
  the exe). It must not be changed in place; the fee function has to be pointed to a
  constant of its own. (`MLMoney.lua` does not need it: its routine sets the factor of
  the salary part to 0 in the function's own stack frame.)
- Free memory for code and tables: `0x047b0200`-`0x047b0fff`, the end of `.trace`
  (3,584 bytes; `MLMoney.lua` uses the first 3,568), and below it `0x047b0124`-
  `0x047b01fe` (used by version 5 only; free again). The end of `.xcode`,
  `0x047d3a43`-`0x047d3dff`: `MLMoney.lua` uses `0x047d3c40`-`0x047d3dbc` for the price
  ceiling; about 500 bytes below it are free. A module must see zeros there before it
  writes.
- A routine that is called from inside a game function can read the arguments of that
  function's caller through the saved `ebp`, if it first checks the return address.
  The ceiling routine does this to get the club level without changing a call.
