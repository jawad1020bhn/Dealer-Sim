-- MLMoney.lua, version 3: real-world player values, salaries, budgets and prize money in
-- the PES 2017 Master League (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...;
-- MLCheck.lua must have said "6 of 6 as expected" on your game before you use this one.
--
-- What it changes, in the running game only (no file is touched):
--   * the value of a player (the transfer fee the game computes) becomes
--         VALUE[rating] x AGE[age] x POSITION[position] x spread x (1 + popularity bonus)
--     instead of  salary x 2.2..3.3 + 9,000 x (rating - 68);
--   * the rating part of the yearly salary becomes SALARY[rating] x SALARY_AGE[age]; the
--     club's place in the ranking, the role bonuses, the popularity part and the award
--     bonuses stay the game's own;
--   * the transfer budget your club gets when a career starts becomes BUDGET_TRANSFER
--     times the mean value of its 16 best players (the game: 2 times);
--   * the prize money of cups (CUP) and of the leagues (LEAGUE, LEAGUE_2);
--   * PRIZE_TO_BUDGET percent of every prize is added to the transfer budget (the game
--     puts a prize into the club's balance only);
--   * the first club of the game's club ranking pays PAY_GAP times the salary of a club
--     outside the first 250 (the game: 2 times);
--   * the role, age and award bonuses of the salary are multiplied by BONUS percent;
--   * a player of 23 or younger can sign for YOUNG_YEARS years (the game: 3).
-- Each of these has its own setting below and can be switched off there. Amounts are
-- what the screens show.
--
-- It first checks that the game holds the expected code and that the memory it needs is
-- empty. If anything differs it writes nothing and says so in sider.log.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLMoney.lua"
-- to sider.ini. Remove that line to have the game's own numbers back.
--
-- Salaries are stored in the contracts: a running career keeps its old salaries until
-- contracts are renewed, and its budgets were made from the old numbers. Start a new
-- career for numbers that fit together, or set SALARY = false for a running one.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type.

local m = {}

-- ============================ settings ============================

-- false: check and report only, write nothing.
local WRITE = true

-- Value of a player at the age where AGE says 100 and a position at 100, by rating:
-- { rating, millions }. Between two entries the value grows by the same percentage per
-- rating point.
local VALUE = {
    { 50, 0.05 }, { 60, 0.3 }, { 65, 0.8 }, { 70, 2.5 }, { 75, 8 }, { 80, 25 },
    { 85, 65 }, { 88, 110 }, { 90, 150 }, { 92, 185 }, { 94, 215 }, { 99, 260 },
}

-- Percent of that value by age: { age, percent }. Straight lines between the entries.
-- At most 300.
local AGE = {
    { 15, 130 }, { 19, 130 }, { 25, 100 }, { 26, 100 }, { 27, 97 }, { 28, 90 },
    { 29, 80 }, { 30, 65 }, { 31, 50 }, { 32, 36 }, { 33, 26 }, { 34, 18 },
    { 35, 12 }, { 36, 8 }, { 37, 6 }, { 38, 5 },
}

-- Percent of that value by the registered position. 0 to 200.
local POSITION = {
    GK = 45, CB = 85, LB = 75, RB = 75, DMF = 95, CMF = 100, LMF = 95, RMF = 95,
    AMF = 105, LWF = 110, RWF = 110, SS = 105, CF = 110,
}

-- Two players of the same rating, age and position do not cost the same: each player
-- gets his own fixed factor between 100 - SPREAD and 100 + SPREAD percent. It never
-- changes for a player. 0 to 30; 0 switches it off.
local SPREAD = 12

-- Percent added to the value for every 1,000 popularity points of the player (the
-- game keeps 0 to 3,000 points per player). 0 to 100.
local FAME = 10

-- Rating part of the yearly salary at the first club of the game's club ranking:
-- { rating, millions }. A club outside the first 250 pays this divided by PAY_GAP, the
-- clubs between pay in proportion. false: leave the game's salary formula alone.
local SALARY = {
    { 50, 0.06 }, { 60, 0.2 }, { 65, 0.5 }, { 70, 1.2 }, { 75, 2.6 }, { 80, 5.5 },
    { 85, 10 }, { 88, 15 }, { 90, 20 }, { 92, 25 }, { 94, 30 }, { 99, 36 },
}

-- Percent of that salary by age: { age, percent }. At most 200.
local SALARY_AGE = {
    { 16, 45 }, { 18, 50 }, { 20, 62 }, { 22, 76 }, { 24, 90 }, { 26, 100 }, { 31, 100 },
    { 33, 92 }, { 35, 80 }, { 37, 65 }, { 39, 50 },
}

-- Transfer budget of your club when a career starts: this many times the mean value of
-- its 16 best players. The game's own number is 2. 0.1 to 10; false: leave the game's code.
local BUDGET_TRANSFER = 3

-- Salary budget of your club when a career starts: the wage bill plus this many times
-- the mean salary of its 16 best paid players. The game's own number is 2.
-- 0.1 to 10; false: leave the game's code.
local BUDGET_SALARY = false

-- Prize of a cup: { competition, stage, millions }. The game pays a cup once, when your
-- club is out or has won it, so each amount is the money of the whole run. competition is
-- the game's number of the cup. stage: 0 winner, 1 runner-up, 2 third place, 3 out in
-- the semi-final, 4 in the quarter-final, 5 in the round of 16 (Europa League only), 7 in
-- the first knock-out round, 9 out in the group stage. Only a competition and stage the
-- game itself has a prize for can stand here (python3 ../tools/prize.py lists them); the
-- ones not named here keep the game's amount, and so do the national cups. 0.001 to 2000.
-- false: leave the game's cup prizes alone.
-- These numbers: the fixed payments of 2025/26 (Sudamericana and Libertadores 2025, AFC
-- 2024/25) added up to the stage; the payments per win and the television shares are not
-- in them. Euros and dollars are taken as the same.
local CUP = {
    -- 2: Champions League
    { 2, 0, 82.12 }, { 2, 1, 75.62 }, { 2, 3, 57.12 }, { 2, 4, 42.12 }, { 2, 7, 29.62 }, { 2, 9, 18.62 },
    -- 3: Europa League
    { 3, 0, 26.06 }, { 3, 1, 20.06 }, { 3, 3, 13.06 }, { 3, 4, 8.86 }, { 3, 5, 6.36 }, { 3, 7, 4.61 },
    { 3, 9, 4.31 },
    -- 4: UEFA Super Cup
    { 4, 0, 5 }, { 4, 1, 4 },
    -- 5: Copa Libertadores
    { 5, 0, 32.25 }, { 5, 1, 15.25 }, { 5, 3, 8.25 }, { 5, 4, 5.95 }, { 5, 7, 4.25 }, { 5, 9, 3 },
    -- 6: Copa Sudamericana
    { 6, 0, 9.5 }, { 6, 1, 5 }, { 6, 3, 3 }, { 6, 4, 2.2 }, { 6, 7, 1.5 }, { 6, 9, 0.9 },
    -- 8: AFC Champions League
    { 8, 0, 12 }, { 8, 1, 6 }, { 8, 3, 2 }, { 8, 4, 1.4 }, { 8, 7, 1 }, { 8, 9, 0.8 },
    -- 1: Club World Cup
    { 1, 0, 5 }, { 1, 1, 4 },
}

-- Prize of a first division by place, millions, place 1 to 22 (22 numbers). The game has
-- one list for all first divisions. These numbers: the Premier League's payments by
-- place of 2024/25. 0 to 2000. false: leave the game's list alone.
local LEAGUE = {
    53.1, 50.4, 47.7, 45.0, 42.4, 39.8, 37.1, 34.5, 31.9, 29.1, 26.5,
    23.8, 21.2, 18.6, 15.9, 13.3, 10.7, 7.9, 5.3, 2.6, 2.6, 2.6,
}

-- Prize of a second division by place, millions, place 1 to 24 (24 numbers).
-- false: leave the game's list alone (2 million for place 1 down to 25,000).
local LEAGUE_2 = false

-- Percent of every cup and league prize that is added to your transfer budget on the day
-- it is paid. The whole prize goes to the club's balance as before. 1 to 100;
-- false: prizes go to the balance only, as in the game.
local PRIZE_TO_BUDGET = 75

-- How many times the salary of a club outside the first 250 of the game's club ranking
-- the first club of that ranking pays. The game's own number is 2. 1 to 10;
-- false: leave the game's code.
local PAY_GAP = 3

-- Percent of the game's salary bonuses: for the team role (1,000 to 15,000 a year in the
-- game, 100,000 to 1,500,000 on the screen), for the age band and for awards. The
-- salaries above are about 3 to 5 times the game's, so 300 keeps the weight of the
-- bonuses. 0 to 1000; false: leave the game's code.
local BONUS = 300

-- Longest contract, in years, for a player of 23 or younger. The game's own number is 3;
-- from 24 to 31 it is 5. 1 to 5; false: leave the game's code.
local YOUNG_YEARS = 5

-- ========================= end of settings =========================

local CAP = 99999900            -- the game's largest amount (9,999,990,000 on the screen)
local CAVE = 0x047b0200         -- unused end of the code section: tables and seven routines
local CAVE_SIZE = 0xa90
local NUMBERS_AT = 0x440         -- offset of the single numbers in that memory
local LEAGUE_AT, LEAGUE_2_AT = 0x5c0, 0x620     -- the two league lists
local GAP_AT = 0x688             -- rise of the club factor per place of the ranking (a double)
local SHARE_AT = 0x690           -- PRIZE_TO_BUDGET, then BONUS
local CUP_AT = 0x720             -- the cup table
local CUP_ROWS = 73
-- the routines: offset in that memory, machine code (source: money_cave.py)
local ROUTINES = {
    { 0x480, "83f8637605b8630000008b048500027b048b4b1cc1e90783e13f0fb70c4d20057b04f7e1f735"
      .. "54067b048b4b04c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b17937"
      .. "9ec1e9180faf0d48067b04c1e908030d44067b04f7e1f73558067b043d9ce0f5057605b89ce0f50589c78b8b"
      .. "b4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745f400000000c3" },
    { 0x540, "83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f735"
      .. "54067b048945c8c745cc00000000c3" },
    { 0x580, "8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3" },
    { 0x5a0, "52f72550067b04f73554067b045a8d3401e92fb906ff" },
    { 0x6a0, "8b44240450e80da50fff83c404e8b37f05ff83782013751c8b4424048b00f72d90087b04f73d"
      .. "54067b045054e8b6a30fff83c408c3" },
    { 0x6e0, "505289f0f72594087b04f73554067b0489c65a580375b0c3" },
    { 0x700, "528b45cc0345b0f72594087b04f73554067b045ac3" },
}

-- The places that are changed: name, address, bytes there now, bytes to write. (The
-- number in "years" is YOUNG_YEARS; it is put in below.)
local SITES = {
    { "fee", 0x038ab8db, "83f844760c8db8bcffffff69ff28230000", "e8a04df000909090909090909090909090" },
    { "salary", 0x038ac875, "89c1c1e10429c1", "e8c63ef000eb5b" },
    { "budget 1", 0x038adc47, "01f68b4030", "e8342bf000" },
    { "budget 2", 0x038add08, "8d3441e8d5e3f6ff", "e8932af000909090" },
    { "cup 1", 0x038aa400, "78b11602", "20097b04" },
    { "cup 2", 0x038aa408, "7cb11602", "24097b04" },
    { "cup 3", 0x038aa423, "80b11602", "28097b04" },
    { "league 1", 0x038aa2dd, "8b848584feffff", "8b0485c0077b04" },
    { "league 2", 0x038aa2c6, "8b8485e0feffff", "8b048520087b04" },
    { "prize 1", 0x03640ac5, "e8eda22600", "e8d6fd1601" },
    { "prize 2", 0x03640b78, "e83aa22600", "e823fd1601" },
    { "pay gap", 0x038aca1b, "88fef201", "88087b04" },
    { "bonus 1", 0x038aca2b, "03b5b0ffffff", "e8b03ef00090" },
    { "bonus 2", 0x038acd96, "8b85ccffffff0385b0ffffff", "e8653bf00090909090909090" },
    { "years", 0x03887fc1, "b803000000", "b805000000" },
}

-- The code and data those places and the routines rely on: name, address, bytes.
local CONTEXT = {
    { "fee code", 0x038ab832,
      "5589e583ec1c5356e8a608f7ff8b75088b4e048b40308b16515289c1e8e26ff7ff89c38b4518803800751d8b"
      .. "4d10833900751556e8df18feff83c40484c074085e31c05b89ec5dc38b550c8b0285c075068b83cc0000008b"
      .. "8bb4000000c1e90b81e1ff0f0000898df8ffffffdb85f8ffffff576a02dc0d48ba16028d95f8ffffff5253dc"
      .. "05b8f2f00189451831ffc785f8ffffff0d000000d99df4ffffffe86d82faff0fb6c083c40c83f844760c8db8"
      .. "bcffffff69ff282300008b4518db451885c07906d805b46dee01d88df4ffffffe85bb303008b4d108d34078b"
      .. "0189b5f8ffffff5f" },
    { "salary code", 0x038ac6f8,
      "e83861f7ff8b0d8412520289c38b07" },
    { "salary code 2", 0x038ac86f,
      "83c40c0fb6c089c1c1e10429c18d94090cfeffff31c98995c8ffffff898dccffffff83f84272128d88bfffff"
      .. "ff69c92c010000898dccffffff83f84c72148d90b5ffffff69d2f401000001d1898dccffffff83f856721183"
      .. "c0ab69c0bc02000001c1898dccffffff8b83b4000000" },
    { "salary roles", 0x038ac937,
      "0fb68bc40000008b83b8000000c1e81a83c1fb31f683e00383f90e775b0fb68912ce8a03ff248dfecd8a03be"
      .. "983a0000eb4683f8017507be88130000eb3a83f8027507be4c1d0000eb2e83f8037529be10270000eb2283f8"
      .. "017507bee8030000eb1683f8027507bed0070000eb0a83f8037505beb80b00008b95acffffff81c2cc84cc00"
      .. "68841252028d8dbcffffff8995c0ffffffbf2c010000e851083dff84c074148b8dc0ffffff8d85bcffffff50"
      .. "e847b988ff89c7d9e8d99db8ffffff81fffa000000772db9fb00000029f9898da4ffffffdb85a4ffffff7906"
      .. "d805b46dee01dc0d88fef201dc058094ee01d99db8ffffff" },
    { "salary sum", 0x038aca2b,
      "03b5b0ffffff03b5ccffffff03b5c8ffffff89b5a4ffffffdb85a4ffffff7906d805b46dee01d88db8ffffff"
      .. "e806a20300" },
    { "salary end", 0x038aca5c,
      "31ff538985a4ffffff89bdb0ffffffe89e75faff83c40489c68d85a0ffffff506a2089d989bdd0ffffff89bd"
      .. "d4ffffff89bdd8ffffffc785dcffffffe8030000c785e0ffffffb80b0000c785e4ffffff88130000c785e8ff"
      .. "ffff10270000c785ecffffff983a000089bda0ffffffe8e1adf7ff83fe0873238bb4b5d0ffffff89b5b0ffff"
      .. "ff39fe74128b85a0ffffff8d0c808d148e8995b0ffffff8b83b400000083e00f89bdccffffff3c060f848802"
      .. "00008bb5acffffff8d8dc8ffffff81c6f86de7005189f189bdc8ffffffe8dbf68dff8d95c8ffffff5289f189"
      .. "c3c785c8ffffff01000000e8c1f68dff89c78d85c8ffffff5089f1c785c8ffffff02000000e8a7f68dff8d8d"
      .. "c8ffffff5189f18985b8ffffffc785c8ffffff03000000e889f68dff89c685db0f84d200000085ff0f84ca00"
      .. "000083bdb8ffffff000f84bd00000085f60f84b50000008b53088b430c8b9da8ffffff538d8dc4ffffff8995"
      .. "c4ffffff8985c8ffffffe8f30e33ff84c0740ac785ccffffff102700008b4f088b570c898dc4ffffff538d8d"
      .. "c4ffffff8995c8ffffffe8c70e33ffbf8813000084c0740601bdccffffff8b85b8ffffff8b48088b500c898d"
      .. "c4ffffff538d8dc4ffffff8995c8ffffffe8940e33ff84c0740601bdccffffff8b4e0c8b4608898dc8ffffff"
      .. "538d8dc4ffffff8985c4ffffffe86c0e33ff84c0740601bdccffffff8bb5acffffff31ff89bdb8ffffff39be"
      .. "e8ec5f000f86200100008d86802e55008985c0ffffff8d1b81ff2c01000072068d8640e85f000fb70889cabb"
      .. "ffff00006639da0f84cd0000008b505c83fa0175090fb7404e6639d8740983fa050f85b300000089ca8d85c8"
      .. "ffffff508d8ef86de7008995c8ffffffe89e0be2ff85c00f849100000031db899de0ffffff899de4ffffff89"
      .. "9de8ffffff8d8de0ffffff518d95c8ffffff5289c1899dfcffffff899dc8ffffffe89192d3ff8bb5e4ffffff"
      .. "8b85e0ffffff29c6c1fe0339de762c89c78b85a8ffffff5089f9e8830d33ff84c0740a8185ccffffffd00700"
      .. "004383c70839de77dc8bbdb8ffffff8d8de0ffffffc785fcffffffffffffffe8386d38008bb5acffffff8b85"
      .. "c0ffffff47052402000089bdb8ffffff8985c0ffffff3bbee8ec5f000f82eefeffff8b85ccffffff0385b0ff"
      .. "ffff0385a4ffffff3d9ce0f5057e07b89ce0f505eb2483f8017d1fb801000000eb18" },
    { "budget code", 0x038adc0b,
      "31c031c985f674208b95c0ffffff83c20883f910740e39ce764b03024183c20c39f172ed85c07505b8102700"
      .. "009983e20f8d3402c1fe04e89ee4f6ff01f68b4030752d31c9eb47663b3d541252020f857dfeffff3b0d5812"
      .. "52020f841fffffffe96cfeffff68fc93f001ff1538747d0489f181feffe0f5057c07b9ffe0f505eb0d81fe01"
      .. "1f0afa7f05b9011f0afa0388c4dfdd00bbffffff7f39d97c088998c4dfdd00eb1a81f9000000807f0cc780c4"
      .. "dfdd0000000080eb068988c4dfdd0031c031c985ff74228b95b0ffffff83c20889ff83f910740e39cf768a03"
      .. "024183c20c39f972ed85c07505b8102700008b8ddcffffff9983e20f01d0c1f8048d3441e8d5e3f6ff8b4030"
      .. "85f6750431c9eb1e89f181feffe0f5057c07b9ffe0f505eb0d81fe011f0afa7f05b9011f0afa0388dcdfdd00"
      .. "39d97c088998dcdfdd00eb1a81f9000000807f0cc780dcdfdd0000000080eb068988dcdfdd00" },
    { "position", 0x03827961,
      "8b41048b4d0cc1e81c8901b0015dc20800" },
    { "age", 0x03827ba9,
      "8b511c8b450cc1ea0783e23f8910b0015dc20800" },
    { "cup prize", 0x038aa307,
      "5589e58b45108b008b0d8412520289c231caf7c2ff3f0000750d31c8a900c0ffff750431c05dc3568b75088b"
      .. "0650e881abffff83c40484c00f853c0100008b0e51e8baabffff83c40484c00f85290100008b0683f82d0f84"
      .. "1e01000083f82e0f841501000083f8460f840c01000083f8470f840301000083f8480f84fa00000083f8360f"
      .. "84f100000083f8370f84e800000083f82f0f84df000000538b5d0c833b0b75065b31c05e5dc35731ffe8ace4"
      .. "f5ff8b3631c983782028753931c089ff39b0e8b41602750a8b90ecb416023b13741283c00c413d3801000072"
      .. "e389f85f5b5e5dc38d04498b3c85f0b4160289f85f5b5e5dc331c039b078b11602750a8b907cb116023b1374"
      .. "0d83c00c413d6c03000072e3eb0e8d04498b3c8580b1160285ff75b98b0383f80677b2ff248587a48a03bf20"
      .. "4e000089f85f5b5e5dc3bf1027000089f85f5b5e5dc3bf8813000089f85f5b5e5dc3bfe803000089f85f5b5e"
      .. "5dc3bff401000089f85f5b5e5dc3bf2c01000089f85f5b5e5dc331c05e5dc3" },
    { "cup table", 0x0216b178,
      "0200000000000000803801000200000001000000409c00000200000003000000307500000200000004000000"
      .. "204e000002000000070000001027000002000000090000008813000003000000000000003075000003000000"
      .. "01000000204e00000300000003000000983a0000030000000400000010270000030000000500000088130000"
      .. "0300000007000000b80b00000300000009000000e80300000400000000000000b88800000400000001000000"
      .. "102700000500000000000000803801000500000001000000409c000005000000030000003075000005000000"
      .. "04000000204e0000050000000700000010270000050000000900000088130000300000000000000080380100"
      .. "3000000001000000409c00003000000003000000307500003000000004000000204e00003000000007000000"
      .. "102700003000000009000000881300000600000000000000307500000600000001000000204e000006000000"
      .. "03000000983a00000600000004000000102700000600000007000000881300000600000009000000b80b0000"
      .. "060000000a000000e80300005b00000000000000307500005b00000001000000204e00005b00000003000000"
      .. "983a00005b00000004000000102700005b00000007000000881300005b00000009000000b80b00005b000000"
      .. "0a000000e80300000700000000000000b8880000070000000100000010270000080000000000000080380100"
      .. "0800000001000000409c00000800000003000000307500000800000004000000204e00000800000007000000"
      .. "102700000800000009000000881300000100000000000000409c00000100000001000000204e000001000000"
      .. "02000000102700000100000003000000881300004900000000000000881300004900000001000000b80b0000"
      .. "4a00000000000000881300004a00000001000000b80b00004b00000000000000881300004b00000001000000"
      .. "b80b00004c00000000000000881300004c00000001000000b80b00004d00000000000000881300004d000000"
      .. "01000000b80b00004e00000000000000881300004e00000001000000b80b00004f0000000000000088130000"
      .. "4f00000001000000b80b00005200000000000000881300005200000001000000b80b00005300000000000000"
      .. "881300005300000001000000b80b00005400000000000000881300005400000001000000b80b0000" },
    { "league prize", 0x038a9ebb,
      "5589e581ec80010000a1501a520231e88985fcffffff5356578b4510898580feffffb8b80b0000bb28230000"
      .. "ba581b0000b98813000031f6899dc8feffff8995ccfeffff898dd0feffff8985d4feffff8985d8feffff8985"
      .. "dcfeffff899df4feffff8995fcfeffff898d04ffffffbba00f000089850cffffffb9d0070000b8e8030000ba"
      .. "f40100008b7d0889b584feffffc78588fefffff0490200c7858cfeffffd0fb0100c78590feffffa0860100c7"
      .. "8594feffff80380100c78598feffff60ea0000c7859cfeffff50c30000c785a0feffffc8af0000c785a4feff"
      .. "ff409c0000c785a8feffffb8880000c785acfeffff30750000c785b0feffff78690000c785b4feffffc05d00"
      .. "00c785b8feffff08520000c785bcfeffff50460000c785c0feffff983a0000c785c4feffffe02e000089b5e0"
      .. "feffffc785e4feffff204e0000c785e8feffff983a0000c785ecfeffffe02e0000c785f0feffff10270000c7"
      .. "85f8feffff401f0000c78500ffffff70170000899d08ffffff898d10ffffffc78514ffffffdc050000898518"
      .. "ffffffc7851cffffff84030000c78520ffffff20030000c78524ffffffbc020000c78528ffffff5802000089"
      .. "952cffffffc78530ffffffc2010000c78534ffffff90010000c78538ffffff5e010000c7853cffffff2c0100"
      .. "00c78540fffffffa00000089b5a0ffffffc785a4ffffff204e0000c785a8ffffff10270000c785acffffff40"
      .. "1f0000c785b0ffffff70170000899db4ffffff898db8ffffff8985bcffffff89b5c0ffffff89b5c4ffffff89"
      .. "b5c8ffffff89b5ccffffff89b5d0ffffff89b5d4ffffff89b5d8ffffff89b5dcffffff89b5e0ffffff89b5e4"
      .. "ffffff89b5e8ffffff89b5ecffffff89b5f0ffffff89b5f4ffffff89b5f8ffffff89b544ffffff898d48ffff"
      .. "ff89854cffffff899550ffffff89b554ffffff89b558ffffff89b55cffffff89b560ffffff89b564ffffff89"
      .. "b568ffffff89b56cffffff89b570ffffff89b574ffffff89b578ffffff89b57cffffff89b580ffffff89b584"
      .. "ffffff89b588ffffff89b58cffffff89b590ffffff89b594ffffff89b598ffffff89b59cffffffe8121ff7ff"
      .. "8b58308b078b0d8412520289c231caf7c2ff3f0000750931c8a900c0ffff74348b8580feffff5057e804fcfc"
      .. "ff8b8d80feffff0fb7f88b0183c40883f801752aba583400006639d7744fb8d82700006639c774455f5e31c0"
      .. "5b8b8dfcffffff31e9e80fca030089ec5dc383f802752ab9593400006639cf7420bad92700006639d774165f"
      .. "5e31c05b8b8dfcffffff31e9e8e0c9030089ec5dc35789d9e84588f7ff83ff3d75138b450c8b0083f81773a4"
      .. "8b848544ffffffeb5883ff3c75138b4d0c8b0183f817738c8b8485a0ffffffeb408b901802000081e2000000"
      .. "c081fa0000004076178b450c8b0083f8190f8361ffffff8b8485e0feffffeb158b4d0c8b0183f8170f834aff"
      .. "ffff8b848584feffff8b9580feffff393274059929d0d1f88b8dfcffffff5f5e31e95be845c9030089ec5dc3" },
    { "prize step", 0x03640abe,
      "8d85d0ffffff50e8eda226008b8dccffffff8b85d0ffffff0141088b95e0ffffff83c404895104c641140185"
      .. "c00f84b40000008d85a8ffffff50e854d926008b088b95e8ffffff898a7c170000e9920000008b8df0ffffff"
      .. "8b43585150e8f58526000fb6f083c40883fe0b747a8b53588d85f0ffffff508d8db8ffffff8995bcffffff51"
      .. "8d95bcffffff5289b5b8ffffffe8b397260083c40c8985c8ffffff85c074448b8dccffffff8941088d85c8ff"
      .. "ffff50897104c6411401e83aa2260083c40439bdc8ffffff" },
    { "balance add", 0x038aadb7,
      "5589e5e82613f7ff8b48308b45088b0085c0741a3dffe0f5057c07b8ffe0f505eb0c3d011f0afa7f05b8011f"
      .. "0afa0381e4dfdd003dffffff7f7c0cc781e4dfdd00ffffff7f5dc33d000000807f0cc781e4dfdd0000000080"
      .. "5dc38981e4dfdd005dc3" },
    { "budget add", 0x038aac87,
      "5589e5e85614f7ff8b48308b45088b0085c0741a3dffe0f5057c07b8ffe0f505eb0c3d011f0afa7f05b8011f"
      .. "0afa0381c4dfdd003dffffff7f7c0cc781c4dfdd00ffffff7f5dc33d000000807f0cc781c4dfdd0000000080"
      .. "5dc38981c4dfdd005dc3" },
    { "mode number", 0x03808865,
      "a1e8f36402c3" },
    { "years limit", 0x03887f5d,
      "5589e551e87f41f9ff8b4d088b51048b098b4030525189c1e8bba8f9ff8d95fcffffff526a2b89c1c785fcff"
      .. "ffff14000000e81cf9f9ff0fb68dfcffffffb80500000083f9237209b80100000089ec5dc383f9207209b802"
      .. "00000089ec5dc383f9177705b80300000089ec5dc3" },
}

-- registered position as the game numbers it -> name in POSITION
local POSITIONS = { "GK", "CB", "LB", "RB", "DMF", "CMF", "LMF", "RMF", "AMF", "LWF", "RWF", "SS", "CF" }

local function hex(s)
    local t = {}
    for i = 1, #s do t[i] = string.format("%02x", string.byte(s, i)) end
    return table.concat(t)
end

local function unhex(h)
    local t = {}
    for i = 1, #h, 2 do t[#t + 1] = string.char(tonumber(string.sub(h, i, i + 1), 16)) end
    return table.concat(t)
end

local function u16(v)
    return string.char(v % 256, math.floor(v / 256) % 256)
end

local function u32(v)
    return string.char(v % 256, math.floor(v / 256) % 256, math.floor(v / 65536) % 256,
        math.floor(v / 16777216) % 256)
end

-- a number of 0 or more as the 8 bytes of a double
local function f64(x)
    if x <= 0 then return string.rep("\0", 8) end
    local e = 1023
    while x >= 2 do x, e = x / 2, e + 1 end
    while x < 1 do x, e = x * 2, e - 1 end
    local low = (x - 1) * 4503599627370496       -- 52 bits
    local high = math.floor(low / 4294967296)
    return u32(low - high * 4294967296) .. u32(high + e * 1048576)
end

-- the dword at byte i (from 0) of a string of hex digits
local function dword(h, i)
    local p = 2 * i
    return tonumber(string.sub(h, p + 7, p + 8) .. string.sub(h, p + 5, p + 6)
        .. string.sub(h, p + 3, p + 4) .. string.sub(h, p + 1, p + 2), 16)
end

-- the game's cup prizes, from the bytes of its table kept in CONTEXT:
-- GAME_CUP[i] = { competition, stage, amount }
local GAME_CUP = {}
for _, c in ipairs(CONTEXT) do
    if c[1] == "cup table" then
        for i = 0, CUP_ROWS - 1 do
            GAME_CUP[i + 1] = { dword(c[3], 12 * i), dword(c[3], 12 * i + 4), dword(c[3], 12 * i + 8) }
        end
    end
end

-- index of the game's row for a competition and stage, or nil
local function cup_row(competition, stage)
    for i, r in ipairs(GAME_CUP) do
        if r[1] == competition and r[2] == stage then return i end
    end
    return nil
end

local function clamp(v, lo, hi)
    if v < lo then return lo end
    if v > hi then return hi end
    return v
end

-- 1234567 -> "1,234,567"
local function commas(v)
    local s = string.format("%.0f", v)
    local out = ""
    while #s > 3 do
        out = "," .. string.sub(s, -3) .. out
        s = string.sub(s, 1, -4)
    end
    return s .. out
end

-- nil, or what is wrong with a list of { x, y } entries
local function list_fault(name, knots, positive)
    if type(knots) ~= "table" or #knots == 0 then return name .. " is empty" end
    for i, k in ipairs(knots) do
        if type(k) ~= "table" or type(k[1]) ~= "number" or type(k[2]) ~= "number" then
            return name .. ": entry " .. i .. " is not { number, number }"
        end
        if i > 1 and k[1] <= knots[i - 1][1] then
            return name .. ": entry " .. i .. " is not above the entry before it"
        end
        if positive and k[2] <= 0 then return name .. ": entry " .. i .. " is not above 0" end
        if k[2] < 0 then return name .. ": entry " .. i .. " is below 0" end
    end
    return nil
end

-- nil, or what is wrong with a single number (off: false is allowed too)
local function number_fault(name, v, lo, hi, off)
    if off and v == false then return nil end
    if type(v) ~= "number" or v < lo or v > hi then
        return name .. " is not a number from " .. lo .. " to " .. hi .. (off and " or false" or "")
    end
    return nil
end

-- nil, or what is wrong with a list of league prizes
local function league_fault(name, list, places)
    if list == false then return nil end
    if type(list) ~= "table" or #list ~= places then
        return name .. " is not a list of " .. places .. " numbers or false"
    end
    for i = 1, places do
        if type(list[i]) ~= "number" or list[i] < 0 or list[i] > 2000 then
            return name .. ": entry " .. i .. " is not a number from 0 to 2000"
        end
    end
    return nil
end

-- nil, or what is wrong with CUP
local function cup_fault()
    if CUP == false then return nil end
    if type(CUP) ~= "table" then return "CUP is not a list or false" end
    for i, r in ipairs(CUP) do
        if type(r) ~= "table" or type(r[1]) ~= "number" or type(r[2]) ~= "number"
            or type(r[3]) ~= "number" then
            return "CUP: entry " .. i .. " is not { competition, stage, millions }"
        end
        if not cup_row(r[1], r[2]) then
            return "CUP: entry " .. i .. ": the game has no prize for competition " .. r[1]
                .. ", stage " .. r[2]
        end
        if r[3] < 0.001 or r[3] > 2000 then
            return "CUP: entry " .. i .. ": the amount is not from 0.001 to 2000"
        end
    end
    return nil
end

local function settings_fault()
    if #GAME_CUP ~= CUP_ROWS then return "the module file is damaged (cup table)" end
    local fault = list_fault("VALUE", VALUE, true) or list_fault("AGE", AGE, false)
        or list_fault("SALARY_AGE", SALARY_AGE, false)
    if fault then return fault end
    if SALARY then
        fault = list_fault("SALARY", SALARY, true)
        if fault then return fault end
    end
    if type(POSITION) ~= "table" then return "POSITION is not a table" end
    for _, name in ipairs(POSITIONS) do
        fault = number_fault("POSITION." .. name, POSITION[name], 0, 200, false)
        if fault then return fault end
    end
    return number_fault("SPREAD", SPREAD, 0, 30, false) or number_fault("FAME", FAME, 0, 100, false)
        or number_fault("BUDGET_TRANSFER", BUDGET_TRANSFER, 0.1, 10, true)
        or number_fault("BUDGET_SALARY", BUDGET_SALARY, 0.1, 10, true)
        or cup_fault() or league_fault("LEAGUE", LEAGUE, 22) or league_fault("LEAGUE_2", LEAGUE_2, 24)
        or number_fault("PRIZE_TO_BUDGET", PRIZE_TO_BUDGET, 1, 100, true)
        or number_fault("PAY_GAP", PAY_GAP, 1, 10, true)
        or number_fault("BONUS", BONUS, 0, 1000, true)
        or number_fault("YOUNG_YEARS", YOUNG_YEARS, 1, 5, true)
end

-- value for every whole number lo..hi (index 1 = lo)
local function curve(knots, lo, hi, geometric)
    local out = {}
    local n = #knots
    for x = lo, hi do
        local y
        if x <= knots[1][1] then
            y = knots[1][2]
        elseif x >= knots[n][1] then
            y = knots[n][2]
        else
            for i = 1, n - 1 do
                local a, b = knots[i], knots[i + 1]
                if a[1] <= x and x <= b[1] then
                    local t = (x - a[1]) / (b[1] - a[1])
                    if geometric then
                        y = a[2] * (b[2] / a[2]) ^ t
                    else
                        y = a[2] + (b[2] - a[2]) * t
                    end
                    break
                end
            end
        end
        out[#out + 1] = y
    end
    return out
end

-- millions on the screen -> the game's stored amount (the screen shows 100 times it),
-- rounded to 10
local function amount(millions)
    return math.floor(millions * 1000 + 0.5) * 10
end

function m.init(ctx)
    log("MLMoney 3: player values, salaries, budgets and prize money from the tables in MLMoney.lua")

    local fault = settings_fault()
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end

    -- the tables as the game will read them
    local value, age, salary, salary_age, position = {}, {}, {}, {}, {}
    for i, v in ipairs(curve(VALUE, 0, 99, true)) do value[i] = clamp(amount(v), 1, CAP) end
    for i, v in ipairs(curve(AGE, 0, 63, false)) do age[i] = clamp(math.floor(v + 0.5), 0, 300) end
    local gap = PAY_GAP or 2
    if SALARY then
        for i, v in ipairs(curve(SALARY, 0, 99, true)) do
            salary[i] = clamp(amount(v / gap), 1, 40000000)
        end
    else
        for i = 1, 100 do salary[i] = 0 end
    end
    for i, v in ipairs(curve(SALARY_AGE, 0, 63, false)) do
        salary_age[i] = clamp(math.floor(v + 0.5), 0, 200)
    end
    for i, name in ipairs(POSITIONS) do position[i] = math.floor(POSITION[name] + 0.5) end
    for i = #POSITIONS + 1, 16 do position[i] = 100 end
    local spread = math.floor(SPREAD + 0.5)
    local fame = math.floor(FAME + 0.5)
    local budget_t = BUDGET_TRANSFER and math.floor(BUDGET_TRANSFER * 100 + 0.5) or 200
    local budget_s = BUDGET_SALARY and math.floor(BUDGET_SALARY * 100 + 0.5) or 200
    -- prizes: the game's cup rows with the amounts of CUP, the two league lists (their
    -- first entry is not a place)
    local cup, league, league_2 = {}, { 0 }, { 0 }
    for i, r in ipairs(GAME_CUP) do cup[i] = r[3] end
    if CUP then
        for _, r in ipairs(CUP) do cup[cup_row(r[1], r[2])] = clamp(amount(r[3]), 10, 20000000) end
    end
    for i = 1, 22 do league[i + 1] = LEAGUE and clamp(amount(LEAGUE[i]), 0, 20000000) or 0 end
    for i = 1, 24 do league_2[i + 1] = LEAGUE_2 and clamp(amount(LEAGUE_2[i]), 0, 20000000) or 0 end
    local share = PRIZE_TO_BUDGET and math.floor(PRIZE_TO_BUDGET + 0.5) or 0
    local bonus = BONUS and math.floor(BONUS + 0.5) or 100
    local years = YOUNG_YEARS and math.floor(YOUNG_YEARS + 0.5) or 3

    local parts = {}
    for i = 1, 100 do parts[#parts + 1] = u32(value[i]) end
    for i = 1, 100 do parts[#parts + 1] = u32(salary[i]) end
    for i = 1, 64 do parts[#parts + 1] = u16(age[i]) end
    for i = 1, 64 do parts[#parts + 1] = u16(salary_age[i]) end
    for i = 1, 16 do parts[#parts + 1] = u16(position[i]) end
    local image = table.concat(parts)
    if #image ~= NUMBERS_AT then
        log("RESULT: nothing written. The module file is damaged (table size " .. #image .. ").")
        return
    end
    -- popularity percent, lowest spread factor and width of the spread in thousandths,
    -- the two budget factors in percent, 100, 1000, a mark
    image = image .. u32(fame) .. u32(1000 - 10 * spread) .. u32(20 * spread) .. u32(budget_t)
        .. u32(budget_s) .. u32(100) .. u32(1000) .. "MLM3"
    -- then the routines and the newer tables, each at its offset
    local pieces = {}
    for _, r in ipairs(ROUTINES) do pieces[#pieces + 1] = { r[1], unhex(r[2]) } end
    parts = {}
    for i = 1, 23 do parts[i] = u32(league[i]) end
    pieces[#pieces + 1] = { LEAGUE_AT, table.concat(parts) }
    parts = {}
    for i = 1, 25 do parts[i] = u32(league_2[i]) end
    pieces[#pieces + 1] = { LEAGUE_2_AT, table.concat(parts) }
    -- the game's own step is 0.004 as a float
    pieces[#pieces + 1] = { GAP_AT, PAY_GAP and f64((PAY_GAP - 1) / 250) or unhex("000000e04d62703f") }
    pieces[#pieces + 1] = { SHARE_AT, u32(share) .. u32(bonus) }
    parts = {}
    for i, r in ipairs(GAME_CUP) do parts[i] = u32(r[1]) .. u32(r[2]) .. u32(cup[i]) end
    pieces[#pieces + 1] = { CUP_AT, table.concat(parts) }
    table.sort(pieces, function(a, b) return a[1] < b[1] end)
    for _, piece in ipairs(pieces) do
        if piece[1] < #image then
            log("RESULT: nothing written. The module file is damaged (piece at " .. piece[1] .. ").")
            return
        end
        image = image .. string.rep("\0", piece[1] - #image) .. piece[2]
    end
    if #image > CAVE_SIZE then
        log("RESULT: nothing written. The module file is damaged (size " .. #image .. ").")
        return
    end
    image = image .. string.rep("\0", CAVE_SIZE - #image)

    -- 1. is this the game the module was made for?
    local good = true
    for _, c in ipairs(CONTEXT) do
        local got = memory.read(c[2], #c[3] / 2)
        local same = (got ~= nil and hex(got) == c[3])
        log(string.format("check: %-13s at %08x  %s", c[1], c[2], same and "as expected" or "DIFFERENT"))
        if not same then good = false end
    end
    local room = memory.read(CAVE, CAVE_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", CAVE_SIZE))
    log(string.format("check: %-13s at %08x  %s", "free memory", CAVE, empty and "empty" or "NOT EMPTY"))
    if not (good and empty) then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end
    if not WRITE then
        log("RESULT: nothing written (WRITE = false). All checks passed.")
        return
    end

    -- 2. tables and routines first; nothing in the game points to them yet
    memory.write(CAVE, image)
    if memory.read(CAVE, CAVE_SIZE) ~= image then
        log("RESULT: the tables could not be written; the game's code is unchanged. "
            .. "Send this log.")
        return
    end

    -- 3. the places in the game's code
    local on = {
        ["fee"] = true, ["salary"] = SALARY, ["budget 1"] = BUDGET_TRANSFER, ["budget 2"] = BUDGET_SALARY,
        ["cup 1"] = CUP, ["cup 2"] = CUP, ["cup 3"] = CUP, ["league 1"] = LEAGUE, ["league 2"] = LEAGUE_2,
        ["prize 1"] = PRIZE_TO_BUDGET, ["prize 2"] = PRIZE_TO_BUDGET, ["pay gap"] = PAY_GAP,
        ["bonus 1"] = BONUS, ["bonus 2"] = BONUS, ["years"] = YOUNG_YEARS,
    }
    for _, s in ipairs(SITES) do
        if on[s[1]] then
            local at, new = s[2], unhex(s[4])
            if s[1] == "years" then new = string.sub(new, 1, 1) .. u32(years) end
            memory.write(at, new)
            local same = (memory.read(at, #new) == new)
            log(string.format("written: %-8s at %08x  %s", s[1], at, same and "ok" or "FAILED"))
            if not same then
                log("RESULT: a change did not go in. Quit the game, remove the module, send this log.")
                return
            end
        end
    end
    local changed = "values"
    for _, c in ipairs({
        { SALARY, "salaries" }, { BUDGET_TRANSFER, "transfer budget" }, { BUDGET_SALARY, "salary budget" },
        { CUP, "cup prizes" }, { LEAGUE or LEAGUE_2, "league prizes" },
        { PRIZE_TO_BUDGET, "prizes into the transfer budget" }, { PAY_GAP, "pay gap" },
        { BONUS, "salary bonuses" }, { YOUNG_YEARS, "contract years" } }) do
        if c[1] then changed = changed .. ", " .. c[2] end
    end

    -- 4. what the screens should show now
    local function shown(rating, years)
        local v = math.floor(value[rating + 1] * age[years + 1] / 100)
        if v > CAP then v = CAP end
        return commas(v * 100)
    end
    log("value on the screen for a position at 100 %, before the player's own factor (+- "
        .. spread .. " %) and the popularity bonus (" .. fame .. " % per 1,000 points):")
    log("  rating          age 20          age 25          age 30          age 33")
    for _, rating in ipairs({ 65, 70, 75, 80, 85, 88, 90, 92, 94 }) do
        log(string.format("  %6d %15s %15s %15s %15s", rating, shown(rating, 20), shown(rating, 25),
            shown(rating, 30), shown(rating, 33)))
    end
    local line = "position percent:"
    for i, name in ipairs(POSITIONS) do line = line .. " " .. name .. " " .. position[i] end
    log(line)
    if SALARY then
        log("rating part of the yearly salary on the screen at the age where SALARY_AGE says 100: "
            .. "first club of the ranking / club outside the first 250")
        for _, rating in ipairs({ 65, 70, 75, 80, 85, 88, 90, 92, 94 }) do
            log(string.format("  %6d %15s %15s", rating,
                commas(math.floor(salary[rating + 1] * gap + 0.5) * 100), commas(salary[rating + 1] * 100)))
        end
    end
    if PAY_GAP then
        log(string.format("pay gap: the first club of the ranking pays %.2f x the salary of a club outside "
            .. "the first 250 (the game: 2)", gap))
    end
    if BONUS then
        log("salary bonuses (team role, age band, awards): " .. bonus .. " % of the game's")
    end
    if YOUNG_YEARS then
        log("longest contract for a player of 23 or younger: " .. years .. " years (the game: 3)")
    end
    if CUP then
        log("cup prizes on the screen, competition: stage amount (only the changed ones):")
        local line, last = nil, nil
        for i, r in ipairs(GAME_CUP) do
            if cup[i] ~= r[3] then
                if r[1] ~= last then
                    if line then log(line) end
                    line, last = string.format("  %3d:", r[1]), r[1]
                end
                line = line .. "  " .. r[2] .. " " .. commas(cup[i] * 100)
            end
        end
        if line then log(line) end
    end
    for _, l in ipairs({ { LEAGUE, "first", league, 22 }, { LEAGUE_2, "second", league_2, 24 } }) do
        if l[1] then
            log("league prize on the screen, " .. l[2] .. " division, place 1 to " .. l[4] .. ":")
            local line = " "
            for i = 1, l[4] do
                line = line .. " " .. commas(l[3][i + 1] * 100)
                if i % 8 == 0 or i == l[4] then
                    log(line)
                    line = " "
                end
            end
        end
    end
    if PRIZE_TO_BUDGET then
        log("of every cup and league prize, " .. share .. " % is added to the transfer budget as well")
    end
    if BUDGET_TRANSFER then
        log(string.format("transfer budget at the start of a career: %.2f x the mean value of the "
            .. "16 best players (the game: 2)", budget_t / 100))
    end
    if BUDGET_SALARY then
        log(string.format("salary budget at the start of a career: wage bill + %.2f x the mean "
            .. "salary of the 16 best paid players (the game: 2)", budget_s / 100))
    end
    log("RESULT: installed. Changed: " .. changed .. ".")
end

return m
