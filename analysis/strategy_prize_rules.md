# Strategy prize rules, pinned from primary sources (2026-07-05)

Verified live (JS-rendered) from the Kaggle pages on 2026-07-05. Plain fetches of these URLs return an
empty JS shell, so any earlier analysis based on plain fetches read nothing. Sources:
https://www.kaggle.com/competitions/pokemon-tcg-ai-battle-challenge-strategy/overview and /rules, plus the
Simulation competition overview and rules.

## The deliverable (Strategy hackathon)

- ONE Kaggle Writeup per team (Hackathon rule 2.2.a: "each Team may submit one (1) Submission only"),
  created with the New Writeup button on the competition site.
- Title, subtitle, detailed analysis, a selected Track, MAX 2000 WORDS (over-limit subject to penalty),
  optional media gallery (images/videos), optional attached assets (code repos, notebooks, external links).
- DRAFTS DO NOT COUNT: the writeup must be explicitly Submitted before the deadline.

## Deadlines

- Entry and team-merger deadline: 2026-09-06.
- Final submission: 2026-09-13, 11:59 PM UTC. Judging 2026-09-14 to 2026-10-11.
- Internal milestones (this repo): full draft by Aug 20; frozen and SUBMITTED by Sep 10 (3-day buffer).

## Prizes and odds

- $240,000 total: EIGHT finalists at $30,000 each, possible Tokyo tournament invite.
- Roughly 151 teams have Strategy submissions as of 2026-07-05, against 8 slots.
- The Simulation track itself pays $0 (knowledge/medals only).

## Scoring (confirmed 70/20/10)

- Model Score 70%: clarity of approach and rationale, originality and technical soundness, consistency
  under repeated matches, avoiding over-reliance on specific initial states or matchups, and leaderboard
  performance as ONE bullet of five. The page explicitly says middle or lower leaderboard tiers can still
  score high overall.
- Deck Score 20%: deck concept clarity, key-card selection supporting the game plan.
- Report Score 10%: structure, effective figures/charts (self-made figures).

## Eligibility and compliance

- Participation in the Simulation category is REQUIRED, and Strategy rule 2.1.c requires the SAME team
  roster as the Simulation division. ACTION (Dan, browser): confirm the team is entered on the Strategy
  hackathon with an identical roster, before Sep 6.
- Winner obligation: winning submission code is open-sourced under MIT (training + inference + reproduction
  docs). Keep the repo publishable: no competition card data, no Pokemon artwork/assets in anything that
  could be open-sourced.
- Competition data is "Competition Use Only": never redistributed, deleted after the competition. Episode
  dump mining is compliant (Simulation rules 2.11: replays "may be publicly available and downloadable";
  external-data clause), but dumps stay team-private.
- Private Kaggle resources attached to the writeup are AUTO-PUBLISHED after the deadline: attach nothing we
  are unwilling to publish. Images violating the Pokemon Elements license disqualify the writeup.

## Simulation final-evaluation semantics (the posture-inverting fact)

- Overview, verbatim: "At the submission deadline on August 16, 2026, additional submissions will be
  locked. From August 16, 2026 for approximately two weeks, we will continue to run games. At the
  conclusion of this period, the leaderboard is final." Timeline: "August 17, 2026 to (approx.) August 31,
  2026 - We will continue to run games, or until the leaderboard has reached convergence."
- Consequence: ratings keep converging after the lock, so a lucky pre-deadline score snapshot DECAYS toward
  true skill. The variance-harvest endgame is dead; the correct Aug plan is locking the two genuinely
  strongest builds early (by ~Aug 12-13) so they accrue convergence episodes.
- Submission mechanics: overview/FAQ say latest-2-auto are active ("Only your most recent 2 are active",
  daily limit 5). One conflict: Simulation Rules 2.2.b says "You may select up to two (2) Final Submissions
  for judging" (standard Kaggle boilerplate that usually has no UI in Simulation comps). Operative rule:
  plan for latest-2-auto; Dan checks the logged-in Submissions page for a selection control before August.
- "There is no Private Leaderboard in Simulation competitions" (rules 2.10). No ingress/egress during
  episodes (2.12).
