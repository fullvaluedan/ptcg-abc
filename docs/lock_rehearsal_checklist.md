# Lock-Rehearsal Checklist: Aug 12-13 Submission Window

**Purpose:** A minute-by-minute procedure for Dan to follow during the Kaggle submission lock window (Aug 12-13, 2026). This checklist ensures each pre-registered build pair is submitted correctly, passes grader validation, and respects Kaggle's quota and competition rules.

**Date range:** Aug 12, 2026 00:00 UTC through Aug 13, 2026 (exact lock time: [CONFIRM: exact Kaggle submission deadline UTC])

**Pre-registered pair:** [CONFIRM: two build refs, e.g. ref_A (primary, ring-positive), ref_B (hedge or identical copy)]

---

## PHASE 1: PRE-SUBMISSION PREPARATION (Aug 11-12, before window opens)

### Grader test all submission tarballs

- [ ] Retrieve the exact tarball files for both pre-registered builds from their build records
- [ ] Run grader test on first build:
  ```
  python tests/test_grader_submission.py
  ```
  Expected: PASS. If any grader test fails: STOP, do not submit. Diagnose the failure and update the tarball.
- [ ] Run grader test on second build (same command)
  Expected: PASS. If any grader test fails: STOP, do not submit.
- [ ] Record both tarball hashes (SHA-256 or equivalent) in a local file
  - First build hash: [CONFIRM: hash or file path]
  - Second build hash: [CONFIRM: hash or file path]
  - These hashes are the immutable identity for the "COMPLETE before next-roll" rule below

### Verify Kaggle quota for Aug 12-13

- [ ] Check current Kaggle submission quota remaining for today (Aug 11): `.venv/Scripts/kaggle.exe competitions submissions -c pokemon-tcg-ai-battle`
  - Note: Kaggle allows 5 submissions per calendar day (UTC). Plan both builds across the 48-hour window.
  - Quota resets each day at [CONFIRM: exact UTC time, likely 00:00 or 24:00 UTC]
- [ ] Confirm that at least 2 submission slots are available across Aug 12-13 (one per build, minimum)
- [ ] Plan submission order:
  - **Strategy:** Submit the first (primary) build early on Aug 12 to start accruing convergence episodes. Wait for its status (COMPLETE, ERROR, or TIMEOUT). Once primary is COMPLETE, submit the second build.
  - **Fallback:** If Kaggle quota or technical issues prevent submitting both by Aug 13 lock, submit the primary build only.

### Prepare submission environment

- [ ] Ensure the latest code is committed to `feat/phase3-followon` branch
- [ ] Do NOT switch branches or modify uncommitted code during the submission window
- [ ] Have `.venv/Scripts/kaggle.exe` ready with valid auth token at `~/.kaggle/access_token`
  - Test access: `.venv/Scripts/kaggle.exe competitions list` should list pokemon-tcg-ai-battle
- [ ] Prepare a file to log submission refs and timestamps (example: `submission_log_aug12_13.txt`)

---

## PHASE 2: SUBMISSION PROCEDURE (Aug 12-13)

### Build 1 Submission (Primary)

**Target time:** Aug 12, morning (early UTC) to maximize convergence-episode accrual

- [ ] **06:00 UTC [CONFIRM: preferred start time]:** Pull the first pre-registered build tarball
- [ ] Verify tarball filename and expected format (e.g., `submission_primary.tar.gz`)
- [ ] Run final grader test:
  ```
  python tests/test_grader_submission.py
  ```
  Expected: PASS. If it fails at this moment: diagnose immediately and do NOT submit.
- [ ] Upload to Kaggle:
  ```
  .venv/Scripts/kaggle.exe competitions submit -c pokemon-tcg-ai-battle -f submission_primary.tar.gz
  ```
- [ ] Record in submission_log_aug12_13.txt:
  - Submission time (UTC)
  - Kaggle reference ID (from command output, e.g., ref 54xxxxxx)
  - Tarball hash (from Phase 1 record)
- [ ] Wait for status: COMPLETE, ERROR, TIMEOUT, or PENDING
  - Check status every 10-30 minutes: `.venv/Scripts/kaggle.exe competitions submissions -c pokemon-tcg-ai-battle`
  - Expected: Status will transition from PENDING to COMPLETE (or ERROR/TIMEOUT within 10-60 minutes)
  - Note the **score** (leaderboard rating) when COMPLETE

#### U108 Standing Rule: Settlement Arithmetic

Once the first build scores and appears on the leaderboard:
- [ ] Read the build's leaderboard score
- [ ] Calculate distance from the current "king" (best-known prior rating):
  - Delta = new_score - king_score
  - Noise band (M) = 240 points (per LOOP_BRIEF.md U108 and prior calibration)
- [ ] If delta is INSIDE the noise band (i.e., -240 <= delta <= +240):
  - **Standing rule:** This score alone does NOT evict the previous build. Ring evidence is the only eviction authority. Do not act on this single read.
  - Log: "Build 1 score [score] is [delta] from king [king_score], inside M-band. Holding."
- [ ] If delta is OUTSIDE the noise band (i.e., delta < -240 or delta > +240):
  - This is a genuine signal. Log it and continue monitoring.

### Build 2 Submission (Hedge or Identical Copy)

**Target time:** Aug 12 or Aug 13, after Build 1 reaches a stable status (COMPLETE or clear ERROR)

- [ ] **Condition for launch:** Build 1 has reached COMPLETE status OR is clearly in ERROR/TIMEOUT (non-recoverable)
- [ ] If Build 1 scored COMPLETE:
  - Wait 2-6 hours after Build 1's completion to allow it to accrue convergence episodes
  - Then submit Build 2
- [ ] If Build 1 scored ERROR or TIMEOUT:
  - Diagnose the error via Kaggle submission logs
  - If error is grader-side (tarball issue): fix and resubmit Build 1
  - If error is environment issue: proceed to submit Build 2 (which may be identical or a fallback build)
- [ ] Pull the second pre-registered build tarball
- [ ] Verify tarball filename (e.g., `submission_hedge.tar.gz` or `submission_copy2.tar.gz`)
- [ ] Run final grader test:
  ```
  python tests/test_grader_submission.py
  ```
  Expected: PASS. If it fails: diagnose and do NOT submit.
- [ ] Upload to Kaggle:
  ```
  .venv/Scripts/kaggle.exe competitions submit -c pokemon-tcg-ai-battle -f submission_hedge.tar.gz
  ```
- [ ] Record in submission_log_aug12_13.txt:
  - Submission time (UTC)
  - Kaggle reference ID
  - Tarball hash (from Phase 1 record)
- [ ] Wait for status: COMPLETE, ERROR, TIMEOUT, or PENDING
  - Check status every 10-30 minutes
  - Expected: COMPLETE or clear failure within 10-60 minutes

#### U108 Standing Rule (repeated for Build 2)

Once the second build scores:
- [ ] Read the build's leaderboard score
- [ ] Calculate delta from current king (which may now be Build 1 if it scored higher):
  - Delta = new_score - current_king_score
  - Noise band (M) = 240 points
- [ ] If delta is INSIDE the noise band:
  - **Standing rule:** This score alone does NOT evict the previous best. Ring evidence only.
  - Log: "Build 2 score [score] is [delta] from current best, inside M-band. Holding."
- [ ] If delta is OUTSIDE the noise band:
  - This is a genuine signal. Continue monitoring per the protocol below.

---

## PHASE 3: CONFIRM COMPLETE BEFORE NEXT ROLL

**Critical rule:** After Aug 13, submit nothing that has not already scored COMPLETE under an identical tarball hash.

### Immediate post-submission (Aug 12-13)

- [ ] Both builds have been submitted and reached a final status (COMPLETE, ERROR, or TIMEOUT)
- [ ] Record final state in submission_log_aug12_13.txt:
  - Build 1: status, final score (if COMPLETE), reference ID
  - Build 2: status, final score (if COMPLETE), reference ID
- [ ] If either build is in ERROR or TIMEOUT:
  - Investigate the error message from Kaggle
  - If grader/tarball issue: note that this build is INELIGIBLE for the final pair (do not resubmit without new code)
  - If environment issue (transient): may be resubmitted during Aug 12-13 window only

### Lock checkpoint (Aug 13, approaching deadline)

- [ ] Check the current leaderboard to confirm both builds appear (if both scored COMPLETE)
- [ ] Confirm that Kaggle latest-2 auto-selection includes the intended pair (both Build 1 and Build 2 in latest-2 window)
  - Expected: Both builds are recent enough to be in Kaggle's latest-2 tracking
- [ ] Record the final pair composition:
  - Primary build: ref_X, score_X, hash_X (COMPLETE)
  - Secondary build: ref_Y, score_Y, hash_Y (COMPLETE)
  - Mark as "LOCKED for final pair" in submission_log_aug12_13.txt

### HARD LOCKDOWN: Aug 13 after submission deadline

**Once Aug 13 deadline passes and both builds are COMPLETE:**
- [ ] NO further submissions to Kaggle (other than the writeup submission, which is separate, due by Sep 1)
- [ ] NO resubmissions of either build, even if a score seems to fluctuate during post-Aug-13 convergence (Aug 17-31)
- [ ] The locked pair (ref_X, ref_Y, with their original tarball hashes) is the final submission for the competition
- [ ] Any changes to the agent after Aug 13 will be for the writeup and future analysis only, NOT for competition scoring

---

## PHASE 4: QUOTA AND CALENDAR RULES

### Daily submission quota (Aug 12-13)

- [ ] **Quota limit:** 5 submissions per calendar day (UTC)
- [ ] **Day 1 (Aug 12):** Maximum 5 submissions; plan to use 1-2 for the primary and secondary builds
- [ ] **Day 2 (Aug 13):** If needed, up to 5 more submissions available (quota resets at [CONFIRM: exact UTC reset time])
- [ ] **Strategy:** Concentrate both builds into Aug 12 if possible. Use Aug 13 only as a fallback.

### Kaggle submission deadline

- [ ] **Final lock time:** [CONFIRM: exact date and time UTC from Kaggle Rules/FAQ, likely Aug 13 11:59 PM UTC or midnight]
- [ ] **Action:** Plan to complete both submissions by [deadline minus 30 minutes] to account for any last-minute processing delays
- [ ] **After deadline:** Kaggle will reject any new submission attempts; do not waste time retrying

---

## PHASE 5: INTEGRATION WITH U108 STANDING RULE

**Governance rule (U108, from LOOP_BRIEF.md):**
A ladder read inside the M-band (240-point noise window) can NEVER evict a ring-positive build. Ring evidence is the only eviction authority.

### Apply during submission monitoring

- [ ] When each build scores, calculate its delta from the prior king
- [ ] If the delta is inside [-240, +240]: this is noise, not a real change. Log and continue.
- [ ] If the delta is outside that band: this is genuine signal. Continue monitoring per the protocol above.
- [ ] Do NOT use individual ladder scores to make decisions about build eviction, reversion, or further submissions. Only ring evidence (from pre-registration via U2/U4/U5) decides pair composition.

### Recording the rule

- [ ] After Aug 13 lock, append to findings.md (section 4D, Governance):
  - "Aug 12-13 lock: both pre-registered builds submitted and locked. U108 settlement rule applied: all intermediate scores fell within M-band; ring evidence from pre-registration (U2/U4/U5) was the decision gate, not ladder reads."
  - Or: "... final pair scored [score_1] and [score_2], deltas [delta_1] and [delta_2] from prior king; [delta_1] [inside/outside] M-band, [delta_2] [inside/outside] M-band. U108 applied: decision authority remains with ring evidence."

---

## APPENDIX: Failure Modes and Recovery

### Grader test fails at submission time

- [ ] Do NOT submit the failed tarball
- [ ] Diagnose: check test output for specific assertion or import error
- [ ] Likely causes: missing file in submission bundle (check tests/test_grader_submission.py), or agent raises an exception
- [ ] Recovery: update the tarball and re-test before re-submitting (only during Aug 12-13 window)

### Kaggle submission times out or errors

- [ ] Check Kaggle's status page (if available) for any known issues
- [ ] Error types:
  - **Grader ERROR:** tarball issue, see above
  - **TIMEOUT:** environment issue on Kaggle's side; safe to retry with an identical tarball (hash unchanged)
  - **PENDING stuck:** rare; wait 30 minutes then try checking status again
- [ ] Recovery: retry during the Aug 12-13 window (does not consume a new quota slot if re-submitting an identical hash)

### Quota exhausted before both builds submitted

- [ ] On Aug 12, if 5 submissions are used for other reasons before the pair is submitted:
  - Wait for quota reset [CONFIRM: UTC reset time] and resume Aug 13
- [ ] On Aug 13, if approaching the deadline and quota is exhausted:
  - Submit the primary build only if it has not yet been submitted
  - The secondary build (hedge) may be foregone if time/quota do not permit

### Both builds score COMPLETE inside M-band (noise)

- [ ] This is expected. Log the scores as noise-driven variation per U108.
- [ ] Do NOT resubmit or adjust. The locked pair remains the final submission.
- [ ] The actual final pair decision was made via ring evidence (U2/U4/U5 pre-registration), not by ladder reads.

### Build changes discovered after Aug 13 deadline

- [ ] Do NOT submit any new version of the agent
- [ ] The locked pair (by reference ID and tarball hash) is final
- [ ] Document any discovered issues in findings.md for the writeup and future work
- [ ] This does not affect the competition scoring; the rule is: after Aug 13, nothing new scores unless it was already COMPLETE before the deadline

---

## SIGN-OFF

**Dan:** After both builds reach COMPLETE (or final status) on Aug 12-13, and U108 settlement arithmetic has been applied, review this checklist and confirm:

- [ ] All grader tests passed before submission
- [ ] Both builds (or at least the primary) are COMPLETE on Kaggle leaderboard
- [ ] Both tarball hashes are recorded and immutable (no further submissions of new tarballs after Aug 13)
- [ ] U108 standing rule was applied: no build was evicted by a noise-band score
- [ ] Submission log (submission_log_aug12_13.txt) is complete and archived
- [ ] findings.md 4D has been updated with the lock outcome

**Completion marker:** Once the above is confirmed, the Aug 12-13 lock is complete. The pair is final and will converge until approximately Aug 31.
