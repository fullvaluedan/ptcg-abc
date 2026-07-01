# Playbook: Build a Kaggle Simulation Agent (almost) Autonomously with Compound Engineering

This is a reproducible method for building a competitive agent for a Kaggle
"simulation" competition (agents play a game, a ladder ranks them) using an AI
coding agent driven in an unattended loop. It is written so a person OR an AI can
follow it. It documents what actually worked, what did not, and the specific traps
that cost us time.

Concrete example throughout: the Pokemon TCG AI Battle Challenge (the "cabt Engine"),
where a from-scratch project reached a working, ladder-rated agent plus a full
toolchain plus a strategy writeup in about a day, mostly hands-off.

Honesty up front: this method reliably produces a solid, well-tested, mid-pack agent
and a strong, explainable writeup, fast. It does NOT automatically reach the very top
of a strong ladder. Read Part 8 before you set expectations.

---

## 0. The shape of the whole thing

1. Set up an isolated environment and the competition SDK locally.
2. Wire up Kaggle auth so you can submit and pull data.
3. RECON FIRST: resolve the simulator's contract from source before writing any agent.
4. Plan the work as gated phases (compound engineering).
5. Build the baseline, then a heuristic, then a search agent, each behind a measurable gate.
6. Run an unattended tmux loop that keeps improving the agent, driven by real ladder data.
7. A human (or a second AI session) manages the loop: steers via a brief, watches via monitors.

The core belief that makes it work: **the scoreboard is the only truth.** Offline
self-play lies; the live ladder decides. Every change is judged by measured result.

---

## 1. Environment setup

Prerequisites: Python 3.11, an AI coding agent CLI (we used Claude Code) installed and
authenticated, tmux, and a Kaggle account. We ran on Windows 11 with Git Bash, but the
method is OS-agnostic.

**Isolate the project OUTSIDE any cloud-synced folder.** Competition data must not sync
to the cloud (terms of service, and sync locks corrupt files). Put the project somewhere
like `C:\Users\you\myproject`, not under OneDrive/Dropbox/iCloud.

```
python -m venv .venv
```

**Install the engine leanly.** Simulation SDKs (here `kaggle-environments`) often pull a
huge ML dependency stack you do not need. On Windows one of those transitive packages
(`orbax-checkpoint`) ships test data with paths longer than the 260-char limit, which
aborts the whole install and rolls it back. The fix generalizes: install minimally, add
dependencies only as import errors demand them.

```
.venv/Scripts/python -m pip install kaggle
.venv/Scripts/python -m pip install --no-deps kaggle-environments
.venv/Scripts/python -m pip install numpy jsonschema flask requests pydantic pyjson5 gymnasium pettingzoo
# then: python -c "from kaggle_environments import make; make('<env>'); print('ok')"
# add any module the import error names, repeat until it imports clean
```

**Confirm the engine runs a match locally** before anything else. If the SDK ships
reference agents, run them against each other and read the result.

---

## 2. Kaggle setup

Three things must be true before you can submit:

1. **Accept the competition rules** on the website (both competitions if it is a paired
   Simulation + Strategy setup, since entry into one usually gates the other).
2. **Verify your phone number** at https://www.kaggle.com/settings. Kaggle requires this
   to submit. If you skip it, `submit` returns **403 Forbidden** while reads still work.
   That exact signature (reads fine, rules accepted, submit 403) means phone verification.
3. **Place an API token.** Modern Kaggle CLI (2.2.x) dropped the legacy `kaggle.json`
   username+key file. It now wants a single token in `~/.kaggle/access_token` or the env
   var `KAGGLE_API_TOKEN`. Generate it under Settings > API. Never paste the token into a
   chat or transcript; write it to the file directly.

Commands you will use constantly:

```
kaggle competitions submissions -c <slug>          # your subs, status, score
kaggle competitions submit <slug> -f sub.tar.gz -m "msg"
kaggle competitions leaderboard <slug> --show      # the field (team, score)
kaggle datasets download kaggle/<episode-dataset>  # replays for scouting (see Part 6)
```

---

## 3. Recon first (do NOT build the agent yet)

The single highest-leverage discipline. Before writing any agent, resolve the simulator's
contract from the actual SDK source, not from assumptions or a blog post. For a game engine
that means:

- The exact **observation** structure the agent receives each turn (fields and types).
- The exact **action** format it must return.
- How to **run one local match** between two agents.
- How a **submission** is produced and packaged (file name, entrypoint signature, bundled files).
- The **time limit** (per move, per match) that decides how deep you can search.
- The **simulator speed** (measure it), which decides whether the provided engine is fast enough.

Read the installed SDK source and any official docs. If the SDK exposes a forward model
(a way to simulate hypothetical futures), that is gold for search agents. Do not fabricate
the API; verify each fact against the source or a live probe, and write the findings down
before building. This step alone prevents most wasted work.

---

## 4. Compound engineering: plan in gated phases

We used the compound-engineering skill set (brainstorm, plan, work, debug, code-review).
The pattern is portable even without those exact tools:

- **Brainstorm / plan** a durable decision document: phases, each with a measurable GATE,
  the files to touch, test scenarios, and risks. The plan is the source of truth, not a
  throwaway.
- **Work** executes one phase at a time. Do not advance until the gate passes.
- **Debug** and **code-review** run inside the loop on every change.

A sensible phase ladder for a game agent:

1. Baseline: return any legal move; produce a valid submission. Gate: a clean local match
   plus a submission the grader accepts.
2. Heuristic: simple rules (take a knockout, develop, manage resources). Gate: beat the
   baseline by a wide margin; submit to get on the ladder.
3. Search: determinized lookahead over the forward model (sample hidden info, roll out,
   pick the highest expected value). Gate: beat the heuristic; stay inside the time budget.
4. Data-driven edges: scout real losses, fix the biggest failure bucket, repeat.

Each phase ships a real submission so the ladder can judge it.

---

## 5. The unattended tmux loop

This is what turns "an AI helps me code" into "the AI grinds on the problem for hours while
I sleep." Two files plus tmux.

**The driver** repeatedly invokes the AI agent headless, once per iteration, each iteration
doing ONE coherent increment. It backs off if a run dies fast (usage limits) so it never
hot-spins.

```bash
#!/usr/bin/env bash
# run_autoloop.sh   watch: tmux attach -t work | tail -f autoloop.log   kill: tmux kill-session -t work
set -u
PROJ="/path/to/project"; CLAUDE="/path/to/claude"; LOG="$PROJ/autoloop.log"
cd "$PROJ" || exit 1
i=0
while true; do
  i=$((i+1)); start=$(date +%s)
  echo "==== iteration $i $(date) ====" | tee -a "$LOG"
  MSYS_NO_PATHCONV=1 "$CLAUDE" -p "$(cat "$PROJ/LOOP_BRIEF.md")" --dangerously-skip-permissions >> "$LOG" 2>&1
  dur=$(( $(date +%s) - start ))
  echo "---- iteration $i exit=$? dur=${dur}s ----" | tee -a "$LOG"
  if [ "$dur" -lt 30 ]; then echo "short run, backing off 300s" | tee -a "$LOG"; sleep 300; else sleep 8; fi
done
```

**The brief** (`LOOP_BRIEF.md`) is the standing instruction the AI reads at the start of
every iteration. Keep it current: it is your steering wheel. It should contain:

- Project location and how to run tests, the gauntlet, and a build.
- What to do THIS iteration (find the next increment, implement, test, review, commit).
- The current TOP PRIORITY (this is what you change to redirect the loop).
- Hard constraints that must never be violated.
- Submission discipline (see below).
- A stop condition (one increment per run, then stop; the driver restarts it).

**Launch, watch, kill:**

```
tmux new-session -d -s work            # bare session (do not pass -c with an MSYS path on Windows)
tmux send-keys -t work "bash /path/to/run_autoloop.sh" Enter
tmux attach -t work                    # watch live (detach: Ctrl-b then d)
tail -f /path/to/project/autoloop.log  # or follow the log
tmux kill-session -t work              # stop it
```

**Autonomy vs guardrails.** `--dangerously-skip-permissions` lets the loop run without
prompts (necessary for unattended work). The safety then lives in the brief, not in
permission gates, so encode hard rules there. The most important one:

- **Submission discipline:** before any submit, run `kaggle competitions submissions` first
  and never submit a build already on the ladder. This prevents double-submits that waste
  your daily quota. (We burned a slot learning this when a manual submit and the loop's
  submit collided within 26 seconds.)

**The manager role.** A human or a second AI session oversees: it reads the loop's status,
steers by editing the brief's TOP PRIORITY, and only intervenes for judgment calls
(which direction to push) or genuine blockers. Watch via a log monitor that fires on
submissions and failures, not on every routine iteration (that is just noise).

---

## 6. The methodology that actually wins games

- **Scout real losses, do not guess.** Kaggle publishes daily episode datasets for
  simulation competitions (`kaggle datasets download kaggle/<comp>-episodes-YYYY-MM-DD`).
  Every replay contains both players' full decklists (in the setup step) and the full game.
  Download them, classify why you lose into concrete buckets, and fix the biggest bucket.
- **The scoreboard is the only truth.** Offline self-play against weak built-in bots is NOT
  predictive of the live ladder. Our most "dominant" offline deck scored mid-pack live.
  Measure changes on the ladder.
- **Falsify your own thesis.** We assumed "copy the top decks and win." We copied the exact
  number-one and number-two decklists, submitted them, and they scored our WORST. We
  documented the refutation instead of forcing the story. That negative result (below) is
  the most valuable thing we learned.
- **The deck-and-pilot coupling.** A top-ranked deck is one half of a system; the other half
  is a skilled pilot. Handing a naive agent a complex meta deck makes it play WORSE, because
  the agent cannot execute the deck's game plan. The gap to the top is usually agent skill,
  not deck choice. Diagnose which half is your bottleneck before optimizing.
- **Low variance beats high ceiling** when the rating is win/loss only. Avoiding bad losses
  (never miss lethal, never deck yourself out, never time out) is worth more than chasing
  blowouts.
- **Rating is noisy.** With few games, two identical agents diverged by 200+ points. Do not
  over-optimize against a single noisy number; let games accumulate.

---

## 7. Traps that cost us time (check these first)

- **Lean install:** the ML dependency stack + Windows long paths abort the install. Install
  minimally, add deps on demand (Part 1).
- **Kaggle auth changed:** single token in `~/.kaggle/access_token`, not the old kaggle.json.
- **Phone verification:** submit returns 403 until you verify your phone.
- **The grader loads your agent with `exec()` and does NOT define `__file__`.** Any module-load
  reference to `__file__` (for example to find a data file) raises NameError and marks the
  whole submission ERROR. Guard it: `if "__file__" in globals(): ...`. This passes every local
  test (imports define `__file__`) and only fails on the grader, so add a regression test that
  builds the submission, extracts it, and runs it via the grader's file-path load path, not a
  module import.
- **The grader entrypoint is the LAST callable defined in the module.** If you define a helper
  function after `agent()`, the grader calls the helper. Define your entrypoint last.
- **Silent inert fallback.** Our search agent imported a shadow copy of the engine in the
  grader sandbox that had no forward model, so every "search" decision silently fell back to
  the heuristic. We caught it only from decision-time forensics (0.02s per move instead of the
  search budget). Verify your agent is actually doing what you think ON the grader, by reading
  per-decision timings in real replays.
- **Latest-two-scored:** many simulation ladders score only your two most recent submissions.
  A careless resubmit can push a good build out of the scored pair.
- **Offline constraint:** the submitted agent must run with no network. Any LLM "council" or
  online helper is a development tool only; it never ships.

---

## 8. Expectations (read this before you start)

What this method reliably delivers, fast and mostly hands-off: a correct, well-tested agent
across baseline, heuristic, and search tiers; a full toolchain (eval gauntlet, submission
builder, replay scout, loss classifier); real ladder presence; and a drafted strategy
writeup. It self-corrects well (in our run its own review passes caught several real bugs,
and it diagnosed and fixed two subtle grader failures and one silent inert-agent bug on its
own).

What it does not do by itself: reach the very top of a strong ladder. In our run the leaders
sat around 1300 while our best builds settled around 570 to 590. That remaining gap is agent
skill (the ability to pilot a strong deck's game plan), which is a real modeling effort, not
another quick iteration. If your competition has a separate Strategy or writeup prize judged
on approach and explainability rather than raw rank, that is where this method is most
competitive: a principled, honestly-iterated, well-documented approach can place well even
without a top rating.

---

## 9. A drop-in kickoff for an AI agent

Point an AI coding agent at a new competition with a prompt like this, then let it run the
loop:

> You are building an agent for the Kaggle competition <slug>. Work in an isolated folder
> outside any cloud-synced directory. FIRST do recon only: from the installed SDK source,
> report the exact observation structure, action format, how to run a local match, the
> submission packaging and entrypoint signature, the per-move time limit, and the simulator
> speed. Do not build the agent until I approve the findings. Then build in gated phases:
> baseline, heuristic, determinized search, then data-driven improvements from real ladder
> replays. Hard constraints: the submitted agent runs fully offline; keep competition data
> isolated and never redistribute it; before every submit, list current submissions and never
> resubmit a build already on the ladder; respect the daily submission quota. The scoreboard
> is the only truth: judge every change by measured ladder result, not offline self-play.

Then set up the unattended loop (Part 5) with a `LOOP_BRIEF.md` whose TOP PRIORITY you update
as the data tells you what matters. Keep a human or a second AI session as manager to steer
the priority and handle judgment calls.

---

*Written from a real run of this method on the cabt Engine competition. The specific ratings,
deck names, and dates are examples; the method and the traps generalize to any Kaggle
simulation competition and most agent-vs-agent ladders.*
