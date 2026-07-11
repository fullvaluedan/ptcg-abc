# Beat-the-meta plan: what cards we use and when we use it (2026-07-11)

Built from three evidence packs and their docs: `analysis/top50_win_mechanisms.md`
(how the field wins), `analysis/top50_loss_modes.md` (how the field loses, with the
predator table), `analysis/top50_ring_baseline.md` (the high-band ring read), plus
`analysis/path_above_1000.md` (the staged plan and its gates) and `findings.md`
section 4B (the closed levers). No em or en dashes anywhere in this file.

## The one-paragraph thesis

The top-50 field is a grind mirror. The three dominant decks (`meta_grimmsnarl` 256g,
`meta_archaludon` 196g, `meta_grimmsnarl_tonakaiiii` 175g) are also the three top
predators, and they beat each other by completing a prize race at median kill turn
13 to 19, dominant inflicted loss shape `grind_loss`. A thin control tail
(`other:Boss's Orders Are All You Need`, `top50_04_third_ptcg_club`) wins a different
way: it decks the opponent out at turn 18 to 22 with 0 to 40% prize-race-complete.
Our incumbent, `candidate_yushin_ito`, is a Mega Starmie ex aggro deck that reaches
its first attack at median turn 2.5 and closes wins in 5 turns (win-mechanisms doc,
`mega_starmie` block). The beat-path is therefore singular and deck-wide: win the
prize race before the grind matures, and survive our own draw engine so the control
tail cannot mill us first. That is a TIMING problem, not a card problem, and the
evidence supports it: deck changes are a four-times-refuted closed lever (4B), and
the loss doc names archetypes and loss shapes, never a specific predator card our
shell lacks.

---

## 1. THE MATCHUP MAP

Kill turns and prize-race-complete rates are from `top50_loss_modes.md`; win
mechanics and prize-take curves from `top50_win_mechanisms.md`. Our clock (prize 1
by turn 4, prize 2 by turn 5, wins in 5 turns) is the `mega_starmie` block of the
wins doc. "Beat-path" is expressed as observable-state behavior because in-game
archetype detection does not exist (U9a missed its gate); we cannot key on "opponent
is X", only on what their board reveals.

### meta_grimmsnarl (256g field, 44.1% WR, top predator: 183 kills)
- How it wins: Dunsparce/Dudunsparce draw engine into Powerful Hand (68 wins),
  Marnie's Grimmsnarl ex, Munkidori damage-move; prize 1 at turn 4, prize 5 at
  turn 8. Median win length 7 turns.
- How it loses: `grind_loss` (53) and `deckout` (45) lead its 143 losses; median
  kill turn 15, it dies with 3 prizes still to take while the winner sits on 1.
  It is beaten most by the mirror (58) and by `meta_archaludon` (29).
- Beat-path: our clock (prize 2 by turn 5) is faster than its (prize 2 by turn 5
  as well, but its median WIN is turn 7 and it takes 15 turns to close its LOSSES).
  Race it: never leave a lethal on the table in the 1 to 2 prize window (rule T1),
  and use Boss's Orders to pull the un-attacked Dudunsparce so it cannot re-load.

### meta_archaludon (196g field, 49.0% WR, predator: 98 kills)
- How it wins: slowest of the big three. Duraludon turn 1, Archaludon ex turn 3,
  Jumbo Ice Cream heal at turn 6 (its top win/loss separator: 27% in wins vs 9%
  in losses). Prize 3 not until turn 9. Median win length 9 turns.
- How it loses: `grind_loss` (42) then `late_collapse` (26) across 100 losses;
  median kill turn 13, dies holding 5 prizes to the winner's 2. It inflicts
  `late_collapse` and `deckout` on its own victims (kills at turn 19).
- Beat-path: this is the matchup our clock most dominates and the one the high-band
  ring says we are WORST at (the two hardest clones are archaludon-family:
  `clone:top50_11_alberto_bonsanto_meta_archaludon`, plus `mitomeat823` and
  `fujiborozoukin`). Deny its setup tempo: Crushing Hammer on a Pokemon showing 2+
  energy before its turn-3 first attack, and close before Jumbo Ice Cream stabilizes
  it at turn 6. Do NOT let the game reach turn 13-plus where it grinds us.

### meta_grimmsnarl_tonakaiiii (175g field, 41.1% WR, predator: 74 kills)
- How it wins: fastest-developing Grimmsnarl variant. Marnie's Impidimp turn 1,
  Munkidori turn 1.5, Shadow Bullet (51 wins); Snorunt/Froslass tech. Prize 1 turn
  4, prize 5 turn 8. Median win 7 turns.
- How it loses: `grind_loss` (46) then `close_loss` (40) across 103 losses, the
  lowest field WR of the big three; median kill turn 13, dies with 3 to the
  winner's 1. Its own separators show Snorunt (48% loss vs 31% win) and Froslass
  are OVER-represented in its losses: the tech line slows it down.
- Beat-path: same as grimmsnarl but the `close_loss` share (40) says these games
  are decided at the margin, which is exactly where the finisher-timing rule (T1)
  and the "do not fumble tempo by retreating" correction (T3) pay off.

### mega_lucario (70g field, 38.6% WR)
- How it wins: fastest clock in the field, prize 1 at turn 3. Solrock/Riolu/Premium
  Power Pro all turn 1, Mega Lucario ex turn 2, Aura Jab (19 wins). Fighting Gong
  is its win separator (52% win vs 33% loss).
- How it loses: lowest WR of the mid-size archetypes; it out-speeds itself into
  `setup_denied` when the engine misses.
- Beat-path: this is a genuine race we can LOSE on raw speed. Mega Starmie ex 330HP
  plus Hero's Cape (+100) plus Wally's Compassion (full heal and recover all energy)
  is the tank answer: survive the first Aura Jab, heal, and win the second exchange.
  No new card needed, the shell already carries it.

### ogerpon_crustle_cornerstone (43g, 34.9%) and ogerpon_crustle_teal (20g, 55%, n=1 team)
- How they win: Crustle/Superb Scissors grind; cornerstone is a turn-16 grind deck
  (prize 3 not until turn 22), teal is faster (first attack turn 1). Urbain (87%
  win vs 46% loss) and Jumbo Ice Cream separate cornerstone's wins.
- How they lose: cornerstone is the slowest deck measured; it simply cannot outrace
  a turn-5 kill.
- Beat-path: pure race. We are dead before their grind engine matures. No tuning
  needed; flagged small-n (teal is one team, 20 games).

### team_rocket_toolbox (20g, 60% WR, n=1 team, kashiwashira)
- How it wins: TR toolbox, Giovanni its separator (83% win vs 25% loss); median
  win 9 turns, prize 5 not until turn 19. A grind/disruption deck.
- How it loses: n=8 losses only; not characterizable.
- Beat-path: race the slow toolbox. Small-n, do not tune to it.

### alakazam_dunsparce (20g, 35%, n=1 team) and mega_starmie (19g, 47.4%, n=1 team WinDecks)
- `mega_starmie` IS our own shell in the field (WinDecks piloting it). Its own
  separators (Staryu 100% win, Dusknoir/Dusclops tech) confirm the aggro-tank plan
  and that the incumbent list is a real, field-present deck, not a synthetic pick.
- Beat-path against alakazam: race; its Sacred Ash/Enhanced Hammer late-game cards
  are OVER-represented in its losses (grind tools that arrive too slow).

### The control tail (the deckout predators, cross-archetype)
- `other:Boss's Orders Are All You Need`: 20 kills, 0% prize-race-complete,
  inflicted shape `deckout`, median kill turn 18. It does not race; it mills.
- `top50_04_third_ptcg_club`: 15 kills, `deckout`, median kill turn 22, wins with
  5.5 prizes still on its side of the board.
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
| 4 | Crushing Hammer (1120) | energy denial (anti-Archaludon tempo) |
| 4 | Wally's Compassion (1229) | full heal + recover all energy on the mega |
| 1 | Boss's Orders (1182) | gust the un-attacked setup piece / grab last prize |
| 1 | Hero's Cape (1159, ACE SPEC) | +100 HP tank |

Every beat-path in section 1 is already executed by a card in this list: race =
the Mega Starmie clock; tank the Lucario race = Hero's Cape + Wally's Compassion;
deny Archaludon tempo = Crushing Hammer; pull the setup piece = Boss's Orders;
survive our own mill = the shipped DRAW_CONSERVE guard. There is no beat-path in
the loss evidence that names a card this deck lacks.

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
- Evidence it exploits: the grind predators complete the prize race in 55%
  (grimmsnarl), 58% (tonakaiiii) of their kills at median turn 13, and
  `meta_grimmsnarl_tonakaiiii` loses 40 games as `close_loss`. Our deck reaches the
  1-to-2 prize window by turn 5. Any turn we leave lethal on the table in that
  window hands a grind or close-race deck a free turn to catch up.
- Caveat and required precheck: `PTCG_PRIZE_CLOSE` measured INERT on the trolley
  deck (U105, 2 of 7 captured lethal positions, 0 decision flips). That was the
  trolley shell. It has NEVER been fires-vs-inert checked on `candidate_yushin_ito`,
  a genuinely faster deck that actually reaches the prize window early. Re-run the
  fires-vs-inert check on yushin FIRST (P8 discipline: inert rules get no ring slot).
- Ring test that gates it: (a) `tools/measure_prize_close.py` pattern on yushin,
  gate = it flips >= 5 real decisions; if inert, STOP, do not ring-test. (b) If it
  fires, n=100 high-band ring (`tools/ring_calibrate.py run_ring`, top50 ring),
  S3 gate >= +10pp vs the flags-off yushin baseline.

### T2. Deckout-survival window vs the control tail
- Lever: `PTCG_W_DRAW_CONSERVE_THRESHOLD` (shipped, default 8) plus
  `PTCG_W_DECKOUT_THRESHOLD` (default 5); `agents/heuristics.py` around L797-824.
- Observable trigger: `own_deck_count(obs) <= 8` -> decline card-advantage Item /
  Supporter draw (Lillie's Determination, Harlequin, Hilda's draw mode), keep
  developing Pokemon and attacking.
- Evidence it exploits: `other:Boss's Orders Are All You Need` (20 kills, 0%
  prize-race-complete, inflicted shape `deckout`) and `top50_04_third_ptcg_club`
  (15 kills, `deckout`, kill turn 22, winner holds 5.5 prizes) win by milling, not
  racing. Our own Lillie's Determination draws 6 to 8 a pop; unchecked it self-decks.
  The guard's own comment cites Lillie's Determination by name as a mill culprit.
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
2. Precheck (no ring): fires-vs-inert for `PTCG_PRIZE_CLOSE` on yushin
   (`tools/measure_prize_close.py`). Kill: 0 decision flips -> drop T1, do not
   ring-test it.
3. T3a, threat_retreat OFF vs ON on yushin, n=100 high-band. Kill: OFF not better
   -> keep it ON; else ship OFF. (Highest-value, directly implied by the baseline.)
4. T3b, ability OFF vs ON on yushin, n=100 high-band. Kill: ability does not clear
   >= 0 on the high band -> default OFF (finish converting the stack to the
   0.753 flags-off build).
5. T1 (only if step 2 fired): `PTCG_PRIZE_CLOSE` n=100 high-band, S3 >= +10pp gate.
   Kill: below +10pp -> park the lever, do not slot it.
6. T2, `PTCG_W_DRAW_CONSERVE_THRESHOLD` sensitivity (6/8/10) n=100 high-band, focus
   vs `clone:top50_04_third_ptcg_club`. Kill: flat -> keep default 8.

Every step is a same-run alternating-seat A/B, so seat and shuffle variance cancel;
every promotion needs the S3 double gate (agreement up AND +10pp high-band).

---

## 5. HONEST LIMITS

- **Archetype detection does not exist in-game** (U9a missed its gate). Every rule
  keys on observable state (our prizes, deck count, opponent's revealed active).
  We cannot condition on "opponent is Archaludon", so the Crushing-Hammer and
  Boss's-Orders beat-paths in section 1 are pilot PLAY-priority behaviors on
  observable board state, not archetype-gated scripts.
- **Small-n matchups cannot be tuned to.** `team_rocket_toolbox` (20g, 1 team),
  `ogerpon_crustle_teal` (20g, 1 team), `alakazam_dunsparce` (20g, 1 team),
  `mega_starmie` (19g, 1 team), and every anecdote predator (n < 5 in the loss doc,
  explicitly flagged) are below the bar for a tuned rule. `mega_lucario` (70g) is
  the only mid-n non-big-three archetype. The plan tunes only to the big three
  (627 of 823 field games) plus the deckout tail.
- **Deck changes are closed, so section 2 is a negative by design.** If a future
  mining scope (lower ratings, a new archetype) or a real population search
  (`path_above_1000` S4, still virgin) produces a candidate that clears the S3
  high-band gate at n=100, this "no swap" conclusion re-opens. Nothing here forbids
  that; it forbids swapping WITHOUT that evidence.
- **The instrument itself is nearly saturated.** `path_above_1000` verdict: the
  saturated calibrated ring has roughly zero rating headroom, and even the high-band
  ring reads 0.693 to 0.753. The realistic EV of this plan is RECOVERY, not a leap:
  turning off the net-negative threat_retreat/ability stack recovers the ~5 to 6pp
  the shipped build is giving away on the high band (steps 3 and 4), and T1/T2 defend
  the finisher and the deckout floor. In rating terms `path_above_1000` puts 1000+
  under 5%, 800+ at 25 to 35%, and a converged 700 to 750 as most likely (55 to
  65%). These timing corrections are consistent with, and defend, the 700-to-750
  outcome; they are not a path to 1000 on their own. The honest headline number to
  chase first is the already-measured 0.753 flags-off read, by proving (steps 3-4)
  that the shipped stack should drop to it.
