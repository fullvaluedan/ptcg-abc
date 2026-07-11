# Top-50 win mechanisms

Source: `data/derived/top50_harvest.json` (the top-50 leaderboard harvest, 827
total harvested games across 50 teams; see `analysis/top50_harvest.md`).

Archetype clustering reuses the existing machinery: the three named families
below (`meta_archaludon`, `meta_grimmsnarl`, `meta_grimmsnarl_tonakaiiii`) are
`analysis.expert_cohort.classify_family`'s builtin field archetypes, already
computed per-deck as `archetype_guess` inside the harvest JSON. The
`archetype_guess == "other"` bucket (197 games, 11 distinct decklists) was
clustered by key-card overlap: `analysis.archetype.signature_of` (every
non-basic-energy card id) pairwise-jaccard'd across the 11 decklists, union-find
merged at jaccard >= 0.5. That merges only near-duplicate decklists (the
strongest merge is 3 decklists at jaccard 0.94-1.00, run by 5 different teams,
all the same Mega Lucario ex / Solrock & Lunatone list; the weakest accepted
merge is 2 decklists at jaccard 0.95, both Ajishio's own Alakazam / Dunsparce
list). It does NOT merge the two Ogerpon ex / Crustle builds (jaccard 0.30,
different Ogerpon form + support suite) -- they are reported as two separate
archetypes.

Of the 827 harvested games, 823 have a resolved decklist and a decisive (W/L)
result; the other 4 are draws or a game whose decklist could not be resolved.
Of those 823, 819 (99.5% of the 823 resolved
games, 99.0% of all 827 harvested games) fall into one
of the 9 archetypes below (each has >= 15 harvested W/L games); the remaining
4 W/L games are two 2-game decklists (a Jellicent ex / Frillish list, an
Iono's Bellibolt ex toolbox) too small to characterize and left uncovered.

Every card name below is read directly from `agents.heuristics.card_index()`
(id -> `CardData.name`); every attack name from `agents.heuristics.attack_index()`
(id -> `Attack.name`). No card id in this document was hand-typed without that
lookup.

## Methodology notes (read before the numbers)

- **Turn numbering.** Replays store one shared turn counter that increments
  every half-turn (seat 0's turns are the odd numbers, seat 1's the even).
  This doc reports each team's own turn number, `player_turn = (shared_turn +
  1) // 2`, so "turn 3" always means that team's own 3rd turn, not the 5th
  half-turn of the game.
- **Timeline extraction.** Walks `analysis.replay_trace.iter_resolved_decisions`
  for the harvested team's own seat (seat resolved per-episode via
  `team_seat`, matching `info.TeamNames`), which yields every MAIN decision
  (PLAY / ATTACH / EVOLVE / ABILITY / RETREAT / ATTACK / END) already resolved
  to a card id. For an ATTACH decision the card id is the Pokemon that
  *received* the energy (the spine's own convention), not the energy card
  itself -- so "energy attached to X" in the timeline never names an energy
  card.
- **Phase buckets** (won games only): setup = turns 1-2, engine = turns 3-5,
  finisher = the game's own last 2 turns (for a short game -- several of these
  archetypes close in 5-6 turns -- the engine and finisher windows overlap;
  that overlap is real, not a bug: it means the deck's mid-game and kill turn
  are the same turn).
- **Prize-take curve.** A team's own `players[seat].prize` list length is
  their remaining prize count (starts at 6). Each observed decrease between
  two consecutive decision snapshots is logged as one "prize taken" event at
  that snapshot's turn; turn attribution is therefore accurate to within one
  of that team's own turns, not half-turn-exact.
- **Separator cards.** For every archetype-signature card played at least
  twice in the represented decklist, compares play rate (fraction of games in
  which it appears at all) and median first-play turn between the archetype's
  own wins and its own losses. Ranked by `|win_rate - loss_rate| + 0.05 *
  |median_turn_loss - median_turn_win|`. Generic format staples (Buddy-Buddy
  Poffin, Ultra Ball, Pokegear 3.0, Poke Pad, Lillie's Determination, Boss's
  Orders, Judge, Night Stretcher, Wally's Compassion, Dawn, Rare Candy,
  Carmine, Dusk Ball, Bug Catching Set, Canari, Team Rocket's Factory) are
  excluded from candidacy since they appear in most top-50 decks regardless of
  archetype and never separate one archetype's wins from its losses.

## Dark / Grimmsnarl ex (`meta_grimmsnarl`)

- Coverage: 256 harvested games (113W-143L, win rate 44.1%) across 14 team(s): Ebi, Hiro Nomo, LiamK, LumenLiquidity, Majkel1337, Yushin Ito, bono, capbloo, ebisu_ya, haggle, matsurih, soyukke, wkonishi, ごんさくよねきち.
- Median game length in wins: 7 turns. Median first-attack turn: 2.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Kadabra (evolved, 34g); Abra (energy attached to, 34g); Dunsparce (energy attached to, 28g); Hilda (played, 26g); Dunsparce (played, 25g); Nighttime Mine (played, 19g)

**Engine (turns 3-5):** Hilda (played, 49g); Alakazam (energy attached to, 47g); Dudunsparce (evolved, 39g); Alakazam (evolved, 38g); Dunsparce (played, 32g); Xerosic’s Machinations (played, 31g)

**Finisher (closing 2 turns of the game):** Alakazam (energy attached to, 27g); Hilda (played, 20g); Dudunsparce (evolved, 19g); Dunsparce (played, 18g); Dunsparce (energy attached to, 9g); Nighttime Mine (played, 8g)

Attacks actually thrown in wins: Powerful Hand (68 wins), Teleportation Attack (21 wins), Super Psy Bolt (19 wins), Shadow Bullet (11 wins), Trading Places (7 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Marnie's Impidimp | 1 | 9% |
| Spikemuth Gym | 1.5 | 2% |
| Dunsparce | 2 | 66% |
| Munkidori | 2 | 11% |
| Marnie's Morgrem | 2 | 4% |
| Dudunsparce | 3 | 58% |
| Xerosic’s Machinations | 3 | 38% |
| Marnie's Grimmsnarl ex | 3 | 12% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 4 | 106 |
| 2 | 5 | 86 |
| 3 | 6 | 61 |
| 4 | 7 | 30 |
| 5 | 8 | 11 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Dunsparce | 66% | 79% | 2 | 3 |
| Munkidori | 11% | 6% | 2 | 4.5 |
| Marnie's Morgrem | 4% | 3% | 2 | 4.5 |
| Dudunsparce | 58% | 66% | 3 | 4 |
| Marnie's Grimmsnarl ex | 12% | 4% | 3 | 3.5 |


## Metal / Archaludon ex (`meta_archaludon`)

- Coverage: 196 harvested games (96W-100L, win rate 49.0%) across 12 team(s): Alberto Bonsanto, Budew, Dũng Đỗ, Kohei, Legend Brothers, MPGaming, RtoABC, S4nkurero, ShumpeiNomura, Zhenyu Zhang, btk15049, shg195.
- Median game length in wins: 9 turns. Median first-attack turn: 3.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Mega Kangaskhan ex (energy attached to, 18g); Dwebble (energy attached to, 18g); Duraludon (energy attached to, 12g); Battle Cage (played, 10g); Crustle (energy attached to, 10g); Dwebble (played, 9g)

**Engine (turns 3-5):** Mega Kangaskhan ex (energy attached to, 21g); Crustle (energy attached to, 17g); Xerosic’s Machinations (played, 15g); Mega Kangaskhan ex (played, 15g); Jumbo Ice Cream (played, 12g); Crustle (evolved, 11g)

**Finisher (closing 2 turns of the game):** Mega Kangaskhan ex (played, 12g); Crustle (energy attached to, 6g); Mega Kangaskhan ex (energy attached to, 6g); Jumbo Ice Cream (played, 6g); Archaludon ex (energy attached to, 6g); Archaludon ex (evolved, 5g)

Attacks actually thrown in wins: Superb Scissors (29 wins), Metal Defender (19 wins), Hammer In (15 wins), Rapid-Fire Combo (13 wins), Ascension (7 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Duraludon | 1 | 20% |
| Full Metal Lab | 1 | 7% |
| Explorer’s Guidance | 2 | 9% |
| Archaludon ex | 3 | 20% |
| Jumbo Ice Cream | 6 | 27% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 5 | 87 |
| 2 | 6.5 | 82 |
| 3 | 9 | 65 |
| 4 | 9 | 41 |
| 5 | 9.5 | 12 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Jumbo Ice Cream | 27% | 9% | 6 | 4 |
| Archaludon ex | 20% | 15% | 3 | 3 |
| Explorer’s Guidance | 9% | 6% | 2 | 2 |
| Duraludon | 20% | 17% | 1 | 1 |
| Full Metal Lab | 7% | 5% | 1 | 1 |


## Dark / Grimmsnarl ex (Tonakaiiii tech) (`meta_grimmsnarl_tonakaiiii`)

- Coverage: 175 harvested games (72W-103L, win rate 41.1%) across 13 team(s): Hiro Nomo, Larry, LumenLiquidity, RtoABC, S4nkurero, Shota Hirao, Sota Uchiyama, Yudai Ueno, nasuo445, payanotty, tonakaiiii, youtube.com/@BigBugginnings, 渡邊征央.
- Median game length in wins: 7 turns. Median first-attack turn: 3.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Marnie's Impidimp (energy attached to, 31g); Munkidori (energy attached to, 22g); Marnie's Impidimp (played, 20g); Marnie's Morgrem (evolved, 17g); Marnie's Grimmsnarl ex (energy attached to, 15g); Marnie's Morgrem (energy attached to, 10g)

**Engine (turns 3-5):** Marnie's Grimmsnarl ex (energy attached to, 34g); Munkidori (energy attached to, 28g); Marnie's Impidimp (energy attached to, 15g); Unfair Stamp (played, 13g); Marnie's Morgrem (energy attached to, 13g); Marnie's Impidimp (played, 13g)

**Finisher (closing 2 turns of the game):** Marnie's Grimmsnarl ex (energy attached to, 18g); Munkidori (energy attached to, 13g); Munkidori (played, 9g); Team Rocket's Petrel (played, 8g); Cynthia's Garchomp ex (energy attached to, 6g); Crushing Hammer (played, 5g)

Attacks actually thrown in wins: Shadow Bullet (51 wins), Corkscrew Dive (12 wins), Jet Headbutt (7 wins), Itchy Pollen (6 wins), Dragonslice (5 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Marnie's Impidimp | 1 | 64% |
| Munkidori | 1.5 | 72% |
| Marnie's Morgrem | 2 | 56% |
| Spikemuth Gym | 2 | 12% |
| Snorunt | 2.5 | 31% |
| Marnie's Grimmsnarl ex | 3 | 58% |
| Team Rocket's Petrel | 3 | 28% |
| Froslass | 5 | 29% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 4 | 69 |
| 2 | 5 | 64 |
| 3 | 6 | 51 |
| 4 | 7 | 37 |
| 5 | 8 | 16 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Snorunt | 31% | 48% | 2.5 | 3 |
| Froslass | 29% | 37% | 5 | 4 |
| Munkidori | 72% | 77% | 1.5 | 3 |
| Spikemuth Gym | 12% | 23% | 2 | 2 |
| Team Rocket's Petrel | 28% | 33% | 3 | 4 |


## Mega Lucario ex / Solrock & Lunatone (`mega_lucario`)

- Coverage: 70 harvested games (27W-43L, win rate 38.6%) across 5 team(s): ImANoob1122, S4nkurero, Zhenyu Zhang, fujiborozoukin, mitomeat823.
- Median game length in wins: 6 turns. Median first-attack turn: 2.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Premium Power Pro (played, 20g); Riolu (energy attached to, 19g); Solrock (energy attached to, 17g); Lunatone (energy attached to, 13g); Fighting Gong (played, 11g); Mega Lucario ex (evolved, 9g)

**Engine (turns 3-5):** Premium Power Pro (played, 16g); Mega Lucario ex (energy attached to, 16g); Riolu (played, 12g); Solrock (played, 11g); Lunatone (played, 10g); Mega Lucario ex (evolved, 9g)

**Finisher (closing 2 turns of the game):** Riolu (played, 7g); Lunatone (played, 6g); Premium Power Pro (played, 6g); Solrock (played, 6g); Solrock (energy attached to, 2g); Mega Lucario ex (energy attached to, 2g)

Attacks actually thrown in wins: Aura Jab (19 wins), Cosmic Beam (9 wins), Accelerating Stab (6 wins), Mega Brave (3 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Solrock | 1 | 96% |
| Riolu | 1 | 96% |
| Premium Power Pro | 1 | 96% |
| Lunatone | 1 | 82% |
| Fighting Gong | 1 | 52% |
| Mega Lucario ex | 2 | 89% |
| Xerosic’s Machinations | 3 | 18% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 3 | 23 |
| 2 | 4 | 21 |
| 3 | 6 | 15 |
| 4 | 7 | 9 |
| 5 | 8.5 | 4 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Fighting Gong | 52% | 33% | 1 | 2 |
| Solrock | 96% | 81% | 1 | 2 |
| Xerosic’s Machinations | 18% | 33% | 3 | 2 |
| Mega Lucario ex | 89% | 81% | 2 | 3 |
| Premium Power Pro | 96% | 91% | 1 | 2 |


## Cornerstone Mask Ogerpon ex / Crustle (`ogerpon_crustle_cornerstone`)

- Coverage: 43 harvested games (15W-28L, win rate 34.9%) across 4 team(s): LiamK, S4nkurero, THIRD PTCG Club, ktr.
- Median game length in wins: 16 turns. Median first-attack turn: 4.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Dwebble (energy attached to, 9g); Munkidori (energy attached to, 5g); Crustle (energy attached to, 3g); Urbain (played, 3g); Crustle (evolved, 3g); Team Rocket's Articuno (played, 3g)

**Engine (turns 3-5):** Crustle (energy attached to, 4g); Munkidori (energy attached to, 3g); Dwebble (played, 2g); Cornerstone Mask Ogerpon ex (energy attached to, 2g); Team Rocket's Articuno (energy attached to, 2g); Crustle (evolved, 2g)

**Finisher (closing 2 turns of the game):** Munkidori (played, 4g); Crustle (energy attached to, 4g); Urbain (played, 3g); Team Rocket's Articuno (energy attached to, 3g); Munkidori (energy attached to, 2g); Cornerstone Mask Ogerpon ex (played, 2g)

Attacks actually thrown in wins: Superb Scissors (9 wins), Dark Frost (4 wins), Mind Bend (2 wins), Ascension (2 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Dwebble | 1 | 80% |
| Munkidori | 2 | 87% |
| Crustle | 2 | 73% |
| Team Rocket's Articuno | 3 | 73% |
| Cornerstone Mask Ogerpon ex | 3 | 40% |
| Urbain | 7 | 87% |
| Jumbo Ice Cream | 21 | 20% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 8 | 12 |
| 2 | 11 | 9 |
| 3 | 22 | 5 |
| 4 | 25 | 1 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Jumbo Ice Cream | 20% | 11% | 21 | 4 |
| Urbain | 87% | 46% | 7 | 4 |
| Munkidori | 87% | 57% | 2 | 2 |
| Dwebble | 80% | 61% | 1 | 3 |
| Cornerstone Mask Ogerpon ex | 40% | 61% | 3 | 4 |


## Team Rocket's toolbox (`team_rocket_toolbox`)

- Coverage: 20 harvested games (12W-8L, win rate 60.0%) across 1 team(s): kashiwashira.
- Median game length in wins: 9 turns. Median first-attack turn: 4.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Team Rocket's Tarountula (energy attached to, 7g); Team Rocket's Mimikyu (energy attached to, 6g); Team Rocket's Mimikyu (played, 4g); Team Rocket's Tarountula (played, 4g); Team Rocket's Articuno (played, 4g); Team Rocket's Articuno (energy attached to, 3g)

**Engine (turns 3-5):** Team Rocket's Ariana (played, 9g); Team Rocket's Giovanni (played, 5g); Team Rocket's Spidops (energy attached to, 5g); Team Rocket's Articuno (energy attached to, 4g); Team Rocket's Spidops (evolved, 4g); Team Rocket's Mimikyu (energy attached to, 4g)

**Finisher (closing 2 turns of the game):** Team Rocket's Articuno (energy attached to, 3g); Team Rocket's Ariana (played, 3g); Team Rocket's Mimikyu (energy attached to, 3g); Team Rocket's Spidops (energy attached to, 3g); Team Rocket's Mewtwo ex (energy attached to, 2g); Team Rocket's Proton (played, 2g)

Attacks actually thrown in wins: Rocket Rush (5 wins), Erasure Ball (4 wins), Take Down (1 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Team Rocket's Tarountula | 1 | 83% |
| Team Rocket's Mimikyu | 1 | 83% |
| Team Rocket's Articuno | 2 | 83% |
| Team Rocket's Spidops | 3 | 92% |
| Team Rocket's Transceiver | 3 | 58% |
| Team Rocket's Mewtwo ex | 3 | 42% |
| Team Rocket's Ariana | 4 | 83% |
| Team Rocket's Giovanni | 4.5 | 83% |
| Team Rocket's Proton | 10 | 25% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 4 | 11 |
| 2 | 6 | 9 |
| 3 | 9 | 8 |
| 4 | 12 | 5 |
| 5 | 19 | 2 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Team Rocket's Giovanni | 83% | 25% | 4.5 | 5.5 |
| Team Rocket's Proton | 25% | 38% | 10 | 3 |
| Team Rocket's Mewtwo ex | 42% | 62% | 3 | 4 |
| Team Rocket's Mimikyu | 83% | 100% | 1 | 2.5 |
| Team Rocket's Articuno | 83% | 100% | 2 | 1 |


## Teal Mask Ogerpon ex / Crustle (`ogerpon_crustle_teal`)

- Coverage: 20 harvested games (11W-9L, win rate 55.0%) across 1 team(s): Kers Aoyagi.
- Median game length in wins: 11 turns. Median first-attack turn: 1.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Dwebble (energy attached to, 4g); Crustle (energy attached to, 3g); Crustle (evolved, 3g); Teal Mask Ogerpon ex (energy attached to, 2g); Teal Mask Ogerpon ex (played, 1g); Cook (played, 1g)

**Engine (turns 3-5):** Crustle (energy attached to, 5g); Waitress (played, 5g); Crustle (evolved, 3g); Teal Mask Ogerpon ex (played, 3g); Jumbo Ice Cream (played, 2g); Dwebble (energy attached to, 2g)

**Finisher (closing 2 turns of the game):** Crustle (energy attached to, 6g); Jumbo Ice Cream (played, 4g); Xerosic’s Machinations (played, 2g); Waitress (played, 2g); Teal Mask Ogerpon ex (played, 1g)

Attacks actually thrown in wins: Superb Scissors (10 wins), Ascension (9 wins), Myriad Leaf Shower (3 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Dwebble | 1.5 | 55% |
| Crustle | 3 | 100% |
| Waitress | 4 | 64% |
| Teal Mask Ogerpon ex | 5 | 73% |
| Xerosic’s Machinations | 7 | 82% |
| Cook | 7 | 27% |
| Jumbo Ice Cream | 8 | 55% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 7 | 10 |
| 2 | 10 | 10 |
| 3 | 8 | 1 |
| 4 | 9 | 1 |
| 5 | 14 | 1 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Jumbo Ice Cream | 55% | 11% | 8 | 6 |
| Crustle | 100% | 56% | 3 | 3 |
| Teal Mask Ogerpon ex | 73% | 56% | 5 | 1 |
| Cook | 27% | 0% | 7 | n/a |
| Waitress | 64% | 44% | 4 | 5 |


## Alakazam / Dunsparce (`alakazam_dunsparce`)

- Coverage: 20 harvested games (7W-13L, win rate 35.0%) across 1 team(s): Ajishio.
- Median game length in wins: 5 turns. Median first-attack turn: 3.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Kadabra (evolved, 4g); Dudunsparce (evolved, 3g); Hilda (played, 2g); Togepi (played, 2g); Enhanced Hammer (played, 1g); Battle Cage (played, 1g)

**Engine (turns 3-5):** Alakazam (energy attached to, 4g); Battle Cage (played, 4g); Lana’s Aid (played, 3g); Hilda (played, 3g); Abra (played, 2g); Alakazam (evolved, 2g)

**Finisher (closing 2 turns of the game):** Battle Cage (played, 2g); Alakazam (energy attached to, 2g); Dunsparce (played, 2g); Abra (energy attached to, 1g); Dunsparce (energy attached to, 1g); Lana’s Aid (played, 1g)

Attacks actually thrown in wins: Powerful Hand (6 wins), Super Psy Bolt (1 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Dudunsparce | 2 | 57% |
| Kadabra | 2 | 57% |
| Hilda | 2.5 | 57% |
| Battle Cage | 3 | 57% |
| Abra | 3.5 | 57% |
| Alakazam | 4.5 | 86% |
| Enhanced Hammer | 5 | 29% |
| Sacred Ash | 5.5 | 29% |
| Dunsparce | 6 | 71% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 4 | 6 |
| 2 | 7 | 3 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Sacred Ash | 29% | 62% | 5.5 | 3 |
| Enhanced Hammer | 29% | 54% | 5 | 2 |
| Battle Cage | 57% | 92% | 3 | 3.5 |
| Dunsparce | 71% | 92% | 6 | 4 |
| Kadabra | 57% | 77% | 2 | 2 |


## Mega Starmie ex (`mega_starmie`)

- Coverage: 19 harvested games (9W-10L, win rate 47.4%) across 1 team(s): WinDecks.
- Median game length in wins: 5 turns. Median first-attack turn: 2.5.

### Win mechanism: card-play timeline (won games only)

**Setup (turns 1-2):** Staryu (energy attached to, 7g); Mega Starmie ex (energy attached to, 4g); Duskull (played, 3g); Staryu (played, 3g); Mega Starmie ex (evolved, 2g); Duskull (energy attached to, 1g)

**Engine (turns 3-5):** Mega Starmie ex (energy attached to, 5g); Staryu (energy attached to, 2g); Mega Starmie ex (evolved, 2g); Staryu (played, 2g); Duskull (played, 1g); Hilda (played, 1g)

**Finisher (closing 2 turns of the game):** Mega Starmie ex (energy attached to, 4g); Mega Starmie ex (evolved, 1g); Hilda (played, 1g); Dusclops (evolved, 1g)

Attacks actually thrown in wins: Jetting Blow (4 wins), Nebula Beam (1 wins), Water Gun (1 wins).

### Median first-turn each key card appears (wins)

| card | median first turn | % of wins that play it |
|---|---|---|
| Staryu | 1 | 100% |
| Mega Starmie ex | 2 | 100% |
| Duskull | 2 | 44% |
| Dusknoir | 3 | 11% |
| Hilda | 4 | 33% |
| Dusclops | 4 | 22% |

### Prize-take curve (median turn per Nth prize, wins)

| prize # | median turn taken | n wins observed |
|---|---|---|
| 1 | 4 | 8 |
| 2 | 5 | 6 |
| 3 | 7 | 4 |

### Cards that most separate wins from losses

| card | play rate in wins | play rate in losses | median turn (win) | median turn (loss) |
|---|---|---|---|---|
| Staryu | 100% | 80% | 1 | 1 |
| Hilda | 33% | 50% | 4 | 4 |
| Duskull | 44% | 60% | 2 | 2 |
| Dusknoir | 11% | 10% | 3 | 5 |
| Dusclops | 22% | 20% | 4 | 3 |

