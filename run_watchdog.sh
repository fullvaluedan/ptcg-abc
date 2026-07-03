#!/usr/bin/env bash
# Watchdog for the ptcg autoloop. Restarts the tmux session when the loop dies or goes silent.
#   Run:    tmux new-session -d -s ptcgdog "bash /c/Users/danom/ptcg-abc/run_watchdog.sh"
#   Watch:  tail -f watchdog.log
# Restart condition: the ptcg tmux session is gone, OR the autoloop log has been silent for
# STALE_MIN minutes AND no claude process is running (long iterations stream output, so a live
# claude with a quiet log is left alone).
set -u
PROJ="/c/Users/danom/ptcg-abc"
LOG="$PROJ/autoloop.log"
WLOG="$PROJ/watchdog.log"
STALE_MIN=45
CHECK_S=300

note() { echo "$(date '+%Y-%m-%d %H:%M:%S') watchdog: $*" >> "$WLOG"; }

note "started (stale threshold ${STALE_MIN}m, check every ${CHECK_S}s)"
while true; do
  restart=""
  if ! tmux has-session -t ptcg 2>/dev/null; then
    restart="tmux session missing"
  else
    now=$(date +%s)
    mtime=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
    age_min=$(( (now - mtime) / 60 ))
    if [ "$age_min" -ge "$STALE_MIN" ]; then
      if ! ps -W 2>/dev/null | grep -qiE "claude(\.exe)?"; then
        restart="log silent ${age_min}m and no claude process"
      fi
    fi
  fi
  if [ -n "$restart" ]; then
    note "restarting loop ($restart)"
    tmux kill-session -t ptcg 2>/dev/null
    tmux new-session -d -s ptcg
    tmux send-keys -t ptcg "bash $PROJ/run_autoloop.sh" Enter
  fi
  sleep "$CHECK_S"
done
