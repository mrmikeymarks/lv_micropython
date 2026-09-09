#!/usr/bin/env bash

# Print the shareable online-simulator link for a demo file.
#
# Usage:
#   share-demo.sh demos/hello_touch.py            # pinned to current commit SHA
#   share-demo.sh demos/hello_touch.py --branch   # live link tracking the branch
#
# The link opens sim.lvgl.io (MicroPython + LVGL 9.0 in the browser) and
# auto-loads the script from the public GitHub fork. The file must be
# committed AND pushed for the link to work. SHA-pinned links are stable
# forever; --branch links update whenever the branch moves.

set -euo pipefail

REPO="mrmikeymarks/lv_micropython"
SIM="https://sim.lvgl.io/v9.0/micropython/ports/webassembly/index.html"

FILE="${1:?usage: share-demo.sh demos/<file>.py [--branch]}"

SCRIPTS_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
MICROPYTHON="$(dirname "$SCRIPTS_DIR")"
cd "$MICROPYTHON"

# repo-relative path
REL="$(python3 -c "import os,sys; print(os.path.relpath(os.path.abspath(sys.argv[1]), os.getcwd()))" "$FILE")"
[ -f "$REL" ] || { echo "ERROR: $REL not found in repo" >&2; exit 1; }

if [ "${2:-}" = "--branch" ]; then
    REF="$(git rev-parse --abbrev-ref HEAD)"
else
    REF="$(git rev-parse HEAD)"
    if ! git diff --quiet HEAD -- "$REL" 2>/dev/null; then
        echo "WARNING: $REL has uncommitted changes; the link serves the committed version." >&2
    fi
fi

if ! git ls-remote --exit-code origin "refs/heads/$(git rev-parse --abbrev-ref HEAD)" >/dev/null 2>&1; then
    echo "WARNING: current branch not found on origin - push before sharing." >&2
fi

URL="${SIM}?script=https://raw.githubusercontent.com/${REPO}/${REF}/${REL}"
echo "$URL"
command -v pbcopy >/dev/null && printf '%s' "$URL" | pbcopy && echo "(copied to clipboard)" >&2
