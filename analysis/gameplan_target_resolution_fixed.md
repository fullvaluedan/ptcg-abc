# Game-plan miner target resolution fix (U91, step 1 of the comprehension track)

## The bug (root-caused directly against the shipped pilot and a real replay)

`analysis/gameplan_mine.py` mines `attach_target` and `play_target` blocks by
reading `card_id` off `analysis/replay_trace.resolve_option`, which routed both
through the generic `option_card_id` (area + index lookup). Two distinct bugs
followed from that, confirmed against `data/replays/82976189.json` and against
`agents/heuristics.py`'s own (already-correct) resolvers:

- **ATTACH**: a real ATTACH option carries BOTH which energy card is spent
  (`area`/`index`, pointing into hand) AND which in-play Pokemon receives it
  (`inPlayArea`/`inPlayIndex`, separate keys). `option_card_id` only ever read
  the first half, so `attach_target` was mining "which energy type did the
  expert attach" (rarely useful, decks run 1-2 energy types) instead of "which
  attacker did the expert power up" (the actual game-plan question, and
  exactly what the shipped pilot's `_attach_slot_card_id`,
  `agents/heuristics.py:512-528`, already reads for its own seeded-attach
  consumer).
- **PLAY**: a real PLAY option carries `{"type": 7, "index": N}` with **no
  `area` key at all**. `option_card_id` requires `area` to route to a zone, so
  it fell through to `None` on every single PLAY option. The shipped pilot's
  own `play_card_id` (`agents/heuristics.py:764-777`) already documents this
  exact gap ("carries a hand index (and no area), so the generic
  option_card_id ... cannot resolve it") and reads the hand index directly
  instead. The miner never used that resolver.

Net effect on the two families mined at 5732-episode scale on 2026-07-02
(`analysis/gameplans/meta_archaludon_gameplan.md`,
`analysis/gameplans/meta_grimmsnarl_gameplan.md`, both barred/diffuse,
`gameplan_seeds_diffuse` in `state/hypotheses.md`): `play_target` resolved at
**0.000** for both families (100% unresolved, structurally barred), and
`attach_target` resolved at only 0.470 / 0.285 (mining the wrong half of the
option). Both were named blockers in that refutation's own re-test condition.

## The fix

`analysis/replay_trace.py`: added `attach_receiver_id` (mirrors
`_attach_slot_card_id`: active ignores `inPlayIndex`, bench indexes it) and
`play_hand_card_id` (mirrors `play_card_id`: reads `index` straight against the
deciding player's hand, no `area` needed). `resolve_option` now dispatches by
category: ATTACH uses `attach_receiver_id`, PLAY uses `play_hand_card_id`,
everything else keeps `option_card_id`. Both new resolvers are pure and
cg-free like the rest of the spine (no card engine import). 11 new tests in
`tests/test_replay_trace.py`; 2 pre-existing tests in `tests/test_gameplan_mine.py`
that had pinned the OLD (buggy) ATTACH semantics were updated to the real
option schema. Full suite: 1090 passed (was 1084).

## Real-data validation

The two originally-mined families (`meta_archaludon`, `meta_grimmsnarl`) no
longer classify any decks in the 2026-06-30 dataset under the CURRENT
`decks/` directory: `tools.expert_census.build_signatures('decks')` now also
loads the L5 bracket ring's `bracket_1..6` archetype csvs (added 2026-07-03,
after this dataset was mined), and `classify_family`'s tie-break (first name
alphabetically wins a coverage tie, `analysis/expert_cohort.py:140-148`) lets
a `bracket_*` name shadow `meta_archaludon`/`meta_grimmsnarl` whenever a real
deck's coverage of the broader bracket signature is no worse than its
coverage of the exact meta-deck signature. Confirmed directly: a 100-episode
sample classified into `bracket_1` through `bracket_6` plus a couple of
`meta_grimmsnarl`, zero `meta_archaludon`. This is a real, separate,
pre-existing tooling gap (a namespace collision between two independently-built
archetype registries), not something this fix caused or should paper over; it
blocks a like-for-like re-mine of the original two named families until
resolved (candidate fix for whoever picks this up: scope
`build_signatures`/`classify_family` calls to the exact decks intended, or
break coverage ties by signature specificity instead of name).

To validate the resolver fix itself on real data without waiting on that,
`bracket_4` (well represented in the 2026-06-30 dataset, 642 winning / 707
losing appearances in a 1500-episode slice) was mined instead:

| block | resolution before (typical) | resolution after (bracket_4, n=1500 episodes) |
| --- | --- | --- |
| attach_target | 0.285-0.470 | 1.000 |
| play_target | 0.000 (barred) | 1.000 |
| evolve_target | 0.489-0.875 (unaffected) | 0.908 |

Both previously-broken blocks now resolve fully. `attach_target` modes to card
190 at 0.319 share and `play_target` to card 1227 at 0.139 share, both under
the 0.70 emission bar on this slice, so this run does not itself emit a seed;
the point of this run was only to confirm the resolver fix, not to re-run the
full U36/U37 seed emission pipeline (that is the next step, on the family the
resolver fix actually unblocks).

## Status and next step

`gameplan_seeds_diffuse`'s named re-test condition ("play_target re-tests only
after the PLAY resolver in analysis/replay_trace exposes the placed card id")
is now MET at the resolver level. The remaining U91 work (per LOOP_BRIEF L8):
re-mine a real target family end-to-end with the fixed resolvers (either fix
the archetype-registry shadowing so meta_archaludon/meta_grimmsnarl classify
again, or adopt one of the bracket families as the mining target going
forward, since those are the deck pool the pilot actually faces per L5), then
mine within-turn sequencing / energy banking / win-condition timing per family
under the CLAIM GATE (n>=200, bootstrap 90% CI excluding zero) and PREDICTION
GATE (must predict held-out top-player moves or be cut).
