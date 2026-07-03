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
PY="$PROJ/.venv/Scripts/python.exe"
LOG="$PROJ/autoloop.log"
COUNTER_FILE="$PROJ/.autoloop_iteration_count"
# U80 wiring: refresh the daily Kaggle dump + our own loss distribution every
# REFRESH_EVERY iterations. The counter persists across watchdog restarts (a
# bash-local `i` resets to 0 each restart, which would make "every Nth" mean
# nothing), and the refresh runs deterministically in bash BEFORE the claude
# call so it is never left to the model's judgment whether to run it.
REFRESH_EVERY=20
cd "$PROJ" || exit 1
i=0
[ -f "$COUNTER_FILE" ] && i=$(cat "$COUNTER_FILE" 2>/dev/null || echo 0)
case "$i" in ''|*[!0-9]*) i=0 ;; esac
while true; do
  i=$((i + 1))
  echo "$i" > "$COUNTER_FILE"
  start=$(date +%s)
  {
    echo ""
    echo "================ iteration $i  $(date '+%Y-%m-%d %H:%M:%S') ================"
  } | tee -a "$LOG"
  if [ $((i % REFRESH_EVERY)) -eq 0 ]; then
    echo "-- iteration $i: U80 daily refresh (every ${REFRESH_EVERY}) --" | tee -a "$LOG"
    "$PY" "$PROJ/tools/daily_refresh.py" >> "$LOG" 2>&1
  fi
  MSYS_NO_PATHCONV=1 "$CLAUDE" -p "$(cat "$PROJ/LOOP_BRIEF.md")" \
      --model claude-sonnet-5 \
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
