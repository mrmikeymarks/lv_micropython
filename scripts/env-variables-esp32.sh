#!/usr/bin/env bash
# Set environment variables for ESP32 development
# Everything lives under /Volumes/1TB_DAVINCI/.espressif (IDF checkouts, toolchains, python envs).
# v5.2.2 is the newest IDF this MicroPython tree supports (v5.3.5/v5.5.4 are past the supported list).
export IDF_TOOLS_PATH=/Volumes/1TB_DAVINCI/.espressif
export ESPIDF=/Volumes/1TB_DAVINCI/.espressif/v5.2.2/esp-idf
#ESPIDF=/Volumes/1TB_DAVINCI/.espressif/v5.3.5/esp-idf
# The IDF python env was created with python3.12 (IDF 5.2 does not support this Mac's
# default python 3.14), so pin it before export.sh runs its auto-detection.
# NOTE: this must be the venv ROOT (no trailing /bin) — IDF appends bin/python itself.
export IDF_PYTHON_ENV_PATH=/Volumes/1TB_DAVINCI/.espressif/python_env/idf5.2_py3.12_env

source $ESPIDF/export.sh


