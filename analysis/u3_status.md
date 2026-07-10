# U3 status (orchestrator note, not a plan deliverable)

Real matched-action extraction run relaunched detached in tmux session
`u3run` at 2026-07-10 ~17:53 (first attempt at 17:36 hung on a blocked
stdin read inside the tmux pane -- killed, relaunched with `python -u`
and `< /dev/null`). Confirmed genuinely progressing: loss states built
(17,951 rows / 558 games), expert corpus loaded (2,503,920 rows), zip
index built (46,632 entries), now in the kNN join step (ball_tree,
chunked query, the fix for the earlier 48GB brute-force leak).

Log: analysis/u3_matched_action_run.log. Check `tmux capture-pane -t u3run -p`
or the log for progress; ends with `DONE_EXIT=<code>` on completion.
Estimated duration ~1.5-2 hours extrapolated from smoke-test timing.

Do not treat U3 as complete until analysis/matched_expert_actions.md exists
with real per-loss-cluster findings and the log shows DONE_EXIT=0.
