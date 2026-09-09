#!/usr/bin/env bash

# Dev loop: push code to the board and watch it run — one command, one port.
# Copies a Python file to the board as main.py, then attaches the serial
# monitor with a reset so you watch it boot and run live. Ctrl-C detaches.
#
# Usage:
#   dev.sh                 attach monitor with reset (no code change)
#   dev.sh app.py          push app.py as main.py, reset, watch it run
#   dev.sh app.py PORT     same, explicit port
#
# A serial port has exactly one reader, so this script takes the port:
# any monitor already attached is stopped first.
#
# Related:
#   mpremote repl          interactive REPL (output + typing), Ctrl-X exits
#   mpremote run app.py    run a file once WITHOUT saving it to the board
#   deploy-fast.sh         reflash firmware (C/frozen-module changes)

set -euo pipefail

FILE="${1:-}"
PORT="${2:-}"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"

if [ -z "$PORT" ]; then
    PORT="$(ls /dev/cu.usbserial* 2>/dev/null | head -1 || true)"
    [ -n "$PORT" ] || { echo "ERROR: no /dev/cu.usbserial* device found." >&2; exit 1; }
fi

PY="${IDF_PYTHON_ENV_PATH:-/Volumes/1TB_DAVINCI/.espressif/python_env/idf5.2_py3.12_env}/bin/python"

# take the port: stop any monitor already attached
HOLDERS="$(lsof -t "$PORT" 2>/dev/null || true)"
if [ -n "$HOLDERS" ]; then
    echo "freeing $PORT (stopping pid(s): $HOLDERS)"
    kill -INT $HOLDERS 2>/dev/null || true
    sleep 1
fi

if [ -n "$FILE" ]; then
    [ -f "$FILE" ] || { echo "ERROR: $FILE not found." >&2; exit 1; }
    echo "=== pushing $FILE -> :main.py ==="
    "$PY" "$MICROPYTHON/tools/mpremote/mpremote.py" connect "$PORT" cp "$FILE" :main.py
fi

echo "=== attaching monitor (reset -> boot -> your code runs; Ctrl-C to detach) ==="
exec "$PY" "$SCRIPTS_DIR/monitor-serial.py" --reset "$PORT"
