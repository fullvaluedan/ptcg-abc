#!/usr/bin/env bash
# Unattended ce-work push launcher (docs/plans/2026-07-10-001-feat-improvement-push-plan.md U1).
#   Watch:  tmux attach -t ptcgwork      or      tail -f cework.log
#   Kill:   tmux kill-session -t ptcgwork   (watchdog clears the orphaned sentinel)
#
# Relaunch gates on COMPLETION, not exit code: a context-exhausted claude -p run exits 0
# without finishing the plan, so the loop continues until .cework_done lists all units
# (done or blocked) or the wall-clock budget expires. Short iterations get the autoloop's
# long backoff and do not count against the attempt budget.
set -u
PROJ="/c/Users/danom/ptcg-abc"
CLAUDE="/c/Users/danom/AppData/Roaming/npm/claude"
LOG="$PROJ/cework.log"
SENTINEL="$PROJ/.cework_active"
DONE_FILE="$PROJ/.cework_done"
UNITS="U2 U3 U4 U5 U6 U7 U8 U9 U10"
BUDGET_HOURS=36
MAX_ATTEMPTS=12
export PYTHONIOENCODING=utf-8
cd "$PROJ" || exit 1

cleanup() { rm -f "$SENTINEL"; }
trap cleanup EXIT

touch "$SENTINEL"
deadline=$(( $(date +%s) + BUDGET_HOURS * 3600 ))
attempts=0

# Wait for any in-flight full autoloop iteration to end before dispatching units,
# so the push never starts mid-edit. The iteration-end marker is the exit footer.
if tmux has-session -t ptcg 2>/dev/null; then
  echo "waiting for in-flight autoloop iteration to end..." | tee -a "$LOG"
  for _ in $(seq 1 60); do
    last=$(tail -3 "$PROJ/autoloop.log" 2>/dev/null | grep -c "exit=" || true)
    [ "$last" -ge 1 ] && break
    sleep 10
  done
fi

all_done() {
  [ -f "$DONE_FILE" ] || return 1
  for u in $UNITS; do
    grep -q "^$u" "$DONE_FILE" || return 1
  done
  return 0
}

while true; do
  all_done && { echo "all units done or blocked; push complete" | tee -a "$LOG"; break; }
  [ $(date +%s) -ge "$deadline" ] && {
    echo "$(date '+%Y-%m-%d %H:%M:%S') NEEDS-DAN: cework push hit the ${BUDGET_HOURS}h budget with units unfinished; see .cework_done" >> "$PROJ/autoloop_status.md"
    echo "budget expired; NEEDS-DAN note written" | tee -a "$LOG"
    break
  }
  [ "$attempts" -ge "$MAX_ATTEMPTS" ] && {
    echo "$(date '+%Y-%m-%d %H:%M:%S') NEEDS-DAN: cework push exhausted ${MAX_ATTEMPTS} attempts; see cework.log and .cework_done" >> "$PROJ/autoloop_status.md"
    echo "attempt budget exhausted; NEEDS-DAN note written" | tee -a "$LOG"
    break
  }
  attempts=$((attempts + 1))
  start=$(date +%s)
  {
    echo ""
    echo "================ cework attempt $attempts  $(date '+%Y-%m-%d %H:%M:%S') ================"
  } | tee -a "$LOG"
  MSYS_NO_PATHCONV=1 cat "$PROJ/CEWORK_PROMPT.md" | "$CLAUDE" -p \
      --model claude-sonnet-5 \
      --dangerously-skip-permissions >> "$LOG" 2>&1
  code=$?
  dur=$(( $(date +%s) - start ))
  echo "---- cework attempt $attempts exit=$code dur=${dur}s ----" | tee -a "$LOG"
  if [ "$dur" -lt 60 ]; then
    attempts=$((attempts - 1))
    echo "short run, backing off 600s (usage limit or launch error; attempt not counted)" | tee -a "$LOG"
    sleep 600
  else
    sleep 15
  fi
done
