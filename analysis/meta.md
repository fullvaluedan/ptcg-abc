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
leaderboard #3 (The Debauchery Tea Party, ~1273). This is the highest focused
win rate in the meta, and the highest-rated humans pick it. Line: Marnie's
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
  scores ~570 on the ladder). The meta deck's real evidence is its 811 wins
  across the live ladder field. Ladder score is the only truth; submit and read.

## Next scouts
- DONE: `decks/meta_grimmsnarl.csv` built from #7, validated LEGAL, gauntleted
  (65%, 0 draws). Ready for a one-command submit once Archaludon's score lands.
- Cross-check tonakaiiii (leaderboard #1, ~1344): not surfaced by name in the
  top-12 team lists here, so harvest with `--teams tonakaiiii` to pull that exact
  deck from a daily dataset.
