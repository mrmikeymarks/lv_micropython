#!/usr/bin/env bash

# Erase the flash memory of the ESP32 board

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPTS_DIR/env-variables-micropython.sh"
source "$SCRIPTS_DIR/env-variables-esp32.sh"

source "$SCRIPTS_DIR/menu-esp32.sh"
if [ -z "$BOARD" ]; then
    exit 1
fi

cd $MICROPYTHON/ports/esp32
make erase BOARD=$BOARD