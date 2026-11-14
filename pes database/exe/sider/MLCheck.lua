-- MLCheck.lua: read-only test for PES 2017 Master League tuning (Sider Lua module).
--
-- It READS a few bytes of the running game and writes what it finds to sider.log.
-- It writes nothing to the game. Its purpose: show that the addresses in
-- MASTER_LEAGUE.md are the addresses in your running game, before any module
-- that changes numbers is tried.
--
-- Install: copy this file into the "modules" folder next to sider.exe and add
--     lua.module = "MLCheck.lua"
-- to sider.ini. Start the game with Sider, wait for the title screen, quit, and
-- look for the lines with "MLCheck" in sider.log.
--
-- Uses only: log, memory.read, string, table, ipairs, tostring.

local m = {}

local function byte_at(s, i) return string.byte(s, i) end

local function hex(s)
    local t = {}
    for i = 1, #s do t[i] = string.format("%02x", byte_at(s, i)) end
    return table.concat(t)
end

local function u32(s, i)
    return byte_at(s, i) + byte_at(s, i + 1) * 256 + byte_at(s, i + 2) * 65536
        + byte_at(s, i + 3) * 16777216
end

-- The two functions that give the overall window of a computer club by its level
-- (MASTER_LEAGUE.md section 9.4). Each is 112 bytes of code followed by a table of
-- ten jump targets, one per level. Every target must point back into the function
-- and hold "mov eax, <overall>" (b8 xx 00 00 00).
local LEVEL = {
    { name = "lowest overall ", code = 0x0365d12d, jumps = 0x0365d19d,
      want = { 47, 51, 55, 59, 63, 67, 70, 73, 76, 83 } },
    { name = "highest overall", code = 0x0365d08d, jumps = 0x0365d0fd,
      want = { 74, 75, 76, 77, 78, 79, 80, 83, 86, 99 } },
}
local LEVEL_CODE = "5589e58b45088b0083f8097758ff2485"   -- first 16 bytes of both
local LEVEL_SIZE = 112

-- Numbers of the transfer fee formula (section 6.2): address, bytes, meaning.
local FEE = {
    { 0x038ab8db, "83f844",           "rating step 68" },
    { 0x038ab8e6, "69ff28230000",     "9,000 per rating point" },
    { 0x0216ba48, "00000020d9b1313f", "factor 0.00027" },
    { 0x01f0f2b8, "000000a099990140", "factor 2.2" },
}

local function level_row(row)
    -- returns the ten values as text, and true if they are the expected ones
    local head = memory.read(row.code, 16)
    if hex(head) ~= LEVEL_CODE then
        return "code differs: " .. hex(head), false
    end
    local jumps = memory.read(row.jumps, 40)
    local out, same = {}, true
    for level = 0, 9 do
        local target = u32(jumps, level * 4 + 1)
        if target < row.code or target > row.code + LEVEL_SIZE - 5 then
            -- not a target inside the function: do not read there
            out[#out + 1] = "??"
            same = false
        else
            local ins = memory.read(target, 5)
            if byte_at(ins, 1) ~= 0xb8 or u32(ins, 2) > 255 then
                out[#out + 1] = "??"
                same = false
            else
                local v = byte_at(ins, 2)
                out[#out + 1] = string.format("%2d", v)
                if v ~= row.want[level + 1] then same = false end
            end
        end
    end
    return table.concat(out, " "), same
end

function m.init(ctx)
    log("MLCheck 1: read-only test, nothing is written to the game")
    local total, good = 0, 0
    local function verdict(same)
        total = total + 1
        if same then good = good + 1 end
        return same and "as expected" or "DIFFERENT"
    end

    log("club level       0  1  2  3  4  5  6  7  8  9")
    for _, row in ipairs(LEVEL) do
        local text, same = level_row(row)
        log(row.name .. " " .. text .. "   " .. verdict(same))
    end
    for _, item in ipairs(FEE) do
        local got = hex(memory.read(item[1], #item[2] / 2))
        local same = (got == item[2])
        log(string.format("fee: %-26s at %08x = %s   %s", item[3], item[1], got, verdict(same)))
    end

    if good == total then
        log("RESULT: " .. good .. " of " .. total .. " as expected. The running game has the code "
            .. "the notes describe, at the same addresses.")
    else
        log("RESULT: only " .. good .. " of " .. total .. " as expected. Do not use tuning modules "
            .. "made for this exe; send this log.")
    end
end

return m
