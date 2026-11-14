-- MLTransfers.lua, version 1: the transfers between the computer clubs in the PES 2017
-- Master League (Sider Lua module). Made for PES2017.exe sha256 44b0caaa... and for
-- MLMoney.lua version 7, whose player values it uses.
--
-- What it changes, in the running game only (no file is touched):
--   * a computer club looks at the price: up to the ceiling of its place in the club
--     ranking it signs as before, above it less and less often, and far above it never
--     (CEILING and the settings after it; the game looks at the rating only).
-- This was part of MLMoney.lua in its versions 5 and 6 and works as it did in version 6.
--
-- It first checks that MLMoney.lua is installed, that the game holds the expected code
-- and that the memory it needs is empty. If anything differs it writes nothing and says
-- so in sider.log. MLMoney.lua is not touched by it and works with or without it.
--
-- Install: copy this file and MLMoney.lua into the "modules" folder next to sider.exe
-- and add, in this order,
--     lua.module = "MLMoney.lua"
--     lua.module = "MLTransfers.lua"
-- to sider.ini. Sider starts the modules in the order of these lines, and this one needs
-- the other to be in before it. Remove the second line to have the computer clubs choose
-- as in the game again.
--
-- It needs no new career: it works from the next time the computer clubs choose players.
--
-- Uses only: log, memory.read, memory.write, string, table, math, ipairs, tonumber, type.

local m = {}

-- ============================ settings ============================

-- false: check and report only, write nothing.
local WRITE = true

-- Price ceiling of the computer clubs. In the game a computer club has no money. It
-- chooses the players it signs by rating, age and position, never by price, and when it
-- finds nobody for a position in the rating range of its size it looks again among all
-- players, from the best down.
-- With this setting a computer club compares a player's value (the value MLMoney.lua
-- computes, before the game's random change) with the ceiling of its place in the
-- game's club ranking. Up to the ceiling it takes the player as the game does. Above it,
-- see CEILING_STRETCH and the settings after it. A player it passes over is skipped and
-- the next best is looked at. The ceilings, in the ten groups the game itself uses for
-- the rating range: millions for the clubs at place
--     1-10, 11-20, 21-50, 51-80, 81-120, 121-170, 171-220, 221-260, 261-300, all others.
-- 0.01 to 9999 each, or 0 for a group without a ceiling. false: computer clubs choose as
-- in the game.
-- Your own club is not touched: what you can buy is a matter of your budget, and offers
-- for your players go another way. No money is booked by this setting; a computer club
-- still has no account, and between two computer clubs the game has no offer and no
-- price: the setting decides only whether the player is within reach.
-- These numbers: about the value of the most valuable player of the middle club of each
-- group in the squads this module was set against, with more room for the first twenty
-- clubs (README.md has the table; ceiling_survey.py prints it for your edit file).
-- If you change VALUE in MLMoney.lua much, change these with it.
local CEILING = { 200, 100, 50, 28, 18, 12, 8, 6, 4.5, 3 }

-- How far a club goes above its ceiling, in percent of the ceiling. At the ceiling a
-- player is sure to be within reach; from there the chance falls evenly and is gone at
-- this much above it. With 50: a player 10 percent above the ceiling is within reach of
-- 4 clubs in 5 of that group, 25 percent above of every second club, 50 percent above of
-- none. Which club goes how far for which player is fixed by the two of them (no dice
-- are thrown), so the same club answers the same way while the player's value stays.
-- 0 to 300. 0: a hard ceiling, nothing above it.
local CEILING_STRETCH = 50

-- Need. The ceiling of a club is this many percent higher
--   * in its second search, when it found nobody for the position in its own rating
--     range (it then looks at the dearer players of that range again before it goes
--     further down), and
--   * when it looks for a key player, which the ten or twenty best clubs do for one
--     position on the last day of a window.
-- CEILING_STRETCH comes on top: with 30 and 50 a club in need never goes beyond 1.95
-- times its ceiling. 0 to 300. 0: need changes nothing.
local CEILING_NEED = 30

-- A seller who wants to sell. For a player his club has put on its list of players to
-- let go, this many percent of his value count against the ceiling. 0 to 100; 100: he
-- counts like any other.
local CEILING_LISTED = 70

-- The same for a player the game signs without a transfer (as far as the code was read:
-- the players without a contract). No fee is due for him, so less of his value counts.
-- 0 to 100; 100: he counts like any other.
local CEILING_FREE = 50

-- The second search. A computer club looks for a player in a rating range that goes by
-- its place in the ranking (the smallest clubs 47 to 74, the ten best 83 to 99). When it
-- finds nobody for a position there, the game lets it look again among all players,
-- from rating 99 down. It leaves out the stars of other clubs who are not for sale, but
-- not the players without a club and not those who have outgrown their club: a small
-- club can come away with one of the best of them.
-- true: in that second search a club takes nobody rated above the top of its own
-- range (74, 75, 76, 77, 78, 79, 80, 83, 86 from the smallest clubs up; the ten best
-- clubs have no limit), so it looks further down, not further up. Without this, the
-- ceiling alone still lets a small club sign a great player of 38 whose value has fallen
-- below it. false: the second search goes from 99 down as in the game.
-- CEILING_STRETCH and CEILING_NEED do not move this limit. Used only while CEILING is on.
local CEILING_RATING = true

-- ========================= end of settings =========================

local CAVE = 0x047d3c40         -- unused end of a code section: the ceilings, four numbers and the routine
local CAVE_SIZE = 0x180
local NUMBERS_AT = 0x34         -- offset of CEILING_STRETCH, 100 + CEILING_NEED, CEILING_LISTED, CEILING_FREE there
local MONEY_MARK = 0x047b065c   -- where MLMoney.lua leaves its mark, "MLM" and the number of its version
-- the highest rating of the range a computer club searches first, smallest clubs first (the game's numbers)
local RANGE_TOP = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 }
-- the routine: offset in that memory, machine code (source: money_cave.py)
local ROUTINE = { 0x44, "53575589e583ec1c8b45008b58d88b480481f9580d6603740c81f9b90d66"
      .. "030f85f70000008b48188b09894de88b50308b128b000fb6481b894df009ca8955e48b401c8b0083f8090f87"
      .. "ce0000000fb688683c7d04894dec8b0485403c7d048945fcc745f80d0000006a028d45f85053e849fe07ff83"
      .. "c40c0fb6c0837df00074093b45ec0f87a2000000837dfcff0f8488000000e873cffdff837de40074128b45fc"
      .. "f725783c7d04f73554067b048945fc0fb74b2c6953309301000131d16955e8b179379e31d169c96bcaeb85c1"
      .. "e9180faf0d743c7d048b45fcf7e1b900640000f7f10145fc8b8bb400000083e10f4983f901b9803c7d047611"
      .. "f783b8000000000000607411b97c3c7d0489f8f721f73554067b0489c73b7dfc771089ec5d5f5b588b4d2456"
      .. "50e9105695ff89ec5d5f5b83c404e96bbde8fe" }

-- The place that is changed: name, address, bytes there now, bytes to write.
local SITE = { "ceiling", 0x0365fb0d, "8b4d2456e8aa98ac00", "e87241170190909090" }

-- What MLMoney.lua must have put into its memory: name, address, bytes.
local MONEY = {
    { "value routine", 0x047b0c90,
      "83f8637605b86300000089c78b048500027b048b4b1cc1e90783e13f0fb69180067b0429d77f0231ff0faf3d"
      .. "800d7b043b3d840d7b0476068b3d840d7b040fb70c4d20057b04f7e1f73554067b0450f7e7f73554067b043b"
      .. "05880d7b047605a1880d7b045901c88b4b04c1e91c0fb70c4d20067b04f7e1f73554067b040fb74b2c695330"
      .. "9301000131d169c9b179379ec1e9180faf0d48067b04c1e908030d44067b04f7e1f73558067b043d9ce0f505"
      .. "7605b89ce0f50589c78b8bb4000000c1e90b81e1ff0f00000faf0d40067b04f7e1b9a0860100f7f101c7c745"
      .. "f400000000c3" },
    { "number 100", 0x047b0654,
      "64000000" },
}

-- The code of the game the place and the routine rely on: name, address, bytes.
local CONTEXT = {
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

-- millions on the screen -> the game's stored amount (the screen shows 100 times it),
-- rounded to 10
local function amount(millions)
    return math.floor(millions * 1000 + 0.5) * 10
end

-- nil, or what is wrong with the settings
local function settings_fault()
    if type(WRITE) ~= "boolean" then return "WRITE is not true or false" end
    if CEILING == false then return nil end
    if type(CEILING_RATING) ~= "boolean" then return "CEILING_RATING is not true or false" end
    for _, c in ipairs({ { CEILING_STRETCH, "CEILING_STRETCH", 300 }, { CEILING_NEED, "CEILING_NEED", 300 },
                         { CEILING_LISTED, "CEILING_LISTED", 100 }, { CEILING_FREE, "CEILING_FREE", 100 } }) do
        if type(c[1]) ~= "number" or c[1] < 0 or c[1] > c[3] then
            return c[2] .. " is not a number from 0 to " .. c[3]
        end
    end
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

-- the highest value by club level 0 to 9 (CEILING starts with the best clubs, level 9;
-- 0xffffffff: no ceiling)
local function values()
    local out = {}
    for level = 0, 9 do
        local v = CEILING[10 - level]
        out[level + 1] = (v == 0) and 0xffffffff or clamp(amount(v), 100, 99990000)
    end
    return out
end

-- what goes into the memory: the ceilings, the highest rating of the second search by
-- club level (255: none), the four numbers of the limit, the routine. nil: the module
-- file is damaged
local function image()
    local parts = {}
    for _, v in ipairs(values()) do parts[#parts + 1] = u32(v) end
    for level = 0, 9 do
        parts[#parts + 1] = string.char(CEILING_RATING and RANGE_TOP[level + 1] or 255)
    end
    local out = table.concat(parts)
    out = out .. string.rep("\0", NUMBERS_AT - #out) .. u32(math.floor(CEILING_STRETCH + 0.5))
        .. u32(100 + math.floor(CEILING_NEED + 0.5)) .. u32(math.floor(CEILING_LISTED + 0.5))
        .. u32(math.floor(CEILING_FREE + 0.5))
    if #out ~= ROUTINE[1] or ROUTINE[1] + #ROUTINE[2] / 2 > CAVE_SIZE then
        return nil
    end
    out = out .. unhex(ROUTINE[2])
    return out .. string.rep("\0", CAVE_SIZE - #out)
end

-- one line of the log for a piece of memory that is compared: -> is it as expected?
local function same(name, at, expected)
    local got = memory.read(at, #expected / 2)
    local good = (got ~= nil and hex(got) == expected)
    log(string.format("check: %-13s at %08x  %s", name, at, good and "as expected" or "DIFFERENT"))
    return good
end

local function report()
    log("price ceiling of the computer clubs: the value on the screen up to which a club signs for sure, by its "
        .. "place in the club ranking:")
    local groups = { "1-10", "11-20", "21-50", "51-80", "81-120", "121-170", "171-220", "221-260", "261-300",
                     "others" }
    local amounts = values()
    local line = " "
    for i = 1, 10 do
        local c = amounts[11 - i]
        line = line .. " " .. groups[i] .. ": " .. (c == 0xffffffff and "none" or commas(c * 100))
            .. (i < 10 and ";" or "")
        if i == 5 or i == 10 then
            log(line)
            line = " "
        end
    end
    log(string.format("  above the ceiling: the chance falls to none at %d percent above it; a club in need "
        .. "counts its ceiling %d percent higher; a listed player counts at %d percent of his value, a player "
        .. "without a contract at %d percent", math.floor(CEILING_STRETCH + 0.5), math.floor(CEILING_NEED + 0.5),
        math.floor(CEILING_LISTED + 0.5), math.floor(CEILING_FREE + 0.5)))
    log(CEILING_RATING and "  second search: no player rated above the top of the club's own rating range"
        or "  second search: from rating 99 down, as in the game")
end

function m.init(ctx)
    log("MLTransfers 1: the price ceiling of the computer clubs from the settings in MLTransfers.lua")

    local fault = settings_fault()
    if fault then
        log("RESULT: nothing written. Settings: " .. fault)
        return
    end
    if CEILING == false then
        log("RESULT: nothing written. CEILING = false: the computer clubs choose as in the game.")
        return
    end
    local memory_image = image()
    if memory_image == nil then
        log("RESULT: nothing written. The module file is damaged (routine).")
        return
    end

    -- 1. is MLMoney.lua in, with the value routine this module calls?
    local mark = memory.read(MONEY_MARK, 4)
    local found = (mark ~= nil and string.sub(mark, 1, 3) == "MLM")
    log(string.format("check: %-13s at %08x  %s", "MLMoney.lua", MONEY_MARK,
        found and ("installed, version " .. string.sub(mark, 4, 4)) or "NOT FOUND"))
    local money = found
    if found then
        for _, c in ipairs(MONEY) do
            if not same(c[1], c[2], c[3]) then money = false end
        end
    end

    -- 2. is this the game the module was made for?
    local good = true
    for _, c in ipairs(CONTEXT) do
        if not same(c[1], c[2], c[3]) then good = false end
    end
    local room = memory.read(CAVE, CAVE_SIZE)
    local empty = (room ~= nil and room == string.rep("\0", CAVE_SIZE))
    log(string.format("check: %-13s at %08x  %s", "free memory", CAVE, empty and "empty" or "NOT EMPTY"))
    if not found then
        log("RESULT: nothing written. MLMoney.lua is not installed, and this module needs its player values. "
            .. "In sider.ini the line for MLMoney.lua must stand above the line for MLTransfers.lua, and "
            .. "the RESULT line of MLMoney.lua must say \"installed\".")
        return
    end
    if not money then
        log("RESULT: nothing written. The MLMoney.lua that is installed is not the version this module was "
            .. "made for. Use the two files that came together.")
        return
    end
    local there = memory.read(SITE[2], #SITE[4] / 2)
    if there ~= nil and hex(there) == SITE[4] then
        log("RESULT: nothing written. The price ceiling is in the game already: by an MLMoney.lua of "
            .. "version 6 with CEILING on (replace it with version 7), or this module stands twice in sider.ini.")
        return
    end
    if not (good and empty) then
        log("RESULT: nothing written. This game does not hold what the module expects; "
            .. "send this log.")
        return
    end
    if not WRITE then
        log("RESULT: nothing written (WRITE = false). All checks passed.")
        return
    end

    -- 3. the table and the routine first; nothing in the game points to them yet
    memory.write(CAVE, memory_image)
    if memory.read(CAVE, CAVE_SIZE) ~= memory_image then
        log("RESULT: the table could not be written; the game's code is unchanged. "
            .. "Send this log.")
        return
    end

    -- 4. the place in the game's code
    local new = unhex(SITE[4])
    memory.write(SITE[2], new)
    local stuck = (memory.read(SITE[2], #new) == new)
    log(string.format("written: %-8s at %08x  %s", SITE[1], SITE[2], stuck and "ok" or "FAILED"))
    if not stuck then
        log("RESULT: a change did not go in. Quit the game, remove the module, send this log.")
        return
    end

    report()
    log("RESULT: installed. Changed: price ceiling of the computer clubs.")
end

return m
