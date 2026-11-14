-- MLMoney.lua: real-world player values and salaries in the PES 2017 Master League
-- (Sider Lua module). Made for PES2017.exe sha256 44b0caaa...; MLCheck.lua must have
-- said "6 of 6 as expected" on your game before you use this one.
--
-- What it changes, in the running game only (no file is touched):
--   * the value of a player (the transfer fee the game computes) becomes
--         VALUE[rating] x AGE[age] x (1 + popularity bonus)
--     instead of  salary x 2.2..3.3 + 9,000 x (rating - 68);
--   * the rating part of the yearly salary comes from SALARY[rating]; the club's place
--     in the ranking, the role bonuses, the popularity part and the award bonuses stay
--     the game's own.
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

-- Value of a player at the age where AGE says 100, by rating: { rating, millions }.
-- Between two entries the value grows by the same percentage per rating point.
local VALUE = {
    { 50, 0.05 }, { 60, 0.3 }, { 65, 0.8 }, { 70, 2.5 }, { 75, 8 }, { 80, 25 },
    { 85, 65 }, { 88, 110 }, { 90, 150 }, { 92, 185 }, { 94, 215 }, { 99, 260 },
}

-- Percent of that value by age: { age, percent }. Straight lines between the entries.
local AGE = {
    { 15, 130 }, { 19, 130 }, { 25, 100 }, { 26, 100 }, { 27, 97 }, { 28, 90 },
    { 29, 80 }, { 30, 65 }, { 31, 50 }, { 32, 36 }, { 33, 26 }, { 34, 18 },
    { 35, 12 }, { 36, 8 }, { 37, 6 }, { 38, 5 },
}

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

-- ========================= end of settings =========================

local CAP = 99999900            -- the game's largest amount (9,999,990,000 on the screen)
local CAVE = 0x047b0200         -- unused end of the code section: tables and two routines
local CAVE_SIZE = 0x460
local FEE_CODE_AT, SALARY_CODE_AT = 0x3c0, 0x430      -- offsets inside it
local FEE_CODE = "83f8637605b8630000008b3c8500027b048b4b1cc1e90783e13f0fb70c4d20057b0489f8f7e1"
    .. "b964000000f7f13d9ce0f5057605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0da0057b04"
    .. "f7e1b9a0860100f7f101c7c745f400000000c3"
local SALARY_CODE = "83f8637605b8630000008b0c8590037b04894dc8c745cc00000000c3"

-- The places that are changed: address, bytes there now, bytes to write.
local FEE_SITE = { 0x038ab8db, "83f844760c8db8bcffffff69ff28230000", "e8e04cf000909090909090909090909090" }
local SALARY_SITE = { 0x038ac875, "89c1c1e10429c1", "e8b63df000eb5b" }

-- The code around those places, which the two routines rely on: name, address, bytes.
local CONTEXT = {
    { "fee code", 0x038ab89e,
      "db85f8ffffff576a02dc0d48ba16028d95f8ffffff5253dc05b8f2f00189451831ffc785f8ffffff0d000000"
      .. "d99df4ffffffe86d82faff0fb6c083c40c83f844760c8db8bcffffff69ff282300008b4518db451885c0"
      .. "7906d805b46dee01d88df4ffffffe85bb303008b4d108d34078b0189b5f8ffffff5f" },
    { "salary code", 0x038ac86f,
      "83c40c0fb6c089c1c1e10429c18d94090cfeffff31c98995c8ffffff898dccffffff83f84272128d88bfffff"
      .. "ff69c92c010000898dccffffff83f84c72148d90b5ffffff69d2f401000001d1898dccffffff83f85672"
      .. "1183c0ab69c0bc02000001c1898dccffffff8b83b4000000" },
    { "salary sum", 0x038aca2b,
      "03b5b0ffffff03b5ccffffff03b5c8ffffff89b5a4ffffffdb85a4ffffff7906d805b46dee01d88db8ffffff"
      .. "e806a20300" },
}

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
    log("MLMoney 1: player values and salaries from the tables in MLMoney.lua")

    local fault = list_fault("VALUE", VALUE, true) or list_fault("AGE", AGE, false)
    if not fault and SALARY then fault = list_fault("SALARY", SALARY, true) end
    if not fault and (type(FAME) ~= "number" or FAME < 0 or FAME > 100) then
        fault = "FAME is not a number from 0 to 100"
    end
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end

    -- the tables as the game will read them
    local value, age, salary = {}, {}, {}
    for i, v in ipairs(curve(VALUE, 0, 99, true)) do value[i] = clamp(amount(v), 1, CAP) end
    for i, v in ipairs(curve(AGE, 0, 63, false)) do age[i] = clamp(math.floor(v + 0.5), 0, 1000) end
    if SALARY then
        for i, v in ipairs(curve(SALARY, 0, 99, true)) do
            salary[i] = clamp(amount(v / 2), 1, 40000000)
        end
    else
        for i = 1, 100 do salary[i] = 0 end
    end
    local fame = math.floor(FAME + 0.5)

    local parts = {}
    for i = 1, 100 do parts[#parts + 1] = u32(value[i]) end
    for i = 1, 100 do parts[#parts + 1] = u32(salary[i]) end
    for i = 1, 64 do parts[#parts + 1] = u16(age[i]) end
    parts[#parts + 1] = u32(fame)
    parts[#parts + 1] = "MLM1"
    local image = table.concat(parts)
    image = image .. string.rep("\0", FEE_CODE_AT - #image) .. unhex(FEE_CODE)
    image = image .. string.rep("\0", SALARY_CODE_AT - #image) .. unhex(SALARY_CODE)
    image = image .. string.rep("\0", CAVE_SIZE - #image)

    -- 1. is this the game the module was made for?
    local good = true
    for _, c in ipairs(CONTEXT) do
        local got = memory.read(c[2], #c[3] / 2)
        local same = (got ~= nil and hex(got) == c[3])
        log(string.format("check: %-12s at %08x  %s", c[1], c[2], same and "as expected" or "DIFFERENT"))
        if not same then good = false end
    end
    local room = memory.read(CAVE, CAVE_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", CAVE_SIZE))
    log(string.format("check: %-12s at %08x  %s", "free memory", CAVE, empty and "empty" or "NOT EMPTY"))
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

    -- 3. the two places in the game's code
    local sites = { { "fee", FEE_SITE } }
    if SALARY then sites[2] = { "salary", SALARY_SITE } end
    for _, s in ipairs(sites) do
        local at, new = s[2][1], unhex(s[2][3])
        memory.write(at, new)
        local same = (memory.read(at, #new) == new)
        log(string.format("written: %-6s at %08x  %s", s[1], at, same and "ok" or "FAILED"))
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
    log("value on the screen, without the popularity bonus (" .. fame .. " % per 1,000 points):")
    log("  rating          age 20          age 25          age 30          age 33")
    for _, rating in ipairs({ 65, 70, 75, 80, 85, 88, 90, 92, 94 }) do
        log(string.format("  %6d %15s %15s %15s %15s", rating, shown(rating, 20), shown(rating, 25),
            shown(rating, 30), shown(rating, 33)))
    end
    if SALARY then
        log("rating part of the yearly salary on the screen: first club of the ranking / club "
            .. "outside the first 250")
        for _, rating in ipairs({ 65, 70, 75, 80, 85, 88, 90, 92, 94 }) do
            log(string.format("  %6d %15s %15s", rating, commas(salary[rating + 1] * 200),
                commas(salary[rating + 1] * 100)))
        end
        log("RESULT: installed. Values and salaries come from the tables.")
    else
        log("RESULT: installed. Values come from the tables; salaries are the game's own.")
    end
end

return m
