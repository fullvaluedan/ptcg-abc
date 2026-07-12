# PTCG_RANKER powered gate (task B part 2)

Task B part 1 (analysis/ranker_outcome_model.md) trained and shipped the outcome-labeled
per-option policy ranker flag-gated off by default, and cleared the fires-vs-inert
precheck: positive control flipped and 17/25 real candidate_yushin_ito positions flipped
with PTCG_RANKER on, so the model is LIVE, not inert. Per analysis/ml_expert_review.md's
own prescription (required n at 80% power, one-sided alpha 0.05: about 710/arm for a
+5pp gate), this doc runs the powered elite-ring gate that decision was explicitly
deferred to, using the new parallel harness (tools/parallel_ring.py).

## Pre-registered thresholds

- Elite ring (35 clone:top50_* opponents): ship PTCG_RANKER only if the same-run delta
  vs plain candidate_yushin_ito is at least +5pp.
- Calibrated ring (9 clone:<family> opponents, the old regression guard): flag a
  regression if the same-run delta falls below -2pp.

Both arms pilot decks/candidate_yushin_ito.csv with PTCG_ABILITY and PTCG_THREAT_RETREAT
off (config 1, "plain", per analysis/top50_flag_config.md's verdict: plain read best
against elite play, 0.850 at n=100, and is the config PTCG_RANKER would be layered onto).
The only difference between arms is PTCG_RANKER off vs on.

## Harness change: FLAG_ATTR gains "ranker"

tools/parallel_ring.py's same-run-safe module-attribute patching (already used for
PTCG_ABILITY and PTCG_THREAT_RETREAT) generalizes directly to PTCG_RANKER: both are
read once at import time as a plain module boolean (agents/heuristics.py's `_RANKER =
os.environ.get("PTCG_RANKER", "0") != "0"`), so env-var flipping post-import is a no-op
the same way it is for the other two flags. Added one line, `FLAG_ATTR["ranker"] =
"_RANKER"`, plus a unit test (tests/test_parallel_ring.py::test_flag_attr_supports_ranker)
locking the mapping. No other harness change was needed to make the flag toggleable.

## Operational finding: an unbounded shard can hang the whole gate

The first full-scale run (elite ring, n=700/arm, jobs=16, no timeout) did not return.
After 15+ minutes, 14 of 16 shards had finished (each in well under a minute) but 2
shards were still running, each pinned near 100% CPU (838-880 accumulated CPU-seconds),
not deadlocked, just taking far longer than every other shard on the same box. The cause
was not obvious from the outside: `cabt.json` sets `episodeSteps: 10000000` and
`actTimeout: 0`, so nothing in the local engine bounds a single match's length or
per-decision time when driven in-process via `env.run()`.

To characterize it without burning more compute on a second unbounded run, a 140-game
probe (35 opponents x 2 seats x 2 flag settings, each isolated in its own subprocess with
a 15s timeout) was run with unseeded randomness. All 140 games completed cleanly, no
timeouts, no errors. That rules out a per-opponent or PTCG_RANKER-universal hang and
points at a specific pseudo-random game trajectory under the original run's shard seeds
(seed 1004 for the timed-out shard at offset 132, seed 1013 for the one at offset 528),
not reproducible from an arbitrary draw.

Rather than chase that exact seed, tools/parallel_ring.py got a bounded fix: `_run_shard`
now accepts a `timeout` (plumbed through `run_parallel_ring`'s new `shard_timeout` and the
CLI's `--shard-timeout`), and a new `_kill_process_tree` reclaims the whole process tree on
timeout, not just the direct child. That second part matters on this box specifically:
`python_exe` (a venv `Scripts/python.exe`) is itself a thin redirector that spawns the real
interpreter as a *child* process rather than exec-replacing its own image (Windows has no
`exec()`), so `subprocess.run(timeout=...)`'s own kill-on-timeout only reaped the
redirector, orphaning the real worker, which kept burning CPU. `_kill_process_tree` uses
`taskkill /PID <pid> /T /F` on Windows (a POSIX process-group kill is included for parity).
A timed-out shard is now reported as a `shard_errors` entry and excluded from the merge,
the same degrade-gracefully contract `tools/parallel_gauntlet.py` already uses for a
failed shard, not silently retried and not allowed to block every other shard's already-
finished result. Covered by 4 new/updated unit tests in tests/test_parallel_ring.py
(`test_run_shard_kills_process_tree_on_timeout` plus the two existing `_run_shard` tests
migrated from mocking `subprocess.run` to `subprocess.Popen`, since the fix needs the
child's pid, which `subprocess.run` never exposes on a timeout).

The gate below reran with `shard_timeout=240s` (about 4x a normal shard's 50-90s). Same
elite-ring seed as the original unbounded attempt, so this run is also the fix's real-world
validation: it hit the identical pathological shards again (this time 3 of them, shards 0,
1, and 10) and killed each cleanly at the 240s mark instead of hanging, landing 13/16 elite
shards completed and the gate below on 568/700 games per arm rather than blocking forever.
The calibrated-ring pass (separate run, separate seed) completed all 16 shards with zero
timeouts.

## Results

### Elite ring (35 clone:top50_* opponents)

Requested n=700/arm; 3 of 16 shards (0, 1, 10) hit the 240s shard timeout and were killed
and excluded, landing **n=568/arm actual** (81% of the request, `analysis/ranker_gate_elite.json`).

| arm | W-D-L | win rate | SE | same-run delta vs ranker_off | 95% CI |
|---|---|---|---|---|---|
| ranker_off (baseline) | 431-0-137 | 0.7588 | 0.0180 | +0.0pp | -4.98 to +4.98 |
| ranker_on | 140-0-428 | 0.2465 | 0.0181 | **-51.23pp** | -56.23 to -46.24 |

### Calibrated ring (9 clone:<family> opponents, regression guard)

Requested and achieved n=200/arm, no shard timeouts (`analysis/ranker_gate_calibrated.json`).

| arm | W-D-L | win rate | SE | same-run delta vs ranker_off | 95% CI |
|---|---|---|---|---|---|
| ranker_off (baseline) | 172-0-28 | 0.8600 | 0.0245 | +0.0pp | -6.80 to +6.80 |
| ranker_on | 82-0-118 | 0.4100 | 0.0348 | **-45.00pp** | -53.34 to -36.66 |

## Verdict vs the pre-registered gates

**REJECT on both.** This is not a borderline miss, either gate's threshold sits many
standard errors from the observed delta:

- Elite ring: needed at least +5pp to ship; observed -51.23pp +/- 2.55pp SE. The gap
  between the gate and the observation is about 22 SEs. The 95% CI (-56.23 to -46.24)
  does not come close to including +5pp, or even 0.
- Calibrated ring: the guard flags a regression below -2pp; observed -45.00pp +/- 4.26pp
  SE, about 10 SEs past the guard. The 95% CI (-53.34 to -36.66) does not include -2pp.

Both rings agree in direction and rough magnitude (-51.23pp elite, -45.00pp calibrated),
so this is not a single-ring artifact. The elite-ring shortfall (568 vs 700 requested,
from the 3 killed shards) has no bearing on the call: the observed effect is about 20
SEs from zero on the achieved n alone, far beyond anything the missing 132 games/arm
could plausibly overturn.

**Do not enable PTCG_RANKER.** It already ships default-off (`os.environ.get("PTCG_RANKER",
"0") != "0"`), so this closes the open ML cell at a hard no with no live regression risk;
nothing about the current submission changes.

## Why the collapse, and what NOT to conclude from it

The magnitude (-45 to -51pp) is large enough to be worth a sanity check against a wiring
bug before writing it off as "the model is just weak." `agents/heuristics.py`'s
`_resolve_ranker` was re-read for this: it tracks `best_idx, best_p` with
`if best_p is None or p > best_p`, a correct argmax, not an inverted comparison. No sign
flip found in the match-time wiring.

The more likely explanation is architectural, not a bug: PTCG_RANKER does not blend with
or nudge the historical category ladder, it fully replaces it on every decision where it
fires (by design, per analysis/ranker_outcome_model.md: "free to override L4/L5 and the
CEM-tuned PRIO_* category order"). The exported model's held-out AUC is 0.5424 (barely
above the 0.5173 first-legal-only baseline, from the same doc's training table), a weak
per-option signal. Substituting a weak, generically-trained scorer for a heuristic ladder
that was CEM-tuned specifically against this ring is consistent with a large loss even
without any defect: every decision the ranker touches is a decision the tuned ladder no
longer makes.

This is a plausibility argument, not a proof; it was not chased further; the point of this
gate is the ship/no-ship call, which is unambiguous either way.

## Files

- `tools/parallel_ring.py` (extended): `FLAG_ATTR["ranker"] = "_RANKER"`; `_run_shard`
  gained a `timeout` parameter (now backed by `subprocess.Popen` + `communicate(timeout=)`
  instead of `subprocess.run`, needed to keep the child pid for tree-killing);
  `_kill_process_tree` (new); `run_parallel_ring`'s new `shard_timeout` parameter; CLI
  `--shard-timeout`.
- `tests/test_parallel_ring.py` (extended): `test_flag_attr_supports_ranker`,
  `test_run_shard_kills_process_tree_on_timeout`, plus the two `_run_shard` tests migrated
  from mocking `subprocess.run` to `subprocess.Popen`. 19 tests, all passing.
- `analysis/ranker_gate_elite.json`, `analysis/ranker_gate_calibrated.json` (raw
  `run_parallel_ring` output for each ring, generated, not hand-edited).
