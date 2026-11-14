#!/usr/bin/env bash
# REA (https://github.com/morluto/rea) ready to analyse PES2017.exe inside the Arena sandbox.
#
#   bash rea-setup.sh        about 15 minutes the first time in a session, seconds after that
#
# What it does:
#   1. npm ci                 REA 6.9.0 + Node 24.22.3 into ./node_modules (package-lock.json)
#   2. extracts pes.7z.001-005 to $WORK/game (PES2017.exe, sider)
#   3. builds Rizin 0.9.1 and its Ghidra decompiler plugin (rz-ghidra 0.9.0) into $WORK/rz
#   4. self-check: REA decompiles one function of PES2017.exe through Rizin
#
# Why a build: the sandbox reaches github.com (git), npm and PyPI only. Ghidra, Hopper and
# every JDK are release downloads on other hosts, so REA's own native engines cannot be
# installed here. Rizin is the engine REA drives with `rea execute-rizin-command`, and it
# builds from git. $WORK is outside the repository and is lost between sessions: run again.
set -euo pipefail

REPO=$(cd "$(dirname "$0")" && pwd)
WORK=${REA_WORK:-$HOME/pes-work}
SRC=$WORK/build
RZ=$WORK/rz
GAME=$WORK/game
EXE=$GAME/PES2017.exe
EXE_SHA256=44b0caaac6703459f1a674ab7defc98d39613008b9254646f2543431fa9d954f
export PATH=/usr/local/bin:$HOME/.local/bin:$PATH
mkdir -p "$SRC" "$GAME"

clone() { # clone <tag> <url> <dir> [extra git options]
  local tag=$1 url=$2 dir=$3; shift 3
  [ -d "$dir/.git" ] || git -c advice.detachedHead=false clone -q --depth 1 -b "$tag" "$@" "$url" "$dir"
}

echo "== 1/4 REA"
[ -x "$REPO/node_modules/.bin/rea" ] || (cd "$REPO" && npm ci --no-audit --no-fund 2>&1 | grep -v EBADENGINE | tail -2)

echo "== 2/4 game files"
if [ ! -f "$EXE" ]; then
  python3 -c 'import py7zz' 2>/dev/null || pip install -q --break-system-packages py7zz
  python3 -c 'import sys, py7zz; py7zz.SevenZipFile(sys.argv[1]).extractall(sys.argv[2])' "$REPO/pes.7z.001" "$GAME"
fi
echo "$EXE_SHA256  $EXE" | sha256sum -c --quiet

echo "== 3/4 Rizin + decompiler plugin"
if [ ! -x "$RZ/bin/rizin" ]; then
  command -v meson >/dev/null && command -v ninja >/dev/null && command -v cmake >/dev/null \
    || pip install -q --break-system-packages meson ninja cmake
  clone v0.9.1 https://github.com/rizinorg/rizin "$SRC/rizin"
  cd "$SRC/rizin"
  # subprojects that come from git or a github.com source archive
  meson subprojects download blake2 blake3 capstone-next libdemangle libmspack lz4 \
    rizin-grammar-c sigdb softfloat tree-sitter >/dev/null 2>&1
  # subprojects whose archive is a release download (blocked): the same tags from git,
  # plus the meson files Rizin keeps for them in subprojects/packagefiles
  cd subprojects
  clone v1.3.2      https://github.com/madler/zlib          zlib-1.3.2
  clone v5.8.3      https://github.com/tukaani-project/xz   xz-5.8.3
  clone v1.11.4     https://github.com/nih-at/libzip        libzip-1.11.4
  clone pcre2-10.47 https://github.com/PCRE2Project/pcre2   pcre2-10.47 --recurse-submodules --shallow-submodules
  clone v1.5.7      https://github.com/facebook/zstd        zstd-1.5.7
  mkdir -p zydis
  for p in zlib-1.3.2:zlib-1.3.2 xz-5.8.3:xz-5.8.3 libzip-1.11.4:libzip-1.11.4 \
           pcre2:pcre2-10.47 zstd-1.5.7:zstd-1.5.7 zydis:zydis; do
    cp -r "packagefiles/${p%%:*}/." "${p##*:}/"
  done
  cd ..
  [ -f build/build.ninja ] || meson setup build --prefix="$RZ" --buildtype=release \
    --wrap-mode=nodownload -Denable_tests=false -Denable_rz_test=false >"$SRC/rizin-setup.log"
  ninja -C build install >"$SRC/rizin-build.log" 2>&1 || { tail -20 "$SRC/rizin-build.log"; exit 1; }
fi
if ! ls "$RZ"/lib/*/rizin/plugins/core_ghidra.so >/dev/null 2>&1; then
  # the plugin needs zlib headers and a static libz: none in the sandbox
  clone v1.3.2 https://github.com/madler/zlib "$SRC/zlib"
  (cd "$SRC/zlib" && CFLAGS=-fPIC ./configure --static --prefix="$SRC/zprefix" >/dev/null \
    && make -j"$(nproc)" >/dev/null 2>&1 && make install >/dev/null)
  clone v0.9.0 https://github.com/rizinorg/rz-ghidra "$SRC/rz-ghidra" --recurse-submodules --shallow-submodules
  cmake -S "$SRC/rz-ghidra" -B "$SRC/rz-ghidra/build" -Wno-author -DCMAKE_BUILD_TYPE=Release \
    -DCMAKE_PREFIX_PATH="$RZ;$SRC/zprefix" -DCMAKE_INSTALL_PREFIX="$RZ" >"$SRC/rz-ghidra-setup.log"
  { cmake --build "$SRC/rz-ghidra/build" -j"$(nproc)" && cmake --install "$SRC/rz-ghidra/build"; } \
    >"$SRC/rz-ghidra-build.log" 2>&1 || { tail -20 "$SRC/rz-ghidra-build.log"; exit 1; }
fi

echo "== 4/4 self-check"
export REA_RIZIN_COMMAND=$RZ/bin/rizin
# 0x039105a0 is the second routine the entry point of PES2017.exe calls
out=$(cd "$REPO" && npx rea execute-rizin-command "$EXE" 'af @ 0x39105a0; pdg @ 0x39105a0' --format json)
echo "$out" | grep -q '"exit_code": *0' || { echo "self-check failed: Rizin did not exit 0"; exit 1; }
echo "$out" | grep -q 'void fcn.039105a0' || { echo "self-check failed: no decompiled function"; exit 1; }
echo "self-check passed: REA -> Rizin -> decompiler works on PES2017.exe"
cat <<E

Use it (from $REPO):
  export REA_RIZIN_COMMAND=$RZ/bin/rizin
  npx rea execute-rizin-command $EXE '<rizin command>'
    ie                          entry point          iS    sections        ii    imports
    pd 40 @ 0x38e6c30           disassemble          /z cmnPlayer.bin      find a string
    af @ ADDR; pdg @ ADDR       decompile the function at ADDR to C
E
