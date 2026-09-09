#!/usr/bin/env bash

# Build MicroPython-LVGL app for: Unix/Linux systems

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
source "$SCRIPTS_DIR/env-variables-micropython.sh"

VARIANT=lvgl

cd $MICROPYTHON
make -C mpy-cross

cd $MICROPYTHON/ports/unix

make VARIANT=$VARIANT
