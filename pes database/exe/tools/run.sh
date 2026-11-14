#!/usr/bin/env bash
# The whole pipeline, from the exe to ../output. First: bash ../../../rea-setup.sh
# About 50 minutes on 2 cores; decompile.py continues where it stopped.
set -euo pipefail
T=$(cd "$(dirname "$0")" && pwd)
WORK=${REA_WORK:-$HOME/pes-work}
EXE=$WORK/game/PES2017.exe
W=$WORK/out
python3 "$T/inventory.py" "$EXE" "$W/inv"
python3 "$T/find_functions.py" "$EXE" "$W/inv/functions_found.tsv" "$W/inv/exports.tsv"
python3 "$T/decompile.py" "$EXE" "$W/inv/functions_found.tsv" "$W/dec" 2 1000
python3 "$T/assemble.py" "$W/dec" "$W/inv/functions_found.tsv" "$W/inv" "$T/../output"
python3 "$T/check.py" "$EXE"
