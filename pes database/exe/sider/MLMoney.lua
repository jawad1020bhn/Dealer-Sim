-- MLMoney.lua: real-world player values, salaries and budgets in the PES 2017 Master
-- League (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...; MLCheck.lua must
-- have said "6 of 6 as expected" on your game before you use this one.
--
-- What it changes, in the running game only (no file is touched):
--   * the value of a player (the transfer fee the game computes) becomes
--         VALUE[rating] x AGE[age] x POSITION[position] x spread x (1 + popularity bonus)
--     instead of  salary x 2.2..3.3 + 9,000 x (rating - 68);
--   * the rating part of the yearly salary becomes SALARY[rating] x SALARY_AGE[age]; the
--     club's place in the ranking, the role bonuses, the popularity part and the award
--     bonuses stay the game's own;
--   * the transfer budget your club gets when a career starts becomes BUDGET_TRANSFER
--     times the mean value of its 16 best players (the game: 2 times).
-- The tables are the settings below. Amounts are what the screens show.
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
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tostring, type.

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
-- { rating, millions }. A club outside the first 250 pays half of it, the clubs between
-- pay in proportion. false: leave the game's salary formula alone.
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

-- ========================= end of settings =========================

local CAP = 99999900            -- the game's largest amount (9,999,990,000 on the screen)
local CAVE = 0x047b0200         -- unused end of the code section: tables and four routines
local CAVE_SIZE = 0x5c0
local NUMBERS_AT = 0x440         -- offset of the single numbers in that memory
-- the routines: offset in that memory, machine code (source: money_cave.py)
local ROUTINES = {
    { 0x480, "83f8637605b8630000008b048500027b048b4b1cc1e90783e13f0fb70c4d20057b04f7e1f7355406"
      .. "7b048b4b04c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c6953309301000131d169c9b179379ec1"
      .. "e9180faf0d48067b04c1e908030d44067b04f7e1f73558067b043d9ce0f5057605b89ce0f50589c78b8bb400"
      .. "0000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745f400000000c3" },
    { 0x540, "83f8637605b8630000008b048590037b048b4b1cc1e90783e13f0fb70c4da0057b04f7e1f7355406"
      .. "7b048945c8c745cc00000000c3" },
    { 0x580, "8b4030505289f0f7254c067b04f73554067b0489c65a5885f6c3" },
    { 0x5a0, "52f72550067b04f73554067b045a8d3401e92fb906ff" },
}

-- The places that are changed: name, address, bytes there now, bytes to write.
local FEE_SITE = { "fee", 0x038ab8db, "83f844760c8db8bcffffff69ff28230000", "e8a04df000909090909090909090909090" }
local SALARY_SITE = { "salary", 0x038ac875, "89c1c1e10429c1", "e8c63ef000eb5b" }
local BUDGET_T_SITE = { "budget 1", 0x038adc47, "01f68b4030", "e8342bf000" }
local BUDGET_S_SITE = { "budget 2", 0x038add08, "8d3441e8d5e3f6ff", "e8932af000909090" }

-- The code those places and the routines rely on: name, address, bytes.
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
    { "salary sum", 0x038aca2b,
      "03b5b0ffffff03b5ccffffff03b5c8ffffff89b5a4ffffffdb85a4ffffff7906d805b46dee01d88db8ffffff"
      .. "e806a20300" },
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

local function settings_fault()
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
    log("MLMoney 2: player values, salaries and budgets from the tables in MLMoney.lua")

    local fault = settings_fault()
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end

    -- the tables as the game will read them
    local value, age, salary, salary_age, position = {}, {}, {}, {}, {}
    for i, v in ipairs(curve(VALUE, 0, 99, true)) do value[i] = clamp(amount(v), 1, CAP) end
    for i, v in ipairs(curve(AGE, 0, 63, false)) do age[i] = clamp(math.floor(v + 0.5), 0, 300) end
    if SALARY then
        for i, v in ipairs(curve(SALARY, 0, 99, true)) do
            salary[i] = clamp(amount(v / 2), 1, 40000000)
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
        .. u32(budget_s) .. u32(100) .. u32(1000) .. "MLM2"
    for _, r in ipairs(ROUTINES) do
        image = image .. string.rep("\0", r[1] - #image) .. unhex(r[2])
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
    local sites, changed = { FEE_SITE }, "values"
    if SALARY then
        sites[#sites + 1] = SALARY_SITE
        changed = changed .. ", salaries"
    end
    if BUDGET_TRANSFER then
        sites[#sites + 1] = BUDGET_T_SITE
        changed = changed .. ", transfer budget"
    end
    if BUDGET_SALARY then
        sites[#sites + 1] = BUDGET_S_SITE
        changed = changed .. ", salary budget"
    end
    for _, s in ipairs(sites) do
        local at, new = s[2], unhex(s[4])
        memory.write(at, new)
        local same = (memory.read(at, #new) == new)
        log(string.format("written: %-8s at %08x  %s", s[1], at, same and "ok" or "FAILED"))
        if not same then
            log("RESULT: a change did not go in. Quit the game, remove the module, send this log.")
            return
        end
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
            log(string.format("  %6d %15s %15s", rating, commas(salary[rating + 1] * 200),
                commas(salary[rating + 1] * 100)))
        end
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
