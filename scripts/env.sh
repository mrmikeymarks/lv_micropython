# lv_micropython environment - source me (bash or zsh):  source scripts/env.sh
#
# Sets MICROPYTHON (repo root) immediately. IDF activation is a function,
# not a side effect, so non-ESP32 work (sim, unix builds) never pays the
# export.sh startup cost:  espressif_env   # idf.py etc. on PATH
#
# IDF discovery is volume-agnostic (repo may move between volumes) and
# prefers the version this tree is CI-tested against (IDF_VER in
# tools/ci.sh); v5.5+ is known-broken here (its ldgen rejects our OBJECT
# libraries). Presets of IDF_TOOLS_PATH / ESPIDF / IDF_PYTHON_ENV_PATH that
# point at existing paths are respected.

_ENV_PATH="${BASH_SOURCE[0]:-${(%):-%x}}"
SCRIPTS_DIR="$(cd "$(dirname "$_ENV_PATH")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"
export MICROPYTHON
BUILD_VERBOSE=1
unset _ENV_PATH

espressif_env() {
    # 1. tools root: this repo's volume, then any volume, then ~
    if [ -z "${IDF_TOOLS_PATH:-}" ] || [ ! -d "${IDF_TOOLS_PATH:-}" ]; then
        local vol cand
        case "$MICROPYTHON" in
            /Volumes/*) vol="/$(echo "$MICROPYTHON" | cut -d/ -f2-3)" ;;
            *)          vol="$HOME" ;;
        esac
        for cand in "$vol/.espressif" /Volumes/*/.espressif "$HOME/.espressif"; do
            if [ -d "$cand" ]; then
                export IDF_TOOLS_PATH="$cand"
                break
            fi
        done
    fi
    # 2. IDF checkout: CI-pinned version first, newest as warned fallback
    if [ -z "${ESPIDF:-}" ] || [ ! -f "${ESPIDF:-}/export.sh" ]; then
        local pin
        pin="$(sed -n 's/^IDF_VER=//p' "$MICROPYTHON/tools/ci.sh" 2>/dev/null | head -1)"
        if [ -n "$pin" ] && [ -f "$IDF_TOOLS_PATH/$pin/esp-idf/export.sh" ]; then
            export ESPIDF="$IDF_TOOLS_PATH/$pin/esp-idf"
        else
            export ESPIDF="$(ls -d "$IDF_TOOLS_PATH"/v*/esp-idf 2>/dev/null | sort -V | tail -1)"
            [ -n "$pin" ] && echo "env.sh: WARNING: pinned IDF $pin not installed; using $ESPIDF" >&2
        fi
    fi
    [ -n "${ESPIDF:-}" ] || { echo "env.sh: ERROR: no ESP-IDF under \$IDF_TOOLS_PATH/v*/esp-idf" >&2; return 1; }
    # 3. python venv matching the chosen IDF's major.minor - never just newest
    if [ -z "${IDF_PYTHON_ENV_PATH:-}" ] || [ ! -x "${IDF_PYTHON_ENV_PATH:-}/bin/python" ]; then
        local mm
        mm="$(basename "$(dirname "$ESPIDF")" | sed -n 's/^v\([0-9]*\.[0-9]*\).*/\1/p')"
        IDF_PYTHON_ENV_PATH="$(ls -d "$IDF_TOOLS_PATH/python_env/idf${mm}_"*_env 2>/dev/null | sort -V | tail -1)"
        if [ -n "$IDF_PYTHON_ENV_PATH" ]; then
            export IDF_PYTHON_ENV_PATH
        else
            unset IDF_PYTHON_ENV_PATH
        fi
    fi
    source "$ESPIDF/export.sh"
}
