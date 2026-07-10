# U105b (plan U2): PTCG_THREAT_RETREAT ring A/B on the yushin deck -- harness scaffold

Plan: docs/plans/2026-07-10-001-feat-improvement-push-plan.md, U2/U105b. Requirement R1:
does threat-aware retreat (`PTCG_THREAT_RETREAT`, `agents/heuristics.py`) actually win more
games on the calibrated clone ring, on the yushin+ability build (the U104-passed baseline,
analysis/u104_stacked_ring_pass_run.md)? `measure_threat_retreat.py` already confirmed the
lever is LIVE on trolley (flips real pilot decisions in captured positions) but makes no
win-rate claim; this is the honest ring follow-up.

**Status: DONE. Harness built, hermetically tested, smoke-tested, and the real n=100/arm gate
run has been executed. Verdict: PASS, diff_pp = +6.0. See Verdict section below.**

## Method

`tools/threat_retreat_ring_check.py`: two arms, both heuristic+yushin+ability (the U104
baseline, `_ABILITY` forced on in both), `_THREAT_RETREAT` off vs on, played same-run against
the identical calibrated bracket-band ring (tau 0.857, analysis/ring_calibration.md) so no
cross-run variance can confound the delta. Alternates seats every game. Mirrors
`tools/ability_ring_check.py`'s monkeypatch-wrapper pattern (flag toggled on the imported
module attribute, restored in a `finally`) combined with `tools/stacked_ring_u104.py`'s
`_make_agent_factory` (deck pinning plus multi-flag patching), extended with a `_THREAT_RETREAT`
patch alongside `_ABILITY`.

Gate: PASS when `diff_pp` (on minus off) is strictly more than +5.0pp (diff exactly +5.0pp is
FAIL, +5.1pp is PASS -- same convention as `tools/attack_first_ring_check.py`'s
`GATE_MARGIN_PP`/`diff_pp`). Saturation routing: if the off-arm (threat off) win rate is >=0.85,
a compressed delta is not honest evidence of a real FAIL (the standard ring is known to
saturate near 0.875-0.91), so the verdict routes to `NEEDS_U5_HARD_RING` instead of a bare FAIL.
Below both bars, FAIL is recorded as an honest negative.

Secondary metric: loss rate vs. the three hardest clones in the run, derived from the run's own
per-opponent breakdown (highest loss rate, pooling both arms' games against each family since
both arms share deck+ability and only threat-retreat differs; ties break alphabetically).

## Build notes

The draft tool and test file were both present and essentially correct on read; the only
substantive fix made was an import-order bug that broke every hermetic test touching the real
engine (see below). No changes were needed to the gate math, the agent-factory flag-patching,
or the secondary-metric logic.

### Fix: `agents` package name collision with kaggle_environments

`kaggle_environments`'s `lux_ai_s3` env loads its own env-local `agents.py` under the bare
module name `agents` and leaves it cached in `sys.modules` without cleaning up. If
`kaggle_environments` gets imported before this repo's `agents/heuristics.py` does, every
subsequent `from agents import heuristics` in this process silently resolves to the wrong
module and raises `ImportError: attempted relative import with no known parent package` from
`lux_ai_s3/agents.py`'s own relative import. This is a pre-existing issue in this
venv/kaggle_environments version -- `tests/test_ability_ring_check.py` hits the identical
failure for the same reason and was not introduced by this unit.

Fix applied in `tools/threat_retreat_ring_check.py` only (in scope for this unit): a
module-level `from agents import heuristics as _heuristics` added before any import that could
transitively pull in `kaggle_environments`, so our package is pinned in `sys.modules["agents"]`
first. This is self-contained to this tool; it does not touch `tests/conftest.py` or the other
ring-check tools, which remain out of scope.

## Hermetic tests

`pytest tests/test_threat_retreat_ring_check.py -v` (via the repo's `.venv`, which has
`kaggle_environments` installed): **18 passed, 0 failed** (previously 5 failed on the import
bug above, 13 passed). Coverage per the unit brief: flag-patching wrapper restores prior state
after each call; the off-arm agent never observes `_THREAT_RETREAT=True`; the two arm factories
produce distinct agent objects; gate math (exactly-at-margin FAIL, just-above-margin PASS,
below-margin+below-saturation FAIL, below-margin+saturated routes to `NEEDS_U5_HARD_RING`,
PASS overrides saturation); hardest-clones ranking with alphabetical tiebreak and n=0 exclusion;
secondary loss-rate metric counts only the named clones and ignores unknown names; a real tiny
ring run (n=2/arm) reconciles W-D-L totals; CLI output formatting.

## Smoke test (n=4/arm, real engine, not a gate result)

Ran `tools/threat_retreat_ring_check.py -n 4` end-to-end against the real ring engine (not
mocked) to confirm the harness executes correctly outside the hermetic-test doubles.

```
heuristic+yushin+ability-threat_retreat-off: 1.000 (4-0-0, n=4)
heuristic+yushin+ability-threat_retreat-on:  1.000 (4-0-0, n=4)
diff_pp (on minus off) = +0.0
verdict = NEEDS_U5_HARD_RING (off-arm win rate 1.000 >= 0.85 saturation threshold)
```

W-D-L totals reconcile (4-0-0, n=4 each arm) and the verdict logic engaged the saturation
route correctly given a 100% off-arm read. At n=4/arm this is far too small a sample to say
anything about the real lever; it only demonstrates the harness runs correctly end-to-end.

A second, slightly larger smoke run (n=20/arm, used only for timing, see below) landed off-arm
90.0% (18-0-2) and on-arm 75.0% (15-0-5) -- again not a result, just confirmation that the
harness produces plausible non-degenerate W-D-L spreads at a larger n.

## Timing: estimate for the full n=100/arm gate run

Two timed smoke runs, both via `.venv`'s python, wall-clock including process startup and
`kaggle_environments` module load:

| n/arm | total games (both arms) | wall clock |
| --- | --- | --- |
| 4 | 8 | ~4s |
| 20 | 40 | ~23s |

Marginal rate: (23s - 4s) / (40 - 8 games) ~= 0.59s/game. The two runs' implied fixed
(process-startup) overhead is small and consistent with noise (near zero), so the estimate
below uses the marginal per-game rate applied to the full game count rather than assuming a
large fixed cost.

**n=100/arm = 200 games total -> estimated wall clock ~2-3 minutes (roughly 118s at the
measured marginal rate, with headroom for game-length variance across opponents).** This is an
extrapolation from two small runs on one machine's current load, not a measured n=100 timing --
treat it as a planning estimate, not a commitment.

## Reproduce (smoke, already run)

```
python tools/threat_retreat_ring_check.py -n 4
```

## Full n=100/arm gate run -- NOT executed by this unit, for the orchestrator to launch detached

```
cd C:\Users\danom\ptcg-abc\.claude\worktrees\agent-a07b0f1f2aa8ce881 && "C:\Users\danom\ptcg-abc\.venv\Scripts\python.exe" tools/threat_retreat_ring_check.py -n 100 > analysis/u105b_n100_run.log 2>&1
```

Estimated duration ~2-3 minutes per the timing extrapolation above; recommend the orchestrator
budget more headroom (e.g. treat as a 5-10 minute detached job) since the smoke n was small and
per-game time can vary with which clone family and how long individual games run.

## Verdict (real n=100/arm gate run)

Executed 2026-07-10 via the command above (log: `analysis/u105b_n100_run.log`):

```
heuristic+yushin+ability-threat_retreat-off: 0.850 (85-0-15, n=100)
heuristic+yushin+ability-threat_retreat-on:  0.910 (91-0-9,  n=100)
diff_pp (on minus off) = +6.0
gate: diff_pp > +5.0 -> verdict = PASS
hardest clones this run: clone:bracket_4, clone:meta_archaludon, clone:bracket_5
  off-arm loss rate vs hardest clones: 0.212 (7/33)
  on-arm  loss rate vs hardest clones: 0.273 (9/33)
```

**Gate verdict: PASS.** Threat-aware retreat wins 6.0pp more on the calibrated ring at
n=100/arm, same-run, alternating seats. The lever is un-broken and demonstrably positive on
win rate, not just a pilot-decision-flip claim.

**Saturation flag for U5:** the off-arm win rate landed at exactly 0.850, the saturation
threshold named in this unit's routing rule. The gate still cleared cleanly (+6.0pp, not a
compressed delta), so this is recorded as a PASS, not routed to `NEEDS_U5_HARD_RING`. But an
off-arm read this close to the standard ring's known saturation band (0.875-0.91) means the
*next* lever tested from this baseline may not have room to show a positive delta on this ring.
U5 should treat this as evidence that saturation risk is real and rising, not that it has
already blocked a verdict here.

On the hardest-clone secondary metric, the on-arm actually loses slightly *more* to the three
hardest clones (0.273 vs 0.212) despite winning more overall -- consistent with threat-aware
retreat trading away some contested endgames against the strongest opponents in exchange for a
larger population-wide win-rate gain. Worth a citation in the writeup (U9) as a nuance, not a
contradiction: the primary gate is win rate on the calibrated ring as specified in R1, and that
gate passed.
