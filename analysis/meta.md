# Winning meta, harvested from the 2026-06-30 episode dataset

Source: `tools/deck_harvest.py harvest` over
`data/episodes/pokemon-tcg-ai-battle-episodes-2026-06-30.zip` (gitignored
competition data, never redistributed). 5734 episodes, 11468 decklists, 150
distinct deck signatures. Ranked by total wins with a min of 8 games so a lucky
single game cannot outrank a proven deck. Card ids map to names via
`data/EN_Card_Data.csv`.

This is the source of the deck-copy strategy: our heuristic on the base decks
tops out near 570 on the ladder while the leaders sit at ~1300+. That gap is
mostly a DECK gap, and the fastest close is to copy a proven meta deck rather
than tweak the agent.

LADDER VERDICT (refuted): both copies were submitted and settled BELOW the
trolley floor (archaludon 451.4, grimmsnarl 409.4, vs trolley 569.6 on the same
heuristic). The gap is NOT purely a deck gap; it is a joint deck-and-pilot gap,
and our floor heuristic mispilots a meta deck (self-deckout on Archaludon's
trainer engine, matchup losses on Grimmsnarl's Rare Candy line). See
`analysis/meta_decks_underperform_on_ladder.md`. These decks stay as harvested
reference and gauntlet foils, NOT as ladder submissions on the current agent.

## The field, by archetype

Four archetypes carry the meta. Raw wins favor whatever is most POPULAR (more
games, more average pilots), so read win RATE alongside win count.

### 1. Metal / Archaludon ex  (the popularity pillar)
Ranks #1 (811W/1786G, 45%), #4 (205W/421G, 49%), #8 (144W/271G, 53%). The most
raw wins and by far the widest field (dozens of teams). A straightforward
"evolve and swing" line, which is why the average pilot can run it: Duraludon
(169) evolves to Archaludon ex (190), backed by Cinderace (666), a thin Metal
energy count (11 to 13x Basic {M} Energy, id 8), and the Full Metal Lab (1244)
stadium. Consistency engine: Ultra Ball (1121), Pokegear 3.0 (1122), Poke Pad
(1152), Explorer's Guidance (1185), Night Stretcher (1097), Boss's Orders
(1182), Lillie's Determination (1227). 45% WR reflects the broad, mixed-skill
field that plays it, not a weak deck.

The exact #1 package is copied to `decks/meta_archaludon.csv` (validated LEGAL
by `tools/deck_validate.py`).

### 2. Dark / Marnie's Grimmsnarl ex  (what the top of the ladder actually plays)
Ranks #7 (kazuki0123, 163W/246G, 66%) and #12 (The Debauchery Tea Party,
95W/159G, 60%). The two teams here are leaderboard #2 (kazuki0123, ~1342) and
leaderboard #3 (The Debauchery Tea Party, ~1273). A targeted `--teams tonakaiiii`
harvest confirms leaderboard #1 (tonakaiiii, ~1344) ALSO pilots this exact
archetype: one dominant signature, 93W/137G (68%). So all three of the highest
humans on the board play Dark Grimmsnarl. This is the highest focused win rate in
the meta, and the top of the ladder converges on it. Line: Marnie's
Impidimp (646) -> Morgrem (647) -> Marnie's Grimmsnarl ex (648) via Rare Candy
(1079), Munkidori (112) for spread/heal, Dark energy (7), Spikemuth Gym (1259),
Dawn (1231). Higher ceiling but a harder pilot (evolution plus abilities), so
its 66% is partly kazuki0123's skill, not purely the deck.

kazuki0123's exact 60 card list is copied to `decks/meta_grimmsnarl.csv`
(harvested with `--teams kazuki0123 --min-games 8`; they run exactly one deck
signature across all 246 games). Validated LEGAL by `tools/deck_validate.py`.
Gauntlet with our heuristic vs the built-in pool (random/first/baseline, n=60):
65% (39W/21L), 0 draws, 0 invalid moves. The 0 draws is the key read: the
heuristic pilots the Rare Candy evolution line with no self-collapse, so a
simple policy does not break on the harder deck. Same offline-not-predictive
caveat as Archaludon applies; ladder score is the only truth.

tonakaiiii's exact 60 card list (leaderboard #1) is copied to
`decks/meta_grimmsnarl_tonakaiiii.csv` (harvested `--teams tonakaiiii
--min-games 5`; one dominant signature, 93W/137G, 68%). It is a genuinely
DISTINCT Grimmsnarl build from kazuki0123's: it runs a Froslass (104) / Snorunt
(860) tech line, Team Rocket's Petrel (1219) x4, Boss's Orders (1182) x2,
Handheld Fan (1161) x2, Unfair Stamp (1080), and an extra Night Stretcher (3 vs
2), while dropping kazuki's Dawn-heavy engine (4x Dawn down to 1) and misc tech.
Validated LEGAL. Gauntlet with our heuristic vs the built-in pool (n=60): 66.7%
(40W/20L), 0 draws, 0 invalid moves; the heuristic pilots it with the same clean,
no-self-collapse profile as the other two meta copies.

### 3. Psychic / Alakazam
Ranks #2 (474W/936G, 51%), #6 (THIRD PTCG Club, 180W/287G, 63%), #10 (129W/254G,
51%). Abra (741) -> Kadabra (742) -> Alakazam (743), Dunsparce (305)/Dudunsparce
(66) engine, Enhanced Hammer (1081), Hilda (1225), Dawn (1231), Telepath Psychic
Energy (19). Wide and consistent; #6's 63% is a strong focused build.

### 4. Others with a foothold
Dragapult ex (#3, 279W/631G, 44%: Dreepy 119 -> Drakloak 120 -> Dragapult ex
121). Mega Starmie ex (#5, 189W/411G, 46%; field includes Yushin Ito, leaderboard
#4). Cynthia's Garchomp ex (#9). Great Tusk / Crustle (#11).

## Read and decision

- Archaludon is the safest known-good copy: most wins, widest adoption, simplest
  line, and it gauntlets cleanly with our heuristic (68% vs random/first/baseline,
  0 invalid moves, 0 self-collapse draws). It is the deck to ship FIRST.
- Dark Grimmsnarl is the higher-ceiling copy (the actual top-players' deck) but a
  harder pilot. Now BUILT and gauntleted (65%, 0 draws): the heuristic pilots it
  cleanly, so it is a live submit candidate. Ship it AFTER Archaludon's ladder
  score lands: if the safer copy beats the ~570 trolley floor, the deck-copy
  thesis is confirmed and Grimmsnarl (higher ceiling) is the obvious next slot; if
  Archaludon flops, the heuristic cannot extract a meta deck and a blind Grimmsnarl
  submit would waste a slot.
- Offline gauntlets are run against weak built-in bots and are NOT predictive of
  ladder rating (the trolley deck beats Archaludon 77% to 68% there yet only
  scores ~570 on the ladder). The meta deck's real evidence is its live-ladder
  wins. Ladder score is the only truth; submit and read.

## Ladder reality check (2026-07-01 04:04 UTC)
- meta_archaludon (54219892) settled to publicScore 546.5, which is BELOW the
  trolley floor (54215558 = 569.6). Its early 586.8 read (which looked like a
  confirmed thesis) drifted down as real games accrued. So the Archaludon copy is
  NOT yet a proven ladder gain over our own trolley deck.
- meta_grimmsnarl (54220220, kazuki0123's list) is still PENDING. Its score is the
  real test of the deck-copy thesis: Grimmsnarl is the top-players' actual pick
  (all three highest humans run it), so if any copy beats the ~570 floor it is the
  most likely one. Read it next iter before drawing any thesis conclusion.

## Next scouts
- DONE: `decks/meta_grimmsnarl.csv` (kazuki0123, #2) built, validated, gauntleted
  (65%, 0 draws); submitted 54220220 (PENDING).
- DONE: `decks/meta_grimmsnarl_tonakaiiii.csv` (tonakaiiii, #1) built, validated,
  gauntleted (66.7%, 0 draws). Ready for a one-command submit as the higher-provenance
  Grimmsnarl variant (the #1 player's exact list). Ship it on a free slot IF
  kazuki0123's Grimmsnarl (54220220) validates the archetype on the ladder; if that
  copy also lands below the trolley floor, do NOT spend a slot on a second Grimmsnarl
  variant blind, diagnose why the heuristic underperforms the meta deck first.
