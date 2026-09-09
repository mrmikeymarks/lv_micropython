#!/usr/bin/env bash
# Serial monitor — delegates to scripts/monitor.sh (see it for usage/options).
exec "$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)/scripts/log.sh" "$@"
