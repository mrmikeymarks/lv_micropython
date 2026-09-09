#!/usr/bin/env bash

# Set environment variables for MicroPython development

BUILD_VERBOSE=1

# Resolve the repo root from this file's own location so the scripts work no
# matter what directory they are run or sourced from (bash or zsh).
_SCRIPT_PATH="${BASH_SOURCE[0]:-${(%):-%x}}"
SCRIPTS_DIR="$(cd "$(dirname "$_SCRIPT_PATH")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"
echo "MICROPYTHON=$MICROPYTHON"
