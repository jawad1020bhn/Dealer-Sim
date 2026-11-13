#!/bin/sh
# Rizin with a memory ceiling: one function of PES2017.exe makes the analysis grow without end.
ulimit -v 1400000
exec "${RIZIN:-$HOME/pes-work/rz/bin/rizin}" "$@"
