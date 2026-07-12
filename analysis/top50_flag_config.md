# Flag-configuration experiment on the elite ring

Four arms, all piloting decks/candidate_yushin_ito.csv, factorized by PTCG_ABILITY x PTCG_THREAT_RETREAT: plain (config 1, both off), +ability (config 2), +threat_retreat (config 3), and +ability+threat_retreat (config 4, the live submission's stack). Each pass is same-run: one script execution, round-robin across the full ring, alternating seats, identical opponent order for every arm (mirrors tools/top50_ring.py and tools/stacked_ring_u104.py).

## Context

The live submission ref 54555716 runs config 4 (+ability+threat_retreat). The only prior same-run elite-ring read (analysis/top50_ring_baseline.md, n=150) found config 4 at 0.693 against 0.753 for config 1 (plain) -- a same-run deficit that only ever compared those two arms and never isolated which lever, if either, causes it. This experiment settles that comparison properly at n=100 same-run, with the two middle configs (ability-only, threat_retreat-only) isolating each lever's individual contribution.

## Headline

Elite ring (35 clone:top50_* opponents, n=100 games/arm):

| config | arm | W-D-L | win rate | delta vs plain (pp, same run) |
|---|---|---|---|---|
| 1 | heuristic+yushin-plain | 85-0-15 | 0.850 | +0.0 |
| 2 | heuristic+yushin+ability | 69-0-31 | 0.690 | -16.0 |
| 3 | heuristic+yushin+threat_retreat | 72-1-27 | 0.720 | -13.0 |
| 4 | heuristic+yushin+ability+threat_retreat | 74-0-26 | 0.740 | -11.0 |

Best against elite play: **heuristic+yushin-plain** (config 1) at 0.850. Worst: **heuristic+yushin+ability** (config 2) at 0.690.

Calibrated (old) ring regression guard (9 clone:<family> opponents, n=50 games/arm):

| config | arm | W-D-L | win rate | delta vs plain (pp, same run) |
|---|---|---|---|---|
| 1 | heuristic+yushin-plain | 47-0-3 | 0.940 | +0.0 |
| 2 | heuristic+yushin+ability | 39-0-11 | 0.780 | -16.0 |
| 3 | heuristic+yushin+threat_retreat | 45-0-5 | 0.900 | -4.0 |
| 4 | heuristic+yushin+ability+threat_retreat | 43-0-7 | 0.860 | -8.0 |

Hardest three top50 clones this run (pooled across all four elite-ring arms, by loss rate): clone:top50_14_fujiborozoukin, clone:top50_07_kers_aoyagi, clone:top50_34_ebisu_ya_meta_grimmsnarl

## Per-opponent breakdown, elite ring: best vs worst config

| opponent | heuristic+yushin-plain W-D-L | win rate | heuristic+yushin+ability W-D-L | win rate |
|---|---|---|---|---|
| clone:top50_01_shota_hirao_meta_grimmsnarl_tonakaiiii | 2-0-1 | 0.667 | 3-0-0 | 1.000 |
| clone:top50_02_bono_meta_grimmsnarl | 2-0-1 | 0.667 | 2-0-1 | 0.667 |
| clone:top50_03_ebi_meta_grimmsnarl | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_04_third_ptcg_club | 3-0-0 | 1.000 | 2-0-1 | 0.667 |
| clone:top50_05_budew_meta_archaludon | 3-0-0 | 1.000 | 1-0-2 | 0.333 |
| clone:top50_06_imanoob1122 | 3-0-0 | 1.000 | 2-0-1 | 0.667 |
| clone:top50_07_kers_aoyagi | 1-0-2 | 0.333 | 1-0-2 | 0.333 |
| clone:top50_08_kashiwashira | 3-0-0 | 1.000 | 1-0-2 | 0.333 |
| clone:top50_09_dung_o_meta_archaludon | 2-0-1 | 0.667 | 2-0-1 | 0.667 |
| clone:top50_10_legend_brothers_meta_archaludon | 2-0-1 | 0.667 | 2-0-1 | 0.667 |
| clone:top50_11_alberto_bonsanto_meta_archaludon | 2-0-1 | 0.667 | 3-0-0 | 1.000 |
| clone:top50_12_youtube_com_bigbugginnings_meta_grimmsnarl_tonakaiiii | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_13_windecks | 3-0-0 | 1.000 | 0-0-3 | 0.000 |
| clone:top50_14_fujiborozoukin | 1-0-2 | 0.333 | 1-0-2 | 0.333 |
| clone:top50_15_mitomeat823 | 3-0-0 | 1.000 | 2-0-1 | 0.667 |
| clone:top50_16_btk15049_meta_archaludon | 1-0-2 | 0.333 | 2-0-1 | 0.667 |
| clone:top50_17_nasuo445_meta_grimmsnarl_tonakaiiii | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_18_team18_meta_grimmsnarl | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_19_payanotty_meta_grimmsnarl_tonakaiiii | 3-0-0 | 1.000 | 2-0-1 | 0.667 |
| clone:top50_20_sota_uchiyama_meta_grimmsnarl_tonakaiiii | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_21_shg195_meta_archaludon | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_22_shumpeinomura_meta_archaludon | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_23_liamk_meta_grimmsnarl | 3-0-0 | 1.000 | 1-0-2 | 0.333 |
| clone:top50_24_haggle_meta_grimmsnarl | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_25_ajishio | 2-0-1 | 0.667 | 3-0-0 | 1.000 |
| clone:top50_26_zhenyu_zhang_meta_archaludon | 3-0-0 | 1.000 | 1-0-2 | 0.333 |
| clone:top50_27_ebisu_ya_meta_grimmsnarl | 2-0-1 | 0.667 | 1-0-2 | 0.333 |
| clone:top50_28_rtoabc_meta_archaludon | 3-0-0 | 1.000 | 3-0-0 | 1.000 |
| clone:top50_29_capbloo_meta_grimmsnarl | 2-0-1 | 0.667 | 2-0-1 | 0.667 |
| clone:top50_30_majkel1337_meta_grimmsnarl | 3-0-0 | 1.000 | 2-0-1 | 0.667 |
| clone:top50_31_capbloo_meta_grimmsnarl | 2-0-0 | 1.000 | 2-0-0 | 1.000 |
| clone:top50_32_lumenliquidity_meta_grimmsnarl | 2-0-0 | 1.000 | 2-0-0 | 1.000 |
| clone:top50_33_kohei_meta_archaludon | 2-0-0 | 1.000 | 1-0-1 | 0.500 |
| clone:top50_34_ebisu_ya_meta_grimmsnarl | 1-0-1 | 0.500 | 0-0-2 | 0.000 |
| clone:top50_35_ajishio | 2-0-0 | 1.000 | 1-0-1 | 0.500 |

## Verdict

Best config against elite play this run: **heuristic+yushin-plain** (config 1), 0.850. This is NOT config 4 (the live submission's stack, which reads 0.740 here, -11.0pp vs plain) -- the live submission is not the best-reading config on this elite-ring pass.

## Recommendation (for the second ladder slot; submission is Dan's call)

Recommend **heuristic+yushin-plain** (config 1) for the second ladder slot: it is the best same-run elite-ring reader in this experiment (0.850, n=100), and its calibrated-ring read (0.940, n=50) is provided above as the regression check. This is a recommendation only; the actual second-slot submission remains Dan's call.

## Notes

- Every arm pilots decks/candidate_yushin_ito.csv, built via tools.threat_retreat_ring_check._make_agent_factory (its flag-patching pattern, reused as-is), so only PTCG_ABILITY and PTCG_THREAT_RETREAT vary between arms.
- Elite ring = tools.top50_ring.top50_ring_names() (clone:top50_*, decks/top50/). Calibrated ring = tools.ring_calibrate.ring_names() (clone:<family>, the old 9-clone calibrated ring); the calibrated pass is a regression guard only, not the primary read.
- Each ring's four-arm pass is same-run: sequential within one script execution against the identical ring opponent list and round-robin seat-alternation order, so arm-to-arm deltas within a ring are not confounded by cross-run variance. The elite pass and the calibrated pass are two separate same-run experiments, not one shared run.
- Prior context: live submission ref 54555716 runs config 4 (+ability+threat_retreat). The prior same-run elite-ring read (analysis/top50_ring_baseline.md, n=150, two arms only) found config 4 at 0.693 against 0.753 for config 1.

