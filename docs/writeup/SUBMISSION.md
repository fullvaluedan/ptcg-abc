# How to submit the Strategy writeup on Kaggle

This is the exact click-path for Dan to submit `docs/writeup/final_synthesis.md`
as the team's ONE Strategy-prize Writeup. No em or en dashes anywhere in this repo.

## The one fact that decides everything

A DRAFT DOES NOT COUNT. The writeup must be explicitly Submitted before the
deadline, and each team may submit only ONE Writeup (Hackathon rule 2.2.a,
`analysis/strategy_prize_rules.md`). Saving is not submitting. Do the final
Submit click and confirm the status flips to Submitted.

## Deadline

- Final submission: 2026-09-13, 11:59 PM UTC (`analysis/strategy_prize_rules.md`).
- Do it earlier. Target: submit by 2026-09-10 to leave a 3-day buffer.
- Judging runs 2026-09-14 to 2026-10-11.

## Before you open the page: prerequisite check

1. Confirm the team is entered on the Strategy hackathon with the SAME roster as
   the Simulation division (Strategy rule 2.1.c). Simulation participation is
   required. If the roster differs, fix it before the team-merger deadline
   (2026-09-06), because you cannot fix it after.

## Click-path

1. Go to the Strategy hackathon page:
   `https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy`
   (log in first; the page is JS-rendered, a plain fetch shows an empty shell).
2. Open the Overview or Submit area and click the **New Writeup** button.
3. Fill the fields, copied verbatim from the top of `docs/writeup/final_synthesis.md`:
   - **Title:** Trustworthy Measurement Under Extreme Noise
   - **Subtitle:** How a Pokemon TCG agent earned, audited, and repeatedly
     overruled its own instruments, and the honest boundary of what learning
     could close.
   - **Track:** select **Strategy (Model Approach)** in the Track dropdown.
4. **Body:** paste the writeup body. Paste everything BELOW the Track line (the
   Title/Subtitle/Track are entered in their own fields in step 3, so do not
   duplicate them in the body). Source: `docs/writeup/final_synthesis.md`.
5. **Figures/media (optional):** if you attach any figure, it must be SELF-MADE
   (Report score, 10%, rewards self-made figures). Attach NO Pokemon artwork or
   card images of any kind, that disqualifies the writeup (Pokemon Elements
   license, `analysis/strategy_prize_rules.md`). The writeup stands on its own
   with zero images; only add a self-made chart if you build one.
6. **Attached assets (optional):** anything you attach is AUTO-PUBLISHED after
   the deadline. Attach nothing you are unwilling to open-source. Do NOT attach
   competition card data or episode dumps (Competition-Use-Only, team-private).
7. Preview, then click **Submit** (not just Save). Confirm the status reads
   Submitted, not Draft.

## Pre-submission checklist (run this immediately before the Submit click)

- [ ] Word count is in band. Run:
      `.venv/Scripts/python.exe -c "print(len(open('docs/writeup/final_synthesis.md',encoding='utf-8').read().split()))"`
      Expect a number between 1900 and 1990 (hard Kaggle ceiling is 2000). If
      Kaggle's own counter shows a different number, trust Kaggle's and trim to
      stay under 2000.
- [ ] Tests green:
      `.venv/Scripts/python.exe -m pytest tests/test_comprehension_writeup.py -q`
      (audits word-count band, that every cited path exists, and no dashes).
- [ ] No em or en dashes in the pasted body (the test enforces this; eyeball the
      paste too, some editors re-insert them).
- [ ] No Pokemon artwork or card images anywhere in the writeup or attachments.
- [ ] Every cited source path resolves (the test checks this on disk; the paths
      are inline backticks, they are references for judges, not live links).
- [ ] Title, Subtitle, and Track fields are filled and Track is Strategy.
- [ ] Team roster matches the Simulation division.
- [ ] Only ONE Writeup exists for the team (delete stray drafts so you do not
      submit the wrong one).
- [ ] Final Submit clicked; status shows Submitted, not Draft.

## If you edit the writeup after reading this

Re-run the two commands in the checklist. The word-count band and the
citations-exist guarantee are both machine-checked by
`tests/test_comprehension_writeup.py`, so a later edit that breaks either one
fails a test instead of shipping silently.
