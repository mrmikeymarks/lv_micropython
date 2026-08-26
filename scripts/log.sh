#!/usr/bin/env bash

# Serial monitor for ESP32 boards — bash entry point, runnable from anywhere.
#
# Usage:
#   monitor.sh [--reset] [--timestamps] [PORT] [BAUD]
#
#   --reset       hard-reset the board on attach to capture the full boot log
#   --timestamps  prefix each output line with a timestamp
#   PORT          defaults to auto-detecting the first USB-serial device
#   BAUD          defaults to 115200
#
# Attaches without resetting the board, and reconnects automatically when the
# board is unplugged/replugged. Ctrl-C exits. Delegates to monitor-serial.py
# using a python that has pyserial (the ESP-IDF env one when available).

set -euo pipefail

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

PY="${IDF_PYTHON_ENV_PATH:-/Volumes/1TB_DAVINCI/.espressif/python_env/idf5.2_py3.12_env}/bin/python"
if [ ! -x "$PY" ]; then
    PY="$(command -v python3)"
fi

exec "$PY" "$SCRIPTS_DIR/monitor-serial.py" "$@"
