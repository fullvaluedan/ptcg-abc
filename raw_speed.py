"""Raw engine throughput: drive battle_select directly, bypassing the
kaggle_environments wrapper. This is the true forward-model / rollout rate that
decides how deep a search we can afford per decision.
"""
import time
import random
from kaggle_environments.envs.cabt.cg.game import battle_start, battle_select, battle_finish
from kaggle_environments.envs.cabt.cg.sim import Battle
from kaggle_environments.envs.cabt.cabt import deck

random.seed(0)


def one_game():
    obs, sd = battle_start(deck, deck)
    if not Battle.battle_ptr:
        battle_finish()
        return 0
    steps = 0
    while True:
        s = obs["current"]
        if s["result"] >= 0:
            break
        sel = obs["select"]
        if sel is None:
            break
        n = len(sel["option"])
        mx = sel["maxCount"]
        choice = random.sample(range(n), mx) if n >= mx else list(range(n))
        try:
            obs = battle_select(choice)
        except Exception:
            break
        steps += 1
        if steps > 100000:
            break
    battle_finish()
    Battle.battle_ptr = None
    return steps


one_game()  # warmup

M = 40
t0 = time.perf_counter()
tot = 0
for _ in range(M):
    tot += one_game()
dt = time.perf_counter() - t0
print(
    f"RAW battle_select: {M} games in {dt:.3f}s | {M/dt:.1f} games/s "
    f"| {tot} selects | {tot/dt:,.0f} selects/s | {dt/tot*1e6:.1f} us/select"
)
print("DONE")
