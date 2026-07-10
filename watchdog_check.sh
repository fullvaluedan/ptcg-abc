#!/usr/bin/env bash
# One-shot autoloop watchdog. A Windows Scheduled Task runs this every ~10 min, so it survives
# tmux-server death (the recurring failure that killed the in-tmux watchdog). It checks whether the
# ptcg loop is alive and restarts it if not, then exits. Idempotent and quiet unless it acts.
set -u
PROJ="/c/Users/danom/ptcg-abc"
LOG="$PROJ/autoloop.log"
WLOG="$PROJ/watchdog.log"
STALE_MIN=40
date '+%Y-%m-%d %H:%M:%S' > "$PROJ/.watchdog_heartbeat"

# Stale-sentinel guard: if the ce-work push session died with its sentinel in
# place, clear it so the autoloop cannot be pinned in maintenance-only forever.
if [ -f "$PROJ/.cework_active" ] && ! tmux has-session -t ptcgwork 2>/dev/null; then
  rm -f "$PROJ/.cework_active"
  echo "$(date '+%Y-%m-%d %H:%M:%S') watchdog: cleared orphaned .cework_active (ptcgwork session gone)" >> "$WLOG"
fi

alive=""
if tmux has-session -t ptcg 2>/dev/null; then
  now=$(date +%s); mtime=$(stat -c %Y "$LOG" 2>/dev/null || echo 0)
  [ $(( (now - mtime) / 60 )) -lt "$STALE_MIN" ] && alive="yes"
  [ -z "$alive" ] && ps -W 2>/dev/null | grep -qiE "claude" && alive="yes"
fi
[ -n "$alive" ] && exit 0

echo "$(date '+%Y-%m-%d %H:%M:%S') watchdog: RESTART (ptcg session missing or log stale > ${STALE_MIN}m)" >> "$WLOG"
tmux kill-session -t ptcg 2>/dev/null
tmux new-session -d -s ptcg
tmux send-keys -t ptcg "bash $PROJ/run_autoloop.sh" Enter
