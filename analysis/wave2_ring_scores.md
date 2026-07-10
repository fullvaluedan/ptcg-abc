# Wave-2 Deck Candidate Ring Scoring (U4 / U39 wave 2)

**Date**: 2026-07-10
**Status**: DONE. Real screen run executed. All five candidates failed the screen; no promote.

## Requirement

R3: ring verdicts for the five wave-2 deck candidates against the `candidate_yushin_ito`
baseline, screen-then-confirm (n=40 screen, n=100 confirm for anything clearing
+0.10 over baseline at screen), via `tools/score_wave2_candidates.py`.

## The five wave-2 candidates

Materialized directly from `analysis/mined_candidates_dedup_report.md`'s "New
Candidates" table into `data/derived/top_rated_decks.json` signatures (never
routed through `tools/dedupe_mined_candidates.py`, whose `--create-candidates`
path silently skips existing filenames and non-ASCII team names -- both of
which apply here). Verified against the real mining data in this repo
checkout: all five on-disk `decks/candidate_*_w2.csv` files match their
mined `team_decks[team][deck_index].signature` exactly, and differ from the
same-named wave-1 CSVs already on disk.

| Team (mining key) | Deck idx | Play count | Stem | Notes |
|---|---|---|---|---|
| THIRD PTCG Club | 0 | 19 | `candidate_third_ptcg_club_w2` | |
| kashiwashira | 0 | 8 | `candidate_kashiwashira_w2` | |
| zoroark190 | 0 | 7 | `candidate_zoroark190_w2` | |
| 変化の書ゾロアーク | 0 | 6 | `candidate_henka_no_sho_zoroark_w2` | ASCII-transliterated stem; original team name is 変化の書ゾロアーク (recorded here and in `tools/score_wave2_candidates.py`'s `WAVE2_CANDIDATES["original_name"]`) |
| BluezLee | 1 | 1 | `candidate_bluezlee_w2` | deck index 1 (not 0) -- BluezLee has two mined decks; the dedup report's "New Candidates" row is specifically index 1, distinct from the wave-1 `candidate_bluezlee` (index 0, already scored and failed) |

Baseline: `candidate_yushin_ito` (best wave-1 candidate; 0.800 win rate, 16/20,
+0.050 over the trolley baseline -- itself below gate -- per the 2026-07-06
phase-2 verdict below).

## Context: 2026-07-06 wave-1 verdict (why this matters)

Per `analysis/new_candidates_phase2_verdict.md`, all 11 wave-1 candidates
(including the same-named `candidate_third_ptcg_club`, `candidate_kashiwashira`,
`candidate_zoroark190`, `candidate_bluezlee` on disk today) were ring-scored
against the **trolley** baseline (0.750 win rate, n=20, 9-opponent bracket
ring) and **none cleared the +0.10 gate**:

| Deck (wave-1) | Win Rate | Delta vs trolley | Promote |
|---|---|---|---|
| candidate_yushin_ito | 0.800 | +0.050 | No |
| candidate_third_ptcg_club | 0.600 | -0.150 | No |
| candidate_bluezlee | 0.550 | -0.200 | No |
| candidate_kashiwashira | 0.300 | -0.450 | No |
| candidate_zoroark190 | 0.350 | -0.400 | No |

Two things changed for wave 2 and make this a genuinely new question rather
than a rerun:

1. **Different baseline.** Wave 2 compares against `candidate_yushin_ito`
   (the best wave-1 performer, 0.800) rather than trolley (0.750) -- a
   *harder* bar to clear.
2. **Different signatures.** Mining windows drift: a team's *current*
   top-rated 60-card list can differ from what was mined for wave 1 even
   under the same team name (confirmed above -- all five wave-2 signatures
   are byte-for-byte different from their wave-1 same-named counterparts on
   disk). `candidate_bluezlee_w2` in particular is a different mined deck
   from the same team (index 1, not the wave-1 index-0 deck) with only 1
   recorded play, so it carries essentially no signal from its own play
   history either way.

Given the wave-1 pattern (real top-rated-mining decks tending to
underperform the ring by a wide margin against a weaker baseline), the prior
for wave 2 clearing a *harder* baseline is not favorable, but the signatures
are genuinely new and the gate is decided by the ring, not by this prior.

## Tooling status

- `tools/score_wave2_candidates.py`: implements materialize -> build
  `{candidate_yushin_ito, five _w2 stems}` builds dict -> `screen_then_confirm`
  (n=40 screen / n=100 confirm, reusing `tools/score_candidate_decks.py`'s
  `promote_verdicts` for verdict math, inclusive `>=` tolerance at the +0.10
  margin) -> report. Pattern follows `tools/ring_calibrate.py`'s `run_ring`.
- `tests/test_score_wave2_candidates.py`: 17 tests, all hermetic logic tests
  pass against a fixture mining-data JSON (materialize overwrite semantics,
  60-card validation, ASCII stem / non-ASCII original-name round-trip,
  builds-dict scope, screen-then-confirm-only-confirms-what-cleared,
  promote-verdict inclusive-tolerance at exactly +0.10). Five additional
  tests check the real materialized `decks/candidate_*_w2.csv` files against
  the real `data/derived/top_rated_decks.json` and pass in this environment.
  One test (`test_screen_then_confirm_real_tiny_smoke_run_end_to_end`)
  requires `kaggle_environments` and is skipped here (see below).

  Result: **16 passed, 1 skipped, 0 failed.**

## Note on the build agent's initial environment

The subagent that built this unit's tooling used a Python interpreter without
`kaggle_environments` installed and could not run the real ring games from
that worktree. The repo's actual dev environment is `.venv/Scripts/python.exe`
(see `run_autoloop.sh`'s `PY` variable), which does have `kaggle_environments`;
the orchestrator re-ran the real screen from that interpreter (see Verdicts
below). A single ring game runs in well under a second (~0.3-0.6s per the U2
timing), so the full six-build, n=40 screen completed in under a minute.

## To run the real screen-then-confirm

From a repo checkout with `kaggle_environments` installed:

```
python tools/score_wave2_candidates.py
```

This (re)materializes the five `decks/candidate_*_w2.csv` files from
`data/derived/top_rated_decks.json`, screens all six builds
(`candidate_yushin_ito` + the five `_w2` stems) at n=40 games each against
the calibrated bracket ring, and for any candidate whose win rate clears
`candidate_yushin_ito`'s by >= +0.10 (inclusive), re-runs just that candidate
plus baseline at n=100 before recording a promote/no-promote verdict. Add
`--out <path>.json` to also write the full machine-readable report. Flags
`--screen-n`, `--confirm-n`, and `--margin` override the defaults (40, 100,
0.10) if a different read is wanted; `--skip-materialize` reuses the
already-written `decks/candidate_*_w2.csv` files as-is instead of
regenerating them from the mining data.

## Verdicts (real run, 2026-07-10)

Screen (n=40 each, calibrated bracket ring):

| Build | Win rate | W/L | Delta vs baseline | Cleared screen (>= +0.10)? |
|---|---|---|---|---|
| candidate_yushin_ito (baseline) | 0.825 | 33/40 | -- | -- |
| candidate_third_ptcg_club_w2 | 0.475 | 19/40 | -0.350 | No |
| candidate_kashiwashira_w2 | 0.400 | 16/40 | -0.425 | No |
| candidate_zoroark190_w2 | 0.375 | 15/40 | -0.450 | No |
| candidate_henka_no_sho_zoroark_w2 | 0.400 | 16/40 | -0.425 | No |
| candidate_bluezlee_w2 | 0.800 | 32/40 | -0.025 | No |

No candidate cleared the +0.10 screen margin, so the n=100 confirm stage was
correctly skipped by the tool (screen-then-confirm only confirms what
cleared).

**Final verdict: no-promote for all five wave-2 candidates.** Note the
baseline itself scored higher here (0.825/40) than its 2026-07-06 mark
(0.800/20) since it is a different, harder ring read (yushin-vs-yushin's own
prior baseline was trolley) -- consistent with wave 2 comparing against a
tougher bar as documented above. `candidate_bluezlee_w2` came closest
(-0.025) but did not clear; its single-play mining provenance (see table
above) is consistent with a candidate that looks strong on paper but has
essentially no track record to back it. The wave-2 mining pass, like wave 1,
did not surface a deck that beats the current best build on the calibrated
ring.
