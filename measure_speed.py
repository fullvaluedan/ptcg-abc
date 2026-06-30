"""Measure cabt simulator speed using the engine's own built-in deck and agents.
No gated data needed. Pure throughput recon for the per-turn search budget.
"""
import time
from kaggle_environments import make
from kaggle_environments.envs.cabt.cabt import random_agent, first_agent

AG = {"random": random_agent, "first": first_agent}


def play(names):
    env = make("cabt", debug=False)
    env.run([AG[n] for n in names])
    last = env.steps[-1]
    return len(env.steps), last[0]["reward"], last[1]["reward"]


t0 = time.perf_counter()
s, r0, r1 = play(["random", "random"])
dt = time.perf_counter() - t0
print(f"[warmup] random vs random: {s} steps reward=({r0},{r1}) {dt*1000:.0f} ms")


def bench(names, N):
    t0 = time.perf_counter()
    tot = 0
    w0 = w1 = dr = 0
    smin, smax = 10**9, 0
    for _ in range(N):
        s, r0, r1 = play(names)
        tot += s
        smin = min(smin, s)
        smax = max(smax, s)
        if r0 == 1:
            w0 += 1
        elif r1 == 1:
            w1 += 1
        else:
            dr += 1
    dt = time.perf_counter() - t0
    print(
        f"{names}: {N} matches in {dt:.2f}s | {N/dt:.2f} matches/s | {dt/N*1000:.1f} ms/match "
        f"| steps avg {tot/N:.1f} (min {smin}, max {smax}) | p0 {w0} / p1 {w1} / draw {dr}"
    )


bench(["random", "random"], 20)
bench(["first", "first"], 20)
bench(["first", "random"], 20)
print("DONE")
