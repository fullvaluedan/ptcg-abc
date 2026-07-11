# Top-50 loss modes: how they lose

Generated from C:\Users\danom\ptcg-abc\data\derived\top50_harvest.json (harvest generated 2026-07-11T13:49:17.385790Z). 460 losses found across the top-50 teams' harvested windows; 460 resolved against their episode JSON and analyzed below, 0 could not be resolved (see Unresolved below).

Every claim below carries its game count (n). Any bucket with n < 5 is flagged **anecdote** and should not be read as a trend.

## Predator table: who beats the top-50 field, and how

Every winning archetype across ALL top-50 losses, ranked by kills. "Prize race complete" = the winner's own remaining-prize count was <=1 at the last captured decision (this replay format's observed floor is 1, never 0 -- the last decision logged always precedes the actual game-ending move, so <=1 is the closest signal to "the winner finished a normal KO-based prize race" this data supports; see Method notes). A LOW rate means that archetype's kills mostly end the game some other way (the loser deckout-ing or collapsing) while the winner still had several prizes left.

| winner archetype | kills | top victims | median kill turn | prize race complete rate | dominant loss shape inflicted |
|---|---|---|---|---|---|
| top50_02_bono_meta_grimmsnarl | 67 | meta_grimmsnarl_tonakaiiii (13), top50_03_ebi_meta_grimmsnarl (9), top50_05_budew_meta_archaludon (5), top50_02_bono_meta_grimmsnarl (4) | 14 | 64% | grind_loss |
| top50_05_budew_meta_archaludon | 36 | top50_02_bono_meta_grimmsnarl (8), meta_grimmsnarl_tonakaiiii (8), top50_23_liamk_meta_grimmsnarl (3), top50_04_third_ptcg_club (3) | 20.0 | 44% | deckout |
| top50_03_ebi_meta_grimmsnarl | 32 | meta_grimmsnarl_tonakaiiii (8), top50_04_third_ptcg_club (4), top50_03_ebi_meta_grimmsnarl (3), top50_10_legend_brothers_meta_archaludon (2) | 12.0 | 50% | grind_loss |
| top50_17_nasuo445_meta_grimmsnarl_tonakaiiii | 30 | meta_grimmsnarl_tonakaiiii (8), top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii (3), top50_11_alberto_bonsanto_meta_archaludon (3), top50_16_btk15049_meta_archaludon (3) | 13.0 | 43% | grind_loss |
| meta_grimmsnarl_tonakaiiii | 29 | top50_02_bono_meta_grimmsnarl (7), top50_08_kashiwashira (2), top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii (2), top50_03_ebi_meta_grimmsnarl (2) | 13 | 72% | grind_loss |
| meta_grimmsnarl | 29 | top50_03_ebi_meta_grimmsnarl (4), meta_grimmsnarl_tonakaiiii (3), top50_15_mitomeat823 (3), top50_27_ebisu_ya_meta_grimmsnarl (2) | 11 | 55% | grind_loss |
| top50_11_alberto_bonsanto_meta_archaludon | 26 | meta_grimmsnarl_tonakaiiii (5), top50_10_legend_brothers_meta_archaludon (2), top50_06_imanoob1122 (2), top50_04_third_ptcg_club (2) | 22.0 | 38% | deckout |
| other:Boss's Orders Are All You Need | 20 | top50_02_bono_meta_grimmsnarl (4), top50_03_ebi_meta_grimmsnarl (3), top50_04_third_ptcg_club (3), top50_23_liamk_meta_grimmsnarl (1) | 18.0 | 0% | deckout |
| top50_13_windecks | 20 | meta_grimmsnarl_tonakaiiii (4), top50_03_ebi_meta_grimmsnarl (3), top50_09_dung_o_meta_archaludon (2), top50_04_third_ptcg_club (2) | 10.0 | 50% | grind_loss |
| top50_08_kashiwashira | 19 | top50_11_alberto_bonsanto_meta_archaludon (3), top50_02_bono_meta_grimmsnarl (3), top50_23_liamk_meta_grimmsnarl (2), top50_09_dung_o_meta_archaludon (2) | 13 | 47% | grind_loss |
| top50_23_liamk_meta_grimmsnarl | 15 | top50_02_bono_meta_grimmsnarl (3), top50_03_ebi_meta_grimmsnarl (2), top50_25_ajishio (2), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1) | 15 | 60% | grind_loss |
| top50_04_third_ptcg_club | 15 | meta_grimmsnarl_tonakaiiii (5), top50_02_bono_meta_grimmsnarl (2), top50_09_dung_o_meta_archaludon (2), top50_03_ebi_meta_grimmsnarl (2) | 22 | 40% | deckout |
| top50_29_capbloo_meta_grimmsnarl | 12 | top50_15_mitomeat823 (3), top50_02_bono_meta_grimmsnarl (2), other:LumenLiquidity (1), top50_11_alberto_bonsanto_meta_archaludon (1) | 11.0 | 50% | grind_loss |
| other:taksai | 9 | top50_04_third_ptcg_club (2), top50_14_fujiborozoukin (2), top50_03_ebi_meta_grimmsnarl (2), top50_09_dung_o_meta_archaludon (1) | 11 | 44% | grind_loss |
| other:zoroark190 | 9 | meta_grimmsnarl_tonakaiiii (3), meta_archaludon (2), top50_21_shg195_meta_archaludon (2), top50_07_kers_aoyagi (1) | 10 | 44% | grind_loss |
| top50_09_dung_o_meta_archaludon | 8 | meta_grimmsnarl_tonakaiiii (2), top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii (1), top50_29_capbloo_meta_grimmsnarl (1), top50_06_imanoob1122 (1) | 23.0 | 38% | grind_loss |
| top50_31_capbloo_meta_grimmsnarl | 7 | top50_13_windecks (2), top50_02_bono_meta_grimmsnarl (1), top50_05_budew_meta_archaludon (1), top50_03_ebi_meta_grimmsnarl (1) | 11 | 57% | grind_loss |
| top50_30_majkel1337_meta_grimmsnarl | 6 | top50_05_budew_meta_archaludon (5), meta_grimmsnarl_tonakaiiii (1) | 10.5 | 17% | grind_loss |
| top50_10_legend_brothers_meta_archaludon | 6 | top50_08_kashiwashira (2), top50_23_liamk_meta_grimmsnarl (1), meta_grimmsnarl_tonakaiiii (1), top50_29_capbloo_meta_grimmsnarl (1) | 20.5 | 50% | grind_loss |
| other:ZETADIVISION | 5 | top50_02_bono_meta_grimmsnarl (1), top50_05_budew_meta_archaludon (1), top50_04_third_ptcg_club (1), top50_15_mitomeat823 (1) | 13 | 100% | grind_loss |
| other:Michael Long | 5 | meta_grimmsnarl_tonakaiiii (4), top50_03_ebi_meta_grimmsnarl (1) | 12 | 60% | close_loss |
| other:e-toppo (anecdote) | 4 | top50_13_windecks (1), meta_grimmsnarl_tonakaiiii (1), top50_02_bono_meta_grimmsnarl (1), top50_03_ebi_meta_grimmsnarl (1) | 44.0 | 0% | deckout |
| top50_06_imanoob1122 (anecdote) | 4 | top50_27_ebisu_ya_meta_grimmsnarl (2), meta_grimmsnarl_tonakaiiii (1), top50_11_alberto_bonsanto_meta_archaludon (1) | 6.5 | 50% | setup_denied |
| top50_14_fujiborozoukin (anecdote) | 4 | meta_grimmsnarl_tonakaiiii (1), top50_28_rtoabc_meta_archaludon (1), meta_archaludon (1), top50_02_bono_meta_grimmsnarl (1) | 15.5 | 25% | grind_loss |
| meta_archaludon (anecdote) | 4 | top50_32_lumenliquidity_meta_grimmsnarl (1), top50_03_ebi_meta_grimmsnarl (1), top50_06_imanoob1122 (1), top50_25_ajishio (1) | 17.5 | 50% | grind_loss |
| other:Raihan Ramadistra (anecdote) | 3 | meta_grimmsnarl_tonakaiiii (2), top50_15_mitomeat823 (1) | 14 | 0% | deckout |
| top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii (anecdote) | 3 | top50_03_ebi_meta_grimmsnarl (1), meta_archaludon (1), meta_grimmsnarl_tonakaiiii (1) | 14 | 100% | close_loss |
| other:THIRD PTCG Club (anecdote) | 3 | meta_grimmsnarl_tonakaiiii (2), top50_07_kers_aoyagi (1) | 11 | 33% | grind_loss |
| other:aaa (anecdote) | 2 | top50_27_ebisu_ya_meta_grimmsnarl (1), top50_21_shg195_meta_archaludon (1) | 12.0 | 50% | grind_loss |
| top50_15_mitomeat823 (anecdote) | 2 | top50_03_ebi_meta_grimmsnarl (1), top50_21_shg195_meta_archaludon (1) | 13.5 | 100% | close_loss |
| other:WinDecks (anecdote) | 2 | meta_grimmsnarl_tonakaiiii (1), other:S4nkurero (1) | 14.0 | 50% | close_loss |
| other:kashiwashira (anecdote) | 2 | meta_grimmsnarl_tonakaiiii (1), other:LumenLiquidity (1) | 11.5 | 50% | close_loss |
| other:やる気元気ミワハルキ (anecdote) | 2 | top50_14_fujiborozoukin (1), top50_24_haggle_meta_grimmsnarl (1) | 14.0 | 50% | grind_loss |
| other:Yushin Ito (anecdote) | 2 | top50_07_kers_aoyagi (2) | 12.5 | 0% | grind_loss |
| other:Majkel1337 (anecdote) | 2 | top50_21_shg195_meta_archaludon (2) | 17.0 | 50% | close_loss |
| top50_28_rtoabc_meta_archaludon (anecdote) | 1 | top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1) | 16 | 100% | close_loss |
| other:koga_poke (anecdote) | 1 | top50_27_ebisu_ya_meta_grimmsnarl (1) | 14 | 0% | deckout |
| other:チームロスギラ (anecdote) | 1 | other:RtoABC (1) | 19 | 0% | close_loss |
| other:TTT Is All You Need (anecdote) | 1 | other:RtoABC (1) | 17 | 100% | close_loss |
| top50_16_btk15049_meta_archaludon (anecdote) | 1 | other:S4nkurero (1) | 10 | 100% | grind_loss |
| other:Kohenyan (anecdote) | 1 | top50_32_lumenliquidity_meta_grimmsnarl (1) | 16 | 100% | grind_loss |
| other:monnosuke (anecdote) | 1 | top50_32_lumenliquidity_meta_grimmsnarl (1) | 20 | 100% | grind_loss |
| other:sqrt4kaido (anecdote) | 1 | top50_32_lumenliquidity_meta_grimmsnarl (1) | 16 | 0% | late_collapse |
| other:Pixegami (anecdote) | 1 | top50_32_lumenliquidity_meta_grimmsnarl (1) | 2 | 0% | setup_denied |
| other:vibechu (anecdote) | 1 | meta_grimmsnarl_tonakaiiii (1) | 9 | 100% | grind_loss |
| other:Gengar (anecdote) | 1 | top50_16_btk15049_meta_archaludon (1) | 15 | 100% | grind_loss |
| other:ykuroka (anecdote) | 1 | meta_archaludon (1) | 21 | 0% | deckout |
| other:Dongwook Kim (anecdote) | 1 | meta_archaludon (1) | 15 | 0% | grind_loss |
| other:katsudon 421 (anecdote) | 1 | meta_archaludon (1) | 11 | 0% | late_collapse |
| other:Ruko (anecdote) | 1 | top50_02_bono_meta_grimmsnarl (1) | 11 | 0% | grind_loss |
| other:Brady Meighan (anecdote) | 1 | top50_21_shg195_meta_archaludon (1) | 18 | 0% | grind_loss |

## How each losing archetype loses

### meta_grimmsnarl_tonakaiiii -- 81 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (13), top50_03_ebi_meta_grimmsnarl (8), top50_05_budew_meta_archaludon (8), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (8), top50_04_third_ptcg_club (5), top50_11_alberto_bonsanto_meta_archaludon (5)
- Loss shapes: grind_loss (38), close_loss (33), late_collapse (4), setup_denied (3), deckout (3)
- Median kill turn 13; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_02_bono_meta_grimmsnarl -- 43 losses

- Beaten by: top50_05_budew_meta_archaludon (8), meta_grimmsnarl_tonakaiiii (7), top50_02_bono_meta_grimmsnarl (4), other:Boss's Orders Are All You Need (4), top50_23_liamk_meta_grimmsnarl (3), top50_08_kashiwashira (3)
- Loss shapes: deckout (21), grind_loss (15), close_loss (5), late_collapse (1), setup_denied (1)
- Median kill turn 17; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_03_ebi_meta_grimmsnarl -- 38 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (9), meta_grimmsnarl (4), top50_13_windecks (3), other:Boss's Orders Are All You Need (3), top50_03_ebi_meta_grimmsnarl (3), top50_23_liamk_meta_grimmsnarl (2)
- Loss shapes: grind_loss (12), close_loss (12), deckout (11), setup_denied (3)
- Median kill turn 13.0; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_04_third_ptcg_club -- 28 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (4), top50_03_ebi_meta_grimmsnarl (4), other:Boss's Orders Are All You Need (3), top50_05_budew_meta_archaludon (3), other:taksai (2), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (2)
- Loss shapes: late_collapse (10), grind_loss (8), deckout (7), setup_denied (2), close_loss (1)
- Median kill turn 19.5; at loss, this archetype had 5.5 prizes left to take (median) while the winner had 3.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### meta_archaludon -- 19 losses

- Beaten by: top50_03_ebi_meta_grimmsnarl (2), other:zoroark190 (2), meta_grimmsnarl (2), top50_05_budew_meta_archaludon (2), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1), other:ykuroka (1)
- Loss shapes: late_collapse (8), grind_loss (5), close_loss (3), setup_denied (2), deckout (1)
- Median kill turn 11; at loss, this archetype had 5 prizes left to take (median) while the winner had 2 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_05_budew_meta_archaludon -- 18 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (5), top50_30_majkel1337_meta_grimmsnarl (5), top50_11_alberto_bonsanto_meta_archaludon (1), top50_03_ebi_meta_grimmsnarl (1), top50_13_windecks (1), top50_08_kashiwashira (1)
- Loss shapes: grind_loss (12), late_collapse (2), setup_denied (2), deckout (1), close_loss (1)
- Median kill turn 13.0; at loss, this archetype had 6.0 prizes left to take (median) while the winner had 2.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_06_imanoob1122 -- 18 losses

- Beaten by: top50_05_budew_meta_archaludon (3), top50_11_alberto_bonsanto_meta_archaludon (2), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (2), top50_02_bono_meta_grimmsnarl (2), meta_grimmsnarl (1), top50_09_dung_o_meta_archaludon (1)
- Loss shapes: grind_loss (11), close_loss (4), deckout (3)
- Median kill turn 14.5; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 1.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_11_alberto_bonsanto_meta_archaludon -- 14 losses

- Beaten by: top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (3), top50_08_kashiwashira (3), top50_11_alberto_bonsanto_meta_archaludon (1), top50_03_ebi_meta_grimmsnarl (1), top50_13_windecks (1), top50_06_imanoob1122 (1)
- Loss shapes: late_collapse (8), setup_denied (4), deckout (1), grind_loss (1)
- Median kill turn 11.0; at loss, this archetype had 6.0 prizes left to take (median) while the winner had 3.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_15_mitomeat823 -- 13 losses

- Beaten by: meta_grimmsnarl (3), top50_29_capbloo_meta_grimmsnarl (3), top50_11_alberto_bonsanto_meta_archaludon (1), other:Boss's Orders Are All You Need (1), other:ZETADIVISION (1), top50_13_windecks (1)
- Loss shapes: grind_loss (5), close_loss (3), setup_denied (3), deckout (2)
- Median kill turn 13; at loss, this archetype had 3 prizes left to take (median) while the winner had 3 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_21_shg195_meta_archaludon -- 13 losses

- Beaten by: meta_grimmsnarl_tonakaiiii (2), other:Majkel1337 (2), other:zoroark190 (2), top50_03_ebi_meta_grimmsnarl (1), top50_15_mitomeat823 (1), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1)
- Loss shapes: grind_loss (8), close_loss (3), setup_denied (1), deckout (1)
- Median kill turn 13; at loss, this archetype had 5 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii -- 12 losses

- Beaten by: top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (3), top50_02_bono_meta_grimmsnarl (3), meta_grimmsnarl_tonakaiiii (2), meta_grimmsnarl (1), top50_09_dung_o_meta_archaludon (1), top50_11_alberto_bonsanto_meta_archaludon (1)
- Loss shapes: grind_loss (7), close_loss (4), deckout (1)
- Median kill turn 16.5; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_14_fujiborozoukin -- 12 losses

- Beaten by: top50_05_budew_meta_archaludon (2), other:taksai (2), top50_08_kashiwashira (1), other:Boss's Orders Are All You Need (1), top50_09_dung_o_meta_archaludon (1), top50_04_third_ptcg_club (1)
- Loss shapes: grind_loss (7), close_loss (3), deckout (1), setup_denied (1)
- Median kill turn 13.5; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 3.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_23_liamk_meta_grimmsnarl -- 11 losses

- Beaten by: top50_05_budew_meta_archaludon (3), top50_08_kashiwashira (2), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1), top50_02_bono_meta_grimmsnarl (1), other:Boss's Orders Are All You Need (1), top50_04_third_ptcg_club (1)
- Loss shapes: deckout (6), grind_loss (4), close_loss (1)
- Median kill turn 23; at loss, this archetype had 4 prizes left to take (median) while the winner had 2 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_16_btk15049_meta_archaludon -- 11 losses

- Beaten by: top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (3), top50_02_bono_meta_grimmsnarl (2), top50_03_ebi_meta_grimmsnarl (1), other:ZETADIVISION (1), top50_11_alberto_bonsanto_meta_archaludon (1), other:Gengar (1)
- Loss shapes: grind_loss (6), close_loss (4), late_collapse (1)
- Median kill turn 17; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_24_haggle_meta_grimmsnarl -- 11 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (3), top50_03_ebi_meta_grimmsnarl (1), other:Boss's Orders Are All You Need (1), top50_05_budew_meta_archaludon (1), meta_grimmsnarl (1), top50_11_alberto_bonsanto_meta_archaludon (1)
- Loss shapes: deckout (4), grind_loss (3), close_loss (2), late_collapse (2)
- Median kill turn 17; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_09_dung_o_meta_archaludon -- 10 losses

- Beaten by: top50_13_windecks (2), top50_04_third_ptcg_club (2), top50_08_kashiwashira (2), top50_05_budew_meta_archaludon (1), top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (1), top50_11_alberto_bonsanto_meta_archaludon (1)
- Loss shapes: late_collapse (7), setup_denied (2), deckout (1)
- Median kill turn 18.0; at loss, this archetype had 4.5 prizes left to take (median) while the winner had 2.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_13_windecks -- 10 losses

- Beaten by: top50_17_nasuo445_meta_grimmsnarl_tonakaiiii (2), top50_31_capbloo_meta_grimmsnarl (2), top50_02_bono_meta_grimmsnarl (2), meta_grimmsnarl_tonakaiiii (1), top50_03_ebi_meta_grimmsnarl (1), other:e-toppo (1)
- Loss shapes: late_collapse (3), grind_loss (2), close_loss (2), setup_denied (2), deckout (1)
- Median kill turn 10.5; at loss, this archetype had 3.0 prizes left to take (median) while the winner had 2.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### meta_grimmsnarl -- 10 losses

- Beaten by: meta_grimmsnarl_tonakaiiii (2), top50_02_bono_meta_grimmsnarl (2), meta_grimmsnarl (1), top50_13_windecks (1), top50_03_ebi_meta_grimmsnarl (1), top50_08_kashiwashira (1)
- Loss shapes: grind_loss (5), close_loss (3), late_collapse (1), setup_denied (1)
- Median kill turn 12.5; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 1.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_07_kers_aoyagi -- 9 losses

- Beaten by: meta_grimmsnarl_tonakaiiii (2), top50_03_ebi_meta_grimmsnarl (2), other:Yushin Ito (2), other:THIRD PTCG Club (1), other:zoroark190 (1), top50_11_alberto_bonsanto_meta_archaludon (1)
- Loss shapes: late_collapse (4), setup_denied (3), grind_loss (2)
- Median kill turn 18; at loss, this archetype had 6 prizes left to take (median) while the winner had 3 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_08_kashiwashira -- 8 losses

- Beaten by: meta_grimmsnarl_tonakaiiii (2), top50_10_legend_brothers_meta_archaludon (2), top50_11_alberto_bonsanto_meta_archaludon (1), top50_05_budew_meta_archaludon (1), meta_grimmsnarl (1), top50_02_bono_meta_grimmsnarl (1)
- Loss shapes: grind_loss (6), deckout (2)
- Median kill turn 15.5; at loss, this archetype had 5.0 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_17_nasuo445_meta_grimmsnarl_tonakaiiii -- 8 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (2), meta_grimmsnarl (1), top50_28_rtoabc_meta_archaludon (1), meta_grimmsnarl_tonakaiiii (1), other:Boss's Orders Are All You Need (1), top50_23_liamk_meta_grimmsnarl (1)
- Loss shapes: deckout (4), close_loss (3), late_collapse (1)
- Median kill turn 14.5; at loss, this archetype had 2.0 prizes left to take (median) while the winner had 2.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_25_ajishio -- 8 losses

- Beaten by: top50_23_liamk_meta_grimmsnarl (2), meta_grimmsnarl (2), top50_13_windecks (1), other:Boss's Orders Are All You Need (1), meta_archaludon (1), top50_05_budew_meta_archaludon (1)
- Loss shapes: grind_loss (3), deckout (3), close_loss (2)
- Median kill turn 13.5; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_27_ebisu_ya_meta_grimmsnarl -- 7 losses

- Beaten by: top50_06_imanoob1122 (2), meta_grimmsnarl (2), top50_13_windecks (1), other:aaa (1), other:koga_poke (1)
- Loss shapes: grind_loss (3), setup_denied (2), close_loss (1), deckout (1)
- Median kill turn 10; at loss, this archetype had 5 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_10_legend_brothers_meta_archaludon -- 6 losses

- Beaten by: top50_11_alberto_bonsanto_meta_archaludon (2), top50_03_ebi_meta_grimmsnarl (2), top50_13_windecks (1), other:Boss's Orders Are All You Need (1)
- Loss shapes: grind_loss (3), deckout (3)
- Median kill turn 17.0; at loss, this archetype had 5.0 prizes left to take (median) while the winner had 4.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_28_rtoabc_meta_archaludon -- 6 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (2), meta_grimmsnarl_tonakaiiii (1), top50_14_fujiborozoukin (1), top50_11_alberto_bonsanto_meta_archaludon (1), top50_23_liamk_meta_grimmsnarl (1)
- Loss shapes: grind_loss (5), close_loss (1)
- Median kill turn 13.0; at loss, this archetype had 3.5 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_32_lumenliquidity_meta_grimmsnarl -- 6 losses

- Beaten by: top50_03_ebi_meta_grimmsnarl (1), other:Kohenyan (1), other:monnosuke (1), other:sqrt4kaido (1), other:Pixegami (1), meta_archaludon (1)
- Loss shapes: grind_loss (4), late_collapse (1), setup_denied (1)
- Median kill turn 15.0; at loss, this archetype had 4.5 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_30_majkel1337_meta_grimmsnarl -- 5 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (4), top50_05_budew_meta_archaludon (1)
- Loss shapes: grind_loss (3), setup_denied (1), deckout (1)
- Median kill turn 13; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_29_capbloo_meta_grimmsnarl -- 5 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (1), top50_03_ebi_meta_grimmsnarl (1), top50_09_dung_o_meta_archaludon (1), top50_10_legend_brothers_meta_archaludon (1), meta_grimmsnarl_tonakaiiii (1)
- Loss shapes: late_collapse (3), close_loss (2)
- Median kill turn 16; at loss, this archetype had 2 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_35_ajishio -- 5 losses

- Beaten by: top50_02_bono_meta_grimmsnarl (3), top50_29_capbloo_meta_grimmsnarl (1), meta_grimmsnarl (1)
- Loss shapes: deckout (2), grind_loss (2), close_loss (1)
- Median kill turn 15; at loss, this archetype had 3 prizes left to take (median) while the winner had 1 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_31_capbloo_meta_grimmsnarl -- 4 losses (ANECDOTE, n < 5)

- Beaten by: meta_grimmsnarl (2), meta_grimmsnarl_tonakaiiii (1), top50_02_bono_meta_grimmsnarl (1)
- Loss shapes: grind_loss (3), close_loss (1)
- Median kill turn 16.0; at loss, this archetype had 6.0 prizes left to take (median) while the winner had 1.0 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### other:S4nkurero -- 4 losses (ANECDOTE, n < 5)

- Beaten by: meta_grimmsnarl_tonakaiiii (1), top50_16_btk15049_meta_archaludon (1), top50_02_bono_meta_grimmsnarl (1), other:WinDecks (1)
- Loss shapes: grind_loss (3), setup_denied (1)
- Median kill turn 12.5; at loss, this archetype had 4.5 prizes left to take (median) while the winner had 1.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### top50_34_ebisu_ya_meta_grimmsnarl -- 3 losses (ANECDOTE, n < 5)

- Beaten by: top50_03_ebi_meta_grimmsnarl (1), top50_23_liamk_meta_grimmsnarl (1), top50_04_third_ptcg_club (1)
- Loss shapes: close_loss (1), grind_loss (1), deckout (1)
- Median kill turn 15; at loss, this archetype had 3 prizes left to take (median) while the winner had 2 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### other:RtoABC -- 2 losses (ANECDOTE, n < 5)

- Beaten by: other:チームロスギラ (1), other:TTT Is All You Need (1)
- Loss shapes: close_loss (2)
- Median kill turn 18.0; at loss, this archetype had 1.5 prizes left to take (median) while the winner had 1.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

### other:LumenLiquidity -- 2 losses (ANECDOTE, n < 5)

- Beaten by: top50_29_capbloo_meta_grimmsnarl (1), other:kashiwashira (1)
- Loss shapes: late_collapse (1), grind_loss (1)
- Median kill turn 12.0; at loss, this archetype had 5.5 prizes left to take (median) while the winner had 2.5 left (median; 1 is this format's observed floor for a finished prize race, see Method notes -- higher means the game ended some other way while the winner still had prizes to go).

## Method notes

- Losing archetype: the top-50 team's OWN decklist for that game, taken straight from data/derived/top50_harvest.json (already computed by tools/top50_harvest.py).
- Winning archetype: re-derived from the SAME episode JSON's opening decklist (analysis.expert_cohort.seat_decklists) via the same 3-family signature set (meta_archaludon / meta_grimmsnarl / meta_grimmsnarl_tonakaiiii); anything else resolves to a top50_harvest.py deck slug when the exact 60-card list matches one, otherwise "other:<team name>".
- Classifier decontamination: family signatures have generic format staples (Buddy-Buddy Poffin, Ultra Ball, Pokegear 3.0, Poke Pad, Lillie's Determination, Boss's Orders, Judge, Night Stretcher, Wally's Compassion, Dawn, Rare Candy, Carmine, Dusk Ball, Bug Catching Set, Canari, Team Rocket's Factory -- the same list top50_win_mechanisms.md's own methodology excludes from separator-card candidacy) stripped from BOTH the coverage numerator and denominator before classify_family scores a deck (tools/top50_loss_modes.py:STAPLE_CARD_IDS / decontaminate_signatures), so a deck that shares only staples with a family signature can no longer clear the 0.35 coverage threshold on staple overlap alone. Without this, a deck with zero archetype-defining cards in common with a family (verified real cases: nasuo445's Cynthia's Garchomp ex toolbox, ZETADIVISION's Dragapult ex toolbox) cleared threshold and polluted that family's win/loss and predator counts; analysis.expert_cohort.py itself is unmodified, only the signatures dict passed into it is pre-shrunk. The effect is large, not anecdotal: several teams previously pooled under meta_grimmsnarl (e.g. bono's exact decklist, shared with wkonishi/soyukke/Majkel1337) carry none of Marnie's Impidimp / Morgrem / Grimmsnarl ex / Morpeko at all (only the generic Dunsparce/Dudunsparce draw engine and Xerosic's Machinations, both shared with other archetypes), so meta_grimmsnarl's kill count drops from 183 to 29 below; the magnitude matches the independently measured 94-of-98 (95.9%) contamination rate on meta_archaludon-labeled winners, which drops from 98 to 4 kills here.
- Legacy slug-name residue: a top50_NN_<team>_meta_<family> "other" fallback slug was minted by tools/top50_harvest.py, which still runs the UNDECONTAMINATED classifier for its own CSV filenames (regenerating top50_harvest.md itself is out of scope here; this tool only reads that file, never writes it). A deck that no longer clears a named family's decontaminated threshold correctly falls out of that family's counts, but the slug text it falls back to can still carry a stale "_meta_grimmsnarl" / "_meta_archaludon" / "_meta_grimmsnarl_tonakaiiii" suffix from that old classification (e.g. top50_02_bono_meta_grimmsnarl, see above). Read every top50_NN_* row below as an opaque per-deck identifier, not an archetype claim.
- Winner rank/rating is reported only when the winner is ALSO one of the harvested top-50 teams (looked up in the same harvest snapshot); this repo has no working broader leaderboard snapshot to resolve a rating for a winner outside the top 50 (data/leaderboard_cache/leaderboard_2026_07_05.csv is a stale kaggle-CLI error dump, not real leaderboard data).
- Loss shape buckets (deckout / setup_denied / late_collapse / close_loss / outraced / grind_loss) are a purpose-built decision tree over the same board-state fields analysis.loss_classifier.parse_replay already extracts (deck/bench/prize end-state); they reuse those SIGNALS, not our own agent's classify_loss BUCKETS or thresholds tuned for search-agent losses. See tools/top50_loss_modes.py:classify_loss_shape.
- "Winning line" is reported as game length (n_turns, the kill-turn signal the task asked for) and both seats' final remaining-prize counts, not a per-turn card-play timeline: a spot check of the replay JSON found the decision-to-chosen-option correlation is not reliably resolvable from the fields inspected (see module docstring), so no first-attack-turn or per-card timeline is claimed here.
- winner_prize_remaining is 1 at minimum across all 460 resolved losses, never 0: this replay format's last captured decision always precedes the actual game-ending move, so a genuine finished prize race shows up as "1 left", not "0 left". "prize race complete rate" therefore uses <=1, not ==0, as the winner-finished-a-real-prize-race signal.

