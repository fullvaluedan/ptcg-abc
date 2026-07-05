# U39 step 2 correction: new deck candidates scored through the calibrated ring

Full method and the two independent n=40 confirmation runs are recorded in
analysis/candidate_decks_ring_gate.md (the canonical doc for this finding; this file holds the
composition and reproduce notes that doc references).

## Candidate composition (candidate_yushin_ito, the promoted deck)

18 unique card ids across 60 cards, one card at 9 copies (likely a basic energy type given the
same pattern seen in trolley.csv), eight others at 4 copies each. Denser and more varied than
trolley's simpler basic-heavy shell, so this is not simply "another trolley-shaped deck that
happens to look similar." Why this particular top-rated deck is pilotable by the generic
heuristic where Archaludon and Grimmsnarl were not is an open question for the writeup/
comprehension track (U100), not answered here.

## What this confirms and what is genuinely new

Five of six candidates reconfirm the existing pattern (analysis/meta_decks_underperform_on_ladder.md,
state/hypotheses.md's meta_deck_copy row): a harvested top-player deck usually underperforms our own
deck under the generic heuristic pilot. candidate_yushin_ito is the first harvested top-rated deck to
beat our current best build's ring win rate under the SAME generic pilot, confirmed across two
independent n=40 runs (see analysis/candidate_decks_ring_gate.md for the full table).

## Reproduce

```
python tools/select_new_deck_candidates.py --top-k 3 --out data/training/new_deck_candidates_report.json
python tools/score_candidate_decks.py -n 40 --out analysis/candidate_deck_ring_scores.json
```
