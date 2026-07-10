# Maintenance-only iteration (ce-work push active)

The ce-work improvement push (tmux session ptcgwork, docs/plans/2026-07-10-001-feat-improvement-push-plan.md)
holds `.cework_active`, so this iteration is MAINTENANCE ONLY. The launcher selected this brief in bash; do
not consult LOOP_BRIEF.md's work queue this iteration.

Allowed actions, in priority order, ONE small increment then STOP:
1. Board check, only if the newest episode id advanced since the last recorded check (tools/scout.py
   discipline, max 2-4/day). Record the reading in autoloop_status.md ONLY. Do not edit state/current.md
   prose, findings.md, docs/writeup/, or any file named in the push plan.
2. If nothing to check: append a one-line heartbeat to autoloop_status.md and stop.

Hard rules still apply: no em dashes anywhere including commit subjects (a commit-msg hook rejects them);
never git add -A; never discard or overwrite foreign uncommitted working-tree changes; JSON STATE block
edits only through tools/loop_state.py (and not this iteration). The ONE-loop rule is amended while the
sentinel exists: ptcgwork is the sanctioned second session; the prohibition applies to additional autoloop
instances only.
