# PTCG_ATTACK_FIRST fires-vs-inert check (U93 step 1)

## What this is

U91 step 2 confirmed two related within-turn patterns on bracket_4 real ladder
replays (both gates pass, n>1400/side): winners attach-before-attack LESS often
than losers (52.4% vs 55.8%) and winners bank energy (attach with no attack that
same turn) LESS often too (19.2% vs 23.6%). `analysis/gameplan_claims_bracket_4.md`
named this as U93's job: design a flag-gated rule from the gap and A/B it,
correlation in mined data is not yet proven prescriptive.

`agents/heuristics.py`'s shipped default always attaches first whenever an attach
option is legal (PRIO_ATTACH outranks PRIO_ATTACK), so it over-attaches relative to
BOTH cohorts in the mined data, not just the losing one. The literal rule the plan
names is: when a positive-value attack is already legal THIS decision using energy
already attached (no further attach needed to unlock it), take the attack now
instead of the discretionary attach. Implemented as `_resolve_attack_first` in
`choose()`, gated behind `PTCG_ATTACK_FIRST` (default off, byte-identical unset).
`tests/test_heuristic.py` covers the resolver directly (inert by default, fires
when both an ATTACH and a positive-value ATTACK are legal, lethal still wins,
no-op without an ATTACH option, no-op when the attack has zero value).

## Fires-vs-inert check

Same discipline as `measure_energy_seq.py` / `measure_bench_dig.py` /
`measure_worlds.py`: CAN-fire is not MATTERS. Before spending a bracket-ring A/B
slot, `tools/measure_attack_first.py` captures real mid-game MAIN observations from
a trolley heuristic-vs-random match where BOTH an ATTACH and an ATTACK option are
legal, then toggles `heuristics._ATTACK_FIRST` off/on and compares the end-to-end
`choose()` decision.

```
.venv/Scripts/python.exe -m tools.measure_attack_first -n 20
```

Result (trolley, heuristic pilot, 20 captured ATTACH+ATTACK positions across up to
10 matches): 8/20 positions had a positive-value attack already on the table
(`ba_value > 0`); the lever flipped the end-to-end pilot decision on 3/20 positions
overall (3 of the 8 live positions, 37.5%). All three flips occurred exactly where
expected (`ba_value > 0`); the 12 zero-value-attack positions never flipped, which
is the resolver's own guard (`ba is None or ba[1] <= 0` declines) working as coded.

**Verdict: LIVE, not inert.** PTCG_ATTACK_FIRST changes real trolley pilot decisions
(3/20 flips, consistent with the 1/3 flip rate that was sufficient to confirm
PTCG_ENERGY_SEQ was live). This is not a win-rate claim (offline weak-bot play is
not ladder-predictive, per meta.md); it only refutes inertness. The next honest
check is the bracket-ring A/B (>=+5pp with gauntlet-direction agreement, per the
plan) before any ladder slot is spent, not this measurement.

## Tests

`tests/test_heuristic.py`: 6 new tests (`test_attack_first_inert_by_default`,
`test_attack_first_prefers_attack_when_flag_on`,
`test_lethal_taken_before_attack_first`,
`test_attack_first_noop_without_attach_option`,
`test_attack_first_noop_when_attack_has_no_value`, plus the shared
`_attack_and_attach_obs` helper). Full suite still passes (see autoloop_status.md
for the exact count this iteration). `tools/measure_attack_first.py` is a dev-only
measurement tool, never shipped, touches no shipped code path (the flag is toggled
on the imported module attribute and restored in a finally).
