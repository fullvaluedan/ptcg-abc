"""Draw down the cumulative thinking bank (KTD2).

cabt sets actTimeout 0 and gives each player a single 600 second bank for the
whole match (remainingOverageTime). A timeout is an automatic loss, so we keep a
hard guard comfortably under 600 and never let one decision spend more than a
soft cap. The agent owns one TimeBudget for the life of the process and records
the wall clock each decision actually used, so the guard tightens as the bank is
drawn down.

No cg import, no clock side effects: the caller measures the wall clock and calls
record, which keeps this trivially testable and lets it ship next to main.py.
"""
from __future__ import annotations

# Stay clear of the real 600s ceiling; a timeout forfeits the match.
HARD_BANK = 540.0
# How much of the 600s bank an ordinary decision may spend. Deliberately generous:
# each determinized rollout runs to a terminal result, so a tiny cap bought only
# about one hidden-world sample per decision, leaving the mean-over-determinizations
# argmax noisy and starving the variance penalty and field prior that both need
# several worlds to do anything (a single world has zero variance). A larger cap
# samples more worlds and uses more of the otherwise idle bank; the reserve fraction
# below and the SAFETY_RESERVE guard keep cumulative time clear of a timeout
# regardless, and the atomic first rollout means an expensive decision is never made
# more expensive, only cheap decisions gain extra worlds up to the cap.
SOFT_CAP = 2.0
# Never commit more than this fraction of the remaining bank to one decision, so
# the agent always keeps time in reserve for the rest of the match.
RESERVE_FRACTION = 0.25
# Hard safety guard (U10): once the bank is this close to the hard ceiling, stop
# searching entirely and answer instantly from the heuristic. With the default
# HARD_BANK this trips at 480s spent, leaving 60s under the 540 guard plus the
# 60s gap to the real 600s ceiling, so cumulative thinking time never approaches
# a timeout (an automatic loss).
SAFETY_RESERVE = 60.0


class TimeBudget:
    """Tracks cumulative search time and allots a per-decision budget."""

    def __init__(self, hard_bank: float = HARD_BANK, soft_cap: float = SOFT_CAP):
        self.hard_bank = hard_bank
        self.soft_cap = soft_cap
        self.spent = 0.0

    def allot(self, soft_cap=None) -> float:
        """Seconds to spend on the current decision (0 once the bank is at risk).

        A per-decision soft_cap override raises the ceiling for a pivotal decision
        (the endgame solver passes a larger cap), but the result is still bounded
        by the remaining-bank reserve fraction, so the hard time guard always holds
        and a single boosted decision can never approach a timeout.
        """
        cap = self.soft_cap if soft_cap is None else soft_cap
        remaining = self.hard_bank - self.spent
        if remaining <= 0:
            return 0.0
        return max(0.0, min(cap, remaining * RESERVE_FRACTION))

    def record(self, seconds: float) -> None:
        self.spent += max(0.0, seconds)

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.hard_bank

    @property
    def at_risk(self) -> bool:
        """True once too little bank remains to safely afford another search.

        The agent checks this before searching and answers instantly from the
        heuristic when it trips, so cumulative time stays clear of the ceiling.
        """
        return self.spent >= self.hard_bank - SAFETY_RESERVE
