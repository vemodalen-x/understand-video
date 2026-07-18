#!/usr/bin/env sh
set -eu

SCRIPT_DIR=$(CDPATH= cd -- "$(dirname -- "$0")" && pwd)
if [ "$#" -eq 0 ]; then
  set -- demo --offline
fi
exec node "$SCRIPT_DIR/understand-video-demo.mjs" "$@"
