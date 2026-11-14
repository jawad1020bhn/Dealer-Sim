"""What MLMoney.lua puts into the game, and the same arithmetic as Python.

    python3 money_cave.py            print the layout and the code bytes
    python3 money_cave.py build      assemble the code again (needs: pip install keystone-engine)
                                     and compare it with the bytes kept in this file
    python3 money_cave.py context <PES2017.exe>
                                     print the CONTEXT list of MLMoney.lua from the exe file

MLMoney.lua changes up to fifteen places of PES2017.exe (sha256 44b0caaa...) and fills a
piece of unused memory with seven small routines and their tables.

Fee, fcn_038ab832 (MASTER_LEAGUE.md 6.2). The 17 bytes at 0x038ab8db hold the rating part
of the formula, `9000 * max(0, rating - 68)`, left in edi. They become a call to FEE_CODE:

    v           = VALUE[rating] * AGE[age] / 100
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
`mov eax, [ebp + eax*4 - 0x120]` at 0x038aa2c6 (second list, index 0 to 24) become
`mov eax, [eax*4 + LEAGUE1_TAB]` and `mov eax, [eax*4 + LEAGUE2_TAB]`, the same length.
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

The memory used is the end of the section .trace: the section's content ends at
0x047b005d, its declared size at 0x047b0123, and its last page runs to 0x047b0fff. The
section is readable, writable and executable. No call or jump of the exe goes there.
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
MARK_AT = CAVE + 0x45c          # 4 bytes "MLM3"
FEE_CODE = CAVE + 0x480
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
CAVE_SIZE = 0xa90
CAVE_LIMIT = 0x047b1000

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

FEE_SOURCE = f'''
    cmp eax, 99
    jbe f1
    mov eax, 99
f1: mov eax, dword ptr [eax*4 + {VALUE_TAB}]
    mov ecx, dword ptr [ebx + 0x1c]
    shr ecx, 7
    and ecx, 0x3f
    movzx ecx, word ptr [ecx*2 + {AGE_TAB}]
    mul ecx
    div dword ptr [{HUNDRED_AT}]
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
# the assembled routines (python3 money_cave.py build checks them against the source above)
FEE_BYTES = bytes.fromhex(
    '83f8637605b8630000008b048500027b048b4b1cc1e90783e13f0fb70c4d20057b04f7e1f73554067b048b4b04'
    'c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b179379ec1e9180faf0d48'
    '067b04c1e908030d44067b04f7e1f73558067b043d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1'
    'ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745f400000000c3')
SALARY_BYTES = bytes.fromhex(
    '83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f73554067b048945c8'
    'c745cc00000000c3')
BUDGET_T_BYTES = bytes.fromhex('8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3')
BUDGET_S_BYTES = bytes.fromhex('52f72550067b04f73554067b045a8d3401e92fb906ff')
PRIZE_BYTES = bytes.fromhex('8b44240450e80da50fff83c404e8b37f05ff83782013751c8b4424048b00f72d90087b04f73d54067b045054e8b6a30fff83c408c3')
BONUS_R_BYTES = bytes.fromhex('505289f0f72594087b04f73554067b0489c65a580375b0c3')
BONUS_END_BYTES = bytes.fromhex('528b45cc0345b0f72594087b04f73554067b045ac3')
ROUTINES = ((FEE_CODE, FEE_SOURCE, 'FEE_BYTES'), (SALARY_CODE, SALARY_SOURCE, 'SALARY_BYTES'),
            (BUDGET_T_CODE, BUDGET_T_SOURCE, 'BUDGET_T_BYTES'), (BUDGET_S_CODE, BUDGET_S_SOURCE, 'BUDGET_S_BYTES'),
            (PRIZE_CODE, PRIZE_SOURCE, 'PRIZE_BYTES'), (BONUS_R_CODE, BONUS_R_SOURCE, 'BONUS_R_BYTES'),
            (BONUS_END_CODE, BONUS_END_SOURCE, 'BONUS_END_BYTES'))

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
)


def call(site, target):
    return b'\xe8' + struct.pack('<i', target - (site + 5))


FEE_SITE_NEW = call(FEE_SITE, FEE_CODE) + b'\x90' * 12
SALARY_SITE_NEW = call(SALARY_SITE, SALARY_CODE) + b'\xeb' + bytes([SALARY_BLOCK_END - (SALARY_SITE + 7)])
BUDGET_T_SITE_NEW = call(BUDGET_T_SITE, BUDGET_T_CODE)
BUDGET_S_SITE_NEW = call(BUDGET_S_SITE, BUDGET_S_CODE) + b'\x90' * 3
#        name, address, bytes of the game, bytes of the module
# ('years': the number in its last four bytes is a setting; Tables.sites() gives it as written)
SITES = (('fee', FEE_SITE, FEE_SITE_OLD, FEE_SITE_NEW), ('salary', SALARY_SITE, SALARY_SITE_OLD, SALARY_SITE_NEW),
         ('budget 1', BUDGET_T_SITE, BUDGET_T_SITE_OLD, BUDGET_T_SITE_NEW),
         ('budget 2', BUDGET_S_SITE, BUDGET_S_SITE_OLD, BUDGET_S_SITE_NEW),
         ('cup 1', 0x038aa400, struct.pack('<I', CUP_TABLE), struct.pack('<I', CUP_TAB)),
         ('cup 2', 0x038aa408, struct.pack('<I', CUP_TABLE + 4), struct.pack('<I', CUP_TAB + 4)),
         ('cup 3', 0x038aa423, struct.pack('<I', CUP_TABLE + 8), struct.pack('<I', CUP_TAB + 8)),
         ('league 1', LEAGUE1_SITE, LEAGUE1_SITE_OLD, b'\x8b\x04\x85' + struct.pack('<I', LEAGUE1_TAB)),
         ('league 2', LEAGUE2_SITE, LEAGUE2_SITE_OLD, b'\x8b\x04\x85' + struct.pack('<I', LEAGUE2_TAB)),
         ('prize 1', PRIZE_SITE_1, PRIZE_SITE_1_OLD, call(PRIZE_SITE_1, PRIZE_CODE)),
         ('prize 2', PRIZE_SITE_2, PRIZE_SITE_2_OLD, call(PRIZE_SITE_2, PRIZE_CODE)),
         ('pay gap', RANK_SITE, RANK_SITE_OLD, struct.pack('<I', RANK_STEP_AT)),
         ('bonus 1', BONUS_R_SITE, BONUS_R_SITE_OLD, call(BONUS_R_SITE, BONUS_R_CODE) + b'\x90'),
         ('bonus 2', BONUS_END_SITE, BONUS_END_SITE_OLD, call(BONUS_END_SITE, BONUS_END_CODE) + b'\x90' * 7),
         ('years', YEARS_SITE, YEARS_SITE_OLD, b'\xb8\x05\x00\x00\x00'))
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
    percent or None; young_years: 1 to 5 or None (the game's own 3)."""

    def __init__(self, value, age, position, spread, fame, salary, salary_age, budget_transfer, budget_salary,
                 cup=None, league=None, league_2=None, prize_share=None, pay_gap=None, bonus=None,
                 young_years=None):
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
        for competition, stage, millions in cup or ():
            hit = [r for r in rows if r[0] == competition and r[1] == stage]
            assert hit, 'the game has no prize row for competition %d, stage %d' % (competition, stage)
            hit[0][2] = prize(millions)
        self.cup_rows = [tuple(r) for r in rows]
        self.has_league, self.has_league_2 = league is not None, league_2 is not None
        assert league is None or len(league) == LEAGUE1_PLACES
        assert league_2 is None or len(league_2) == LEAGUE2_PLACES
        self.league = [0] + [prize(m, 0) for m in league] if self.has_league else [0] * (LEAGUE1_PLACES + 1)
        self.league_2 = [0] + [prize(m, 0) for m in league_2] if self.has_league_2 else [0] * (LEAGUE2_PLACES + 1)
        self.prize_share = None if not prize_share else clamp(int(prize_share + 0.5), 0, MAX_SHARE)
        self.bonus = None if bonus is None else clamp(int(bonus + 0.5), 0, MAX_BONUS)
        self.young_years = None if not young_years else clamp(int(young_years + 0.5), MIN_YEARS, MAX_YEARS)

    def sites(self):
        """The places the module changes with these settings: (name, address, old, new)."""
        share, bonus = self.prize_share is not None, self.bonus is not None
        on = (True, self.has_salary, self.budget_transfer is not None, self.budget_salary is not None,
              self.has_cup, self.has_cup, self.has_cup, self.has_league, self.has_league_2, share, share,
              self.has_gap, bonus, bonus, self.young_years is not None)
        used = [s for s, yes in zip(SITES, on) if yes]
        if self.young_years is not None:
            used[-1] = used[-1][:3] + (b'\xb8' + struct.pack('<I', self.young_years),)
        return used


def prize(millions, lowest=10):
    """Millions on the screen -> stored prize."""
    return clamp(amount(millions), lowest, amount(MAX_PRIZE))


def image(t):
    d = struct.pack('<100I', *t.value) + struct.pack('<100I', *t.salary) + struct.pack('<64H', *t.age)
    d += struct.pack('<64H', *t.salary_age) + struct.pack('<16H', *t.position)
    assert len(d) == FAME_AT - CAVE
    d += struct.pack('<7I', t.fame, t.spread_low, t.spread_range, t.budget_transfer or 200, t.budget_salary or 200,
                     100, 1000) + b'MLM3'
    pieces = [(at, globals()[name]) for at, _, name in ROUTINES]
    pieces += [(LEAGUE1_TAB, struct.pack('<23I', *t.league)), (LEAGUE2_TAB, struct.pack('<25I', *t.league_2)),
               (RANK_STEP_AT, struct.pack('<d', t.rank_step)),
               (SHARE_AT, struct.pack('<2I', t.prize_share or 0, 100 if t.bonus is None else t.bonus)),
               (CUP_TAB, b''.join(struct.pack('<3I', *r) for r in t.cup_rows))]
    for at, piece in sorted(pieces):
        assert len(d) <= at - CAVE, hex(at)
        d = d.ljust(at - CAVE, b'\0') + piece
    assert len(d) <= CAVE_SIZE
    return d.ljust(CAVE_SIZE, b'\0')


def spread_hash(id_low, id_high):
    """The byte the fee routine makes from a player's id."""
    x = (id_low & 0xffff) ^ (id_high * HASH_A & 0xffffffff)
    return (x * HASH_B & 0xffffffff) >> 24


def fee(t, rating, age, popularity, position=5, player=(0, 0), base=0, percent=0, keep=False):
    """The transfer fee with MLMoney.lua in place (stored amount; the screen shows 100 times it).
    position: 0 GK ... 12 CF (the edit file's order); player: the two parts of the player's id;
    base, percent, keep: as in ../tools/money.py fee()."""
    x = t.value[min(rating, 99)] * t.age[age] // 100
    x = x * t.position[position] // 100
    x = min(CAP, x * (t.spread_low + (spread_hash(*player) * t.spread_range >> 8)) // 1000)
    x += x * (popularity * t.fame) // 100000
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
    return CUP_FALLBACK.get(stage, 0)


def league_prize(t, league, division, place, half=0):
    """What league_prize (fcn_038a9ebb) gives. league: the number of the club's league
    (60 and 61 have lists of their own); division: the two top bits of the league record's
    +0x218 (0, 1: the first list, 2, 3: the second); place: 1 = first; half: 0, or 1 or 2
    for a league played in two halves. t = None: the game's own."""
    if half == 1 and league not in (0x3458, 0x27d8) or half == 2 and league not in (0x3459, 0x27d9):
        return 0
    if league in (60, 61):
        amounts = GAME_LEAGUE[league]
    elif division < 2:
        amounts = t.league if t is not None and t.has_league else GAME_LEAGUE['first']
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
    return {name: bytes(ks.asm(source, at)[0]) for at, source, name in ROUTINES}


def context_lua(exe):
    """The CONTEXT list of MLMoney.lua, from the bytes of the exe file."""
    import os
    sys.path.insert(0, os.path.join(os.path.dirname(os.path.abspath(__file__)), '..', 'tools'))
    from layout import load, off
    d = load(exe)
    lines = ['local CONTEXT = {']
    for name, at, n in CONTEXT:
        h = d[off(at):off(at) + n].hex()
        parts = [h[i:i + 88] for i in range(0, len(h), 88)]
        lines.append('    { "%s", 0x%08x,' % (name, at))
        lines.append('\n'.join('      %s"%s"' % ('.. ' if i else '', p) for i, p in enumerate(parts)) + ' },')
    lines.append('}')
    return '\n'.join(lines)


if __name__ == '__main__':
    if sys.argv[1:2] == ['context']:
        print(context_lua(sys.argv[2]))
        sys.exit(0)
    if sys.argv[1:] == ['build']:
        for name, code in build().items():
            assert code == globals()[name], '%s: the bytes kept in this file are not what the source assembles to: %s' % (name, code.hex())
        print('ok: the source assembles to the bytes kept in this file')
    print('memory   %08x - %08x' % (CAVE, CAVE + CAVE_SIZE - 1))
    for name, at, old, new in SITES:
        print('%-9s %08x: %s -> %s' % (name, at, old.hex(), new.hex()))
    if sys.argv[1:] == ['lua']:
        for at, _, name in ROUTINES:
            print('    { 0x%03x, "%s" },' % (at - CAVE, globals()[name].hex()))
        for name, at, old, new in SITES:
            print('    { "%s", 0x%08x, "%s", "%s" },' % (name, at, old.hex(), new.hex()))
        sys.exit(0)
    for at, _, name in ROUTINES:
        print('%-15s %08x: %s' % (name, at, globals()[name].hex()))
