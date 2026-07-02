# Per-archetype expert-agreement baselines (U32)

The heuristic pilot's top-1 move agreement with the expert cohort, computed PER
archetype family on the frozen md5 test bucket. Every later aware-pilot A/B (U34
ability lever, U38 two-step attribution, U40 learned ranker) is scored per family,
so each family needs its own held-out baseline to measure a delta against. The
single pooled number (the historic 0.212 in move_ranking_diverges_ability_gap.md,
measured on the 3-named-team cohort) is not transferable: a build can help one
family and hurt another while the pooled number barely moves.

## Method

- Cohort: the winning seat of each decided episode (analysis/expert_cohort, the U25
  resolved fork). Same cohort the census counted.
- Family: the cohort seat's opening decklist classified against the real archetype
  signatures (analysis/archetype builtins) at coverage threshold 0.35, exactly as
  the census classifies.
- Split: the canonical md5 episode split (analysis/replay_trace, KD4),
  test = md5(episode_id) mod 100 < 25. This is the SAME held-out partition the
  spike, the baseline, and the trainer all read, so a delta measured here composes
  with a delta measured there.
- Pilot: the deployed heuristic `agents.heuristics.choose`, top-1 (argmax) agreement
  over each cohort seat's scorable MAIN single-pick decisions.
- Coverage: 1457 test-bucket episodes, 42,724 held-out decisions (1 draw skipped).

## Result (held-out test bucket, deployed heuristic pilot)

| family | episodes | decisions | top-1 agreement |
| --- | --- | --- | --- |
| meta_archaludon | 578 | 12487 | 0.283 |
| meta_grimmsnarl (target) | 521 | 17994 | 0.269 |
| meta_grimmsnarl_tonakaiiii | 206 | 7481 | 0.226 |
| other | 152 | 4762 | 0.250 |
| pooled | 1457 | 42724 | 0.263 |

The families span 0.226 to 0.283 (about 6pp), so the pooled 0.263 masks a real
per-family spread. The target family (meta_grimmsnarl, U25) sits at 0.269; the
tonakaiiii Grimmsnarl variant is the hardest to imitate at 0.226, which is where an
aware pilot has the most room to improve.

## How this is consumed

- The committed machine artifact is analysis/per_archetype_baselines.json (aggregate
  counts and rates per family; no raw episodes, so the competition data stays
  isolated). Downstream A/Bs load a family's `agreement` as the delta reference.
- A candidate aware pilot PASSES the offline filter for a family only when its
  held-out top-1 agreement clears that family's baseline here (U40 PASS bar is
  baseline + 0.03), and it never regresses another family. This is a filter that
  BLOCKS a ladder slot; the ladder A/B is still the sole arbiter.

## Reproduce

```
.venv/Scripts/python.exe -m tools.per_archetype_baseline \
  data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip \
  --split test --commit analysis/per_archetype_baselines.json
```

Runtime about 4.5 minutes over the full dataset. The machine dump also lands
isolated under data/derived/census/ via tools.isolation.
