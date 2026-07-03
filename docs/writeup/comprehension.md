# The comprehension track: why the clone opponent failed, what it actually taught, and what shipped from it (Strategy prize writeup, U90-U94)

This section is a companion to [offline_ladder_transfer.md](offline_ladder_transfer.md)
(which covers whether an offline proxy can be trusted) and
[genome_tuning.md](genome_tuning.md) (whether an offline optimizer can be
trusted). This one is about a single closed loop that ran end to end: a
recorded negative result was re-examined and found to be a measurement
artifact, not a fact about the game; the artifact was fixed at the
instrument level, not by trying more model variants; the resulting
understanding was mined into concrete, gated claims about what winning play
looks like; one of those claims was turned into a real, flag-gated rule on
the shipped agent and cleared two independent offline gates; and, in
parallel, the original clone-opponent question was re-asked one more time
with a genuinely different method and got a clean, final answer. Every
number below cites the committed analysis file it came from.

## Why this track exists: a wrong conclusion, caught late

The project's U71 clone-opponent effort trained a model to imitate what
top-20 teams actually did on their turns, so the offline bracket ring could
include opponents that play like the field instead of like first-legal.
Three attempts (a linear model, then a shallow gradient-boosted tree, then a
richer feature set) all collapsed to the same behavior: the trained model's
top-1 pick equaled the first legal option on 100% of held-out decisions,
identical to a policy with zero learned content at all
(`analysis/clone_quality.md`). The recorded verdict at the time was "top-20
play is too subtle to imitate from this feature set." That verdict was
wrong, and it was wrong in a way that would have quietly capped how much
this project believed it could ever learn from the expert data: it
generalized a specific optimizer failure into a claim about the underlying
skill, without first checking whether the optimizer itself was the problem.

## The autopsy: three concrete instrument defects, not unlearnable play

Re-reading the same evidence with the question "what would make this
*optimizer* collapse to first-legal even if the data has learnable
structure in it" found three separate, independently verified defects, all
in `analysis/clone_quality.md`:

1. **The training objective's zero-risk optimum was already first-legal.**
   Every attempt used a per-row, pointwise log-loss ("is this option the one
   that was played, yes or no"). Because first-legal already clears
   33 to 45 percent raw accuracy per family before any model is fit,
   a classifier trained this way has no incentive to ever deviate from
   copying position: deviating can only look worse against a baseline that
   is frequently already right. Verified directly on `meta_grimmsnarl`
   (13,019 held-out decisions): the fitted model's top-1 pick equaled
   global option 0 in 13,019 of 13,019 cases, even though its fitted
   coefficients were not degenerate (real content weights like
   `attach_x_no_energy_yet` and `is_attack` survived fitting, just too
   small to ever overcome the position weight).
2. **The baseline was handed to the model as a feature while the gate
   measured margin over that same baseline.** `opt_is_first` and
   `opt_index_norm` were both inputs and the thing being beaten.
3. **The features were semantically blind.** Eight regex-derived action
   tags, no card identity, no energy costs, no evolution lines. Boss's
   Orders and every other named effect card were invisible to the model.

None of this made the data itself uninformative. A read-only pass over the
same held-out decisions found a real, previously invisible seam: the
option a top player actually picked is the *first option within its own
action category* 53 to 72 percent of the time, far above the 33 to 45
percent baseline for "first option in the whole list"
(`analysis/clone_quality.md`, the local-rank diagnosis, all four families).
And the option-0 category distribution on `meta_grimmsnarl` never once
contains `END_TURN` (0 of 13,019), even though ending the turn was the
real played choice 556 of those 13,019 times (4.3 percent), a concrete,
checkable example of a decision the position-only baseline structurally
cannot ever get right no matter how the model is tuned.

## The final answer on the objective itself (U92 step 0, 2026-07-04)

One live hypothesis remained after the autopsy: maybe the *objective*, not
the model family or the feature set, was the reason every attempt copied
position. `tools/rank_clone_killtest.py` rebuilt the U26 pairwise-logistic
RankNet (`analysis/unit_zero_spike.py`'s `PairwiseLinearRanker`, generalized
to read its own feature width instead of a hard-coded 20) and reran it on
the exact same dataset and train/test split the three `tools/train_clone.py`
attempts were gated on, with the full feature set restored (position
features included). A pairwise ranking loss does not have the same
zero-risk shortcut a pointwise classifier does, so this was a genuinely
different test, not a fourth cosmetic variant.

| family | ranker accuracy | first-legal baseline | margin | n scored |
|---|---:|---:|---:|---:|
| meta_archaludon | 0.4439 | 0.4454 | -0.0015 | 1951 |
| meta_grimmsnarl | 0.3956 | 0.3957 | -0.0001 | 11092 |
| meta_grimmsnarl_tonakaiiii | 0.3903 | 0.3903 | +0.0000 | 1299 |
| other | 0.3282 | 0.3296 | -0.0015 | 1353 |

(`analysis/rank_clone_killtest.md`)

Every family still ties first-legal to within 0.0015. This is the fourth
independent way of asking "can a per-decision model beat first-legal on
this dataset" (two model families, two feature-set variants, now a
different objective family), and the fourth time the answer is no. Combined
with the earlier ablation that showed removing the position features
outright makes every model *worse* than first-legal by 4.7 to 6.5 points
(`analysis/clone_quality.md`), the honest conclusion is narrow and final:
on this dataset, with this label scheme, engine list order already carries
more predictive power over top-player MAIN decisions than the full
hand-engineered content feature set does. `tools/train_clone2.py` (a
planned from-scratch rebuild with a groupwise objective) is closed without
being built. This does not mean the data has no learnable structure, only
that per-decision imitation on `imitation_features` is the wrong shape to
find it; the two sections below found real structure by mining *aggregate*
behavior instead of trying to predict single decisions.

## The WHY layer: naming capability gaps before building anything (U90)

`analysis/move_ranking_diverges_ability_gap.md` had already found the
single clearest capability gap in the whole project: over 4,524 real
top-player MAIN decisions, the shipped pilot agreed with the expert's exact
choice 21.2% of the time overall, and ABILITY decisions were a total blind
spot, 0 of 554 (0.0%), because `heuristics.choose` had no code path that
could ever return one. Adding a flag-gated once-per-turn ability branch
(placed after develop steps, before retreat/attack) lifted ABILITY
agreement to 0.139 while leaving EVOLVE (0.570), PLAY (0.263), and ATTACH
(0.060) exactly preserved, and net top-1 agreement rose 0.212 to 0.225.
That lever (`PTCG_ABILITY`) went on to clear an offline gauntlet (+4.0
percentage points, 67.5% to 71.5%, `analysis/ability_ab.md`) and the
calibrated bracket ring (+20.0 points, `analysis/ability_ring_check.md`)
before shipping (see TRACK L, L1, below).

U90 asked a follow-on question in the same spirit: does the engine surface
*on-evolve* abilities (Archaludon ex's Assemble Alloy, card 190; Marnie's
Grimmsnarl ex's Punk Up, card 648) as a distinct trigger class, and does the
shipped pilot's own deck ever reach one? Both cards fire once, at the
moment they are played from hand to evolve something, a different shape
from the repeatable or once-per-turn actives the heuristic already
recognizes. `agents/card_effects.py` gained an additive `ON_EVOLVE_TRIGGER`
tag that catches both. The pilot-facing answer was a clean negative: the
shipped king (`decks/trolley.csv`) and its sibling (`decks/trolley_thick.csv`)
only evolve Snover into Mega Abomasnow ex, which carries no effect text at
all, so `ON_EVOLVE_TRIGGER` never fires against our own deck. That is a
deck-design gap, not a heuristic-logic one, and it is recorded so a future
deck change does not have to re-derive it (`analysis/on_evolve_probe.md`).
The same pass closed the meta-deck tag-coverage gap it was piggybacked on:
`meta_archaludon` 10/15 to 15/15 cards tagged, `meta_grimmsnarl` 15/19 to
19/19, pool-wide untagged fraction 0.4917 to 0.4204.

## The playbooks: mining winners vs losers with two honesty gates (U91)

U91 went back to an earlier refuted claim, `gameplan_seeds_diffuse`
("mining top decks for concentrated always-do-X seeds comes back nearly
empty"), and found its own re-test condition had never actually been met:
the miner had two real bugs, not a diffuse signal. `analysis/replay_trace.py`
resolved ATTACH options by reading which energy card was spent, not which
Pokemon received it, and PLAY options carry no `area` key at all, so
`play_target` resolved at exactly 0.000 for every family, structurally
barred, before any conclusion about diffuseness could even be reached
(`analysis/gameplan_target_resolution_fixed.md`). Fixing both resolvers
(mirroring the shipped pilot's own already-correct `_attach_slot_card_id`
and `play_card_id`) and validating on `bracket_4` (n=1,500 episodes) moved
`attach_target` from 0.285-0.470 to 1.000 and `play_target` from 0.000 to
1.000.

With working resolvers, `analysis/gameplan_claim_gate.py` mined three new
within-turn behavior blocks and put each through two gates before trusting
it: a **claim gate** (>=200 observations per side, bootstrap 90% confidence
interval on the win-minus-loss gap excluding zero) and a **prediction
gate** (the pattern, mined on the KD4 train split only, must replicate on
the untouched KD4 test split). Full results on `bracket_4`
(`analysis/gameplan_claims_bracket_4.md`):

| block | n (win/loss) | win rate | loss rate | claim gate CI | verdict |
|---|---|---:|---:|---|---|
| attach_before_attack | 1472/1446 | 0.524 | 0.558 | (-0.064, -0.003) | CONFIRMED |
| energy_banking | 1822/1892 | 0.192 | 0.236 | (-0.066, -0.022) | CONFIRMED |
| game_length_turns | 1561/1695 | 1.905 turns | 1.972 turns | (-0.145, 0.014) | CUT (straddles zero) |

Both confirmed blocks replicated on 473 to 591 held-out test-split turns
the pattern was never mined from. The direction is small but consistent:
winning play attaches before attacking 3.4 points less often than losing
play, and banks energy (attaches with no attack that same turn) 4.4 points
less often. Both are explicitly flagged as descriptive, not yet
prescriptive: correlation in the mined data does not by itself prove that
nudging the pilot toward the winning-side behavior makes it win more, since
bracket_4 opponents who bank energy less may simply already be ahead on
board for unrelated reasons. That is exactly the question U93 was scoped to
answer with a real A/B rather than by porting the correlation directly.

## Transfer to the shipped pilot: a real lever, gated twice before it can spend a ladder slot (U93)

`agents/heuristics.py`'s shipped default always attaches first whenever an
attach option is legal, over-attaching relative to *both* cohorts in the
mined data, not just the losing one. U93 built the literal rule the mined
gap names: `_resolve_attack_first`, gated behind `PTCG_ATTACK_FIRST`
(default off, byte-identical unset), takes an already-legal positive-value
attack instead of a discretionary attach when no further attach is needed
to unlock it.

Before spending any offline compute on an A/B, the same "can-fire is not
matters" discipline used for the project's other sequencing levers
(`measure_energy_seq.py`, `measure_bench_dig.py`) checked whether the rule
changes real decisions at all: `tools/measure_attack_first.py` captured 20
real mid-game ATTACH-and-ATTACK positions from a trolley heuristic-vs-random
match; 8 of the 20 had a positive-value attack already on the table, and
the rule flipped the end-to-end pilot decision on 3 of those 20 (37.5% of
the live positions), confirming the lever is live, not inert
(`analysis/attack_first_flip_check.md`).

With liveness confirmed, both required offline gates passed:

| gate | off | on | diff | source |
|---|---:|---:|---:|---|
| weak-bot gauntlet, 200 games/arm | 71.5% (143/57) | 77.0% (154/46) | +5.5pp | `analysis/attack_first_ab.md` |
| calibrated bracket ring, 20 games/arm | 75.0% | 85.0% | +10.0pp | `analysis/attack_first_ring_check.md` |

Both agree in direction. The build (`submission_trolley_attack_first.tar.gz`)
is grader-verified (`tests/test_grader_submission.py`, both the in-process
and extracted-tarball paths) and pre-registered
(`heuristic+trolley-attack_first`, direction up, margin 60, N=30,
settle-by 2026-07-11, `state/current.md`). It is staged, not yet
submitted, because both scored ladder slots were occupied when it cleared
its gates; TRACK L's standing rule is to submit it the instant either
tracked build settles.

## The claims ledger

Every number in this chapter, one row per claim, cites the committed
analysis file (or test) that produced it. `tests/test_comprehension_writeup.py`
parses this table mechanically and asserts every cited path exists in the
repository, so a future edit that renames or removes a source file fails a
test instead of silently leaving a dangling claim.

| claim | number | source |
|---|---|---|
| Three per-decision clone attempts collapse to first-legal | 100% top-1==option0 on 13019/13019 held-out decisions (meta_grimmsnarl) | `analysis/clone_quality.md` |
| Local-rank-within-category seam exists but is never used by either model | 53-72% local-rank-0 vs 33-45% global first-legal, all 4 families | `analysis/clone_quality.md` |
| Removing position features makes every model worse than first-legal | margin -0.0470 to -0.0650 across 4 families | `analysis/clone_quality.md` |
| END_TURN is invisible to a position-only baseline but is a real choice | 0/13019 at option-0, 556/13019 (4.3%) actually played | `analysis/clone_quality.md` |
| Pairwise-RankNet kill test still ties first-legal | margin -0.0015 to +0.0000, n=1299-11092 per family | `analysis/rank_clone_killtest.md` |
| Ability is a total capability blind spot | 0/554 (0.0%) agreement, 21.2% overall top-1 agreement | `analysis/move_ranking_diverges_ability_gap.md` |
| PTCG_ABILITY lifts ABILITY agreement without regressing develop steps | 0.000 to 0.139 ABILITY, 0.212 to 0.225 overall | `analysis/move_ranking_diverges_ability_gap.md` |
| PTCG_ABILITY offline gauntlet gate | 67.5% to 71.5%, +4.0pp | `analysis/ability_ab.md` |
| PTCG_ABILITY bracket-ring gate | +20.0pp, agrees in direction | `analysis/ability_ring_check.md` |
| On-evolve engine cards named but absent from the shipped deck | Archaludon ex (190) / Grimmsnarl ex (648) on-evolve; trolley/trolley_thick evolve line has no effect text | `analysis/on_evolve_probe.md` |
| Meta-deck tag coverage closed to 100% | archaludon 10/15 to 15/15, grimmsnarl 15/19 to 19/19, pool untagged 0.4917 to 0.4204 | `analysis/on_evolve_probe.md` |
| Game-plan miner target resolution was structurally broken, then fixed | attach_target 0.285-0.470 to 1.000, play_target 0.000 to 1.000 (bracket_4, n=1500) | `analysis/gameplan_target_resolution_fixed.md` |
| attach_before_attack confirmed (both gates) | win 0.524 vs loss 0.558, CI (-0.064,-0.003), n=1472/1446 | `analysis/gameplan_claims_bracket_4.md` |
| energy_banking confirmed (both gates) | win 0.192 vs loss 0.236, CI (-0.066,-0.022), n=1822/1892 | `analysis/gameplan_claims_bracket_4.md` |
| game_length_turns cut (claim gate fails) | CI (-0.145, 0.014) straddles zero | `analysis/gameplan_claims_bracket_4.md` |
| PTCG_ATTACK_FIRST confirmed live, not inert | 3/20 real positions flipped (8/20 had a positive-value attack) | `analysis/attack_first_flip_check.md` |
| PTCG_ATTACK_FIRST offline gauntlet gate | 71.5% to 77.0%, +5.5pp | `analysis/attack_first_ab.md` |
| PTCG_ATTACK_FIRST bracket-ring gate | 75.0% to 85.0%, +10.0pp | `analysis/attack_first_ring_check.md` |
| PTCG_ATTACK_FIRST pre-registered, staged, not yet submitted | M=60, N=30, settle-by 2026-07-11 | `state/current.md` |

## Bottom line for the Strategy prize

The differentiated story here is not "we found a lever," it is the shape of
the investigation that found it. A recorded negative result was not
accepted at face value: it was re-examined for an instrument defect,
the defect was named and fixed at the mining-tool level (two real bugs in
`analysis/replay_trace.py`, not a new model), and the same discipline that
gates every ladder candidate in this project (a claim gate against sampling
noise, a prediction gate against overfitting to the mining split, an
offline gauntlet, and an independently calibrated bracket ring) was applied
before any of it touched the shipped agent. In parallel, the original
per-decision imitation question was asked one final time with a genuinely
different training objective and got a clean, converged, negative answer,
closing four independent attempts rather than leaving the question open to
be re-tried a fifth time on a hunch. One real, gated, ladder-ready lever
(`PTCG_ATTACK_FIRST`) came out of this track; it is staged and will submit
the instant a slot frees, per TRACK L's standing priority.
