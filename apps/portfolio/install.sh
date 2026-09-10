#!/usr/bin/env bash

# Install the portfolio content onto a board running lv_micropython firmware
# with the portfolio engine frozen in (see `scripts/lvmp flash`).
#
# Usage:
#   install.sh [PORT] [--launcher]
#     PORT        defaults to the first /dev/cu.usbserial* device
#     --launcher  boot to a standby screen and start on the BOOT button
#                 (default: start the portfolio immediately)
#
# Only two small files reach the board: portfolio.txt (all the content) and
# a one-line main.py. The engine itself is frozen firmware, so editing
# content is: edit portfolio.txt, run this again. No rebuild, no compiler.

set -euo pipefail

APP_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(cd "$APP_DIR/../.." && pwd)"

PORT=""
ENTRY="portfolio_main"
for arg in "$@"; do
    case "$arg" in
        --launcher) ENTRY="portfolio_launcher" ;;
        *) PORT="$arg" ;;
    esac
done

if [ -z "$PORT" ]; then
    PORT="$(ls /dev/cu.usbserial* 2>/dev/null | head -1 || true)"
    if [ -z "$PORT" ]; then
        echo "ERROR: no /dev/cu.usbserial* device found. Plug the board in or pass a port." >&2
        exit 1
    fi
fi

MPREMOTE="python $MICROPYTHON/tools/mpremote/mpremote.py connect $PORT"
MAIN="$(mktemp)"
trap 'rm -f "$MAIN"' EXIT
echo "import $ENTRY" > "$MAIN"

echo "=== Installing portfolio content to $PORT (entry: $ENTRY) ==="
$MPREMOTE fs cp "$APP_DIR/portfolio.txt" :portfolio.txt
$MPREMOTE fs cp "$MAIN" :main.py
echo "=== Resetting board ==="
$MPREMOTE reset
echo "Done. Edit portfolio.txt and re-run to change content."
