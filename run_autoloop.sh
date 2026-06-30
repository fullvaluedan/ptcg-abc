#!/usr/bin/env bash
# Unattended compound-engineering loop for ptcg-abc.
#   Watch:  tmux attach -t ptcg      or      tail -f autoloop.log
#   Kill:   tmux kill-session -t ptcg
#
# Each iteration runs one headless claude pass against LOOP_BRIEF.md (full autonomy).
# A short iteration triggers a long backoff so a usage limit or auth error does not
# hot spin.
set -u
PROJ="/c/Users/danom/ptcg-abc"
CLAUDE="/c/Users/danom/AppData/Roaming/npm/claude"
LOG="$PROJ/autoloop.log"
cd "$PROJ" || exit 1
i=0
while true; do
  i=$((i + 1))
  start=$(date +%s)
  {
    echo ""
    echo "================ iteration $i  $(date '+%Y-%m-%d %H:%M:%S') ================"
  } | tee -a "$LOG"
  MSYS_NO_PATHCONV=1 "$CLAUDE" -p "$(cat "$PROJ/LOOP_BRIEF.md")" \
      --dangerously-skip-permissions >> "$LOG" 2>&1
  code=$?
  dur=$(( $(date +%s) - start ))
  echo "---- iteration $i exit=$code dur=${dur}s ----" | tee -a "$LOG"
  if [ "$dur" -lt 30 ]; then
    echo "short iteration, backing off 300s (possible usage limit or error)" | tee -a "$LOG"
    sleep 300
  else
    sleep 8
  fi
done
