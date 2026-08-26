#!/usr/bin/env bash

# One-shot pipeline: build lv_micropython for ESP32, flash it, install the
# LVGL display drivers + hello-world main.py, and verify the board boots.
#
# Usage:
#   run-esp32-all.sh [BOARD] [BOARD_VARIANT] [PORT] [BAUD]
#
#   BOARD          defaults to ESP32_GENERIC
#   BOARD_VARIANT  defaults to none (e.g. SPIRAM)
#   PORT           defaults to the first /dev/cu.usbserial* device
#   BAUD           flashing baud rate, defaults to 921600 (also settable as
#                  a BAUD env var); drop to 460800 if flashing reports
#                  sync/corruption errors on a weaker USB-UART adapter
#
# Works from any directory. Examples:
#   run-esp32-all.sh
#   run-esp32-all.sh ESP32_GENERIC_S3
#   run-esp32-all.sh ESP32_GENERIC SPIRAM /dev/cu.usbserial-020F8C5C
#   BAUD=921600 run-esp32-all.sh

set -euo pipefail

BOARD="${1:-ESP32_GENERIC}"
BOARD_VARIANT="${2:-}"
PORT="${3:-}"
BAUD="${4:-${BAUD:-921600}}"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPTS_DIR/env-variables-micropython.sh"
source "$SCRIPTS_DIR/env-variables-esp32.sh"

if [ -z "$PORT" ]; then
    PORT="$(ls /dev/cu.usbserial* 2>/dev/null | head -1 || true)"
    if [ -z "$PORT" ]; then
        echo "ERROR: no /dev/cu.usbserial* device found. Plug the board in or pass a port." >&2
        exit 1
    fi
fi

MPREMOTE="python $MICROPYTHON/tools/mpremote/mpremote.py connect $PORT"
BINDING="$MICROPYTHON/user_modules/lv_binding_micropython"

echo "=== [1/5] Building mpy-cross ==="
make -C "$MICROPYTHON/mpy-cross"

echo "=== [2/5] Building firmware: BOARD=$BOARD VARIANT=${BOARD_VARIANT:-<none>} ==="
make -C "$MICROPYTHON/ports/esp32" BOARD="$BOARD" BOARD_VARIANT="$BOARD_VARIANT" \
    LV_CFLAGS="-DLV_COLOR_DEPTH=16"

echo "=== [3/5] Flashing to $PORT @ $BAUD baud ==="
make -C "$MICROPYTHON/ports/esp32" deploy BOARD="$BOARD" BOARD_VARIANT="$BOARD_VARIANT" \
    LV_CFLAGS="-DLV_COLOR_DEPTH=16" PORT="$PORT" BAUD="$BAUD"

