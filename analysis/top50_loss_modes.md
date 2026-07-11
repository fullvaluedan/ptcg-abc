# Top-50 loss modes: how they lose

Generated from C:\Users\danom\ptcg-abc\data\derived\top50_harvest.json (harvest generated 2026-07-11T13:49:17.385790Z). 460 losses found across the top-50 teams' harvested windows; 460 resolved against their episode JSON and analyzed below, 0 could not be resolved (see Unresolved below).

Every claim below carries its game count (n). Any bucket with n < 5 is flagged **anecdote** and should not be read as a trend.

## Predator table: who beats the top-50 field, and how

Every winning archetype across ALL top-50 losses, ranked by kills. "Prize race complete" = the winner's own remaining-prize count was <=1 at the last captured decision (this replay format's observed floor is 1, never 0 -- the last decision logged always precedes the actual game-ending move, so <=1 is the closest signal to "the winner finished a normal KO-based prize race" this data supports; see Method notes). A LOW rate means that archetype's kills mostly end the game some other way (the loser deckout-ing or collapsing) while the winner still had several prizes left.

| winner archetype | kills | top victims | median kill turn | prize race complete rate | dominant loss shape inflicted |
|---|---|---|---|---|---|
| meta_grimmsnarl | 183 | meta_grimmsnarl (58), meta_grimmsnarl_tonakaiiii (44), meta_archaludon (36), top50_04_third_ptcg_club (10) | 13 | 55% | grind_loss |
| meta_archaludon | 98 | meta_grimmsnarl (29), meta_grimmsnarl_tonakaiiii (20), meta_archaludon (16), top50_06_imanoob1122 (9) | 19.0 | 42% | grind_loss |
| meta_grimmsnarl_tonakaiiii | 74 | meta_grimmsnarl (22), meta_archaludon (18), meta_grimmsnarl_tonakaiiii (17), top50_13_windecks (4) | 13.0 | 58% | grind_loss |
| other:Boss's Orders Are All You Need | 20 | meta_grimmsnarl (10), top50_04_third_ptcg_club (3), meta_archaludon (2), meta_grimmsnarl_tonakaiiii (1) | 18.0 | 0% | deckout |
| top50_13_windecks | 20 | meta_archaludon (6), meta_grimmsnarl (6), meta_grimmsnarl_tonakaiiii (4), top50_04_third_ptcg_club (2) | 10.0 | 50% | grind_loss |
| top50_08_kashiwashira | 19 | meta_grimmsnarl (6), meta_archaludon (6), meta_grimmsnarl_tonakaiiii (3), top50_04_third_ptcg_club (2) | 13 | 47% | grind_loss |
| top50_04_third_ptcg_club | 15 | meta_grimmsnarl (6), meta_grimmsnarl_tonakaiiii (5), meta_archaludon (3), top50_14_fujiborozoukin (1) | 22 | 40% | deckout |
| other:zoroark190 | 9 | meta_archaludon (4), meta_grimmsnarl_tonakaiiii (3), top50_07_kers_aoyagi (1), top50_06_imanoob1122 (1) | 10 | 44% | grind_loss |
| top50_06_imanoob1122 (anecdote) | 4 | meta_grimmsnarl (2), meta_grimmsnarl_tonakaiiii (1), meta_archaludon (1) | 6.5 | 50% | setup_denied |
| top50_14_fujiborozoukin (anecdote) | 4 | meta_archaludon (2), meta_grimmsnarl_tonakaiiii (1), meta_grimmsnarl (1) | 15.5 | 25% | grind_loss |
| top50_15_mitomeat823 (anecdote) | 2 | meta_grimmsnarl (1), meta_archaludon (1) | 13.5 | 100% | close_loss |
| other:WinDecks (anecdote) | 2 | meta_grimmsnarl_tonakaiiii (1), meta_archaludon (1) | 14.0 | 50% | close_loss |
| other:kashiwashira (anecdote) | 2 | meta_grimmsnarl_tonakaiiii (2) | 11.5 | 50% | close_loss |
| other:やる気元気ミワハルキ (anecdote) | 2 | top50_14_fujiborozoukin (1), meta_grimmsnarl (1) | 14.0 | 50% | grind_loss |
| other:Majkel1337 (anecdote) | 2 | meta_archaludon (2) | 17.0 | 50% | close_loss |
| other:TTT Is All You Need (anecdote) | 1 | meta_archaludon (1) | 17 | 100% | close_loss |
| other:Kohenyan (anecdote) | 1 | meta_grimmsnarl (1) | 16 | 100% | grind_loss |
| other:vibechu (anecdote) | 1 | meta_grimmsnarl_tonakaiiii (1) | 9 | 100% | grind_loss |
| other:katsudon 421 (anecdote) | 1 | meta_archaludon (1) | 11 | 0% | late_collapse |

## How each losing archetype loses

### meta_grimmsnarl -- 143 losses

- Beaten by: meta_grimmsnarl (58), meta_archaludon (29), meta_grimmsnarl_tonakaiiii (22), other:Boss's Orders Are All You Need (10), top50_08_kashiwashira (6), top50_04_third_ptcg_club (6)
- Loss shapes: grind_loss (53), deckout (45), close_loss (28), setup_denied (9), late_collapse (8)
- Median kill turn 15; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### meta_grimmsnarl_tonakaiiii -- 103 losses

- Beaten by: meta_grimmsnarl (44), meta_archaludon (20), meta_grimmsnarl_tonakaiiii (17), top50_04_third_ptcg_club (5), top50_13_windecks (4), top50_08_kashiwashira (3)
- Loss shapes: grind_loss (46), close_loss (40), deckout (8), late_collapse (6), setup_denied (3)
- Median kill turn 13; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### meta_archaludon -- 100 losses

- Beaten by: meta_grimmsnarl (36), meta_grimmsnarl_tonakaiiii (18), meta_archaludon (16), top50_13_windecks (6), top50_08_kashiwashira (6), other:zoroark190 (4)
- Loss shapes: grind_loss (42), late_collapse (26), close_loss (13), setup_denied (11), deckout (8)
- Median kill turn 13.0; at loss, this archetype had 5.0 prizes left to take (median) while the winner had 2.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_04_third_ptcg_club -- 28 losses

- Beaten by: meta_grimmsnarl (10), meta_archaludon (7), meta_grimmsnarl_tonakaiiii (4), other:Boss's Orders Are All You Need (3), top50_13_windecks (2), top50_08_kashiwashira (2)
- Loss shapes: late_collapse (10), grind_loss (8), deckout (7), setup_denied (2), close_loss (1)
- Median kill turn 19.5; at loss, this archetype had 5.5 prizes left to take (median) while the winner had 3.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_06_imanoob1122 -- 18 losses

- Beaten by: meta_archaludon (9), meta_grimmsnarl (4), meta_grimmsnarl_tonakaiiii (2), other:Boss's Orders Are All You Need (1), top50_08_kashiwashira (1), other:zoroark190 (1)
- Loss shapes: grind_loss (11), close_loss (4), deckout (3)
- Median kill turn 14.5; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 1.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_15_mitomeat823 -- 13 losses

- Beaten by: meta_grimmsnarl (8), meta_archaludon (2), other:Boss's Orders Are All You Need (1), meta_grimmsnarl_tonakaiiii (1), top50_13_windecks (1)
- Loss shapes: grind_loss (5), close_loss (3), setup_denied (3), deckout (2)
- Median kill turn 13; at loss, this archetype had 3 prizes left to take (median) while the winner had 3 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_14_fujiborozoukin -- 12 losses

- Beaten by: meta_archaludon (5), meta_grimmsnarl (2), top50_08_kashiwashira (1), other:Boss's Orders Are All You Need (1), top50_04_third_ptcg_club (1), meta_grimmsnarl_tonakaiiii (1)
- Loss shapes: grind_loss (7), close_loss (3), deckout (1), setup_denied (1)
- Median kill turn 13.5; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 3.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_13_windecks -- 10 losses

- Beaten by: meta_grimmsnarl (6), meta_grimmsnarl_tonakaiiii (4)
- Loss shapes: late_collapse (3), grind_loss (2), close_loss (2), setup_denied (2), deckout (1)
- Median kill turn 10.5; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 2.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_07_kers_aoyagi -- 9 losses

- Beaten by: meta_grimmsnarl (3), meta_archaludon (3), meta_grimmsnarl_tonakaiiii (2), other:zoroark190 (1)
- Loss shapes: late_collapse (4), setup_denied (3), grind_loss (2)
- Median kill turn 18; at loss, this archetype had 6 prizes left to take (median) while the winner had 3 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_08_kashiwashira -- 8 losses

- Beaten by: meta_archaludon (4), meta_grimmsnarl_tonakaiiii (2), meta_grimmsnarl (2)
- Loss shapes: grind_loss (6), deckout (2)
- Median kill turn 15.5; at loss, this archetype had 5.0 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_25_ajishio -- 8 losses

- Beaten by: meta_grimmsnarl (4), meta_archaludon (2), top50_13_windecks (1), other:Boss's Orders Are All You Need (1)
- Loss shapes: grind_loss (3), deckout (3), close_loss (2)
- Median kill turn 13.5; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_35_ajishio -- 5 losses

- Beaten by: meta_grimmsnarl (5)
- Loss shapes: deckout (2), grind_loss (2), close_loss (1)
- Median kill turn 15; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### other:S4nkurero -- 2 losses (ANECDOTE, n < 5)

- Beaten by: meta_grimmsnarl_tonakaiiii (1), meta_archaludon (1)
- Loss shapes: setup_denied (1), grind_loss (1)
- Median kill turn 6.5; at loss, this archetype had 5.0 prizes left to take (median) while the winner had 3.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### other:RtoABC -- 1 losses (ANECDOTE, n < 5)

- Beaten by: meta_grimmsnarl (1)
- Loss shapes: close_loss (1)
- Median kill turn 19; at loss, this archetype had 1 prizes left to take (median) while the winner had 2 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

## Method notes

- Losing archetype: the top-50 team's OWN decklist for that game, taken straight from data/derived/top50_harvest.json (already computed by tools/top50_harvest.py).
- Winning archetype: re-derived from the SAME episode JSON's opening decklist (analysis.expert_cohort.seat_decklists) via the same 3-family signature set (meta_archaludon / meta_grimmsnarl / meta_grimmsnarl_tonakaiiii); anything else resolves to a top50_harvest.py deck slug when the exact 60-card list matches one, otherwise "other:<team name>".
- Winner rank/rating is reported only when the winner is ALSO one of the harvested top-50 teams (looked up in the same harvest snapshot); this repo has no working broader leaderboard snapshot to resolve a rating for a winner outside the top 50 (data/leaderboard_cache/leaderboard_2026_07_05.csv is a stale kaggle-CLI error dump, not real leaderboard data).
- Loss shape buckets (deckout / setup_denied / late_collapse / close_loss / outraced / grind_loss) are a purpose-built decision tree over the same board-state fields analysis.loss_classifier.parse_replay already extracts (deck/bench/prize end-state); they reuse those SIGNALS, not our own agent's classify_loss BUCKETS or thresholds tuned for search-agent losses. See tools/top50_loss_modes.py:classify_loss_shape.
- "Winning line" is reported as game length (n_turns, the kill-turn signal the task asked for) and both seats' final remaining-prize counts, not a per-turn card-play timeline: a spot check of the replay JSON found the decision-to-chosen-option correlation is not reliably resolvable from the fields inspected (see module docstring), so no first-attack-turn or per-card timeline is claimed here.
- winner_prize_remaining is 1 at minimum across all 460 resolved losses, never 0: this replay format's last captured decision always precedes the actual game-ending move, so a genuine finished prize race shows up as "1 left", not "0 left". "prize race complete rate" therefore uses <=1, not ==0, as the winner-finished-a-real-prize-race signal.

