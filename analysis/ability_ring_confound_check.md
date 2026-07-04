# Does the calibrated bracket ring share the ability lever's mirror-match confound?

LOOP_BRIEF.md L1/L9 raised, and `analysis/ability_isolated_confound_check.md` closed, a confound
in the offline weak-bot gauntlet gate for `heuristic+trolley-ability`: `PTCG_ABILITY` is a single
process-global (`agents/heuristics.py`'s `_ABILITY`), and every `deck:<name>` gauntlet opponent is
piloted by `heuristics.choose()` in the SAME process (`tools/opponents.py`'s `_deck_opponent`), so
the "on" arm gave the ability lever to both seats, not just our pilot. That check found the
gauntlet's own +4.0pp point estimate (`analysis/ability_ab.md`) was noise-dominated regardless of
the confound (isolated diff_pp oscillated +2.5/-0.5/-1.3 across three runs, mean +0.2).

That check did not cover the OTHER offline signal for this lever: the calibrated bracket ring's
+20.0pp reading (`analysis/ability_ring_check.md`), which per L9 is the standing decision gate for
keeping `heuristic+trolley-ability` as shadow-king. This unit asks the same question of the ring.

## Finding: the ring's clone opponents never read `_ABILITY` at all

`tools/ring_calibrate.py`'s ring opponents are `clone:<family>` names, which resolve
(`tools/opponents.py:get`) to `_clone_opponent`. Unlike `_deck_opponent`, `_clone_opponent` never
calls `heuristics.choose()`. Its full decision path is:

- a guaranteed lethal (`heuristics.lethal_move`), then
- `_safe_first_legal_index` (built from `heuristics.options_by_type`, `option_card_id`, and
  `_is_once_per_turn_ability`, only to VETO a repeatable ability option so a stateless picker
  cannot loop on it -- it never proactively activates anything), then
- `heuristics.cap_count_for_deckout`.

`_ABILITY` is read in exactly one place in `agents/heuristics.py` (grep-verified, one hit outside
its own definition/env-read): inside `choose()`'s `_resolve_ability()` closure, at the decision
ladder `choose()` builds internally. `_clone_opponent` never calls `choose()`, so no code path a
clone opponent executes ever consults `_ABILITY`, on or off, regardless of which process-global
value is currently set.

This means toggling the "opponent" side's ability access in `ability_ring_check.py`'s wrapper
(`_ability_trolley_agent`, which only ever wraps OUR pilot's `deck:trolley` call, never the ring's
clone opponents) was never actually a mirror-match confound in the first place: the ring's
opponents structurally cannot use the ability lever no matter what `_ABILITY` is set to when it is
their turn to move.

## Verification

Code-level proof only (no new match-running tool needed; the claim is about which code paths run,
not about a measurable win-rate delta): `tests/test_opponents.py::
test_clone_opponent_ignores_ability_flag_never_reads_it` builds a MAIN selection with a safe
(once-per-turn) ABILITY option at index 0 and an END option at index 1, monkeypatches
`option_card_id`/`_is_once_per_turn_ability` so the ability option resolves and is not vetoed, and
asserts `_clone_opponent`'s decision is identical (`[0]`, plain first-legal, index 0 not vetoed)
whether `heuristics._ABILITY` is `True` or `False`. If `_clone_opponent` ever routed through
`choose()` (a regression this test would catch), the two arms could diverge; today they cannot,
because the code path never inspects the flag.

## Reading

The ring's +20.0pp reading (`analysis/ability_ring_check.md`) is a genuinely one-sided measurement
already: only our pilot (`deck:trolley` wrapped with the toggle) ever had access to the ability
lever in either arm, and the ring's clone opponents were never capable of using it regardless of
the process-global state. This is different from, and better evidence than, the gauntlet's
+4.0pp, which the isolated re-check (`analysis/ability_isolated_confound_check.md`) found was
noise-dominated once deconfounded. The ring result does not need, and does not get, the same
downgrade: no confound was ever present to remove.

This does not newly justify the ability build's shadow-king status beyond what L9 already
recorded (the ring, tau 0.857, is the standing decision gate); it closes a specific open question
LOOP_BRIEF.md's L1 caveat did not explicitly answer (whether the ring reading needed the same
deconfounding the gauntlet got) with a clear, code-verified "no, it never had that problem."
