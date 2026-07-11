# Top-50 high-band ring baseline (plan S1, analysis/path_above_1000.md)

Ring: 35 clone:top50_* opponents (decks/top50/, tools/top50_harvest.py). Same-run comparison, alternating seats, n=150 games per arm.

## Headline

Stack (heuristic+yushin+ability+threat_retreat) reads **0.693** (104-0-46, n=150) against the high-band ring, **+21.7pp** below the saturated calibrated-ring read of 0.910 (analysis/path_above_1000.md's S1 gate reference).

Flags-off (heuristic+yushin-flags_off) reads **0.753** (113-0-37, n=150); the ability+threat_retreat lift on this ring is -6.0pp.

Hardest three top50 clones this run (pooled across both arms, by loss rate): clone:top50_11_alberto_bonsanto_meta_archaludon, clone:top50_15_mitomeat823, clone:top50_14_fujiborozoukin

## Per-opponent W/L

| opponent | stack W-D-L | stack win rate | flags-off W-D-L | flags-off win rate |
|---|---|---|---|---|
| clone:top50_01_shota_hirao_meta_grimmsnarl_tonakaiiii | 4-0-1 | 0.800 | 5-0-0 | 1.000 |
| clone:top50_02_bono_meta_grimmsnarl | 2-0-3 | 0.400 | 4-0-1 | 0.800 |
| clone:top50_03_ebi_meta_grimmsnarl | 4-0-1 | 0.800 | 3-0-2 | 0.600 |
| clone:top50_04_third_ptcg_club | 4-0-1 | 0.800 | 5-0-0 | 1.000 |
| clone:top50_05_budew_meta_archaludon | 4-0-1 | 0.800 | 3-0-2 | 0.600 |
| clone:top50_06_imanoob1122 | 4-0-1 | 0.800 | 4-0-1 | 0.800 |
| clone:top50_07_kers_aoyagi | 2-0-3 | 0.400 | 4-0-1 | 0.800 |
| clone:top50_08_kashiwashira | 5-0-0 | 1.000 | 3-0-2 | 0.600 |
| clone:top50_09_dung_o_meta_archaludon | 2-0-3 | 0.400 | 5-0-0 | 1.000 |
| clone:top50_10_legend_brothers_meta_archaludon | 3-0-2 | 0.600 | 3-0-2 | 0.600 |
| clone:top50_11_alberto_bonsanto_meta_archaludon | 1-0-3 | 0.250 | 1-0-3 | 0.250 |
| clone:top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii | 4-0-0 | 1.000 | 4-0-0 | 1.000 |
| clone:top50_13_windecks | 2-0-2 | 0.500 | 3-0-1 | 0.750 |
| clone:top50_14_fujiborozoukin | 2-0-2 | 0.500 | 2-0-2 | 0.500 |
| clone:top50_15_mitomeat823 | 2-0-2 | 0.500 | 1-0-3 | 0.250 |
| clone:top50_16_btk15049_meta_archaludon | 4-0-0 | 1.000 | 4-0-0 | 1.000 |
| clone:top50_17_nasuo445_meta_grimmsnarl_tonakaiiii | 1-0-3 | 0.250 | 3-0-1 | 0.750 |
| clone:top50_18_team18_meta_grimmsnarl | 4-0-0 | 1.000 | 3-0-1 | 0.750 |
| clone:top50_19_payanotty_meta_grimmsnarl_tonakaiiii | 4-0-0 | 1.000 | 4-0-0 | 1.000 |
| clone:top50_20_sota_uchiyama_meta_grimmsnarl_tonakaiiii | 3-0-1 | 0.750 | 4-0-0 | 1.000 |
| clone:top50_21_shg195_meta_archaludon | 4-0-0 | 1.000 | 4-0-0 | 1.000 |
| clone:top50_22_shumpeinomura_meta_archaludon | 3-0-1 | 0.750 | 3-0-1 | 0.750 |
| clone:top50_23_liamk_meta_grimmsnarl | 2-0-2 | 0.500 | 2-0-2 | 0.500 |
| clone:top50_24_haggle_meta_grimmsnarl | 4-0-0 | 1.000 | 3-0-1 | 0.750 |
| clone:top50_25_ajishio | 2-0-2 | 0.500 | 2-0-2 | 0.500 |
| clone:top50_26_zhenyu_zhang_meta_archaludon | 4-0-0 | 1.000 | 3-0-1 | 0.750 |
| clone:top50_27_ebisu_ya_meta_grimmsnarl | 3-0-1 | 0.750 | 3-0-1 | 0.750 |
| clone:top50_28_rtoabc_meta_archaludon | 4-0-0 | 1.000 | 4-0-0 | 1.000 |
| clone:top50_29_capbloo_meta_grimmsnarl | 1-0-3 | 0.250 | 3-0-1 | 0.750 |
| clone:top50_30_majkel1337_meta_grimmsnarl | 3-0-1 | 0.750 | 3-0-1 | 0.750 |
| clone:top50_31_capbloo_meta_grimmsnarl | 2-0-2 | 0.500 | 3-0-1 | 0.750 |
| clone:top50_32_lumenliquidity_meta_grimmsnarl | 2-0-2 | 0.500 | 4-0-0 | 1.000 |
| clone:top50_33_kohei_meta_archaludon | 3-0-1 | 0.750 | 2-0-2 | 0.500 |
| clone:top50_34_ebisu_ya_meta_grimmsnarl | 4-0-0 | 1.000 | 2-0-2 | 0.500 |
| clone:top50_35_ajishio | 2-0-2 | 0.500 | 4-0-0 | 1.000 |

## Notes

- STACK is the current live build: heuristic piloting decks/candidate_yushin_ito.csv with PTCG_ABILITY and PTCG_THREAT_RETREAT both patched on, built via tools.threat_retreat_ring_check._make_agent_factory (its on-arm pattern).
- FLAGS_OFF is the same deck with both flags patched off (the shipped heuristic before either lever), a same-run comparison arm, not the threat_retreat-only off-arm tools/threat_retreat_ring_check.py already measures.
- Ring opponents are `clone:top50_*` (tools.opponents.top50_clone_names()), a separate registration path from the existing calibrated bracket ring (clone_family_names()); this run never touches that ring.

