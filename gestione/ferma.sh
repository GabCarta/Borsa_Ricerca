#!/bin/bash
# Ferma i 4 programmi avviati con avvia.sh
GESTIONE=$(cd "$(dirname "$0")" && pwd)
for nome in dashboard dt-factory dr-registration authentication; do
  f="$GESTIONE/log/$nome.pid"
  if [ -f "$f" ]; then
    # uccide anche i processi figli (il reloader di Flask)
    pkill -P "$(cat "$f")" 2>/dev/null; kill "$(cat "$f")" 2>/dev/null && echo "$nome fermato"
    rm -f "$f"
  fi
done
