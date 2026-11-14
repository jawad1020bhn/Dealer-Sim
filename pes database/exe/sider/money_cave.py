"""What MLMoney.lua and MLTransfers.lua put into the game, and the same arithmetic as Python.

    python3 money_cave.py            print the layout and the code bytes
    python3 money_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                     and compare it with the bytes kept in this file
    python3 money_cave.py lua <PES2017.exe>
                                     print the part of MLMoney.lua that is made from this file and
                                     the exe: ROUTINES, SITES and CONTEXT (test_money.py checks that
                                     MLMoney.lua holds exactly this text)
    python3 money_cave.py lua <PES2017.exe> transfers
                                     the same for MLTransfers.lua: ROUTINE, SITE, MONEY and CONTEXT

MLMoney.lua changes up to 25 places of PES2017.exe (sha256 44b0caaa...) and fills a
piece of unused memory with 13 small routines and their tables. MLTransfers.lua changes
one place more and fills a second piece (the price ceiling of the computer clubs, which
was part of MLMoney.lua in its versions 5 and 6). Its routine calls FEE_CODE and divides
by the 100 at HUNDRED_AT, both in the memory of MLMoney.lua, so it writes nothing unless
it finds them there (MONEY_NEEDED).

Fee, fcn_038ab832 (MASTER_LEAGUE.md 6.2). The 17 bytes at 0x038ab8db hold the rating part
of the formula, `9000 * max(0, rating - 68)`, left in edi. They become a call to FEE_CODE:

    v           = VALUE[rating] * AGE[age] / 100
    p           = min(max(0, rating - TALENT[age]) * TALENT_STEP, TALENT_MAX)
    v           = v + min(v * p / 100, TALENT_CAP)       the talent bonus; TALENT[age] = 255: none
    v           = v * POSITION[registered position] / 100
    v           = v * (SPREAD_LOW + (hash * SPREAD_RANGE >> 8)) / 1000, at most 99,999,900
    edi         = v + v * (popularity * FAME) / 100000
    [ebp - 0xc] = 0.0        the factor of the salary part; the game goes on to compute
                             trunc(salary * factor) + edi, which is now edi

All divisions drop the remainder. rating is in eax there (0 to 255; above 99 counts as
99) and the player record in ebx. Of the record (what the game's getter fcn_038278b0
gives for fields 0x2b and 0x00): age = 6 bits at +0x1c, bits 7-12; registered position =
4 bits at +0x04, bits 28-31, in the edit file's order (0 GK ... 12 CF). popularity is the
12-bit number at +0xb4, bits 11-22. hash is one byte made from the player's id (the word
at +0x2c and the dword at +0x30), so it is the same for a player at every call.
Everything after that in the function is as before: a handed-in figure taken as it is,
the random change, the limit.

Salary, fcn_038ac66e (6.1). The 98 bytes from 0x038ac875 compute A = 30 * rating - 500
into [ebp - 0x38] and B (the three steps at 65, 75, 85) into [ebp - 0x34]. The first 7
bytes become a call to SALARY_CODE and a jump over the rest:

    [ebp - 0x38] = SALARY[rating] * SALARY_AGE[age] / 100
    [ebp - 0x34] = 0

so `salary = trunc((role bonus + popularity part + that) * club factor) + ...`.

Budgets, fcn_038ad9c4 (6.4). `add esi, esi; mov eax, [eax + 0x30]` at 0x038adc47 (the
mean value of the 16 best players, doubled) becomes a call to BUDGET_T_CODE:
`esi = esi * BUDGET_T / 100`, the same mov, and the zero flag the next jump reads.
`lea esi, [ecx + eax*2]; call 0x0381c0e5` at 0x038add08 (wage bill + twice the mean
salary of the 16 best paid) becomes a call to BUDGET_S_CODE and three nops:
`esi = ecx + eax * BUDGET_S / 100`, then a jump to 0x0381c0e5, which returns to the nops.

Prize money (6.7). cup_prize (fcn_038aa307) searches the 73 rows (competition, stage,
amount) at 0x0216b178. The three instructions that hold the table's address get the
address of a copy with other amounts (CUP_TAB); the game's table is not written.
league_prize (fcn_038a9ebb) reads the amount for a place from a list on its stack:
`mov eax, [ebp + eax*4 - 0x17c]` at 0x038aa2dd (first list, index 0 to 22) and
`mov eax, [ebp + eax*4 - 0x120]` at 0x038aa2c6 (second list, index 0 to 24). The second
becomes `mov eax, [eax*4 + LEAGUE2_TAB]`, the same length. The first becomes a call to
LEAGUE_CODE: the number of the club's league is in edi there (16 bits, from fcn_03879e04);
if it is one of the LEAGUE_COUNT numbers at LEAGUE_IDS, the amount is that league's row of
LEAGUE_ROWS_TAB (words, in units of 100 stored), else `[eax*4 + LEAGUE1_TAB]`. The routine
uses ecx and edx, which the game loads anew right after.
A cup without a row in the table gets one of six amounts by stage, the immediates of six
`mov edi` (NATIONAL_SITES); the module writes other numbers there.
prize_step (fcn_03640686) hands every prize to balance_add (fcn_038aadb7), at 0x03640ac5
(league) and 0x03640b78 (cup). Both calls go to PRIZE_CODE instead: it calls balance_add
with the same argument and then, in game mode 0x13 (Master League), transfer_budget_add
(fcn_038aac87) with `amount * SHARE / 100`.

Salary once more. `fmul qword [0x01f2fe88]` at 0x038aca19 multiplies (251 - rank) by 0.004;
its address operand (0x038aca1b) is pointed to RANK_STEP, a number of the module, so the
shared constant stays as it is. `add esi, [ebp - 0x50]` at 0x038aca2b (esi = the role
bonus R) becomes a call to BONUS_R_CODE: `esi = esi * BONUS / 100`, then that add.
`mov eax, [ebp - 0x34]; add eax, [ebp - 0x50]` at 0x038acd96 (award bonuses + band bonus
T) becomes a call to BONUS_END_CODE: `eax = (awards + T) * BONUS / 100`.

Contract years (7.3). `mov eax, 3` at 0x03887fc1 in fcn_03887f5d is the limit for players
of 23 and younger; its number is replaced.

Yearly income (6.4). season_income (fcn_038ade76) calls the wage bill function and then
overwrites its result: `call wage_bill; mov eax, [ebp + 8]; push eax; call club_popularity`.
The nine bytes after the first call become a call to WAGES_KEEP_CODE, which stores eax in
the function's local [ebp - 4] (a flag byte for the wage bill function, not read again),
pushes the argument under its own return address and jumps to club_popularity, so that
function returns to the nops after the call as if the game had called it. The last step
of the amount, `lea eax, [esi - 3451330]` at 0x038adeee, becomes a call to INCOME_N_CODE:

    eax = esi - 3451330
    eax = eax * INCOME / 100            only if eax > 0 (INCOME_SCALE_CODE)
    eax = eax + [ebp - 4] * INCOME_WAGES / 100

and the game's `test eax, eax` and its floor of 1,000 follow as before. With INCOME_WAGES
off the percent is 0 and the first place is not changed. `imul eax, eax, 5000` at
0x038a9e9c (the amount by rank, fcn_038a9e6b) and `add esi, 15000` at 0x038ae025 (the
starting amount in club_money_setup) become calls that do the same and apply INCOME.

The yearly budget step (6.7) is not changed. june_grants() below is its arithmetic, and
test_money.py runs the game's code for both days against it.

Transfers of the computer clubs (9.6, 9.10; MLTransfers.lua). ai_candidates (fcn_0365f5c2) lists up to
three players a computer club may sign for a position: it walks lists of players by
overall from the top of the club's rating range down and adds every player who passes
its tests with `mov ecx, [ebp + 0x24]; push esi; call 0x041293c0` at 0x0365fb0d. None of
the tests reads a price. Those nine bytes become a call to CEILING_CODE, which works out
the player's value (the game's rating call, then FEE_CODE) and compares it with a limit
made from CEILING_TAB[club level]; in the club's second search, among all players, it
first compares the rating with CEILING_TOP[club level]. Above either, it drops its return
address and jumps to 0x0365fb28, where the game's own failed tests go: the next player.
The level and the "second search" byte are arguments and locals of ai_pick_candidate
(fcn_03660c52), the only caller; the routine reads them through the saved ebp, and only
if ai_candidates will return to one of its two calls there. Otherwise, and with a level
above 9, the player is added as in the game.

The limit (version 6; all divisions drop the remainder):

    limit = CEILING_TAB[level]
    limit = limit * (100 + NEED) / 100           if the club is in need: the second search,
                                                 or a slot that asks for a status band
    limit = limit + limit * (h * STRETCH) / 25600
    price = value * FREE / 100                   player of status 1 or 2 (signed without a transfer)
          = value * LISTED / 100                 else, player with mark 29 or 30 (listed by his club)
          = value                                else
    refused if price > limit

h is one byte made from the player's id and the id of the buying club, so one club goes
further for a player than another, and the same club decides the same way about the same
player: h = ((word at +0x2c) ^ (dword at +0x30) * 0x01000193 ^ club id * 0x9e3779b1)
* 0x85ebca6b >> 24. The band asked for is ai_candidates' last argument ([ebp + 0x30] ->
number), the buying club the first dword of the plan record ([ebp + 0x18]). With STRETCH
= 0, NEED = 0, LISTED = FREE = 100 this is the plain ceiling of version 5. limit() and
candidates() below are the same in Python; test_money.py runs the whole of ai_candidates,
and ai_pick_candidate up to the end of its two calls, against them.

The memory used is the end of the section .trace: the section's content ends at
0x047b005d, its declared size at 0x047b0123, and its last page runs to 0x047b0fff. The
section is readable, writable and executable. No call or jump of the exe goes there.
The ceiling's tables and routine are in a second piece (CAVE_2): the end of the last
page of the section .xcode, which follows .trace in memory. That section's content ends at
0x047d3a42, its declared size at 0x047d3c22, the file's bytes for it at 0x047d3dff and its
last page at 0x047d3fff; it is readable, writable and executable too. The file holds zeros
from 0x047d3a43 on, and no call, jump or stored address of the unencrypted sections points
into 0x047d3a43-0x047d3fff. (Version 5 kept the ceiling at 0x047b0130-0x047b01fb, below
the first piece; the larger routine of version 6 does not fit there, and that range is
unused again.)
"""
import struct
import sys

CAP = 99999900
UNIT = 100                      # the screens show 100 times the stored amount
CAVE = 0x047b0200
VALUE_TAB = CAVE                # 100 dwords, by rating 0-99
SALARY_TAB = CAVE + 0x190       # 100 dwords, by rating 0-99
AGE_TAB = CAVE + 0x320          # 64 words, percent, by age 0-63
SALARY_AGE_TAB = CAVE + 0x3a0   # 64 words, percent, by age 0-63
POSITION_TAB = CAVE + 0x420     # 16 words, percent, by registered position
FAME_AT = CAVE + 0x440          # dword: percent of value per 1000 popularity points
SPREAD_LOW_AT = CAVE + 0x444    # dword: lowest factor of the spread, in thousandths
SPREAD_RANGE_AT = CAVE + 0x448  # dword: width of the spread, in thousandths
BUDGET_T_AT = CAVE + 0x44c      # dword: transfer budget, percent of the mean value of the best 16
BUDGET_S_AT = CAVE + 0x450      # dword: salary budget, percent of the mean salary of the best 16
HUNDRED_AT = CAVE + 0x454       # dword 100
THOUSAND_AT = CAVE + 0x458      # dword 1000
MARK_AT = CAVE + 0x45c          # 4 bytes: MARK
MARK = b'MLM7'                  # MLTransfers.lua looks for its first three bytes
TALENT_TAB = CAVE + 0x480       # 64 bytes, by age 0-63: the rating above which a young player gets the
                                # talent bonus (255: no bonus at this age)
INCOME_N_CODE = CAVE + 0x460     # (0x4c0 to 0x4cb are not used)
INCOME_M_CODE = CAVE + 0x4cc
INCOME_SCALE_CODE = CAVE + 0x4d8
INCOME_S_CODE = CAVE + 0x4ec
LEAGUE_CODE = CAVE + 0x500
WAGES_KEEP_CODE = CAVE + 0x532
SALARY_CODE = CAVE + 0x540
BUDGET_T_CODE = CAVE + 0x580
BUDGET_S_CODE = CAVE + 0x5a0
LEAGUE1_TAB = CAVE + 0x5c0      # 23 dwords: league prize by place, first list (index 0 is not a place)
LEAGUE2_TAB = CAVE + 0x620      # 25 dwords: league prize by place, second list
RANK_STEP_AT = CAVE + 0x688     # double: rise of the club factor per place of the ranking
SHARE_AT = CAVE + 0x690         # dword: percent of a prize that goes to the transfer budget
BONUS_AT = CAVE + 0x694         # dword: percent of the game's role, band and award bonuses
PRIZE_CODE = CAVE + 0x6a0
BONUS_R_CODE = CAVE + 0x6e0
BONUS_END_CODE = CAVE + 0x700
CUP_TAB = CAVE + 0x720          # 73 rows of 12 bytes: competition, stage, amount
FEE_CODE = CAVE + 0xa90         # (0x480 in version 3)
TALENT_STEP_AT = CAVE + 0xb80   # dword: percent of value per rating point above TALENT_TAB
TALENT_MAX_AT = CAVE + 0xb84    # dword: the most percent
TALENT_CAP_AT = CAVE + 0xb88    # dword: the most the bonus can be, as an amount
INCOME_AT = CAVE + 0xb8c        # dword: percent of the game's two yearly incomes
LEAGUE_IDS_AT = CAVE + 0xb90    # 12 words: leagues with a prize list of their own
LEAGUE_COUNT_AT = CAVE + 0xba8  # dword: how many of them are used
INCOME_WAGES_AT = CAVE + 0xbac  # dword: percent of the wage bill that is added to the yearly income
LEAGUE_ROWS_TAB = CAVE + 0xbb0  # 12 rows of 24 words: prize by place in units of LEAGUE_UNIT, index 0 unused
LEAGUE_ROWS, LEAGUE_ROW_WORDS, LEAGUE_UNIT = 12, 24, 100
CAVE_SIZE = 0xdf0
CAVE_LIMIT = 0x047b1000
# a second piece, the unused end of the next section (.xcode): the price ceiling of the
# computer clubs (only written when CEILING is on)
CAVE_2 = 0x047d3c40
CAVE_2_SIZE = 0x180
CAVE_2_LIMIT = 0x047d4000
CEILING_TAB = CAVE_2            # 10 dwords, by club level 0-9: the value a club of that level takes for sure
CEILING_TOP = CAVE_2 + 0x28     # 10 bytes, by club level: the highest rating it takes in the second, wide search
STRETCH_AT = CAVE_2 + 0x34      # dword: percent above the ceiling at which the chance to take a player reaches none
NEED_AT = CAVE_2 + 0x38         # dword: 100 + the percent by which need raises the ceiling
LISTED_AT = CAVE_2 + 0x3c       # dword: percent of his value that counts for a player listed by his club
FREE_AT = CAVE_2 + 0x40         # dword: the same for a player signed without a transfer (status 1 or 2)
CEILING_CODE = CAVE_2 + 0x44
NO_CEILING = 0xffffffff         # in CEILING_TAB: this level takes any value
NO_TOP = 0xff                   # in CEILING_TOP: this level takes any rating
LEVELS = 10
# the highest overall of the rating range of a club, by level 0 to 9 (fcn_0365d08d)
WINDOW_TOP = (74, 75, 76, 77, 78, 79, 80, 83, 86, 99)
# the club ranking places of each level, 9 down to 0 (fcn_036720d7 and fcn_03672359; the last has no end)
LEVEL_PLACES = ((1, 10), (11, 20), (21, 50), (51, 80), (81, 120), (121, 170), (171, 220), (221, 260), (261, 300),
                (301, None))

FEE_SITE = 0x038ab8db
FEE_SITE_OLD = bytes.fromhex('83f844760c8db8bcffffff69ff28230000')
SALARY_SITE = 0x038ac875
SALARY_SITE_OLD = bytes.fromhex('89c1c1e10429c1')
SALARY_BLOCK_END = 0x038ac8d7
BUDGET_T_SITE = 0x038adc47
BUDGET_T_SITE_OLD = bytes.fromhex('01f68b4030')
BUDGET_S_SITE = 0x038add08
BUDGET_S_SITE_OLD = bytes.fromhex('8d3441e8d5e3f6ff')
MODE_OBJECT_GETTER = 0x0381c0e5
MENU_GETTER = 0x03808865          # -> object whose +0x20 is the game mode number
MASTER_LEAGUE = 0x13
BALANCE_ADD = 0x038aadb7
TRANSFER_BUDGET_ADD = 0x038aac87
CUP_TABLE, CUP_ROWS = 0x0216b178, 73    # the game's own table
LEAGUE1_SITE, LEAGUE1_SITE_OLD = 0x038aa2dd, bytes.fromhex('8b848584feffff')
LEAGUE2_SITE, LEAGUE2_SITE_OLD = 0x038aa2c6, bytes.fromhex('8b8485e0feffff')
LEAGUE1_PLACES, LEAGUE2_PLACES = 22, 24
PRIZE_SITE_1, PRIZE_SITE_1_OLD = 0x03640ac5, bytes.fromhex('e8eda22600')
PRIZE_SITE_2, PRIZE_SITE_2_OLD = 0x03640b78, bytes.fromhex('e83aa22600')
RANK_SITE, RANK_SITE_OLD = 0x038aca1b, bytes.fromhex('88fef201')
RANK_STEP_OLD = 0.004000000189989805
BONUS_R_SITE, BONUS_R_SITE_OLD = 0x038aca2b, bytes.fromhex('03b5b0ffffff')
BONUS_END_SITE, BONUS_END_SITE_OLD = 0x038acd96, bytes.fromhex('8b85ccffffff0385b0ffffff')
YEARS_SITE, YEARS_SITE_OLD = 0x03887fc1, bytes.fromhex('b803000000')
# yearly income: season_income (fcn_038ade76), the amount by rank (fcn_038a9e6b), and the
# same amount by club level when a career is set up (fcn_038adf0c)
INCOME_N_SITE, INCOME_N_SITE_OLD = 0x038adeee, bytes.fromhex('8d863e56cbff')   # lea eax, [esi - 0x34a9c2]
INCOME_M_SITE, INCOME_M_SITE_OLD = 0x038a9e9c, bytes.fromhex('69c088130000')   # imul eax, eax, 5000
INCOME_S_SITE, INCOME_S_SITE_OLD = 0x038ae025, bytes.fromhex('81c6983a0000')   # add esi, 15000
# season_income calls the wage bill function and throws the result away; right after that call:
# mov eax, [ebp + 8]; push eax; call club_popularity
INCOME_W_SITE, INCOME_W_SITE_OLD = 0x038adeaa, bytes.fromhex('8b450850e8a2a9fcff')
CLUB_POPULARITY = 0x03878855
# ai_candidates (fcn_0365f5c2): a player who passed every test is put on the list of candidates:
# mov ecx, [ebp + 0x24]; push esi; call take
CEILING_SITE, CEILING_SITE_OLD = 0x0365fb0d, bytes.fromhex('8b4d2456e8aa98ac00')
AI_CANDIDATES, AI_PICK, AI_MAX_OVERALL = 0x0365f5c2, 0x03660c52, 0x0365d08d
AI_NEXT_PLAYER = 0x0365fb28                     # where ai_candidates goes on when a player fails a test
AI_TAKEN = 0x0365fb16                           # the instruction after the replaced ones
AI_PICK_RETURNS = (0x03660d58, 0x03660db9)      # where ai_candidates returns to: its two calls in ai_pick_candidate
TAKE = 0x041293c0                               # adds an id pair to a list (thiscall, one argument)
RATING = 0x03853b42                             # (player record, -> position or 13, kind) -> rating in al
# cup_prize: the amounts for a cup that has no row in the table, by stage (immediates of six mov edi)
NATIONAL_SITES = ((0x038aa43a, 20000), (0x038aa446, 10000), (0x038aa452, 5000), (0x038aa45e, 1000),
                  (0x038aa46a, 500), (0x038aa476, 300))
NATIONAL_STAGES = ((0,), (1,), (2, 3), (4,), (5,), (6,))        # the stages each of the six serves
# the game's cup table: (competition, stage, amount)
GAME_CUP_ROWS = struct.iter_unpack('<3I', bytes.fromhex(
    '0200000000000000803801000200000001000000409c00000200000003000000307500000200000004000000204e0000'
    '0200000007000000102700000200000009000000881300000300000000000000307500000300000001000000204e0000'
    '0300000003000000983a00000300000004000000102700000300000005000000881300000300000007000000b80b0000'
    '0300000009000000e80300000400000000000000b8880000040000000100000010270000050000000000000080380100'
    '0500000001000000409c00000500000003000000307500000500000004000000204e0000050000000700000010270000'
    '0500000009000000881300003000000000000000803801003000000001000000409c0000300000000300000030750000'
    '3000000004000000204e0000300000000700000010270000300000000900000088130000060000000000000030750000'
    '0600000001000000204e00000600000003000000983a0000060000000400000010270000060000000700000088130000'
    '0600000009000000b80b0000060000000a000000e80300005b00000000000000307500005b00000001000000204e0000'
    '5b00000003000000983a00005b00000004000000102700005b00000007000000881300005b00000009000000b80b0000'
    '5b0000000a000000e80300000700000000000000b8880000070000000100000010270000080000000000000080380100'
    '0800000001000000409c00000800000003000000307500000800000004000000204e0000080000000700000010270000'
    '0800000009000000881300000100000000000000409c00000100000001000000204e0000010000000200000010270000'
    '0100000003000000881300004900000000000000881300004900000001000000b80b00004a0000000000000088130000'
    '4a00000001000000b80b00004b00000000000000881300004b00000001000000b80b00004c0000000000000088130000'
    '4c00000001000000b80b00004d00000000000000881300004d00000001000000b80b00004e0000000000000088130000'
    '4e00000001000000b80b00004f00000000000000881300004f00000001000000b80b0000520000000000000088130000'
    '5200000001000000b80b00005300000000000000881300005300000001000000b80b0000540000000000000088130000'
    '5400000001000000b80b0000'))
GAME_CUP_ROWS = tuple(GAME_CUP_ROWS)
assert len(GAME_CUP_ROWS) == CUP_ROWS
# what cup_prize gives for a cup without a row, by stage (switch at 0x038aa42b)
CUP_FALLBACK = {0: 20000, 1: 10000, 2: 5000, 3: 5000, 4: 1000, 5: 500, 6: 300}
CUP_NONE = (0x2d, 0x2e, 0x2f, 0x36, 0x37, 0x46, 0x47, 0x48)
# league_prize's four lists, index 0 to the last place
GAME_LEAGUE = {
    'first': (0, 150000, 130000, 100000, 80000, 60000, 50000, 45000, 40000, 35000, 30000, 27000, 24000, 21000,
              18000, 15000, 12000, 9000, 7000, 5000, 3000, 3000, 3000),
    'second': (0, 20000, 15000, 12000, 10000, 9000, 8000, 7000, 6000, 5000, 4000, 3000, 2000, 1500, 1000, 900,
               800, 700, 600, 500, 450, 400, 350, 300, 250),
    60: (0, 20000, 10000, 8000, 6000, 4000, 2000, 1000) + (0,) * 15,
    61: (0, 2000, 1000, 500) + (0,) * 19,
}

POSITIONS = ('GK', 'CB', 'LB', 'RB', 'DMF', 'CMF', 'LMF', 'RMF', 'AMF', 'LWF', 'RWF', 'SS', 'CF')
HASH_A, HASH_B = 0x01000193, 0x9e3779b1
HASH_C = 0x85ebca6b             # the last step of the hash of the ceiling (player and buying club)

FEE_SOURCE = f'''
    cmp eax, 99
    jbe f1
    mov eax, 99
f1: mov edi, eax
    mov eax, dword ptr [eax*4 + {VALUE_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx edx, byte ptr [ecx + {TALENT_TAB}]
    sub edi, edx
    jg t1
    xor edi, edi
t1: imul edi, dword ptr [{TALENT_STEP_AT}]
    cmp edi, dword ptr [{TALENT_MAX_AT}]
    jbe t2
    mov edi, dword ptr [{TALENT_MAX_AT}]
t2: movzx ecx, word ptr [ecx*2 + {AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    push eax
    mul edi
    div dword ptr [{HUNDRED_AT}]
    cmp eax, dword ptr [{TALENT_CAP_AT}]
    jbe t3
    mov eax, dword ptr [{TALENT_CAP_AT}]
t3: pop ecx
    add eax, ecx
    mov ecx, dword ptr [ebx + 4]
    shr ecx, 28
    movzx ecx, word ptr [ecx*2 + {POSITION_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    movzx ecx, word ptr [ebx + 0x2c]
    imul edx, dword ptr [ebx + 0x30], {HASH_A}
    xor ecx, edx
    imul ecx, ecx, {HASH_B}
    shr ecx, 24
    imul ecx, dword ptr [{SPREAD_RANGE_AT}]
    shr ecx, 8
    add ecx, dword ptr [{SPREAD_LOW_AT}]
    mul ecx
    div dword ptr [{THOUSAND_AT}]
    cmp eax, {CAP}
    jbe f2
    mov eax, {CAP}
f2: mov edi, eax
    mov ecx, dword ptr [ebx + 0xb4]
    shr ecx, 11
    and ecx, 0xfff
    imul ecx, dword ptr [{FAME_AT}]
    mul ecx
    mov ecx, 100000
    div ecx
    add edi, eax
    mov dword ptr [ebp - 0xc], 0
    ret
'''
SALARY_SOURCE = f'''
    cmp eax, 99
    jbe s1
    mov eax, 99
s1: mov eax, dword ptr [eax*4 + {SALARY_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {SALARY_AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
    mov dword ptr [ebp - 0x38], eax
    mov dword ptr [ebp - 0x34], 0
    ret
'''
BUDGET_T_SOURCE = f'''
    mov eax, dword ptr [eax + 0x30]
    push eax
    push edx
    mov eax, esi
    mul dword ptr [{BUDGET_T_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov esi, eax
    pop edx
    pop eax
    test esi, esi
    ret
'''
BUDGET_S_SOURCE = f'''
    push edx
    mul dword ptr [{BUDGET_S_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
    lea esi, [ecx + eax]
    jmp {MODE_OBJECT_GETTER}
'''
PRIZE_SOURCE = f'''
    mov eax, dword ptr [esp + 4]
    push eax
    call {BALANCE_ADD}
    add esp, 4
    call {MENU_GETTER}
    cmp dword ptr [eax + 0x20], {MASTER_LEAGUE}
    jne p1
    mov eax, dword ptr [esp + 4]
    mov eax, dword ptr [eax]
    imul dword ptr [{SHARE_AT}]
    idiv dword ptr [{HUNDRED_AT}]
    push eax
    push esp
    call {TRANSFER_BUDGET_ADD}
    add esp, 8
p1: ret
'''
BONUS_R_SOURCE = f'''
    push eax
    push edx
    mov eax, esi
    mul dword ptr [{BONUS_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov esi, eax
    pop edx
    pop eax
    add esi, dword ptr [ebp - 0x50]
    ret
'''
BONUS_END_SOURCE = f'''
    push edx
    mov eax, dword ptr [ebp - 0x34]
    add eax, dword ptr [ebp - 0x50]
    mul dword ptr [{BONUS_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
    ret
'''
INCOME_N_SOURCE = f'''
    lea eax, [esi - 0x34a9c2]
    call {INCOME_SCALE_CODE}
    mov ecx, eax
    mov eax, dword ptr [ebp - 4]
    mul dword ptr [{INCOME_WAGES_AT}]
    div dword ptr [{HUNDRED_AT}]
    add eax, ecx
    ret
'''
# [ebp - 4] of season_income holds a flag byte for the wage bill function, which nothing
# reads after that call. The routine keeps the wage bill there and goes on to
# club_popularity with the argument the replaced instructions pushed. With the percent at
# INCOME_WAGES_AT 0 this routine is not used and whatever [ebp - 4] holds is multiplied by 0.
WAGES_KEEP_SOURCE = f'''
    mov dword ptr [ebp - 4], eax
    pop eax
    push dword ptr [ebp + 8]
    push eax
    jmp {CLUB_POPULARITY}
'''
INCOME_M_SOURCE = f'''
    imul eax, eax, 0x1388
    jmp {INCOME_SCALE_CODE}
'''
INCOME_SCALE_SOURCE = f'''
    test eax, eax
    jle i1
    push edx
    mul dword ptr [{INCOME_AT}]
    div dword ptr [{HUNDRED_AT}]
    pop edx
i1: ret
'''
INCOME_S_SOURCE = f'''
    add esi, 0x3a98
    push eax
    mov eax, esi
    call {INCOME_SCALE_CODE}
    mov esi, eax
    pop eax
    ret
'''
LEAGUE_SOURCE = f'''
    xor ecx, ecx
    jmp l3
l1: movzx edx, word ptr [ecx*2 + {LEAGUE_IDS_AT}]
    cmp edx, edi
    je l2
    inc ecx
l3: cmp ecx, dword ptr [{LEAGUE_COUNT_AT}]
    jb l1
    mov eax, dword ptr [eax*4 + {LEAGUE1_TAB}]
    ret
l2: imul ecx, ecx, {LEAGUE_ROW_WORDS}
    add ecx, eax
    movzx eax, word ptr [ecx*2 + {LEAGUE_ROWS_TAB}]
    imul eax, eax, {LEAGUE_UNIT}
    ret
'''
# The price ceiling. Entered by a call from ai_candidates (ebp = its frame) in the place of
# `mov ecx, [ebp + 0x24]; push esi; call take`. The player record the function is looking
# at is its local [ebp - 0x28], the plan record of the buying club its argument
# [ebp + 0x18] (club id in the first dword), the status band the slot asks for its last
# argument ([ebp + 0x30] -> number). The club level is not handed to ai_candidates; it is
# an argument of its only caller, ai_pick_candidate ([its ebp + 0x1c] -> level), whose
# frame is the saved ebp; the byte [its ebp + 0x1b] is 1 in the second, wide search (lowest
# overall handed in as 0). If ai_candidates was not called from one of the two known
# places, or the level is not 0 to 9, the player is taken as in the game. Otherwise:
#   - the rating is fetched with the game's rating call, as the fee function does;
#   - in the wide search a rating above CEILING_TOP[level] is refused;
#   - a level without a ceiling takes the player;
#   - the limit is the ceiling, raised by NEED in the wide search and for a slot that asks
#     for a band, and then by up to STRETCH percent by the hash of player and club;
#   - the value is worked out by FEE_CODE (record in ebx, scratch dword at [ebp - 0xc]),
#     counted at FREE percent for status 1 or 2 and else at LISTED percent with mark 29 or
#     30, and refused if it is above the limit.
# Refused: the return address is dropped and the game's "next player" follows.
# Locals: [ebp - 4] limit, [ebp - 8] position 13, [ebp - 0xc] scratch of FEE_CODE,
# [ebp - 0x10] wide search, [ebp - 0x14] highest rating, [ebp - 0x18] buying club,
# [ebp - 0x1c] need.
CEILING_SOURCE = f'''
    push ebx
    push edi
    push ebp
    mov ebp, esp
    sub esp, 0x1c
    mov eax, dword ptr [ebp]
    mov ebx, dword ptr [eax - 0x28]
    mov ecx, dword ptr [eax + 4]
    cmp ecx, {AI_PICK_RETURNS[0]}
    je c1
    cmp ecx, {AI_PICK_RETURNS[1]}
    jne c3
c1: mov ecx, dword ptr [eax + 0x18]
    mov ecx, dword ptr [ecx]
    mov dword ptr [ebp - 0x18], ecx
    mov edx, dword ptr [eax + 0x30]
    mov edx, dword ptr [edx]
    mov eax, dword ptr [eax]
    movzx ecx, byte ptr [eax + 0x1b]
    mov dword ptr [ebp - 0x10], ecx
    or edx, ecx
    mov dword ptr [ebp - 0x1c], edx
    mov eax, dword ptr [eax + 0x1c]
    mov eax, dword ptr [eax]
    cmp eax, {LEVELS - 1}
    ja c3
    movzx ecx, byte ptr [eax + {CEILING_TOP}]
    mov dword ptr [ebp - 0x14], ecx
    mov eax, dword ptr [eax*4 + {CEILING_TAB}]
    mov dword ptr [ebp - 4], eax
    mov dword ptr [ebp - 8], 0xd
    push 2
    lea eax, [ebp - 8]
    push eax
    push ebx
    call {RATING}
    add esp, 12
    movzx eax, al
    cmp dword ptr [ebp - 0x10], 0
    je c2
    cmp eax, dword ptr [ebp - 0x14]
    ja c4
c2: cmp dword ptr [ebp - 4], -1
    je c3
    call {FEE_CODE}
    cmp dword ptr [ebp - 0x1c], 0
    je c5
    mov eax, dword ptr [ebp - 4]
    mul dword ptr [{NEED_AT}]
    div dword ptr [{HUNDRED_AT}]
    mov dword ptr [ebp - 4], eax
c5: movzx ecx, word ptr [ebx + 0x2c]
    imul edx, dword ptr [ebx + 0x30], {HASH_A}
    xor ecx, edx
    imul edx, dword ptr [ebp - 0x18], {HASH_B}
    xor ecx, edx
    imul ecx, ecx, {HASH_C}
    shr ecx, 24
    imul ecx, dword ptr [{STRETCH_AT}]
    mov eax, dword ptr [ebp - 4]
    mul ecx
    mov ecx, 25600
    div ecx
    add dword ptr [ebp - 4], eax
    mov ecx, dword ptr [ebx + 0xb4]
    and ecx, 0xf
    dec ecx
    cmp ecx, 1
    mov ecx, {FREE_AT}
    jbe c6
    test dword ptr [ebx + 0xb8], 0x60000000
    jz c7
    mov ecx, {LISTED_AT}
c6: mov eax, edi
    mul dword ptr [ecx]
    div dword ptr [{HUNDRED_AT}]
    mov edi, eax
c7: cmp edi, dword ptr [ebp - 4]
    ja c4
c3: mov esp, ebp
    pop ebp
    pop edi
    pop ebx
    pop eax
    mov ecx, dword ptr [ebp + 0x24]
    push esi
    push eax
    jmp {TAKE}
c4: mov esp, ebp
    pop ebp
    pop edi
    pop ebx
    add esp, 4
    jmp {AI_NEXT_PLAYER}
'''
# the assembled routines (python3 money_cave.py build checks them against the source above)
FEE_BYTES = bytes.fromhex(
    '83f8637605b86300000089c78b048500027b048b4b1cc1e90783e13f0fb69180067b0429d77f0231ff0faf3d800d7b043b3d840d7b0476'
    '068b3d840d7b040fb70c4d20057b04f7e1f73554067b0450f7e7f73554067b043b05880d7b047605a1880d7b045901c88b4b04c1e91c0f'
    'b70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b179379ec1e9180faf0d48067b04c1e908030d44067b04f7e1'
    'f73558067b043d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745'
    'f400000000c3')
SALARY_BYTES = bytes.fromhex('83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f73554067b048945c8c745cc00000000c3')
BUDGET_T_BYTES = bytes.fromhex('8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3')
BUDGET_S_BYTES = bytes.fromhex('52f72550067b04f73554067b045a8d3401e92fb906ff')
PRIZE_BYTES = bytes.fromhex('8b44240450e80da50fff83c404e8b37f05ff83782013751c8b4424048b00f72d90087b04f73d54067b045054e8b6a30fff83c408c3')
BONUS_R_BYTES = bytes.fromhex('505289f0f72594087b04f73554067b0489c65a580375b0c3')
BONUS_END_BYTES = bytes.fromhex('528b45cc0345b0f72594087b04f73554067b045ac3')
INCOME_N_BYTES = bytes.fromhex('8d863e56cbffe86d00000089c18b45fcf725ac0d7b04f73554067b0401c8c3')
WAGES_KEEP_BYTES = bytes.fromhex('8945fc58ff750850e916810cff')
INCOME_M_BYTES = bytes.fromhex('69c088130000eb04')
INCOME_SCALE_BYTES = bytes.fromhex('85c07e0e52f7258c0d7b04f73554067b045ac3')
INCOME_S_BYTES = bytes.fromhex('81c6983a00005089f0e8deffffff89c658c3')
LEAGUE_BYTES = bytes.fromhex('31c9eb0d0fb7144d900d7b0439fa7411413b0da80d7b0472eb8b0485c0077b04c36bc91801c10fb7044db00d7b046bc064c3')
CEILING_BYTES = bytes.fromhex(
    '53575589e583ec1c8b45008b58d88b480481f9580d6603740c81f9b90d66030f85f70000008b48188b09894de88b50308b128b000fb648'
    '1b894df009ca8955e48b401c8b0083f8090f87ce0000000fb688683c7d04894dec8b0485403c7d048945fcc745f80d0000006a028d45f8'
    '5053e849fe07ff83c40c0fb6c0837df00074093b45ec0f87a2000000837dfcff0f8488000000e873cffdff837de40074128b45fcf72578'
    '3c7d04f73554067b048945fc0fb74b2c6953309301000131d16955e8b179379e31d169c96bcaeb85c1e9180faf0d743c7d048b45fcf7e1'
    'b900640000f7f10145fc8b8bb400000083e10f4983f901b9803c7d047611f783b8000000000000607411b97c3c7d0489f8f721f7355406'
    '7b0489c73b7dfc771089ec5d5f5b588b4d245650e9105695ff89ec5d5f5b83c404e96bbde8fe')
assert CEILING_CODE + len(CEILING_BYTES) <= CAVE_2 + CAVE_2_SIZE <= CAVE_2_LIMIT
ROUTINES = ((FEE_CODE, FEE_SOURCE, 'FEE_BYTES'), (SALARY_CODE, SALARY_SOURCE, 'SALARY_BYTES'),
            (BUDGET_T_CODE, BUDGET_T_SOURCE, 'BUDGET_T_BYTES'), (BUDGET_S_CODE, BUDGET_S_SOURCE, 'BUDGET_S_BYTES'),
            (PRIZE_CODE, PRIZE_SOURCE, 'PRIZE_BYTES'), (BONUS_R_CODE, BONUS_R_SOURCE, 'BONUS_R_BYTES'),
            (BONUS_END_CODE, BONUS_END_SOURCE, 'BONUS_END_BYTES'),
            (INCOME_N_CODE, INCOME_N_SOURCE, 'INCOME_N_BYTES'), (INCOME_M_CODE, INCOME_M_SOURCE, 'INCOME_M_BYTES'),
            (INCOME_SCALE_CODE, INCOME_SCALE_SOURCE, 'INCOME_SCALE_BYTES'),
            (INCOME_S_CODE, INCOME_S_SOURCE, 'INCOME_S_BYTES'), (LEAGUE_CODE, LEAGUE_SOURCE, 'LEAGUE_BYTES'),
            (WAGES_KEEP_CODE, WAGES_KEEP_SOURCE, 'WAGES_KEEP_BYTES'))

# limits the module keeps, so that no step of the routines can overflow 32 bits
MAX_AGE_PERCENT = 300
MAX_POSITION_PERCENT = 200
MAX_SPREAD = 30
MAX_FAME = 100
MAX_SALARY = 40000000
MAX_SALARY_AGE_PERCENT = 200
MIN_BUDGET, MAX_BUDGET = 0.1, 10.0
MIN_PRIZE, MAX_PRIZE = 0.001, 2000      # millions on the screen
MAX_SHARE = 100
MIN_GAP, MAX_GAP = 1.0, 10.0
MAX_BONUS = 1000
MIN_YEARS, MAX_YEARS = 1, 5
MAX_TALENT_STEP, MAX_TALENT_PERCENT = 50, 200
MIN_INCOME, MAX_INCOME = 10, 1000
MAX_INCOME_WAGES = 100                  # percent: the wage bill times this still fits the division
MAX_LEAGUE_ROW = 650                    # millions: a place of a list by league is kept in 16 bits
MIN_CEILING, MAX_CEILING = 0.01, 9999   # millions; 0 in the list: no ceiling for that group of clubs
MAX_STRETCH, MAX_NEED = 300, 300        # percent: the largest ceiling times both still fits 32 bits
NO_TALENT = 255

# the code the routines rely on: name, address, byte count (MLMoney.lua compares these
# bytes of the running game with the bytes of the exe file before it writes anything)
CONTEXT = (
    ('fee code', 0x038ab832, 228),          # start of the fee function to the end of the changed part and its use
    ('salary code', 0x038ac6f8, 15),        # the player record goes into ebx
    ('salary code 2', 0x038ac86f, 110),     # the rating part and what follows
    ('salary roles', 0x038ac937, 244),      # role bonus and club factor, up to the sum
    ('salary sum', 0x038aca2b, 49),         # where the two numbers are added
    ('salary end', 0x038aca5c, 870),        # band bonus, award bonuses, the last sum and its limits
    ('budget code', 0x038adc0b, 346),       # both budget sums to the place they are stored
    ('position', 0x03827961, 17),           # getter of the registered position
    ('age', 0x03827ba9, 20),                # getter of the age
    ('cup prize', 0x038aa307, 383),         # the whole function
    ('cup table', CUP_TABLE, 876),          # the game's 73 rows
    ('league prize', 0x038a9ebb, 1100),     # the whole function
    ('prize step', 0x03640abe, 200),        # both places where a prize is paid
    ('balance add', BALANCE_ADD, 98),       # the whole function
    ('budget add', TRANSFER_BUDGET_ADD, 98),  # the whole function
    ('mode number', MENU_GETTER, 6),        # the whole function
    ('years limit', 0x03887f5d, 109),       # the whole function
    ('income', 0x038ade76, 141),            # season_income, the whole function
    ('rank income', 0x038a9e6b, 66),        # the whole function
    ('career money', 0x038adfb6, 144),      # club_money_setup: the amount by club level
)


# the same for MLTransfers.lua (the price ceiling); compared only when CEILING is on
CONTEXT_CEILING = (
    ('choose', AI_CANDIDATES, 1462),        # ai_candidates, the whole function
    ('pick', AI_PICK, 373),                 # ai_pick_candidate up to the end of its two calls of ai_candidates
    ('range', AI_MAX_OVERALL, 152),         # the highest overall of a club's rating range, by level (WINDOW_TOP)
    ('rating', RATING, 9),                  # the rating call of the fee function
    ('take', TAKE, 114),                    # the function that adds a player to the candidates, both its returns
)


def call(site, target):
    return b'\xe8' + struct.pack('<i', target - (site + 5))


# what MLTransfers.lua must find in the memory of MLMoney.lua before it writes: name,
# address, bytes. (FEE_BYTES is defined above; the mark is compared apart, for the log.)
MONEY_NEEDED = (('value routine', FEE_CODE, FEE_BYTES), ('number 100', HUNDRED_AT, struct.pack('<I', 100)))


FEE_SITE_NEW = call(FEE_SITE, FEE_CODE) + b'\x90' * 12
SALARY_SITE_NEW = call(SALARY_SITE, SALARY_CODE) + b'\xeb' + bytes([SALARY_BLOCK_END - (SALARY_SITE + 7)])
BUDGET_T_SITE_NEW = call(BUDGET_T_SITE, BUDGET_T_CODE)
BUDGET_S_SITE_NEW = call(BUDGET_S_SITE, BUDGET_S_CODE) + b'\x90' * 3
#        name, address, bytes of the game, bytes of the module
# ('years': the number in its last four bytes is a setting, and so are the amounts of the six
# 'nat' places; Tables.sites() gives them as written)
SITES = (('fee', FEE_SITE, FEE_SITE_OLD, FEE_SITE_NEW), ('salary', SALARY_SITE, SALARY_SITE_OLD, SALARY_SITE_NEW),
         ('budget 1', BUDGET_T_SITE, BUDGET_T_SITE_OLD, BUDGET_T_SITE_NEW),
         ('budget 2', BUDGET_S_SITE, BUDGET_S_SITE_OLD, BUDGET_S_SITE_NEW),
         ('cup 1', 0x038aa400, struct.pack('<I', CUP_TABLE), struct.pack('<I', CUP_TAB)),
         ('cup 2', 0x038aa408, struct.pack('<I', CUP_TABLE + 4), struct.pack('<I', CUP_TAB + 4)),
         ('cup 3', 0x038aa423, struct.pack('<I', CUP_TABLE + 8), struct.pack('<I', CUP_TAB + 8)),
         ('league 1', LEAGUE1_SITE, LEAGUE1_SITE_OLD, call(LEAGUE1_SITE, LEAGUE_CODE) + b'\x90' * 2),
         ('league 2', LEAGUE2_SITE, LEAGUE2_SITE_OLD, b'\x8b\x04\x85' + struct.pack('<I', LEAGUE2_TAB)),
         ('prize 1', PRIZE_SITE_1, PRIZE_SITE_1_OLD, call(PRIZE_SITE_1, PRIZE_CODE)),
         ('prize 2', PRIZE_SITE_2, PRIZE_SITE_2_OLD, call(PRIZE_SITE_2, PRIZE_CODE)),
         ('pay gap', RANK_SITE, RANK_SITE_OLD, struct.pack('<I', RANK_STEP_AT)),
         ('bonus 1', BONUS_R_SITE, BONUS_R_SITE_OLD, call(BONUS_R_SITE, BONUS_R_CODE) + b'\x90'),
         ('bonus 2', BONUS_END_SITE, BONUS_END_SITE_OLD, call(BONUS_END_SITE, BONUS_END_CODE) + b'\x90' * 7),
         ('years', YEARS_SITE, YEARS_SITE_OLD, b'\xb8\x05\x00\x00\x00'),
         ('income 1', INCOME_N_SITE, INCOME_N_SITE_OLD, call(INCOME_N_SITE, INCOME_N_CODE) + b'\x90'),
         ('income 2', INCOME_M_SITE, INCOME_M_SITE_OLD, call(INCOME_M_SITE, INCOME_M_CODE) + b'\x90'),
         ('income 3', INCOME_S_SITE, INCOME_S_SITE_OLD, call(INCOME_S_SITE, INCOME_S_CODE) + b'\x90'),
         ('income 4', INCOME_W_SITE, INCOME_W_SITE_OLD, call(INCOME_W_SITE, WAGES_KEEP_CODE) + b'\x90' * 4),
         ) + tuple(('nat %d' % i, at, struct.pack('<I', old), struct.pack('<I', old))
                   for i, (at, old) in enumerate(NATIONAL_SITES)) + (
         ('ceiling', CEILING_SITE, CEILING_SITE_OLD, call(CEILING_SITE, CEILING_CODE) + b'\x90' * 4),)
assert all(len(old) == len(new) for _, _, old, new in SITES)


def f32(x):
    return struct.unpack('<f', struct.pack('<f', x))[0]


def curve(knots, lo, hi, geometric):
    """Value for every whole number lo..hi from a list of (x, y) knots: straight lines
    between the knots (or, geometric, straight lines of the logarithm), the end values
    outside them."""
    out = []
    for x in range(lo, hi + 1):
        if x <= knots[0][0]:
            y = knots[0][1]
        elif x >= knots[-1][0]:
            y = knots[-1][1]
        else:
            for (x1, y1), (x2, y2) in zip(knots, knots[1:]):
                if x1 <= x <= x2:
                    t = (x - x1) / (x2 - x1)
                    y = y1 * (y2 / y1) ** t if geometric else y1 + (y2 - y1) * t
                    break
        out.append(y)
    return out


def amount(millions):
    """Millions on the screen -> stored amount, rounded to 10 (1,000 on the screen)."""
    return int(millions * 1000 + 0.5) * 10


def clamp(v, lo, hi):
    return lo if v < lo else hi if v > hi else v


class Tables:
    """The settings of MLMoney.lua as the module stores them.

    value, age: lists of (x, y) knots; position: {name: percent}; spread: percent;
    fame: percent per 1,000 points; salary: knots or None (the salary formula stays the
    game's); salary_age: knots; budget_transfer, budget_salary: factor or None (the
    game's own 2); cup: list of (competition, stage, millions) or None; league, league_2:
    millions for place 1 to 22 and 1 to 24, or None; prize_share: percent or None;
    pay_gap: factor of the first club of the ranking or None (the game's own 2); bonus:
    percent or None; young_years: 1 to 5 or None (the game's own 3); talent: knots (age,
    rating) or None, talent_step: percent per rating point, talent_max: percent,
    talent_cap: millions; income: percent or None; league_by_id: list of (league, list of
    millions | percent of `league`) or None; cup_national: six amounts in millions or
    None; cup_tv: list of (competition, millions) or None; income_wages: percent of the
    wage bill added to the yearly income, or None; ceiling: 10 amounts in millions for the
    club ranking places of LEVEL_PLACES (best clubs first; 0: no ceiling), or None;
    ceiling_rating: with a ceiling, the second search of a club stays below the top of its
    rating range; ceiling_stretch: percent above its ceiling at which a club's chance to
    take a player has fallen to none; ceiling_need: percent by which need raises the
    ceiling; ceiling_listed, ceiling_free: percent of his value that counts for a listed
    player and for one signed without a transfer."""

    def __init__(self, value, age, position, spread, fame, salary, salary_age, budget_transfer, budget_salary,
                 cup=None, league=None, league_2=None, prize_share=None, pay_gap=None, bonus=None,
                 young_years=None, talent=None, talent_step=0, talent_max=0, talent_cap=0, income=None,
                 league_by_id=None, cup_national=None, cup_tv=None, income_wages=None, ceiling=None,
                 ceiling_rating=True, ceiling_stretch=0, ceiling_need=0, ceiling_listed=100, ceiling_free=100):
        self.value = [clamp(amount(m), 1, CAP) for m in curve(value, 0, 99, True)]
        self.age = [clamp(int(p + 0.5), 0, MAX_AGE_PERCENT) for p in curve(age, 0, 63, False)]
        self.position = [clamp(int(position[n] + 0.5), 0, MAX_POSITION_PERCENT) for n in POSITIONS] + [100] * 3
        s = clamp(int(spread + 0.5), 0, MAX_SPREAD)
        self.spread_low, self.spread_range = 1000 - 10 * s, 20 * s
        self.fame = clamp(int(fame + 0.5), 0, MAX_FAME)
        self.has_salary = bool(salary)
        self.has_gap = bool(pay_gap)
        self.gap = clamp(float(pay_gap), MIN_GAP, MAX_GAP) if pay_gap else 2.0
        self.rank_step = (self.gap - 1) / 250 if pay_gap else RANK_STEP_OLD
        self.salary = ([clamp(amount(m / self.gap), 1, MAX_SALARY) for m in curve(salary, 0, 99, True)]
                       if salary else [0] * 100)
        self.salary_age = [clamp(int(p + 0.5), 0, MAX_SALARY_AGE_PERCENT) for p in curve(salary_age, 0, 63, False)]
        self.budget_transfer = None if not budget_transfer else int(budget_transfer * 100 + 0.5)
        self.budget_salary = None if not budget_salary else int(budget_salary * 100 + 0.5)
        self.has_cup = cup is not None
        rows = [list(r) for r in GAME_CUP_ROWS]
        tv = dict((int(c), m) for c, m in cup_tv or ())
        for competition, stage, millions in cup or ():
            hit = [r for r in rows if r[0] == competition and r[1] == stage]
            assert hit, 'the game has no prize row for competition %d, stage %d' % (competition, stage)
            hit[0][2] = prize(millions + tv.get(competition, 0))
        self.cup_rows = [tuple(r) for r in rows]
        self.has_league, self.has_league_2 = league is not None, league_2 is not None
        assert league is None or len(league) == LEAGUE1_PLACES
        assert league_2 is None or len(league_2) == LEAGUE2_PLACES
        self.league = [0] + [prize(m, 0) for m in league] if self.has_league else [0] * (LEAGUE1_PLACES + 1)
        self.league_2 = [0] + [prize(m, 0) for m in league_2] if self.has_league_2 else [0] * (LEAGUE2_PLACES + 1)
        self.prize_share = None if not prize_share else clamp(int(prize_share + 0.5), 0, MAX_SHARE)
        self.bonus = None if bonus is None else clamp(int(bonus + 0.5), 0, MAX_BONUS)
        self.young_years = None if not young_years else clamp(int(young_years + 0.5), MIN_YEARS, MAX_YEARS)
        # talent: the rating above which the bonus starts, by age; ages above the last entry have none
        self.talent = [NO_TALENT] * 64
        if talent:
            last = int(talent[-1][0])
            for a, r in enumerate(curve(talent, 0, 63, False)):
                if a <= last:
                    self.talent[a] = clamp(int(r + 0.5), 0, 254)
        self.talent_step = clamp(int(talent_step + 0.5), 0, MAX_TALENT_STEP) if talent else 0
        self.talent_max = clamp(int(talent_max + 0.5), 0, MAX_TALENT_PERCENT) if talent else 0
        self.talent_cap = clamp(amount(talent_cap), 0, CAP) if talent else 0
        self.income = None if not income else clamp(int(income + 0.5), MIN_INCOME, MAX_INCOME)
        self.income_wages = None if not income_wages else clamp(int(income_wages + 0.5), 1, MAX_INCOME_WAGES)
        # lists by league: only with `league` on. A list shorter than 22 is filled with its last number.
        self.league_rows = []
        for league_id, what in (league_by_id or ()) if self.has_league else ():
            if isinstance(what, (list, tuple)):
                full = [prize(m, 0) for m in what] + [prize(what[-1], 0)] * (LEAGUE1_PLACES - len(what))
            else:
                full = [a * int(what + 0.5) // 100 for a in self.league[1:]]
            words = [0] + [min(a // LEAGUE_UNIT, 0xffff) for a in full[:LEAGUE1_PLACES]] + [0]
            assert len(words) == LEAGUE_ROW_WORDS
            self.league_rows.append((int(league_id), words))
        assert len(self.league_rows) <= LEAGUE_ROWS
        self.national = None if not cup_national else [prize(m) for m in cup_national]
        assert self.national is None or len(self.national) == len(NATIONAL_SITES)
        # by club level 0 to 9 (the list in the settings starts with the best clubs, level 9)
        assert ceiling is None or len(ceiling) == LEVELS
        self.ceiling = None if ceiling is None else [
            clamp(amount(m), amount(MIN_CEILING), amount(MAX_CEILING)) if m else NO_CEILING for m in reversed(ceiling)]
        self.ceiling_top = list(WINDOW_TOP) if ceiling_rating else [NO_TOP] * LEVELS
        self.ceiling_stretch = clamp(int(ceiling_stretch + 0.5), 0, MAX_STRETCH)
        self.ceiling_need = clamp(int(ceiling_need + 0.5), 0, MAX_NEED)
        self.ceiling_listed = clamp(int(ceiling_listed + 0.5), 0, 100)
        self.ceiling_free = clamp(int(ceiling_free + 0.5), 0, 100)

    def sites(self):
        """The places the module changes with these settings: (name, address, old, new)."""
        share, bonus, income = self.prize_share is not None, self.bonus is not None, self.income is not None
        wages = self.income_wages is not None
        on = {'fee': True, 'salary': self.has_salary, 'budget 1': self.budget_transfer is not None,
              'budget 2': self.budget_salary is not None, 'cup 1': self.has_cup, 'cup 2': self.has_cup,
              'cup 3': self.has_cup, 'league 1': self.has_league, 'league 2': self.has_league_2,
              'prize 1': share, 'prize 2': share, 'pay gap': self.has_gap, 'bonus 1': bonus, 'bonus 2': bonus,
              'years': self.young_years is not None, 'income 1': income or wages, 'income 2': income, 'income 3': income,
              'income 4': wages, 'ceiling': self.ceiling is not None}
        used = []
        for name, at, old, new in SITES:
            if name == 'years' and on[name]:
                new = b'\xb8' + struct.pack('<I', self.young_years)
            if name.startswith('nat '):
                if self.national is None:
                    continue
                new = struct.pack('<I', self.national[int(name[4:])])
            elif not on[name]:
                continue
            used.append((name, at, old, new))
        return used


def prize(millions, lowest=10):
    """Millions on the screen -> stored prize."""
    return clamp(amount(millions), lowest, amount(MAX_PRIZE))


def image(t):
    d = struct.pack('<100I', *t.value) + struct.pack('<100I', *t.salary) + struct.pack('<64H', *t.age)
    d += struct.pack('<64H', *t.salary_age) + struct.pack('<16H', *t.position)
    assert len(d) == FAME_AT - CAVE
    d += struct.pack('<7I', t.fame, t.spread_low, t.spread_range, t.budget_transfer or 200, t.budget_salary or 200,
                     100, 1000) + MARK
    pieces = [(at, globals()[name]) for at, _, name in ROUTINES]
    pieces += [(LEAGUE1_TAB, struct.pack('<23I', *t.league)), (LEAGUE2_TAB, struct.pack('<25I', *t.league_2)),
               (RANK_STEP_AT, struct.pack('<d', t.rank_step)),
               (SHARE_AT, struct.pack('<2I', t.prize_share or 0, 100 if t.bonus is None else t.bonus)),
               (CUP_TAB, b''.join(struct.pack('<3I', *r) for r in t.cup_rows)),
               (TALENT_TAB, bytes(t.talent)),
               (TALENT_STEP_AT, struct.pack('<4I', t.talent_step, t.talent_max, t.talent_cap, t.income or 100)),
               (LEAGUE_IDS_AT, struct.pack('<%dH' % len(t.league_rows), *[i for i, _ in t.league_rows])),
               (LEAGUE_COUNT_AT, struct.pack('<2I', len(t.league_rows), t.income_wages or 0)),
               (LEAGUE_ROWS_TAB, b''.join(struct.pack('<%dH' % LEAGUE_ROW_WORDS, *w) for _, w in t.league_rows))]
    for at, piece in sorted(pieces):
        assert len(d) <= at - CAVE, hex(at)
        d = d.ljust(at - CAVE, b'\0') + piece
    assert len(d) <= CAVE_SIZE
    return d.ljust(CAVE_SIZE, b'\0')


def image_2(t):
    """The second piece of memory: the ceilings by club level, the four numbers of the
    limit and the routine."""
    d = struct.pack('<%dI' % LEVELS, *t.ceiling) + bytes(t.ceiling_top)
    d = d.ljust(STRETCH_AT - CAVE_2, b'\0') + struct.pack('<4I', t.ceiling_stretch, 100 + t.ceiling_need,
                                                           t.ceiling_listed, t.ceiling_free)
    assert CAVE_2 + len(d) == CEILING_CODE
    d += CEILING_BYTES
    assert len(d) <= CAVE_2_SIZE
    return d.ljust(CAVE_2_SIZE, b'\0')


def spread_hash(id_low, id_high):
    """The byte the fee routine makes from a player's id."""
    x = (id_low & 0xffff) ^ (id_high * HASH_A & 0xffffffff)
    return (x * HASH_B & 0xffffffff) >> 24


def value(t, rating, age, popularity, position=5, player=(0, 0)):
    """What the fee routine leaves in edi: the player's value before a handed-in figure,
    the random change and the game's limit."""
    rating = min(rating, 99)
    x = t.value[rating] * t.age[age] // 100
    percent_more = min(max(0, rating - t.talent[age]) * t.talent_step, t.talent_max)
    x += min(x * percent_more // 100, t.talent_cap)
    x = x * t.position[position] // 100
    x = min(CAP, x * (t.spread_low + (spread_hash(*player) * t.spread_range >> 8)) // 1000)
    return x + x * (popularity * t.fame) // 100000


def level_of_place(place):
    """The club level 0 to 9 the game gives a place of its club ranking."""
    for level, (first, last) in zip(range(LEVELS - 1, -1, -1), LEVEL_PLACES):
        if last is None or place <= last:
            return level


def stretch_hash(player, club):
    """The byte the ceiling routine makes from a player's id and the buying club's id."""
    x = (player[0] & 0xffff) ^ (player[1] * HASH_A & 0xffffffff) ^ (club * HASH_B & 0xffffffff)
    return (x * HASH_C & 0xffffffff) >> 24


def limit(t, level, player=(0, 0), club=0, need=False):
    """The most a computer club of this level counts as affordable for this player.
    need: its second search, or a slot that asks for a status band."""
    x = t.ceiling[level]
    if need:
        x = x * (100 + t.ceiling_need) // 100
    return x + x * (stretch_hash(player, club) * t.ceiling_stretch) // 25600


def affordable(t, level, rating, age, popularity, position=5, player=(0, 0), wide=False, from_pick=True,
               club=0, band=0, status=0, listed=False):
    """Does a computer club of this level take the player as a candidate (after all the
    game's own tests)? wide: the second search, among all players; club: the buying club's
    id; band: the status band the slot asks for; status: of the player (+0xb4, bits 0-3);
    listed: he carries mark 29 or 30. Without the ceiling, with a level outside 0 to 9, or
    when the choosing code was not entered from ai_pick_candidate: always."""
    if t is None or t.ceiling is None or not from_pick or not 0 <= level < LEVELS:
        return True
    if wide and rating > t.ceiling_top[level]:
        return False
    if t.ceiling[level] == NO_CEILING:
        return True
    price = value(t, rating, age, popularity, position, player)
    if status in (1, 2):
        price = price * t.ceiling_free // 100
    elif listed:
        price = price * t.ceiling_listed // 100
    return price <= limit(t, level, player, club, bool(wide or band))


def candidates(t, level, lists, lowest, highest, wide=False, passes=lambda p: True, most=3, club=0, band=0):
    """The walk of ai_candidates over one set of lists: from the highest overall asked for
    down to the lowest, each list in its order, the first `most` players who pass the
    game's tests and the ceiling. lists: {overall: [player, ...]}, a player being a dict
    with rating, age, popularity, position, id and, if not 0, status and listed. As the
    game, the walk leaves out the list of `lowest` itself."""
    out = []
    for overall in range(highest, lowest, -1):
        for p in lists.get(overall, ()):
            if passes(p) and affordable(t, level, p['rating'], p['age'], p['popularity'], p['position'], p['id'],
                                        wide, True, club, band, p.get('status', 0), p.get('listed', False)):
                out.append(p)
                if len(out) >= most:
                    return out
    return out


def fee(t, rating, age, popularity, position=5, player=(0, 0), base=0, percent=0, keep=False):
    """The transfer fee with MLMoney.lua in place (stored amount; the screen shows 100 times it).
    position: 0 GK ... 12 CF (the edit file's order); player: the two parts of the player's id;
    base, percent, keep: as in ../tools/money.py fee()."""
    x = value(t, rating, age, popularity, position, player)
    if keep:
        x = base
    if percent:
        x += int(x * f32(percent / 100.0))
    return max(1, min(CAP, x))


def salary(t, rating, age, popularity, role_bonus=0, rank=300, band_bonus=0, awards=0):
    """The yearly salary with MLMoney.lua in place. role_bonus: R of MASTER_LEAGUE.md 6.1;
    band_bonus: T (with its 20 * field 0x20); awards: the sum of the award bonuses."""
    x = popularity
    if popularity > 800:
        x += (5 * popularity - 4000) * 2
    if popularity > 1800:
        x += (5 * popularity - 9000) * 4
    f = f32(1.0) if rank > 250 else f32((251 - rank) * t.rank_step + 1.0)
    if t.has_salary:
        part = t.salary[min(rating, 99)] * t.salary_age[age] // 100
    else:                                           # the game's own A + B
        part = 30 * rating - 500 + 300 * max(0, rating - 65) + 500 * max(0, rating - 75) + 700 * max(0, rating - 85)
    if t.bonus is not None:
        role_bonus = role_bonus * t.bonus // 100
        awards, band_bonus = (awards + band_bonus) * t.bonus // 100, 0
    return max(1, min(CAP, awards + band_bonus + int((role_bonus + x + part) * f)))


def cup_prize(t, competition, stage):
    """What cup_prize (fcn_038aa307) gives in Master League. t = None: the game's own."""
    if competition in CUP_NONE or stage == 11:
        return 0
    for c, s, a in (t.cup_rows if t is not None and t.has_cup else GAME_CUP_ROWS):
        if (c, s) == (competition, stage):
            if a:
                return a
            break
    if t is not None and t.national is not None:
        for amount_, stages in zip(t.national, NATIONAL_STAGES):
            if stage in stages:
                return amount_
    return CUP_FALLBACK.get(stage, 0)


def league_prize(t, league, division, place, half=0):
    """What league_prize (fcn_038a9ebb) gives. league: the number of the club's league
    (60 and 61 have lists of their own); division: the two top bits of the league record's
    +0x218 (0, 1: the first list, 2, 3: the second); place: 1 = first; half: 0, or 1 or 2
    for a league played in two halves. t = None: the game's own."""
    league &= 0xffff                                # the game keeps 16 bits of the number
    if half == 1 and league not in (0x3458, 0x27d8) or half == 2 and league not in (0x3459, 0x27d9):
        return 0
    if league in (60, 61):
        amounts = GAME_LEAGUE[league]
    elif division < 2:
        amounts = t.league if t is not None and t.has_league else GAME_LEAGUE['first']
        for league_id, words in (t.league_rows if t is not None else ()):
            if league_id == league:
                amounts = [w * LEAGUE_UNIT for w in words[:LEAGUE1_PLACES + 1]]
                break
    else:
        amounts = t.league_2 if t is not None and t.has_league_2 else GAME_LEAGUE['second']
    a = amounts[place] if 0 <= place < len(amounts) else 0
    return a // 2 if half else a


def prize_paid(t, amount, mode=MASTER_LEAGUE):
    """What a prize adds to (balance, transfer budget)."""
    limit = lambda v: clamp(v, -99999999, 99999999)
    share = t.prize_share if t is not None and t.prize_share is not None and mode == MASTER_LEAGUE else 0
    part = abs(amount) * share // 100               # the division drops the remainder
    return limit(amount), limit(part if amount >= 0 else -part)


def scaled_income(t, v):
    """An amount of yearly income as the module leaves it (amounts of 0 and below are not scaled)."""
    return v if t is None or t.income is None or v <= 0 else v * t.income // 100


def season_income(t, popularity, field, wage_bill=0):
    """season_income (fcn_038ade76): popularity = club_popularity, field = the dword at +4 of
    the club's record in the ranking, wage_bill = what fcn_038ad7a8 gives for the club (the
    game works it out in this function and does not use it). t = None: the game's own."""
    v = scaled_income(t, 25 * max(150000, popularity) - 670 * min(400, field) - 3451330)
    if t is not None and t.income_wages is not None:
        v = (v + wage_bill * t.income_wages // 100 + 2 ** 31) % 2 ** 32 - 2 ** 31     # 32 bits, as the code adds
    return v if v > 0 else 1000


def rank_income(t, rank):
    """fcn_038a9e6b: the yearly amount by the club's place in the ranking."""
    v = scaled_income(t, (403 - rank) * 5000)
    return v if v > 0 else 1000


def career_income(t, level):
    """club_money_setup: the same kind of amount when a career starts, by club level 0-9,
    before the random change of -10 to +10 percent."""
    return scaled_income(t, 165000 * level + 15000)


JUNE_28, JUNE_30 = 0.6000000238418579, 0.4000000059604645        # the doubles at 0x01f0a0a0 and 0x01f0a780
GRANT_A, GRANT_B = (0.00699999975040555, 0.10000000149011612), (0.00215000007301569, 0.07000000029802322)
GRANT_LOW, GRANT_LOWEST = 0.05000000074505806, 0.019999999552965164


def june_grants(day, grade, rank, wage_bill, top_fees, salary_budget=None, extras=(0.0, 0.0)):
    """What the yearly budget step (fcn_03640d19) works out on its two days:
    (salary budget grant, transfer budget grant). day: 28 or 30 (June); grade: 1 to 6 as
    the step numbers it on that day; rank: the club's place, 1 to 200; top_fees: the sum
    top_fees_sum gives for 10 players. The two days differ in three things. The constant
    (0.6 and 0.4). The grades (30 June has no grant for grades 3 and 4). And the transfer
    grant: on 28 June it is taken from the salary grant and the wage bill; on 30 June the
    salary grant first gets two extras (`extras`, two fractions the step works out
    before; this model takes them as given) and is then set against `salary_budget`, the
    salary budget of the account, not against the wage bill. The game's own numbers; the
    module changes none of this."""
    k = JUNE_28 if day == 28 else JUNE_30
    by_rank = {28: {1: GRANT_A, 3: GRANT_B}, 30: {1: GRANT_A, 2: GRANT_B}}[day]
    flat = {28: {2: GRANT_B[1], 4: GRANT_LOW, 5: GRANT_LOW, 6: GRANT_LOWEST}, 30: {5: GRANT_LOW, 6: GRANT_LOWEST}}[day]
    if grade in by_rank:
        a, b = by_rank[grade]
        s = int((rank * a + b) * wage_bill * k)
    elif grade in flat:
        s = int(wage_bill * flat[grade] * k)
    else:
        s = 0
    against = wage_bill
    if day != 28:
        for extra in extras:
            s += int(s * f32(extra))
        against = wage_bill if salary_budget is None else salary_budget
    t = int(top_fees * f32((s + against) / against) / 5.0 * k)
    return s, t


def young_years(t, age):
    """The limit of contract years by age (fcn_03887f5d)."""
    if age >= 35:
        return 1
    if age >= 32:
        return 2
    if age <= 23:
        return 3 if t is None or t.young_years is None else t.young_years
    return 5


def budgets(t, fees, salaries, wage_bill):
    """What fcn_038ad9c4 adds to the transfer budget and to the salary budget of the
    user's club. fees, salaries: of every player of the squad. t = None: the game's own."""
    def mean(amounts):
        return (sum(sorted(amounts, reverse=True)[:16]) or 10000) // 16
    bt = 200 if t is None or t.budget_transfer is None else t.budget_transfer
    bs = 200 if t is None or t.budget_salary is None else t.budget_salary
    limit = lambda v: clamp(v, -99999999, 99999999)
    return limit(mean(fees) * bt // 100), limit(wage_bill + mean(salaries) * bs // 100)


def build():
    import keystone
    ks = keystone.Ks(keystone.KS_ARCH_X86, keystone.KS_MODE_32)
    out = {name: bytes(ks.asm(source, at)[0]) for at, source, name in ROUTINES}
    out['CEILING_BYTES'] = bytes(ks.asm(CEILING_SOURCE, CEILING_CODE)[0])
    return out


def context_lua(exe, name='CONTEXT', pieces=None):
    """The CONTEXT list of MLMoney.lua, from the bytes of the exe file."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    from layout import load, off
    d = load(exe)
    lines = ['local %s = {' % name]
    for name, at, n in CONTEXT if pieces is None else pieces:
        h = d[off(at):off(at) + n].hex()
        parts = [h[i:i + 88] for i in range(0, len(h), 88)]
        lines.append('    { "%s", 0x%08x,' % (name, at))
        lines.append('\n'.join('      %s"%s"' % ('.. ' if i else '', p) for i, p in enumerate(parts)) + ' },')
    lines.append('}')
    return '\n'.join(lines)


def quoted(h, first, width=88):
    parts = [h[:first]] + [h[k:k + width] for k in range(first, len(h), width)]
    return '\n      .. '.join('"%s"' % x for x in parts if x)


def lua_block(exe):
    """The lines of MLMoney.lua from `local ROUTINES` to the end of CONTEXT."""
    out = 'local ROUTINES = {\n'
    for at, _, name in ROUTINES:
        out += '    { 0x%03x, %s },\n' % (at - CAVE, quoted(globals()[name].hex(), 76))
    out += ('}\n\n-- The places that are changed: name, address, bytes there now, bytes to write. (The\n'
            '-- number in "years" is YOUNG_YEARS and the amounts of the six "nat" places are\n'
            '-- CUP_NATIONAL; they are put in below.)\nlocal SITES = {\n')
    for name, at, old, new in SITES:
        if name != 'ceiling':                                # that place belongs to MLTransfers.lua
            out += '    { "%s", 0x%08x, "%s", "%s" },\n' % (name, at, old.hex(), new.hex())
    return (out + '}\n\n-- The code and data those places and the routines rely on: name, address, bytes.\n'
            + context_lua(exe) + '\n')


def lua_block_transfers(exe):
    """The lines of MLTransfers.lua from `local ROUTINE` to the end of CONTEXT."""
    (name, at, old, new), = [x for x in SITES if x[0] == 'ceiling']
    out = ('local ROUTINE = { 0x%02x, %s }\n\n-- The place that is changed: name, address, bytes there now, bytes to write.\n'
           'local SITE = { "%s", 0x%08x, "%s", "%s" }\n\n'
           '-- What MLMoney.lua must have put into its memory: name, address, bytes.\nlocal MONEY = {\n' % (
               CEILING_CODE - CAVE_2, quoted(CEILING_BYTES.hex(), 60), name, at, old.hex(), new.hex()))
    for name, at, data in MONEY_NEEDED:
        out += '    { "%s", 0x%08x,\n      %s },\n' % (name, at, quoted(data.hex(), 88))
    return (out + '}\n\n-- The code of the game the place and the routine rely on: name, address, bytes.\n'
            + context_lua(exe, 'CONTEXT', CONTEXT_CEILING) + '\n')


if __name__ == '__main__':
    if sys.argv[1:2] == ['lua']:
        print((lua_block_transfers if sys.argv[3:] == ['transfers'] else lua_block)(sys.argv[2]), end='')
        sys.exit(0)
    if sys.argv[1:] == ['build']:
        for name, code in build().items():
            assert code == globals()[name], '%s: the bytes kept in this file are not what the source assembles to: %s' % (name, code.hex())
        print('ok: the source assembles to the bytes kept in this file')
    print('memory   %08x - %08x' % (CAVE, CAVE + CAVE_SIZE - 1))
    print('memory 2 %08x - %08x (MLTransfers.lua: the price ceiling)' % (CAVE_2, CAVE_2 + CAVE_2_SIZE - 1))
    for name, at, old, new in SITES:
        print('%-9s %08x: %s -> %s' % (name, at, old.hex(), new.hex()))
    for at, _, name in ROUTINES:
        print('%-15s %08x: %s' % (name, at, globals()[name].hex()))
    print('%-15s %08x: %s' % ('CEILING_BYTES', CEILING_CODE, CEILING_BYTES.hex()))
