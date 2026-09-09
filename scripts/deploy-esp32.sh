#!/usr/bin/env bash

# Deploy firmware ESP32 boards

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPTS_DIR/env-variables-micropython.sh"
source "$SCRIPTS_DIR/env-variables-esp32.sh"

source "$SCRIPTS_DIR/menu-esp32.sh"
if [ -z "$BOARD" ]; then
    exit 1
fi

cd $MICROPYTHON/ports/esp32
make deploy BOARD=$BOARD BOARD_VARIANT=$BOARD_VARIANT  LV_CFLAGS="-DLV_COLOR_DEPTH=16" 
