-- MLMoney.lua, version 5: real-world player values, salaries, budgets, income and prize
-- money in the PES 2017 Master League, and a price ceiling for the transfers of the
-- computer clubs (Sider Lua module). Made for PES2017.exe sha256
-- 44b0caaa...; MLCheck.lua must have said "6 of 6 as expected" on your game before you use
-- this one.
--
-- What it changes, in the running game only (no file is touched):
--   * the value of a player (the transfer fee the game computes) becomes
--         VALUE[rating] x AGE[age] x (1 + talent bonus) x POSITION[position] x spread
--         x (1 + popularity bonus)
--     instead of  salary x 2.2..3.3 + 9,000 x (rating - 68);
--   * the rating part of the yearly salary becomes SALARY[rating] x SALARY_AGE[age]; the
--     popularity part stays the game's own;
--   * the transfer budget your club gets when a career starts becomes BUDGET_TRANSFER
--     times the mean value of its 16 best players (the game: 2 times);
--   * the yearly income of your club grows by INCOME_WAGES percent of its wage bill, so
--     that it carries the larger salaries (INCOME multiplies the game's amounts instead);
--   * the prize money of cups (CUP, CUP_TV, CUP_NATIONAL) and of the leagues (LEAGUE,
--     LEAGUE_BY_ID, LEAGUE_2);
--   * PRIZE_TO_BUDGET percent of every prize is added to the transfer budget (the game
--     puts a prize into the club's balance only);
--   * the first club of the game's club ranking pays PAY_GAP times the salary of a club
--     outside the first 250 (the game: 2 times);
--   * the role, age and award bonuses of the salary are multiplied by BONUS percent;
--   * a player of 23 or younger can sign for YOUNG_YEARS years (the game: 3);
--   * a computer club no longer signs a player whose value is above what a club of its
--     place in the club ranking pays at most (CEILING; the game looks at the rating only).
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
-- career for numbers that fit together, or set SALARY, PAY_GAP, BONUS and INCOME_WAGES to
-- false for a running one. Prizes and the contract limit work in a running career at once.
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

-- Talent: a young player who is already good for his age costs more. The game keeps no
-- "potential" number for a player that this module could read (see README.md), so the
-- rating a player has at his age stands for it. { age, rating }: the rating that is
-- ordinary at that age, straight lines between the entries; ages above the last entry get
-- no bonus. false: no talent bonus.
local TALENT = { { 16, 62 }, { 18, 66 }, { 20, 70 }, { 22, 74 }, { 23, 76 } }

-- Percent added to the value for every rating point above that rating (0 to 50), the most
-- percent it can add (0 to 200) and the most millions it can add (0 to 999). The bonus is
-- worked out before position, spread and popularity.
local TALENT_STEP = 6
local TALENT_MAX = 60
local TALENT_CAP = 40

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

-- Yearly income of your club. The game books two amounts on the first day of a season:
-- one by the club's place in its club ranking (about 200 million for the first club, 75
-- million for place 250) and one by the popularity of the club and its players (30 to 80
-- million). Neither knows what the club pays its players, and SALARY above makes a strong
-- squad cost two to two and a half times what it costs in the game.
--
-- INCOME_WAGES: this percent of the club's wage bill of that day is added to the second
-- amount. With 60, the year's income less the wages comes out within about 15 million of
-- what the game alone gives, for a strong squad and for a weak one (README.md has the
-- table). It also means that of every salary you add, 60 percent comes back as income.
-- 1 to 100; false: nothing is added.
local INCOME_WAGES = 60

-- INCOME: both amounts in percent of the game's, and with them the amount of the first
-- kind that a new career starts with. A blunt tool: 150 gives the richest clubs what
-- INCOME_WAGES = 60 gives them, and gives every small club 50 to 90 million a year more
-- than it needs. Prizes are not part of either setting. 10 to 1000; false: the game's
-- amounts.
local INCOME = false

-- Prize of a cup: { competition, stage, millions }. The game pays a cup once, when your
-- club is out or has won it, so each amount is the money of the whole run. competition is
-- the game's number of the cup. stage: 0 winner, 1 runner-up, 2 third place, 3 out in
-- the semi-final, 4 in the quarter-final, 5 in the round of 16 (Europa League only), 7 in
-- the first knock-out round, 9 out in the group stage. Only a competition and stage the
-- game itself has a prize for can stand here (python3 ../tools/prize.py lists them); the
-- ones not named here keep the game's amount, and so do the national cups. 0.001 to 2000.
-- false: leave the game's cup prizes alone.
-- These numbers: the fixed payments of 2025/26 (Sudamericana and Libertadores 2025, AFC
-- 2024/25) added up to the stage; the payments per win are not in them, the television
-- shares are in CUP_TV. Euros, pounds and dollars are taken as the same.
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

-- Television money of a cup: { competition, millions }, added to every amount CUP names
-- for that competition. These numbers: UEFA's "value" share of 2024/25 divided by the 36
-- clubs (853 million in the Champions League, 198 million in the Europa League); in
-- reality a club gets between a few million and about 45, by its ranking and country.
-- 0 to 2000; false: nothing is added. With CUP = false this setting does nothing.
local CUP_TV = { { 2, 23.7 }, { 3, 5.5 } }

-- Prize of every cup the game has no row for, which is every national cup: millions for
-- { winner, runner-up, out in the semi-final (and third place), out in the quarter-final,
-- out in the round of 16, out in the round before }. The game: 2, 1, 0.5, 0.1, 0.05, 0.03.
-- One list serves all countries. These numbers: the FA Cup's payments of 2024/25 from the
-- third round on, added up (the DFB-Pokal pays about 11 million to its winner, added up
-- the same way). 0.001 to 2000; false: leave the game's amounts.
local CUP_NATIONAL = { 3.91, 2.91, 1.41, 0.46, 0.235, 0.115 }

-- Prize of a first division by place, millions, place 1 to 22 (22 numbers). This list
-- serves every first division that LEAGUE_BY_ID does not name. These numbers: the
-- Premier League's payments by place of 2024/25. 0 to 2000. false: leave the game's list
-- alone (and LEAGUE_BY_ID does nothing).
local LEAGUE = {
    53.1, 50.4, 47.7, 45.0, 42.4, 39.8, 37.1, 34.5, 31.9, 29.1, 26.5,
    23.8, 21.2, 18.6, 15.9, 13.3, 10.7, 7.9, 5.3, 2.6, 2.6, 2.6,
}

-- First divisions with numbers of their own: { league, { millions by place } } with up to
-- 22 numbers (places after the last number get the last number), or { league, percent }
-- for that percent of LEAGUE. league is the game's number of the league: 17 England,
-- 18 Italy, 19 Spain, 20 France, 21 Netherlands, 22 Portugal, 29 Brazil, 30 Argentina,
-- 50, 51 and 52 the three leagues without a licence (50 is Germany in the usual patches),
-- 67 Chile. At most 12 entries; an amount is at most 650 and is kept in steps of 10,000.
-- false: LEAGUE for every first division.
-- These numbers are not all of one kind, because the leagues publish different things:
--   19 Spain: the quarter of LaLiga's television money that is shared by place, 2023/24;
--   50 Germany: a club's television money of 2024/25 less about 26 million, which is
--      roughly the part every club gets (shared by results of several years, not by place);
--   18 Italy: the same for 2023/24 less the equal share of 26.8 million; only the first
--      ten amounts are published figures, places 11 to 20 are filled in evenly;
--   21 Netherlands: all of a club's media money of 2026/27 (by results of several years);
--   29 Brazil: the prize by place of 2024 at 6 reais to the euro; places 17 to 20 get none;
--   20 France: 9 percent, the size of the television money of 2025/26 (80 million in all);
--   22, 30, 51, 52, 67: 5 percent, an estimate without a published list behind it.
local LEAGUE_BY_ID = {
    { 19, { 58.4, 51.5, 44.6, 37.8, 30.9, 24.0, 17.2, 12.0, 10.3, 9.4,
            8.6, 7.7, 6.9, 6.0, 5.1, 4.3, 3.4, 2.6, 1.7, 0.9 } },
    { 50, { 71.1, 61.5, 60.4, 57.5, 53.3, 46.7, 43.8, 41.6, 39.1, 35.2,
            31.6, 27.3, 24.0, 19.9, 17.3, 14.4, 8.9, 6.6 } },
    { 18, { 74.2, 60.6, 59.9, 44.6, 40.1, 40.0, 33.6, 32.6, 29.4, 20.6,
            18.6, 16.9, 15.1, 13.4, 11.7, 9.9, 8.2, 6.5, 4.7, 3.0 } },
    { 21, { 14.73, 13.22, 11.7, 10.19, 9.38, 8.15, 6.93, 5.71, 4.78, 4.37,
            4.09, 3.8, 3.56, 3.47, 3.44, 3.42, 3.4, 3.37 } },
    { 29, { 8.0, 7.6, 7.2, 6.8, 6.4, 6.0, 5.6, 5.2, 4.8, 4.4,
            3.5, 3.2, 3.0, 2.9, 2.8, 2.7, 0, 0, 0, 0 } },
    { 20, 9 }, { 22, 5 }, { 30, 5 }, { 51, 5 }, { 52, 5 }, { 67, 5 },
}

-- Prize of a second division by place, millions, place 1 to 24 (24 numbers).
-- false: leave the game's list alone (2 million for place 1 down to 25,000). The English
-- second division pays no prize by place at all, so the game's size is about right.
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

-- Price ceiling of the computer clubs. In the game a computer club has no money. It
-- chooses the players it signs by rating, age and position, never by price, and when it
-- finds nobody for a position in the rating range of its size it looks again among all
-- players, from the best down.
-- With this setting a computer club passes over every player whose value (the value this
-- module computes, before the game's random change) is above the club's ceiling, and
-- takes the best players below it instead. The ceiling goes by the club's place in the
-- game's club ranking, in the ten groups the game itself uses for the rating range:
-- millions for the clubs at place
--     1-10, 11-20, 21-50, 51-80, 81-120, 121-170, 171-220, 221-260, 261-300, all others.
-- 0.01 to 9999 each, or 0 for a group without a ceiling. false: computer clubs choose as
-- in the game.
-- Your own club is not touched: what you can buy is a matter of your budget, and offers
-- for your players go another way. No money is booked by this setting; a computer club
-- still has no account.
-- These numbers: about the value of the most valuable player of the middle club of each
-- group in the squads this module was set against, with more room for the first twenty
-- clubs (README.md has the table; ceiling_survey.py prints it for your edit file).
-- If you change VALUE much, change these with it.
local CEILING = { 200, 100, 50, 28, 18, 12, 8, 6, 4.5, 3 }

-- The second search. A computer club looks for a player in a rating range that goes by
-- its place in the ranking (the smallest clubs 47 to 74, the ten best 83 to 99). When it
-- finds nobody for a position there, the game lets it look again among all players,
-- from rating 99 down. It leaves out the stars of other clubs who are not for sale, but
-- not the players without a club and not those who have outgrown their club: a small
-- club can come away with one of the best of them. true: in that second search a club takes nobody rated above the top of its own
-- range (74, 75, 76, 77, 78, 79, 80, 83, 86 from the smallest clubs up; the ten best
-- clubs have no limit), so it looks further down, not further up. Without this, the
-- ceiling alone still lets a small club sign a great player of 38 whose value has fallen
-- below it. false: the second search goes from 99 down as in the game.
-- Used only while CEILING is on.
local CEILING_RATING = true

-- ========================= end of settings =========================

local CAP = 99999900            -- the game's largest amount (9,999,990,000 on the screen)
local CAVE = 0x047b0200         -- unused end of the code section: tables and 13 routines
local CAVE_SIZE = 0xdf0
local NUMBERS_AT = 0x440         -- offset of the single numbers in that memory
local LEAGUE_AT, LEAGUE_2_AT = 0x5c0, 0x620     -- the two league lists
local GAP_AT = 0x688             -- rise of the club factor per place of the ranking (a double)
local SHARE_AT = 0x690           -- PRIZE_TO_BUDGET, then BONUS
local CUP_AT = 0x720             -- the cup table
local CUP_ROWS = 73
local TALENT_AT = 0x480            -- by age: the rating above which the talent bonus starts
local NUMBERS_2_AT = 0xb80         -- talent step, most percent, most amount, income percent
local LEAGUE_IDS_AT = 0xb90        -- the leagues of LEAGUE_BY_ID
local LEAGUE_COUNT_AT = 0xba8      -- how many there are, then INCOME_WAGES
local LEAGUE_ROWS_AT = 0xbb0       -- their lists
local LEAGUE_ROWS = 12
local CAVE_2 = 0x047b0130       -- a second unused piece of the same page: the price ceilings and their routine
local CAVE_2_SIZE = 0xcc
-- the highest rating of the range a computer club searches first, smallest clubs first (the game's numbers)
local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }
-- the routines: offset in that memory, machine code (source: money_cave.py)
local ROUTINES = {
    { 0xa90, "83f8637605b86300000089c78b048500027b048b4b1cc1e90783e13f0fb69180067b0429d77f"
      .. "0231ff0faf3d800d7b043b3d840d7b0476068b3d840d7b040fb70c4d20057b04f7e1f73554067b0450f7e7f7"
      .. "3554067b043b05880d7b047605a1880d7b045901c88b4b04c1e91c0fb70c4d20067b04f7e1f73554067b040f"
      .. "b74b2c6953309301000131d169c9b179379ec1e9180faf0d48067b04c1e908030d44067b04f7e1f73558067b"
      .. "043d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100"
      .. "f7f101c7c745f400000000c3" },
    { 0x540, "83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f735"
      .. "54067b048945c8c745cc00000000c3" },
    { 0x580, "8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3" },
    { 0x5a0, "52f72550067b04f73554067b045a8d3401e92fb906ff" },
    { 0x6a0, "8b44240450e80da50fff83c404e8b37f05ff83782013751c8b4424048b00f72d90087b04f73d"
      .. "54067b045054e8b6a30fff83c408c3" },
    { 0x6e0, "505289f0f72594087b04f73554067b0489c65a580375b0c3" },
    { 0x700, "528b45cc0345b0f72594087b04f73554067b045ac3" },
    { 0x460, "8d863e56cbffe86d00000089c18b45fcf725ac0d7b04f73554067b0401c8c3" },
    { 0x4cc, "69c088130000eb04" },
    { 0x4d8, "85c07e0e52f7258c0d7b04f73554067b045ac3" },
    { 0x4ec, "81c6983a00005089f0e8deffffff89c658c3" },
    { 0x500, "31c9eb0d0fb7144d900d7b0439fa7411413b0da80d7b0472eb8b0485c0077b04c36bc91801c1"
      .. "0fb7044db00d7b046bc064c3" },
    { 0x532, "8945fc58ff750850e916810cff" },
}

-- The places that are changed: name, address, bytes there now, bytes to write. (The
-- number in "years" is YOUNG_YEARS and the amounts of the six "nat" places are
-- CUP_NATIONAL; they are put in below.)
local SITES = {
    { "fee", 0x038ab8db, "83f844760c8db8bcffffff69ff28230000", "e8b053f000909090909090909090909090" },
    { "salary", 0x038ac875, "89c1c1e10429c1", "e8c63ef000eb5b" },
    { "budget 1", 0x038adc47, "01f68b4030", "e8342bf000" },
    { "budget 2", 0x038add08, "8d3441e8d5e3f6ff", "e8932af000909090" },
    { "cup 1", 0x038aa400, "78b11602", "20097b04" },
    { "cup 2", 0x038aa408, "7cb11602", "24097b04" },
    { "cup 3", 0x038aa423, "80b11602", "28097b04" },
    { "league 1", 0x038aa2dd, "8b848584feffff", "e81e64f0009090" },
    { "league 2", 0x038aa2c6, "8b8485e0feffff", "8b048520087b04" },
    { "prize 1", 0x03640ac5, "e8eda22600", "e8d6fd1601" },
    { "prize 2", 0x03640b78, "e83aa22600", "e823fd1601" },
    { "pay gap", 0x038aca1b, "88fef201", "88087b04" },
    { "bonus 1", 0x038aca2b, "03b5b0ffffff", "e8b03ef00090" },
    { "bonus 2", 0x038acd96, "8b85ccffffff0385b0ffffff", "e8653bf00090909090909090" },
    { "years", 0x03887fc1, "b803000000", "b805000000" },
    { "income 1", 0x038adeee, "8d863e56cbff", "e86d27f00090" },
    { "income 2", 0x038a9e9c, "69c088130000", "e82b68f00090" },
    { "income 3", 0x038ae025, "81c6983a0000", "e8c226f00090" },
    { "income 4", 0x038adeaa, "8b450850e8a2a9fcff", "e88328f00090909090" },
    { "nat 0", 0x038aa43a, "204e0000", "204e0000" },
    { "nat 1", 0x038aa446, "10270000", "10270000" },
    { "nat 2", 0x038aa452, "88130000", "88130000" },
    { "nat 3", 0x038aa45e, "e8030000", "e8030000" },
    { "nat 4", 0x038aa46a, "f4010000", "f4010000" },
    { "nat 5", 0x038aa476, "2c010000", "2c010000" },
    { "ceiling", 0x0365fb0d, "8b4d2456e8aa98ac00", "e85006150190909090" },
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
    { "income", 0x038ade76,
      "5589e55157e865e2f6ff8b78308d87c4dfdd0085c075055f89ec5dc3568d8dffffffff518d550852c685ffff"
      .. "ffff00e8fef8ffff8b450850e8a2a9fcff83c40c8d4d08518d8fcc84cc0089c6e86d3d90ff8b40043d900100"
      .. "007605b89001000081fef04902007d05bef049020069c09e0200006bf61929c68d863e56cbff5e85c07f05b8"
      .. "e80300005f89ec5dc3" },
    { "rank income", 0x038a9e6b,
      "5589e5e87222f7ff8b40308d88c4dfdd0085c9750431c05dc38d5508528d88cc84cc00e8a0e488ff89c1b893"
      .. "01000029c869c08813000085c07f05b8e80300005dc3" },
    { "career money", 0x038adfb6,
      "e8bbfeffff8d8dffffffff518d95f8ffffff528985f4ffffffc685ffffffff00c785f8ffffff15000000e8b3"
      .. "79faff8b8df0ffffff83e80a8985f8ffffff83c4108d85f0ffffff50e86f83dcff508d8bcc84cc00e8253c90"
      .. "ffdb85f8ffffff0fb6700e69f688840200dc35806dee0181c6983a000089b5f0ffffffda8df0ffffffe8268c"
      .. "03008d8df8ffffff01f05189" },
}

-- The price ceiling: its routine (offset in the second piece of memory) and the code
-- it relies on, which is compared only when CEILING is on.
local CEILING_ROUTINE = { 0x32, "53575589e583ec148b45008b58d88b480481f9580d6603740881f9b90d66"
      .. "0375558b000fb6481b894df08b401c8b0083f80977420fb68858017b04894dec8b048530017b048945fcc745"
      .. "f80d0000006a028d45f85053e885390aff83c40c0fb6c0837df00074053b45ec771ae8bd0a00003b7dfc7710"
      .. "89ec5d5f5b588b4d245650e9d89197ff89ec5d5f5b83c404e933f9eafe" }
local CEILING_CONTEXT = {
    { "choose", 0x0365f5c2,
      "5589e583ec64535689cb31f657899df4ffffff89b5fcffffffe805cb1b008b40308d8ddcffffff518985f8ff"
      .. "ffff89b5e8ffffffe856ee24008b45108b550c83c404bf630000002b388d8dccffffff518b4d18be63000000"
      .. "2b3289bdd0ffffffe84b6d01008b108b8df8ffffff52e834331c0089f28985d4ffffff8995e4ffffff39fe0f"
      .. "832405000083c63cc1e60401de89b5e0ffffff8b45088b0883f9010f8ff004000083fa3c0f83e704000083f9"
      .. "0175078b46042b06eb0c8b8644fcffff2b8640fcffffc1f80485c00f84c404000083f90175078b0e894d10eb"
      .. "098b9640fcffff8955108b4d108b45088b0083f8017e058b4304eb0d75058b4604eb068b8644fcffff39c10f"
      .. "84790400008b51048b018b8df8ffffff5250e8822f1c0089c689b5d8ffffff85f60f843d040000f786b80000"
      .. "00000000100f852d0400008b83a00700008b0d34eb4f0289c231caf7c2ff3f0000750931c8a900c0ffff744d"
      .. "838dfcffffff018d450c508d8dc8ffffff5189f1c7450c00000000e845b91c008b008b8ba007000089c231ca"
      .. "f7c2ff3f0000751331c8a900c0ffff750a8b0d34eb4f02b001eb088b0d34eb4f0230c0f685fcffffff017407"
      .. "83a5fcfffffffe84c00f85a50300008b83a407000089c231caf7c2ff3f0000750931c8a900c0ffff7441838d"
      .. "fcffffff028d450c508d8dc4ffffff5189f1c7450c00000000e8c3b81c008b008b8ba407000089c231caf7c2"
      .. "ff3f0000750d31c8a900c0ffff7504b001eb0230c0f685fcffffff02740783a5fcfffffffd84c00f852f0300"
      .. "008d450c508d8dc0ffffff5189f1c7450c00000000e86fb81c008b4d188d95bcffffff5289c7e8496b01008b"
      .. "088b0789c231caf7c2ff3f0000750d31c8a900c0ffff0f84e8020000f686b4000000300f85db0200008d450c"
      .. "50bf140000006a2b89f1897d0ce848801c000fb64d0c8b55283b0a0f82b70200008d450c506a2b89f1897d0c"
      .. "e829801c000fb64d0c8b552c3b0a0f87980200008b4508833801745d56e86a471f008b5d3089c78b0383c404"
      .. "39c70f8272020000f686b40000000f753683f80772178d8ddcffffff5189f1e825d1feff83f8020f824d0200"
      .. "00833b007515f786b800000000000060750983ff060f83330200008b9df4ffffff8b7d14833f0d741d8b5520"
      .. "528d450f50575689d9c6450f00e87bd9ffff84c00f840e020000833f000f852e0100008d4d0c518d95f0ffff"
      .. "ff5289f1c7450c00000000e845b71c006834eb4f028d8df0ffffffe8d5d861ff84c00f84fd0000008b85f0ff"
      .. "ffff8b8df8ffffff31f65089b5ecffffffe8f52f1c00f7802803000000fe00000f86aa010000c7450cf80000"
      .. "00908b8df0ffffff518b8df8ffffffe8cb2f1c008b90280300008b3d04eb4f028b1d08eb4f02c1ea0983e27f"
      .. "89bdacffffff899db0ffffff39d673168b4d0c8b3c018b5c010489bdacffffff899db0ffffff6804eb4f028d"
      .. "8dacffffffe8d2e057ff84c075298b8df8ffffff5357e8382e1c0089c789f9e80983abff85c0750ff687b400"
      .. "0000307506ff85ecffffff8b85f0ffffff8b8df8ffffff83450c085046e8392f1c008b8828030000c1e90983"
      .. "e17f39ce0f8248ffffff83bdecffffff020f86d70000008bb5d8ffffff8b7d18c6450f0083c708bb10000000"
      .. "85ff74288b4d108b178b4704518d8da4ffffff8995a4ffffff8985a8ffffffe834e057ff84c07404c6450f01"
      .. "83c7104b75ce385d0f0f85870000008b7d1880bf080100000175388b562c8b46308d8db8ffffff518b8dd4ff"
      .. "ffff89959cffffff8985a0ffffffe8a1680100508d959cffffff52e805c2220083c40884c074438b7510568d"
      .. "85b4ffffff5089f9e87b68010050e80af6220083c40884c07509c6870801000001eb1b8b4d2456e8aa98ac00"
      .. "8b85e8ffffff408985e8ffffff83f80373478b9df4ffffff8b4d108bb5e0ffffff8bbdd0ffffff83c110894d"
      .. "10e963fbffff83bde8ffffff03731e8b95e4ffffff4283c6108995e4ffffff89b5e0ffffff39fa0f82eafaff"
      .. "ff5f5e5b89ec5dc22c00" },
    { "pick", 0x03660c52,
      "5589e56aff680c64540464a1000000005083ec30535657a1501a520231e8508d85f4ffffff64a30000000089"
      .. "8decffffff8b45188b108b451c508995e0ffffffe8f6c3ffff8985e4ffffffc6451b0085d27511b863000000"
      .. "c6451b018985e4ffffffeb0583fa28730ac785e0ffffff2800000083f863760ac785e4ffffff6300000031f6"
      .. "31ff89bdc4ffffff89b5c8ffffff89b5ccffffff89b5fcffffffe8f0b31b008b48308b5d108b4304898de8ff"
      .. "ffff83f801745b83f80474568b55288b45248b4d205250518b4d148d95c4ffffff528b550c8d451b50515352"
      .. "8d85e0ffffff508d8de4ffffff518b8decffffff8d95d8ffffff52c785d8ffffff01000000e86ae8ffff8bb5"
      .. "c8ffffff8bbdc4ffffffc685f3ffffff0039f775588b45288b4d248b55205051528b55148d85c4ffffff508b"
      .. "450c8d4d1b515253508d8de0ffffff518b8decffffff8d95e4ffffff528d85d8ffffff50c785d8ffffff0000"
      .. "0000e809e8ffff8bb5c8ffffff8bbdc4ffffffeb07" },
    { "range", 0x0365d08d,
      "5589e58b45088b0083f8097758ff2485fdd06503b84b0000005dc20400b84c0000005dc20400b84d0000005d"
      .. "c20400b84e0000005dc20400b84f0000005dc20400b8500000005dc20400b8530000005dc20400b856000000"
      .. "5dc20400b8630000005dc20400b84a0000005dc2040089fff2d06503a1d06503aad06503b3d06503bcd06503"
      .. "c5d06503ced06503d7d06503e0d06503e9d06503" },
    { "rating", 0x03853b42,
      "5589e55de94f4efeff" },
    { "take", 0x041293c0,
      "5589e55689ce8b4604578b7d0839c773388b0e39f9773229cfc1ff033b460875096a0189f1e8eafaffff8b4e"
      .. "0485c974378b068b14f889118b44f804894104834604085f5e5dc204003b460875096a0189f1e8bdfaffff8b"
      .. "460485c0740a8b0f89088b5704895004834604085f5e5dc20400" },
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

-- nil, or what is wrong with LEAGUE_BY_ID
local function league_by_id_fault()
    if LEAGUE_BY_ID == false then return nil end
    if type(LEAGUE_BY_ID) ~= "table" or #LEAGUE_BY_ID > LEAGUE_ROWS then
        return "LEAGUE_BY_ID is not a list of at most " .. LEAGUE_ROWS .. " entries or false"
    end
    for i, e in ipairs(LEAGUE_BY_ID) do
        local name = "LEAGUE_BY_ID: entry " .. i
        if type(e) ~= "table" or type(e[1]) ~= "number" or e[1] < 1 or e[1] > 65000
            or e[1] ~= math.floor(e[1]) then
            return name .. " does not start with the number of a league"
        end
        for k = 1, i - 1 do
            if LEAGUE_BY_ID[k][1] == e[1] then return name .. " names league " .. e[1] .. " a second time" end
        end
        if type(e[2]) == "number" then
            if e[2] < 0 or e[2] > 1000 then return name .. ": the percent is not from 0 to 1000" end
        elseif type(e[2]) == "table" and #e[2] >= 1 and #e[2] <= 22 then
            for k = 1, #e[2] do
                if type(e[2][k]) ~= "number" or e[2][k] < 0 or e[2][k] > 650 then
                    return name .. ": amount " .. k .. " is not a number from 0 to 650"
                end
            end
        else
            return name .. " has neither a percent nor a list of 1 to 22 amounts"
        end
    end
    return nil
end

-- nil, or what is wrong with TALENT and its three numbers
local function talent_fault()
    if TALENT == false then return nil end
    local fault = list_fault("TALENT", TALENT, false)
    if fault then return fault end
    for i, k in ipairs(TALENT) do
        if k[1] > 63 or k[1] ~= math.floor(k[1]) or k[2] > 254 then
            return "TALENT: entry " .. i .. " is not { age up to 63, rating up to 254 }"
        end
    end
    return number_fault("TALENT_STEP", TALENT_STEP, 0, 50, false)
        or number_fault("TALENT_MAX", TALENT_MAX, 0, 200, false)
        or number_fault("TALENT_CAP", TALENT_CAP, 0, 999, false)
end

-- nil, or what is wrong with CUP_TV and CUP_NATIONAL
local function cup_more_fault()
    if CUP_TV ~= false then
        if type(CUP_TV) ~= "table" then return "CUP_TV is not a list or false" end
        for i, r in ipairs(CUP_TV) do
            if type(r) ~= "table" or type(r[1]) ~= "number" or type(r[2]) ~= "number"
                or r[2] < 0 or r[2] > 2000 then
                return "CUP_TV: entry " .. i .. " is not { competition, millions from 0 to 2000 }"
            end
            local named = not CUP                -- CUP = false: nothing to add to
            for _, c in ipairs(CUP or {}) do
                if c[1] == r[1] then named = true end
            end
            if not named then
                return "CUP_TV: entry " .. i .. ": CUP has no amounts for competition " .. tostring(r[1])
            end
        end
    end
    if CUP_NATIONAL ~= false then
        if type(CUP_NATIONAL) ~= "table" or #CUP_NATIONAL ~= 6 then
            return "CUP_NATIONAL is not a list of 6 numbers or false"
        end
        for i = 1, 6 do
            if type(CUP_NATIONAL[i]) ~= "number" or CUP_NATIONAL[i] < 0.001 or CUP_NATIONAL[i] > 2000 then
                return "CUP_NATIONAL: entry " .. i .. " is not a number from 0.001 to 2000"
            end
        end
    end
    return nil
end

-- nil, or what is wrong with CEILING
local function ceiling_fault()
    if CEILING == false then return nil end
    if type(CEILING_RATING) ~= "boolean" then return "CEILING_RATING is not true or false" end
    if type(CEILING) ~= "table" or #CEILING ~= 10 then
        return "CEILING is not a list of 10 numbers or false"
    end
    for i = 1, 10 do
        local v = CEILING[i]
        if type(v) ~= "number" or (v ~= 0 and (v < 0.01 or v > 9999)) then
            return "CEILING: entry " .. i .. " is not 0 or a number from 0.01 to 9999"
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
        or number_fault("INCOME", INCOME, 10, 1000, true)
        or number_fault("INCOME_WAGES", INCOME_WAGES, 1, 100, true)
        or talent_fault() or league_by_id_fault() or cup_more_fault() or ceiling_fault()
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

-- The price ceiling of the computer clubs, kept apart from m.init (a Lua function can
-- name only 60 things from outside itself).
local ceiling = { on = CEILING and true or false }

-- the highest value by club level 0 to 9 (CEILING starts with the best clubs, level 9;
-- 0xffffffff: no ceiling)
function ceiling.values()
    local out = {}
    for level = 0, 9 do
        local v = CEILING[10 - level]
        out[level + 1] = (v == 0) and 0xffffffff or clamp(amount(v), 100, 99990000)
    end
    return out
end

-- the second piece of memory: the ceilings, the highest rating of the second search by
-- club level (255: none), the routine. nil: the module file is damaged
function ceiling.image()
    local parts = {}
    for _, v in ipairs(ceiling.values()) do parts[#parts + 1] = u32(v) end
    for level = 0, 9 do
        parts[#parts + 1] = string.char(CEILING_RATING and RANGE_TOP[level + 1] or 255)
    end
    local image = table.concat(parts)
    if #image ~= CEILING_ROUTINE[1] or CEILING_ROUTINE[1] + #CEILING_ROUTINE[2] / 2 > CAVE_2_SIZE then
        return nil
    end
    image = image .. unhex(CEILING_ROUTINE[2])
    return image .. string.rep("\0", CAVE_2_SIZE - #image)
end

-- is the code the routine relies on as expected, and its memory empty?
function ceiling.checks()
    local good = true
    for _, c in ipairs(CEILING_CONTEXT) do
        local got = memory.read(c[2], #c[3] / 2)
        local same = (got ~= nil and hex(got) == c[3])
        log(string.format("check: %-13s at %08x  %s", c[1], c[2], same and "as expected" or "DIFFERENT"))
        if not same then good = false end
    end
    local room = memory.read(CAVE_2, CAVE_2_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", CAVE_2_SIZE))
    log(string.format("check: %-13s at %08x  %s", "free memory 2", CAVE_2, empty and "empty" or "NOT EMPTY"))
    return good and empty
end

function ceiling.write(image)
    memory.write(CAVE_2, image)
    return memory.read(CAVE_2, CAVE_2_SIZE) == image
end

function ceiling.report()
    log("price ceiling of the computer clubs: the highest value on the screen a club signs, by its "
        .. "place in the club ranking:")
    local groups = { "1-10", "11-20", "21-50", "51-80", "81-120", "121-170", "171-220", "221-260", "261-300",
                     "others" }
    local values = ceiling.values()
    local line = " "
    for i = 1, 10 do
        local c = values[11 - i]
        line = line .. " " .. groups[i] .. ": " .. (c == 0xffffffff and "none" or commas(c * 100))
            .. (i < 10 and ";" or "")
        if i == 5 or i == 10 then
            log(line)
            line = " "
        end
    end
    log(CEILING_RATING and "  second search: no player rated above the top of the club's own rating range"
        or "  second search: from rating 99 down, as in the game")
end

function m.init(ctx)
    log("MLMoney 5: player values, salaries, budgets, income, prize money and the price ceiling of the "
        .. "computer clubs from the tables in MLMoney.lua")

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
        local tv = {}
        if CUP_TV then
            for _, r in ipairs(CUP_TV) do tv[r[1]] = r[2] end
        end
        for _, r in ipairs(CUP) do
            cup[cup_row(r[1], r[2])] = clamp(amount(r[3] + (tv[r[1]] or 0)), 10, 20000000)
        end
    end
    local national = {}
    if CUP_NATIONAL then
        for i = 1, 6 do national[i] = clamp(amount(CUP_NATIONAL[i]), 10, 20000000) end
    end
    for i = 1, 22 do league[i + 1] = LEAGUE and clamp(amount(LEAGUE[i]), 0, 20000000) or 0 end
    for i = 1, 24 do league_2[i + 1] = LEAGUE_2 and clamp(amount(LEAGUE_2[i]), 0, 20000000) or 0 end
    local share = PRIZE_TO_BUDGET and math.floor(PRIZE_TO_BUDGET + 0.5) or 0
    local bonus = BONUS and math.floor(BONUS + 0.5) or 100
    local years = YOUNG_YEARS and math.floor(YOUNG_YEARS + 0.5) or 3
    local income = INCOME and math.floor(INCOME + 0.5) or 100
    local income_wages = INCOME_WAGES and math.floor(INCOME_WAGES + 0.5) or 0
    -- talent: by age, the rating above which the bonus starts (255: no bonus at that age)
    local talent, talent_step, talent_max, talent_cap = {}, 0, 0, 0
    for i = 1, 64 do talent[i] = 255 end
    if TALENT then
        local last = TALENT[#TALENT][1]
        for i, v in ipairs(curve(TALENT, 0, 63, false)) do
            if i - 1 <= last then talent[i] = clamp(math.floor(v + 0.5), 0, 254) end
        end
        talent_step = math.floor(TALENT_STEP + 0.5)
        talent_max = math.floor(TALENT_MAX + 0.5)
        talent_cap = clamp(amount(TALENT_CAP), 0, CAP)
    end
    -- the first divisions with numbers of their own: league number, then 24 amounts in
    -- units of 100 (the first and the last are not places)
    local league_ids, league_rows = {}, {}
    if LEAGUE and LEAGUE_BY_ID then
        for _, e in ipairs(LEAGUE_BY_ID) do
            local row = { 0 }
            for i = 1, 22 do
                local a
                if type(e[2]) == "table" then
                    a = clamp(amount(e[2][math.min(i, #e[2])]), 0, 20000000)
                else
                    a = math.floor(league[i + 1] * math.floor(e[2] + 0.5) / 100)
                end
                row[i + 1] = math.min(math.floor(a / 100), 65535)
            end
            row[24] = 0
            league_ids[#league_ids + 1] = e[1]
            league_rows[#league_rows + 1] = row
        end
    end

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
        .. u32(budget_s) .. u32(100) .. u32(1000) .. "MLM5"
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
    parts = {}
    for i = 1, 64 do parts[i] = string.char(talent[i]) end
    pieces[#pieces + 1] = { TALENT_AT, table.concat(parts) }
    pieces[#pieces + 1] = { NUMBERS_2_AT, u32(talent_step) .. u32(talent_max) .. u32(talent_cap) .. u32(income) }
    parts = {}
    for i = 1, #league_ids do parts[i] = u16(league_ids[i]) end
    pieces[#pieces + 1] = { LEAGUE_IDS_AT, table.concat(parts) }
    pieces[#pieces + 1] = { LEAGUE_COUNT_AT, u32(#league_ids) .. u32(income_wages) }
    parts = {}
    for _, row in ipairs(league_rows) do
        for i = 1, 24 do parts[#parts + 1] = u16(row[i]) end
    end
    pieces[#pieces + 1] = { LEAGUE_ROWS_AT, table.concat(parts) }
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
    local image_2 = nil
    if ceiling.on then
        image_2 = ceiling.image()
        if image_2 == nil then
            log("RESULT: nothing written. The module file is damaged (ceiling routine).")
            return
        end
    end

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
    if ceiling.on and not ceiling.checks() then good = false end
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

    if ceiling.on and not ceiling.write(image_2) then
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
        ["income 1"] = INCOME or INCOME_WAGES, ["income 2"] = INCOME, ["income 3"] = INCOME,
        ["income 4"] = INCOME_WAGES, ["ceiling"] = ceiling.on,
    }
    for i = 0, 5 do on["nat " .. i] = CUP_NATIONAL end
    for _, s in ipairs(SITES) do
        if on[s[1]] then
            local at, new = s[2], unhex(s[4])
            if s[1] == "years" then new = string.sub(new, 1, 1) .. u32(years) end
            if string.sub(s[1], 1, 4) == "nat " then new = u32(national[tonumber(string.sub(s[1], 5)) + 1]) end
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
        { BONUS, "salary bonuses" }, { YOUNG_YEARS, "contract years" }, { INCOME or INCOME_WAGES, "yearly income" },
        { CUP_NATIONAL, "national cup prizes" }, { ceiling.on, "price ceiling of the computer clubs" } }) do
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
    if TALENT then
        local line = "talent bonus: " .. talent_step .. " % of the value per rating point above"
        for _, a in ipairs({ 17, 19, 21, 23 }) do
            if talent[a + 1] < 255 then line = line .. " " .. talent[a + 1] .. " at " .. a .. "," end
        end
        log(line .. " at most " .. talent_max .. " % and " .. commas(talent_cap * 100))
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
    for k, id in ipairs(league_ids) do
        log(string.format("league %d, place 1, 2, 10, 18: %s, %s, %s, %s", id, commas(league_rows[k][2] * 10000),
            commas(league_rows[k][3] * 10000), commas(league_rows[k][11] * 10000), commas(league_rows[k][19] * 10000)))
    end
    if CUP_NATIONAL then
        local line = "cups without a row of their own (national cups), winner to the round before the round of 16:"
        for i = 1, 6 do line = line .. " " .. commas(national[i] * 100) end
        log(line)
    end
    if INCOME_WAGES then
        log("yearly income of your club: the game's, plus " .. income_wages .. " % of the wage bill (a wage bill of "
            .. "150,000,000 adds " .. commas(math.floor(1500000 * income_wages / 100) * 100) .. ")")
    end
    if INCOME then
        log("yearly income of your club: " .. income .. " % of the game's (first club of the ranking: "
            .. commas(math.floor(2010000 * income / 100) * 100) .. " by place)")
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
    if ceiling.on then ceiling.report() end
    log("RESULT: installed. Changed: " .. changed .. ".")
end

return m
