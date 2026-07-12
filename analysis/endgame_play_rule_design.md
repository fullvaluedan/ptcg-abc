# Endgame PLAY rule design: PTCG_ENDGAME_PLAY (plan S2 follow-on)

Designed from `analysis/endgame_divergence.md` (the near-endgame PLAY-category
divergence at scale: 26326 scorable decisions, near-endgame PLAY agreement 26.9%
= 718/2667, overall PLAY 32.6%). No em or en dashes anywhere in this file.

This document specifies ONE flag-gated rule, its exact observable trigger, the
exact change to `agents/heuristics.py` `choose()`'s resolver ladder, the divergence
counts that support it, what it deliberately does NOT cover, its interaction with
every existing lever, and a pre-registered gate (with the mandatory U105
fires-vs-inert precheck) that must clear before any ring compute is spent.

---

## 1. The divergence, split into two clusters

The top-10 near-endgame PLAY divergence patterns (`endgame_divergence.md`, table
"Top near-endgame PLAY divergence patterns") are NOT one phenomenon. They split
cleanly by our pilot's chosen alternative and, critically, by hand size:

### Cluster A: EVOLVE-instead (the rule's target)

Expert PLAYed a draw/search/setup trainer; our pilot would EVOLVE Dudunsparce.
Every one of these has a LARGE hand.

| # | expert did | count | hand (median) | bench | prizes us/opp | deck |
|---|---|---|---|---|---|---|
| 1 | PLAY Hilda | 45 | 19 | 2 | 2/1 | 2 |
| 2 | PLAY Buddy-Buddy Poffin | 34 | 13.5 | 3 | 3/2 | 6 |
| 4 | PLAY Dunsparce | 30 | 11.5 | 2.5 | 2/2 | 2 |
| 5 | PLAY Dawn | 26 | 14.0 | 3 | 2/2 | 8 |
| 7 | PLAY Boss's Orders | 22 | 16.5 | 4 | 3/2 | 7.5 |
| 9 | PLAY Poke Pad | 19 | 17 | 4 | 3/2 | 9 |

**Cluster A total: 176 decisions.** Hand median range 11.5 to 19. All six are the
identical pilot answer (EVOLVE Dudunsparce) losing to a hand-deployment PLAY.

### Cluster B: ATTACK-instead (deliberately NOT covered, see section 4)

Expert PLAYed a trainer; our pilot would ATTACK Shadow Bullet. Every one has a
SMALL hand.

| # | expert did | count | hand (median) | bench | prizes us/opp | deck |
|---|---|---|---|---|---|---|
| 3 | PLAY Lillie's Determination | 34 | 7.0 | 4 | 3/2 | 13 |
| 6 | PLAY Boss's Orders | 24 | 6.0 | 4 | 2.5/2 | 19.5 |
| 8 | PLAY Night Stretcher | 19 | 6 | 5 | 3/2 | 17 |
| 10 | PLAY Dawn | 18 | 6.0 | 5 | 2/4 | 18 |

**Cluster B total: 95 decisions.** Hand median 6 to 7.

The two clusters are linearly separable on hand size alone: Cluster A minimum
median 11.5, Cluster B maximum median 7.0. A hand threshold anywhere in (7, 11.5)
splits them; this rule uses 10 (section 3).

---

## 2. Why Cluster A is the largest coherent slice, and why the pilot is wrong there

Near-endgame PLAY has 1949 total disagreements (2667 decisions, 718 agree). Cluster
A's 176 decisions are 9.0% of that disagreement mass and, more importantly, are the
single largest HOMOGENEOUS sub-slice in the ranked evidence: six of the top nine
patterns, one identical pilot answer, one identical state fingerprint (large hand,
near-endgame, a draw/setup trainer on offer). No other coherent group in the top-10
is as large (Cluster B is 95 and is itself heterogeneous, see section 4).

Why the pilot's EVOLVE is the wrong pick in this state, mechanically:

- The pilot evolves because `_resolve_evolve` sits at `PRIO_EVOLVE = 5.0`, ABOVE
  `_resolve_play` at `PRIO_PLAY = 4.0` (`agents/heuristics.py` ladder, L1320-1329).
  So whenever an EVOLVE and a PLAY are both legal, EVOLVE always wins.
- With a 15-plus-card hand two prizes from the end, the field's top players spend
  the hand: they PLAY the draw/search/gust engine (Hilda, Poffin, Dawn, Poke Pad,
  Boss's Orders) to convert a bloated hand into board position and the exact prizes
  they need, and they defer a discretionary evolution (Dudunsparce is a shared
  draw-engine evolution, not a finisher) to later in the same turn.
- The change is a within-turn REORDER, not a cancellation. PLAY and EVOLVE are both
  legal on every MAIN decision of the turn (neither is once-per-turn at the engine
  level for these options), so playing the trainer first and evolving on a later
  decision the same turn keeps BOTH actions. As the hand is spent it drops below the
  threshold and EVOLVE returns to its normal `PRIO_EVOLVE = 5.0` priority. The rule
  changes sequence, it does not skip the evolution.

That within-turn-reorder property is what makes the rule low-risk on decks where the
evolution IS the finisher (see the transfer-validity risk, section 7).

---

## 3. The rule: PTCG_ENDGAME_PLAY

### Master flag

```python
# Endgame PLAY-priority correction (PTCG_ENDGAME_PLAY, default off). In the
# near-endgame with a bloated hand, demote the discretionary EVOLVE below PLAY so
# the pilot spends its hand (draw/search/gust trainers) before committing a
# non-finisher evolution, matching the field's top players (176 near-endgame PLAY
# divergences, analysis/endgame_play_rule_design.md cluster A). Flag-gated for A/B
# validation; default off keeps every shipped build byte-identical.
_ENDGAME_PLAY = os.environ.get("PTCG_ENDGAME_PLAY", "0") != "0"

# Hand size at or above which the endgame-play demotion engages. Cluster A's hand
# medians run 11.5 to 19; cluster B (ATTACK-instead, NOT this rule's target) runs
# 6 to 7. 10 sits in the separating gap. CEM-tunable (PTCG_W_ENDGAME_HAND).
ENDGAME_HAND = _env_num("PTCG_W_ENDGAME_HAND", 10, int)
```

### Exact observable trigger (obs only, no archetype detection)

The demotion fires on a MAIN decision when ALL of:

1. `_ENDGAME_PLAY` is on.
2. **Near-endgame:** `min(_our_prize_count(obs), _opp_prize_count(obs)) <= 2`.
   This is the exact `near_endgame` definition `endgame_divergence.md` uses ("either
   side at or below 2 prizes remaining"). `_our_prize_count` already exists;
   `_opp_prize_count` is its mirror on `players[1 - yi]` (a one-function add reading
   the public prize-pile length, no new observation surface).
3. **Bloated hand:** `len(me.get("hand") or []) >= ENDGAME_HAND` (default 10).
4. **Both categories legal:** `OPT_PLAY in groups and OPT_EVOLVE in groups`.
   (If either is absent the reorder is a no-op, so gating on it keeps the rule
   provably inert outside its target state.)

No turn counter, deck count, or bench count is in the trigger: hand size alone
separates cluster A from cluster B, and adding conditions the evidence does not
require would only shrink coverage (ponytail: the minimal trigger that separates
the clusters).

### Exact behavioral change in the resolver ladder

`choose()` builds a `ladder` tuple of `(priority, tiebreak, resolver)` and takes the
highest-priority resolver that returns a legal index (`agents/heuristics.py`
L1319-1333). The only change: when the trigger fires, the EVOLVE entry's priority is
lowered from `PRIO_EVOLVE` to `PRIO_PLAY - 0.5`, with a tiebreak of `2.1`:

```python
# default (flag off or trigger absent): (PRIO_EVOLVE, 1, _resolve_evolve)
_endgame_play_fires = (
    _ENDGAME_PLAY
    and OPT_PLAY in groups
    and OPT_EVOLVE in groups
    and (len(me.get("hand") or []) >= ENDGAME_HAND)
    and min(_our_prize_count(obs), _opp_prize_count(obs)) <= 2
)
_evolve_prio = (PRIO_PLAY - 0.5) if _endgame_play_fires else PRIO_EVOLVE
_evolve_tb = 2.1 if _endgame_play_fires else 1
...
ladder = (
    (PRIO_CANDY,        0,          _resolve_candy),
    (_evolve_prio,      _evolve_tb, _resolve_evolve),   # <-- only this entry changes
    (PRIO_PLAY,         2,          _resolve_play),
    (PRIO_ATTACH + 0.5, 2.5,        _resolve_attack_first),
    (PRIO_ATTACH,       3,          _resolve_attach),
    (PRIO_ABILITY,      4,          _resolve_ability),
    (PRIO_RETREAT,      5,          _resolve_retreat),
    (PRIO_ATTACK,       6,          _resolve_attack),
)
```

At shipped defaults this makes the fired ordering: candy(6.0) -> play(4.0) ->
evolve(3.5) -> attack_first(3.5) -> attach(3.0) -> ability(2.0) -> retreat(1.0) ->
attack(0.0). Play now precedes evolve; evolve stays ABOVE attach/ability/retreat/
attack, so if no PLAY resolver yields a move (for example the near-deckout PLAY VETO
declines every play) the evolution still fires this decision. Flag off, `_evolve_prio
== PRIO_EVOLVE` and the tuple is byte-identical to today's.

**Placement relative to the lethal FORCE and the guards:**

- **Below L1 (lethal FORCE), unconditionally.** The `if lethal: return [ba[0]]`
  short-circuit at L1240-1242 runs BEFORE the ladder is ever built, so a guaranteed
  knockout is still taken first and this rule can never override it. This is
  deliberate and is exactly why cluster B (the ATTACK-instead lethal preemptions) is
  out of scope, section 4.
- **Never RAISES evolve.** `PRIO_PLAY - 0.5 < PRIO_EVOLVE` at defaults; the rule can
  only lower evolve below play, never promote it, so it cannot reorder evolve above
  Rare Candy (CANDY stays 6.0) or invert any guard.
- **The three safety guards (L1 lethal, L2 ability-loop, L3 deckout) are untouched.**
  L2 lives inside `_resolve_ability`, L3 inside `choose_play`/`cap_count_for_deckout`;
  neither is reordered. `tests/test_safety.py`'s scorer-independent locks still hold
  because the rule only shuffles two strategic (non-safety) priorities.

---

## 4. What the rule deliberately does NOT cover

- **Cluster B (ATTACK-instead, 95 decisions, patterns 3/6/8/10).** These are the
  pilot's L1 lethal FORCE (or lowest-priority attack) firing while the expert PLAYs a
  trainer first: Boss's Orders to redirect the knockout to a higher-value target,
  Night Stretcher to recover a piece, Lillie's Determination / Dawn to refuel before
  attacking. Fixing them would require (a) touching the locked L1 lethal guard, which
  `tests/test_safety.py` pins scorer-independent, and (b) modeling that a trainer
  redirects or improves a knockout the pilot's static damage calc cannot see. They
  are also heterogeneous: four different trainers serving four different pre-attack
  purposes, no single reorder captures them. This is the exact "hoist lethal-seeking
  above develop actions, a new implementation not a flag flip" redesign that
  `beat_the_meta_plan.md` section 3 (T1) and `analysis/u105_threat_prize_inert_check.md`
  already scoped OUT. Out of scope here for the same reason.

- **The remaining 638 distinct near-endgame PLAY patterns below the top 10.** The
  divergence doc reports 648 distinct (expert card, our choice) patterns; the long
  tail is by construction low-count and heterogeneous. Tuning to it violates the
  small-n discipline (`beat_the_meta_plan.md` section 5).

- **Exact-index recovery is not promised.** Agreement is exact-option-index. When the
  rule flips the pilot from EVOLVE to PLAY, `_resolve_play` picks `choose_play`'s
  target (bench-a-Basic when thin, else `play_opts[0]`), which is not guaranteed to be
  the expert's exact trainer index. The rule closes the CATEGORY error (evolve when
  the expert played); the residual within-PLAY index error is a separate, smaller
  problem. This is why the gate is win-rate, not agreement (section 6): the design is
  motivated by the agreement divergence but adjudicated on whether the behavior wins.

---

## 5. Interaction with every existing lever

- **L1 lethal FORCE.** Untouched; runs before the ladder. Rule can never fire when a
  lethal exists (the ladder is not even consulted). Cluster B stays L1's domain.
- **`_ABILITY` (L2 ability-loop VETO / `_resolve_ability`).** Ability sits at
  `PRIO_ABILITY = 2.0`, below the demoted evolve (3.5). Demoting evolve never crosses
  ability, so no interaction; if both flags are on, play still precedes evolve
  precedes ability. The loop-safety VETO is independent of priority.
- **`_THREAT_RETREAT` (`should_retreat`, `_resolve_retreat` at 1.0).** Retreat is far
  below the demoted evolve; no ordering interaction. The two levers touch disjoint
  categories (retreat vs evolve/play). The plan's T3 correction (default threat_retreat
  OFF on the high band) is orthogonal; PTCG_ENDGAME_PLAY should be A/B'd with the
  same flag stack the high-band incumbent ships (see the gate's "identical config"
  clause, section 6).
- **Deckout guards (L3: `DRAW_CONSERVE_THRESHOLD` in `choose_play`,
  `DECKOUT_THRESHOLD` in `cap_count_for_deckout`).** Near a self-deckout `_resolve_play`
  may return None (only drilling plays remain). Because the demoted evolve (3.5) still
  sits above attach/ability/retreat/attack, the evolution correctly still fires when
  the deckout VETO declines the play. So the rule and the deckout guard compose: play
  if the deckout guard allows it, else evolve, exactly as intended. No conflict.
- **THIN_BENCH (L4 thin-bench FORCE, inside `choose_play` and `_resolve_candy`).**
  Cluster A's benches are 2 to 4 (`THIN_BENCH = 2` means thin only at bench 0 or 1),
  so the rule's typical state is NOT thin. When it IS thin, demoting evolve below play
  is if anything BETTER: `choose_play`'s thin-bench branch benches a Basic first,
  which is the higher-priority `early_collapse` defense, and evolve still follows. The
  levers reinforce. Note `_resolve_candy` (Rare Candy) is itself gated on
  `not _bench_is_thin`, unchanged.
- **Rare Candy FORCE (L5, `_resolve_candy` at CANDY 6.0).** Stays strictly above both
  play and the demoted evolve. Rare Candy (a Stage-2 accelerator the expert also
  plays) is never deferred by this rule. Correct.
- **CEM PRIO_* genome.** The demotion is expressed as `PRIO_PLAY - 0.5`, RELATIVE to
  the tuned play weight, so a CEM-tuned vector keeps evolve just below whatever play
  is tuned to. It never hard-codes an absolute that a tuned genome could invert. The
  drift test that pairs defaults with `weight_space.PARAM_SPACE` is unaffected (no new
  PRIO_* entry; `ENDGAME_HAND` is a threshold knob like `THIN_BENCH`).

---

## 6. Pre-registered gate

All three steps below are pre-registered. The fires-vs-inert precheck runs FIRST and
BEFORE any ring compute (the U105 lesson: a zero from a subsumed or broken probe is
indistinguishable from a zero from a good probe, so the flag MUST be shown to flip a
real decision on the target deck before spending ring games on it).

### Step 0 (mandatory, near-instant): fires-vs-inert with a positive control

Before any ring run, on `decks/candidate_yushin_ito` (the ring deck), capture MAIN
decisions across a handful of self-play or replay games and count, per decision:

- **Fires:** trigger true (near-endgame, hand >= `ENDGAME_HAND`, both OPT_PLAY and
  OPT_EVOLVE legal).
- **Flips:** `choose(obs)` with `_ENDGAME_PLAY` off returns an EVOLVE index AND with
  `_ENDGAME_PLAY` on returns a PLAY index, on the identical obs (patch the module
  attribute in-process, restore in a finally, exactly as
  `tools/threat_retreat_ring_check._make_agent_factory` does; the flag is read from a
  module attribute at call time via the ladder, so patch `H._ENDGAME_PLAY`, never the
  env at runtime).

**Positive control (the U105 guard against a broken probe):** hand-construct one obs
in the target state (our prizes = 2, a legal OPT_EVOLVE option, a legal OPT_PLAY
option, hand of 12 cards) and assert `choose` flips EVOLVE -> PLAY when the flag is
toggled. If the control does not flip, the probe is broken and any ring zero is
uninterpretable; fix the probe before proceeding.

**Kill:** if flips == 0 on yushin across the captured decisions (and the positive
control DID flip, proving the probe works), the lever is inert on the ring deck the
same way `PTCG_PRIZE_CLOSE` was (`analysis/u105_threat_prize_inert_check.md`). Do NOT
spend ring compute; record the honest inert result and stop. Note yushin runs
Staryu -> Mega Starmie ex, not Dudunsparce, so this precheck is also the test of
whether the cross-deck-motivated rule fires AT ALL on the ring deck.

### Step 1 (primary): +5pp on the top-50 elite ring at n=100, same-run

Run a same-run alternating-seat A/B on the top-50 high-band ring
(`tools/top50_ring.py` / `tools/threat_retreat_ring_check._ring_win_rate` over
`opponents.top50_clone_names()`), n=100 per arm, both arms the identical config
(same `_ABILITY` / `_THREAT_RETREAT` stack the high-band incumbent ships) EXCEPT
`_ENDGAME_PLAY`: off vs on. Build the two arms by extending the existing
`_make_agent_factory` monkeypatch pattern to also pin `_ENDGAME_PLAY` per arm.

**PASS:** `on_win_rate - off_win_rate > +5.0pp` (strictly greater; at the margin is
not a pass). At ~1.7 to 1.9 games/s this A/B is 200 games, roughly 2 minutes.

### Step 2 (regression guard): no worse than -2pp on the calibrated ring at n=50

Same on-vs-off A/B against the calibrated bracket ring (`tools/ring_calibrate.py`
`ring_names()`), n=50 per arm, same-run.

**Kill:** `on_win_rate - off_win_rate < -2.0pp` on the calibrated ring FAILS the rule
even if Step 1 passes (the "wins the high band, wrecks the saturated ring" guard).

### Promotion

Ship `_ENDGAME_PLAY` default ON (and, if `ENDGAME_HAND` matters, A/B 8 vs 10 vs 12 as
a follow-on) ONLY when Step 0 flips > 0 with a passing positive control, Step 1 is
`> +5.0pp`, AND Step 2 is `>= -2.0pp`. Any one miss keeps the flag default off and
the shipped build byte-identical.

---

## 7. Risks

- **Transfer validity (the headline risk).** The 176-decision evidence comes from
  EXPERT decks that run Dudunsparce as a shared, non-finisher draw engine, where
  deferring its evolution to spend the hand is clearly right. The ring is piloted on
  `candidate_yushin_ito`, whose evolution (Staryu -> Mega Starmie ex) IS the win
  condition. Demoting THAT evolution below trainer plays could delay the attacker and
  cost tempo. Mitigations, in order of strength: (a) the change is a within-turn
  REORDER, not a skip (section 2), so the mega still evolves the same turn once the
  hand is spent below threshold; (b) Step 0 measures whether the rule even fires on
  yushin and Step 1 measures whether it wins there; (c) Step 2 guards the saturated
  ring. The gate, not the intuition, adjudicates; a negative Step 1 is a clean,
  cheap kill.
- **Probe subsumption (U105).** As with `PTCG_PRIZE_CLOSE`, the rule could be inert on
  the ring deck if yushin rarely reaches near-endgame with a 10-plus hand and both
  categories legal. Step 0's fires count with a positive control catches this before
  any ring spend.
- **Exact-index residue.** Flipping to PLAY does not guarantee the expert's exact
  trainer index (section 4), so agreement recovery will be partial even where win-rate
  improves. Acceptable: the gate is win-rate, and the category error is the larger,
  more coherent one.
- **Threshold brittleness.** 10 is chosen from cluster medians, not per-occurrence
  distributions; individual cluster-A decisions below 10 or cluster-B decisions above
  7 exist. `ENDGAME_HAND` is CEM-tunable so the boundary can be swept if Step 1 is
  marginal, but the shipped default sits in a wide separating gap (7 to 11.5).
- **`_opp_prize_count` add.** A one-function mirror of `_our_prize_count` on the
  opponent seat; the opponent prize-pile length is public, so no hidden-information
  assumption. Defensive-return 0 on a degenerate obs, same contract as the existing
  helper, which makes the trigger fail-closed (0 <= 2 is true, so a degenerate obs
  would let it fire; guard the min against a None/absent seat by treating a missing
  count as large, i.e. not near-endgame, to fail-closed toward inert).
