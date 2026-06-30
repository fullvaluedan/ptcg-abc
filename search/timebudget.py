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
# Most decisions are not pivotal, so the per-move soft cap is modest by default.
SOFT_CAP = 0.5
# Never commit more than this fraction of the remaining bank to one decision, so
# the agent always keeps time in reserve for the rest of the match.
RESERVE_FRACTION = 0.25


class TimeBudget:
    """Tracks cumulative search time and allots a per-decision budget."""

    def __init__(self, hard_bank: float = HARD_BANK, soft_cap: float = SOFT_CAP):
        self.hard_bank = hard_bank
        self.soft_cap = soft_cap
        self.spent = 0.0

    def allot(self) -> float:
        """Seconds to spend on the current decision (0 once the bank is at risk)."""
        remaining = self.hard_bank - self.spent
        if remaining <= 0:
            return 0.0
        return max(0.0, min(self.soft_cap, remaining * RESERVE_FRACTION))

    def record(self, seconds: float) -> None:
        self.spent += max(0.0, seconds)

    @property
    def exhausted(self) -> bool:
        return self.spent >= self.hard_bank
