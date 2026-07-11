# Beat-the-meta plan: what cards we use and when we use it (2026-07-11)

Built from three evidence packs and their docs: `analysis/top50_win_mechanisms.md`
(how the field wins), `analysis/top50_loss_modes.md` (how the field loses, with the
predator table), `analysis/top50_ring_baseline.md` (the high-band ring read), plus
`analysis/path_above_1000.md` (the staged plan and its gates) and `findings.md`
section 4B (the closed levers). No em or en dashes anywhere in this file.

**Corrected 2026-07-11 against decontaminated classification.** Both source docs
were regenerated after an independently verified classifier-contamination defect:
`analysis.expert_cohort.classify_family` at its default 0.35 coverage threshold let
generic format staples (Boss's Orders, Buddy-Buddy Poffin, Poke Pad, Lillie's
Determination, Night Stretcher, and others, see `tools/top50_loss_modes.py:STAPLE_CARD_IDS`)
alone clear the bar, pulling unrelated decks into a named archetype's numbers. The
fix strips those staples from the coverage numerator and denominator before scoring
(`tools.top50_loss_modes.decontaminate_signatures`); `analysis/expert_cohort.py`
itself was not edited. The effect was large, not cosmetic: most of what was
labeled `meta_grimmsnarl` (256g) turned out to be an unrelated Alakazam/Dunsparce
deck with none of Marnie's Impidimp / Morgrem / Grimmsnarl ex in it, and 94 of 98
`meta_archaludon`-labeled winning decklists (95.9%) never ran Duraludon or
Archaludon ex at all -- the real dominant line in that bucket is a Crustle /
Superb Scissors and Mega Kangaskhan ex / Rapid-Fire Combo deck (`crustle_dwebble`
below). Every number in this file is sourced from the regenerated docs; where a
regenerated number differs from an earlier hand-run figure, the regenerated
number is the one to trust.

## The one-paragraph thesis

The top-50 field is a grind mirror, though the true "three dominant decks" picture
looks different post-correction. The three biggest CORRECTLY-classified pools are
`abra_alakazam` (252g, the deck previously mislabeled `meta_grimmsnarl`),
`crustle_dwebble` (162g, previously mislabeled `meta_archaludon`), and
`meta_grimmsnarl_tonakaiiii` (132g, down from 175g after removing contaminated
kills); the TRUE `meta_grimmsnarl` (Marnie's Grimmsnarl ex line) and TRUE
`meta_archaludon` (Duraludon / Archaludon ex line) are each much smaller, real
pools (24g and 43g respectively). All of them still beat each other by completing
a prize race in the turn-11-to-22 range, dominant inflicted loss shape `grind_loss`
or `deckout` depending on the matchup (see section 1 below for the corrected
per-archetype breakdown). A thin control tail (`other:Boss's Orders Are All You
Need`, `top50_04_third_ptcg_club`, both unaffected by the classifier fix) wins a
different way: it decks the opponent out at turn 18 to 22 with 0 to 40%
prize-race-complete. Our incumbent, `candidate_yushin_ito`, is a Mega Starmie ex
aggro deck that reaches its first attack at median turn 2.5 and closes wins in 5
turns (win-mechanisms doc, `staryu_mega_starmie_ex` block, unaffected by the fix).
The beat-path is therefore still singular and deck-wide: win the prize race before
the grind matures, and survive our own draw engine so the control tail cannot mill
us first. That is a TIMING problem, not a card problem, and the evidence supports
it even more clearly post-correction: the real archetypes we now see are, if
anything, SLOWER than the contaminated buckets implied (`crustle_dwebble` wins in a
median of 12 turns, not the 9 the old `meta_archaludon` number claimed), so our
5-to-7-turn clock dominates by a wider margin than previously stated. Deck changes
remain a four-times-refuted closed lever (4B), and the loss doc names archetypes
and loss shapes, never a specific predator card our shell lacks.

---

## 1. THE MATCHUP MAP

Kill turns and prize-race-complete rates are from `top50_loss_modes.md`; win
mechanics and prize-take curves from `top50_win_mechanisms.md`. Our clock (prize 1
by turn 4, prize 2 by turn 5, wins in 5 turns) is the `staryu_mega_starmie_ex`
block of the wins doc. "Beat-path" is expressed as observable-state behavior
because in-game archetype detection does not exist (U9a missed its gate); we
cannot key on "opponent is X", only on what their board reveals.

**Timeline reliability caveat.** `top50_win_mechanisms.md` now has a committed
generator (`tools/top50_win_mechanisms.py`), which walks
`analysis.replay_trace.iter_resolved_decisions` to build every per-card and
per-attack timing number below (first-attack turn, "primary attack" wins counts,
prize-take curves, key-card first-play turns). That iterator only yields a
decision with more than one legal option; a turn where an attack is the ONLY
legal action never appears in the stream at all, so every attack-derived number
in this section (first-attack turn, "X is the primary attack" wins counts)
UNDERCOUNTS true attack frequency -- confirmed on episode 85300966, where the
winning seat scored multiple knockouts across the game but zero of its 21
captured decisions were an ATTACK pick. This does NOT undermine the deck
composition or win/loss aggregate numbers in this section (games, W-L, win
rate, coverage by team), which come straight from the harvest's own decklists
and results, never from this decision stream. It DOES mean every turn number
and "played in N wins" attack count below should be read as a directional
lower bound, not an exact play-by-play; treat the RELATIVE ordering between
archetypes (who is faster, who separates on which card) as the reliable
signal, not the absolute counts.

### abra_alakazam (252g field, 42.1% WR) -- NEW: this is what the doc used to call "meta_grimmsnarl"
- This pool was previously reported as `meta_grimmsnarl` (256g, 183 predator
  kills). Decontaminated, it is a completely different deck: an Abra/Kadabra/
  Alakazam attacker on the SAME Dunsparce/Dudunsparce draw engine several
  archetypes share, carrying zero copies of Marnie's Impidimp / Morgrem /
  Grimmsnarl ex. Its own win-mechanism timeline confirms this directly: Kadabra
  (evolved), Alakazam (energy attached to), Hilda, Sacred Ash, Battle Cage --
  never a Grimmsnarl-line card.
- How it wins: Kadabra turn 2, Alakazam turn 3, Powerful Hand (65 wins) as the
  overwhelming primary attack (Super Psy Bolt and Teleportation Attack a distant
  second at 17 wins each); prize 1 at turn 4, prize 5 at turn 7. Median win
  length 6 turns.
- How it loses: `deckout` (per the predator table's own `top50_02_bono_meta_grimmsnarl`
  / `top50_03_ebi_meta_grimmsnarl` / etc. slugs, still legacy-named after the old
  classification -- see `top50_loss_modes.md`'s "Legacy slug-name residue" note)
  and `grind_loss` dominate across its 146 losses; median kill turn in the 12-17
  range depending on pilot.
- Beat-path: same timing logic as the old grimmsnarl entry still applies (our
  clock is faster than its 6-turn win and much faster than its double-digit-turn
  losses): never leave a lethal on the table in the 1-to-2 prize window (rule
  T1). Boss's Orders to pull the un-attacked Dudunsparce still denies its re-load,
  since that draw engine is shared with the real archetypes below too.

### meta_grimmsnarl (CORRECTED: 24g field, 58.3% WR, predator: 29 kills -- the genuine Grimmsnarl ex deck)
- The real Marnie's Grimmsnarl ex deck, formerly conflated with `abra_alakazam` above.
- How it wins: Marnie's Impidimp turn 1 (64% of wins), Munkidori turn 2 (79%),
  Marnie's Grimmsnarl ex turn 3 (86%), Shadow Bullet as its overwhelming primary
  attack (9 of 14 wins). Prize 1 turn 3, prize 5 turn 7. Median win length 7 turns.
- How it loses: only 10 losses harvested (both harvested teams, Yushin Ito and
  ごんさくよねきち, have strong overall records); `grind_loss` (5) then `close_loss`
  (3) lead; median kill turn 12.5.
- Beat-path: unchanged in spirit from the old entry (race it, pull the setup piece
  with Boss's Orders), but this is now a much smaller, thinner slice of the field
  than previously believed -- most of what the plan needs to beat under the old
  "meta_grimmsnarl" label is actually `abra_alakazam` above.

### crustle_dwebble and meta_archaludon (CORRECTED: one contaminated bucket splits into two real archetypes)
- The old `meta_archaludon` entry (196g field, 49.0% WR, predator: 98 kills) was
  contaminated: 94 of its 98 winning decklists (95.9%) never ran Duraludon or
  Archaludon ex at all. Decontaminated, the field splits:
  - **`crustle_dwebble` (162g field, 47.5% WR, the real dominant line, also
    absorbing the old doc's separately-reported `ogerpon_crustle_cornerstone` /
    `ogerpon_crustle_teal` clusters)**: Dwebble turn 1 into Crustle turn 3,
    Superb Scissors as the primary attack (42 of 77 wins), Mega Kangaskhan ex /
    Rapid-Fire Combo (10 wins) and Ascension (16 wins) as secondary lines. Its
    top win/loss separator is still Jumbo Ice Cream, and the earlier doc's
    reading of that card (27% in wins vs 9% in losses) checks out directionally
    on the corrected population too (34% in wins vs 13% in losses here). Prize 3
    not until turn 9; SLOWER than the old contaminated number claimed -- median
    win length 12 turns, not 9.
  - **`meta_archaludon` (43g field, 55.8% WR, the real Duraludon/Archaludon ex
    deck)**: much smaller and FASTER than the old contaminated read implied --
    Duraludon turn 1 (79% of wins), Archaludon ex turn 3 (79%), Metal Defender
    as the primary attack (19 of 24 wins). Median win length 7 turns, not 9.
- How it loses / inflicts: NOT "late_collapse and deckout" as previously
  summarized. Pooling every predator-table entry that carries an
  archaludon-family label (82 kills total, since most of `crustle_dwebble`'s
  wins still surface under a legacy `top50_NN_<team>_meta_archaludon` slug --
  see `top50_loss_modes.md` Method notes), the dominant inflicted shape is
  `deckout` (32) narrowly ahead of `grind_loss` (29), with `late_collapse` (11)
  a clear third; median kill turn 21.
- Beat-path: this is still the matchup our clock most dominates, but the
  ring-read used to justify the urgency was itself wrong. `top50_ring_baseline.md`'s
  three hardest clones (`clone:top50_11_alberto_bonsanto_meta_archaludon`,
  `clone:top50_15_mitomeat823`, `clone:top50_14_fujiborozoukin`) are NOT
  archaludon-family under the corrected classification: `mitomeat823` and
  `fujiborozoukin` are `mega_lucario` pilots (`top50_harvest.md` lines 103-104
  tag both "other"; the win-mechanisms doc lists both under `mega_lucario`), and
  `top50_11_alberto_bonsanto`'s own harvested decklist
  (`decks/top50/top50_11_alberto_bonsanto_meta_archaludon.csv`) carries Crustle /
  Dwebble / Mega Kangaskhan ex with zero copies of Duraludon or Archaludon ex --
  it is `crustle_dwebble` too (verified directly against the decontaminated
  classifier and the raw decklist, beyond what the correction was originally
  scoped to check). NONE of the three hardest clones is the true Duraludon/
  Archaludon ex deck. Deny `crustle_dwebble`'s setup tempo (Crushing Hammer on a
  Pokemon showing 2+ energy before its turn-4 first attack) and close before
  Jumbo Ice Cream stabilizes it around turn 6; the smaller, faster true
  `meta_archaludon` pool is an even more lopsided race in our favor. Do NOT let
  either game reach turn 13-plus where the grind favors them.

### meta_grimmsnarl_tonakaiiii (CORRECTED: 132g field, 38.6% WR, down from 175g/41.1%)
- How it wins: fastest-developing Grimmsnarl variant, unchanged in character from
  the earlier read. Marnie's Impidimp turn 1 (90% of wins), Munkidori turn 1 (88%),
  Shadow Bullet the overwhelming primary attack (50 of 51 wins); Snorunt/Froslass
  tech. Prize 1 turn 4, prize 5 turn 6. Median win length 6 turns.
- How it loses: 81 losses (down from 103 after removing contaminated entries like
  nasuo445's Cynthia's Garchomp ex toolbox and ZETADIVISION's Dragapult ex toolbox,
  both of which used to be misclassified into this bucket's numbers purely on
  staple overlap). `grind_loss` (38) then `close_loss` (33) still lead; median
  kill turn 13. Its own separators still show Snorunt (60% loss vs 39% win) and
  Froslass OVER-represented in its losses: the tech line still slows it down.
- Beat-path: unchanged -- same as `meta_grimmsnarl` but the `close_loss` share
  says these games are decided at the margin, which is exactly where the
  finisher-timing rule (T1) and the "do not fumble tempo by retreating"
  correction (T3) pay off.

### mega_lucario (70g field, 38.6% WR -- unaffected by the classifier fix, same population as before)
- How it wins: fastest clock in the field, prize 1 at turn 3. Solrock/Riolu/Premium
  Power Pro all turn 1, Mega Lucario ex turn 2, Aura Jab (18 wins). Fighting Gong
  is its win separator (48% win vs 33% loss).
- How it loses: CORRECTED -- team-level data across its 3 harvested pilot slugs
  (`top50_06_imanoob1122`, `top50_14_fujiborozoukin`, `top50_15_mitomeat823`, 43
  losses total) shows `grind_loss` dominating (23) with `close_loss` (10) and
  `deckout` (6) ahead of `setup_denied` (only 4, last of the four shapes). It does
  NOT "out-speed itself into setup_denied when the engine misses" as the earlier
  draft claimed; when this archetype loses, it is almost always in an extended,
  traded game it still loses, not a fast setup failure.
- Beat-path: this is a genuine race we can LOSE on raw speed. Mega Starmie ex 330HP
  plus Hero's Cape (+100) plus Wally's Compassion (full heal and recover all energy)
  is the tank answer: survive the first Aura Jab, heal, and win the second exchange.
  No new card needed, the shell already carries it.

### Newly-surfaced pools (previously hidden inside contaminated buckets; none clears the 100+ game bar above)
- `drakloak_dreepy` (33g, 39.4% WR, LumenLiquidity / RtoABC / BigBugginnings): a
  Dragapult ex toolbox, previously blended into `meta_grimmsnarl_tonakaiiii`'s
  contaminated count. Jet Headbutt / Itchy Pollen its attacks; median win 7 turns.
- `okidogi_solrock` (24g, 45.8% WR, S4nkurero / btk15049): an Okidogi ex /
  Solrock line distinct from `mega_lucario`'s Mega Lucario ex build, previously
  hidden inside `abra_alakazam`'s contaminated `meta_grimmsnarl` count.
- `cynthias_gabite_cynthias_gible` (20g, 60% WR, nasuo445): this is the exact
  Cynthia's Garchomp ex toolbox the classifier-contamination defect report names
  as a verified misclassification case (it used to score into
  `meta_grimmsnarl_tonakaiiii` on staple overlap alone). Corkscrew Dive its
  primary attack.
- `ns_zoroark_ex_ns_zorua` (19g, 31.6% WR, shg195): an N's Zoroark ex deck,
  previously hidden inside the contaminated `meta_archaludon` count (shg195's
  deck carried the `top50_21_shg195_meta_archaludon` slug under the old
  classification).
- None of these is large enough on its own to justify a tuned rule (section 5's
  small-n discipline still applies); they are listed here so the matchup map
  stays honest about where the field's mass actually is post-correction, not to
  add new beat-path work.

### team_rocket_toolbox (20g, 60% WR, n=1 team, kashiwashira -- unaffected by the fix)
- Now clustered by the regenerated tool as `team_rockets_spidops_team_rockets_tarountula`.
- How it wins: TR toolbox, Giovanni its separator; median win 9 turns (n=12
  traced), prize 5 not until turn 19. A grind/disruption deck.
- How it loses: n=8 losses only; not characterizable.
- Beat-path: race the slow toolbox. Small-n, do not tune to it.

### mega_starmie (19g, 47.4% WR, n=1 team WinDecks -- unaffected by the fix)
- Now clustered by the regenerated tool as `staryu_mega_starmie_ex`; the old
  `alakazam_dunsparce` entry has folded into `abra_alakazam` above, since it is
  the same deck.
- `mega_starmie` IS our own shell in the field (WinDecks piloting it). Its own
  separators (Staryu, Dusknoir/Dusclops tech, Hilda) confirm the aggro-tank plan
  and that the incumbent list is a real, field-present deck, not a synthetic pick.

### The control tail (the deckout predators, cross-archetype -- unaffected by the fix)
- Neither team here is one of the 50 harvested pilots, so neither is touched by
  the classifier fix.
- `other:Boss's Orders Are All You Need`: 20 kills, 0% prize-race-complete,
  inflicted shape `deckout`, median kill turn 18. It does not race; it mills.
- `top50_04_third_ptcg_club`: 15 kills, `deckout`, median kill turn 22. CORRECTED:
  the "wins with 5.5 prizes still on its side of the board" claim was itself
  top50_04_third_ptcg_club's own LOSS-side stat (its median remaining prizes when
  IT loses), not a winner-side one. On the winner side, when it wins it holds a
  median of 2 prizes remaining (mostly finishing 1-2 short of a clean sweep,
  consistent with a deckout-driven win rather than a prize-race blowout).
- Beat-path: two-sided. (a) Out-clock them: we win by turn 5-7, they need turn 18-22.
  (b) Do not mill OURSELVES first: our Lillie's Determination (draw 6-8), Harlequin,
  and Hilda can self-deck if we keep drilling. The DRAW_CONSERVE guard (deck <= 8,
  already shipped) is the exact defense (rule T2).

---

## 2. OUR CARDS

### Recommendation: NO card swaps. The incumbent is the shell.

`decks/candidate_yushin_ito.csv` validates LEGAL (`tools/deck_validate.py`:
`candidate_yushin_ito.csv: LEGAL`). Decoded via `card_index()`, it is a Mega Starmie
ex aggro-tank deck:

| n | card | role |
|---|---|---|
| 3 | Staryu (1030) / 3 Mega Starmie ex (1031) | attacker line, 330 HP mega |
| 4 | Cinderace (666) | Explosiveness free-set alt attacker / opener |
| 9 | Basic W Energy (3), 4 Ignition Energy (17) | energy |
| 4 | Buddy-Buddy Poffin (1086) | basic search |
| 4 | Mega Signal (1145) / 4 Salvatore (1189) | mega search + free evolve |
| 2 | Hilda (1225) / 4 Lillie's Determination (1227) / 2 Harlequin (1223) | draw/search |
| 4 | Pokegear 3.0 (1122) / 1 Ultra Ball (1121) / 2 Night Stretcher (1097) | consistency/recovery |
| 4 | Crushing Hammer (1120) | energy denial (anti-crustle_dwebble / anti-Archaludon tempo) |
| 4 | Wally's Compassion (1229) | full heal + recover all energy on the mega |
| 1 | Boss's Orders (1182) | gust the un-attacked setup piece / grab last prize |
| 1 | Hero's Cape (1159, ACE SPEC) | +100 HP tank |

Every beat-path in section 1 is already executed by a card in this list: race =
the Mega Starmie clock; tank the Lucario race = Hero's Cape + Wally's Compassion;
deny crustle_dwebble / Archaludon tempo = Crushing Hammer; pull the setup piece =
Boss's Orders; survive our own mill = the shipped DRAW_CONSERVE guard. There is
no beat-path in the loss evidence that names a card this deck lacks.

### Why no swap is evidence-backed (the disciplined negative)

The task permits swaps ONLY where the predator evidence names cards that execute a
beat-path, each swap tied to the games that demonstrate it. That evidence does not
exist at the card level:

1. `top50_loss_modes.md` reports predators as ARCHETYPES and LOSS SHAPES
   (`grind_loss`, `deckout`), never as a specific card we are missing. Its method
   notes are explicit: it deliberately does NOT claim a per-card timeline for the
   winner (the decision-to-option correlation was not reliably resolvable). So no
   swap can be "tied to the games that demonstrate it."
2. Deck changes are a hard-closed lever in `findings.md` 4B with four converging
   negatives: `meta_deck_copy` (the pilot plays meta decks WORSE than the trolley
   floor), `search_active_beats_heuristic`, `clone_imitation_beats_first_legal`
   (four model/objective variants all tie first-legal), and crucially
   `deck_exploration_top_rated_mining`: `candidate_yushin_ito` was the BEST of 11
   mined elite candidates and scored 0.800 vs 0.750 baseline, +0.050, BELOW the
   +0.10 promotion gate. It is the incumbent precisely because nothing beat it, not
   because it cleared a bar.
3. The high-band ring already scores this exact 60-card list at 0.693 (stacked) /
   0.753 (flags-off). A swap would have to clear the S3 n=100 high-band gate
   (>= +10pp) to earn a ladder slot, and the entire deck-search lane that would
   generate candidates is closed. Proposing a swap here would be re-opening a
   refuted lever without new evidence.

Conclusion: the incumbent embodies the best available shell for this pilot. The
lever is timing (section 3), plus one build-flag correction the high-band ring
directly implies (rule T3).

---

## 3. WHEN WE USE IT (timing rules keyed on observable state)

All three key on observation only (our hand/board, prize counts, deck count,
opponent's REVEALED active), never on a guessed opponent archetype. Each is a
flag-lever candidate that already exists or is a one-flag addition, each must pass
the S3 gate (category-agreement improvement AND >= +10pp on the high-band ring at
n=100) before any ladder slot.

### T1. Finisher timing: never fumble the 1-to-2 prize window
- Lever: `PTCG_PRIZE_CLOSE` (exists, default off; `agents/heuristics.py` `_resolve_attack`).
- Observable trigger: `_our_prize_count(obs) <= 2 and _our_prize_count(obs) > 0`
  AND the best legal attack is flagged lethal (`ba[2]` true) -> take the
  game-winning OHKO over any discretionary attach.
- Evidence it exploits: CORRECTED. The grind predators complete the prize race in
  55% (`meta_grimmsnarl`) to 72% (`meta_grimmsnarl_tonakaiiii`) of their kills at
  median turn 11-13 (predator table, regenerated), and `meta_grimmsnarl_tonakaiiii`
  loses 33 games as `close_loss` (down from an earlier, pre-correction count of 40).
  Our deck reaches the 1-to-2 prize window by turn 5. Any turn we leave lethal on
  the table in that window hands a grind or close-race deck a free turn to catch up.
- Caveat and required precheck: CORRECTED CITATION. `PTCG_PRIZE_CLOSE` measured
  INERT on the trolley deck (`analysis/u105_threat_prize_inert_check.md`): 5
  captured positions where 1-2 prizes were remaining and an attack was offered,
  only 1 of those 5 had a lethal attack available at all, and 0 of 5 decisions
  were flipped by enabling the flag (the earlier draft of this plan cited "2 of 7",
  which is not what that doc says). That doc's own superseded-header addendum adds
  a STRUCTURAL reason this lever can never fire as currently written, not just an
  empirical one: `choose()` already takes any available lethal at step 1, before
  the heuristic resolver ladder (where `PTCG_PRIZE_CLOSE` lives) ever runs. The
  flag is redundant with an existing, unconditional lethal-taking FORCE -- it is
  not "rarely triggered," it is subsumed by code that runs earlier every time.
  Re-testing it fires-vs-inert on `candidate_yushin_ito` would predictably show the
  same 0-flip result regardless of how fast that deck is, since the short-circuit
  has nothing to do with which deck is playing. This materially weakens (and
  removes) the earlier "just re-test it on yushin" plan below.
- Ring test that gates it: NONE, as currently written. This lever cannot earn a
  ladder slot without a code change first (hoisting lethal-seeking evaluation
  ABOVE develop-style actions in the decision order, rather than adding a second,
  later-running copy of the same lethal FORCE), which is a new implementation, not
  a flag flip, and is out of scope for this plan. If that redesign happens later,
  it re-enters the test ladder as a fresh lever with its own fires-vs-inert
  precheck; the version described above should not be ring-tested as-is.

### T2. Deckout-survival window vs the control tail
- Lever: `PTCG_W_DRAW_CONSERVE_THRESHOLD` (shipped, default 8) plus
  `PTCG_W_DECKOUT_THRESHOLD` (default 5); `agents/heuristics.py` around L797-824.
- Observable trigger: `own_deck_count(obs) <= 8` -> decline card-advantage Item /
  Supporter draw (Lillie's Determination, Harlequin, Hilda's draw mode), keep
  developing Pokemon and attacking.
- Evidence it exploits: `other:Boss's Orders Are All You Need` (20 kills, 0%
  prize-race-complete, inflicted shape `deckout`) and `top50_04_third_ptcg_club`
  (15 kills, `deckout`, kill turn 22, winner holds a median of 2 prizes remaining
  when it wins -- CORRECTED, an earlier draft of this plan cited "5.5 prizes",
  which is that archetype's own LOSS-side remaining-prize stat, not a winner-side
  one) win by milling, not racing. Our own Lillie's Determination draws 6 to 8 a
  pop; unchecked it self-decks. The guard's own comment cites Lillie's
  Determination by name as a mill culprit.
- Ring test that gates it: A/B the threshold (on vs off, then 6 vs 8 vs 10) at n=100
  on the high-band ring, reporting per-opponent win rate against the deckout-shaped
  clone `clone:top50_04_third_ptcg_club` specifically. Kill: flat delta -> keep the
  shipped default 8, do not tune.

### T3. Threat_retreat correction: DO NOT retreat from a race we are winning
- Lever: `PTCG_THREAT_RETREAT` (currently ON in the shipped stack); `should_retreat`
  at `agents/heuristics.py` L759-780.
- Observable trigger (current, when it FIRES): opponent's revealed active can OHKO
  our active (`_opponent_best_attack_damage >= hp`) and we have a healthier bench.
- The correction: on the high-band ring this lever is NET NEGATIVE. `top50_ring_baseline.md`:
  stack with threat_retreat+ability ON reads 0.693, flags-OFF reads 0.753, the
  lift is -6.0pp; and per `findings.md` 4C U105b the on-arm loses MORE to the three
  hardest clones (0.273 vs 0.212). For a 330-HP tank that heals with Wally's
  Compassion, ceding the active and the tempo to dodge one OHKO throws away the
  prize-race lead the whole plan depends on. This is the exact "wins the saturated
  ring, loses the high-band ring" pattern S3 names as a kill criterion.
- Ring test that gates it: factor threat_retreat OFF on yushin at n=100 high-band
  (same-run A/B). Kill criterion (S3): if OFF is not worse than ON, default it OFF.
  Then repeat the same isolation for `PTCG_ABILITY` (the other half of the -6.0pp
  stack gap) to decide whether the shipped high-band build should be flags-off.

---

## 4. THE TEST LADDER (cheapest first, n=100 each on the top50 ring, S3 gate)

Throughput is 1.7 to 1.9 games/s (`tools/ring_calibrate.py run_ring`), so an
n=100 same-run A/B (200 games) is roughly 2 minutes of compute; the fires-vs-inert
prechecks are near-instant. Order is cheapest-and-most-decisive first.

1. Reference (already paid, near-zero): adopt `flags_off` yushin (0.753,
   `top50_ring_baseline.md`) as the working high-band incumbent, since it already
   beats the shipped stack. No new run. This reframes 2 and 3 as recoveries toward
   a number we have already measured.
2. T3a, threat_retreat OFF vs ON on yushin, n=100 high-band. Kill: OFF not better
   -> keep it ON; else ship OFF. (Highest-value, directly implied by the baseline.)
3. T3b, ability OFF vs ON on yushin, n=100 high-band. Kill: ability does not clear
   >= 0 on the high band -> default OFF (finish converting the stack to the
   0.753 flags-off build).
4. T2, `PTCG_W_DRAW_CONSERVE_THRESHOLD` sensitivity (6/8/10) n=100 high-band, focus
   vs `clone:top50_04_third_ptcg_club`. Kill: flat -> keep default 8.

CORRECTED: T1 (`PTCG_PRIZE_CLOSE`) is DROPPED from this ladder entirely, not just
gated behind a precheck. `analysis/u105_threat_prize_inert_check.md`'s superseded
addendum establishes a STRUCTURAL reason the rule as currently written can never
flip a decision (`choose()` already takes any available lethal at step 1, before
the resolver ladder this flag lives in ever runs) -- re-running the fires-vs-inert
precheck on a faster deck would not change that, since the short-circuit is in the
decision order, not in how often lethal happens to be available. Spending a ring
slot (or even the near-instant precheck) on the lever as currently implemented is
not justified; see T1's writeup in section 3 for the redesign this would need
(hoisting lethal-seeking above develop actions) before it is worth reconsidering.

Every step is a same-run alternating-seat A/B, so seat and shuffle variance cancel;
every promotion needs the S3 double gate (agreement up AND +10pp high-band).

---

## 5. HONEST LIMITS

- **Archetype detection does not exist in-game** (U9a missed its gate). Every rule
  keys on observable state (our prizes, deck count, opponent's revealed active).
  We cannot condition on "opponent is Archaludon", so the Crushing-Hammer and
  Boss's-Orders beat-paths in section 1 are pilot PLAY-priority behaviors on
  observable board state, not archetype-gated scripts.
- **Small-n matchups cannot be tuned to.** `team_rocket_toolbox` (20g, 1 team,
  `ogerpon_crustle_teal` folded into `crustle_dwebble` and `alakazam_dunsparce`
  folded into `abra_alakazam` post-correction, so neither is its own line item
  any more), `mega_starmie` (19g, 1 team), `drakloak_dreepy` (33g), `okidogi_solrock`
  (24g), `cynthias_gabite_cynthias_gible` (20g), `ns_zoroark_ex_ns_zorua` (19g),
  and every anecdote predator (n < 5 in the loss doc, explicitly flagged) are below
  the bar for a tuned rule. `mega_lucario` (70g), the real `meta_grimmsnarl` (24g),
  and the real `meta_archaludon` (43g) are all mid-size at best post-correction.
  CORRECTED: the plan's real "big three" by size are now `abra_alakazam` (252g,
  formerly hidden inside a contaminated `meta_grimmsnarl` label),
  `crustle_dwebble` (162g, formerly hidden inside a contaminated `meta_archaludon`
  label), and `meta_grimmsnarl_tonakaiiii` (132g) -- 546 of 823 field games, not
  the earlier "627 of 823" figure, which summed three buckets that no longer exist
  in their original form.
- **Deck changes are closed, so section 2 is a negative by design.** If a future
  mining scope (lower ratings, a new archetype) or a real population search
  (`path_above_1000` S4, still virgin) produces a candidate that clears the S3
  high-band gate at n=100, this "no swap" conclusion re-opens. Nothing here forbids
  that; it forbids swapping WITHOUT that evidence.
- **The instrument itself is nearly saturated.** `path_above_1000` verdict: the
  saturated calibrated ring has roughly zero rating headroom, and even the high-band
  ring reads 0.693 to 0.753. The realistic EV of this plan is RECOVERY, not a leap:
  turning off the net-negative threat_retreat/ability stack recovers the ~5 to 6pp
  the shipped build is giving away on the high band (steps 2 and 3 of section 4,
  renumbered after dropping T1), and T2 defends the deckout floor (T1 itself is
  dropped, see section 4). In rating terms `path_above_1000` puts 1000+
  under 5%, 800+ at 25 to 35%, and a converged 700 to 750 as most likely (55 to
  65%). These timing corrections are consistent with, and defend, the 700-to-750
  outcome; they are not a path to 1000 on their own. The honest headline number to
  chase first is the already-measured 0.753 flags-off read, by proving (steps 2-3
  of section 4) that the shipped stack should drop to it.
