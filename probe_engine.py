"""Read-only recon probe for the installed cabt engine.
Goal: confirm the engine ships locally, read its timeout config, and see if the
card database is embedded (so we can measure speed without the gated deck data).
No agent logic here. Pure inspection.
"""
import os, json, sys, traceback, importlib
import kaggle_environments as ke

print("=== kaggle_environments ===")
print("version:", getattr(ke, "version", "?"))

cabt_dir = os.path.join(os.path.dirname(ke.__file__), "envs", "cabt")
print("cabt_dir:", cabt_dir, "exists=", os.path.isdir(cabt_dir))

print("=== cabt env file tree ===")
py_files, bin_files, json_files = [], [], []
if os.path.isdir(cabt_dir):
    for root, dirs, files in os.walk(cabt_dir):
        rel = os.path.relpath(root, cabt_dir)
        for f in files:
            p = os.path.join(rel, f) if rel != "." else f
            print("  ", p)
            low = f.lower()
            if low.endswith(".py"):
                py_files.append(p)
            elif low.endswith((".dll", ".so", ".dylib")):
                bin_files.append(p)
            elif low.endswith(".json"):
                json_files.append(p)
print("py_files:", py_files)
print("bin_files:", bin_files)
print("json_files:", json_files)

# Read any json spec for timeout-related keys
for jf in json_files:
    full = os.path.join(cabt_dir, jf)
    try:
        data = json.load(open(full, encoding="utf-8"))
    except Exception as e:
        print(f"  [{jf}] parse error:", e)
        continue
    cfg = data.get("configuration", data) if isinstance(data, dict) else {}
    keys = ["actTimeout", "runTimeout", "agentTimeout", "episodeSteps", "timeout",
            "decks", "steps", "maxTurns"]
    found = {k: (cfg.get(k) if isinstance(cfg, dict) else None) for k in keys}
    print(f"=== {jf} timeout/config keys ===")
    print(json.dumps(found, indent=2, default=str))

# Make the env and dump resolved configuration
print("=== make('cabt') resolved configuration ===")
try:
    env = ke.make("cabt", debug=True)
    try:
        cfg = dict(env.configuration)
        print(json.dumps(cfg, indent=2, default=str)[:4000])
    except Exception as e:
        print("config dump err:", e, repr(env.configuration)[:2000])
    spec = getattr(env, "specification", None)
    if spec is not None:
        try:
            print("=== spec.configuration ===")
            sc = spec.get("configuration") if hasattr(spec, "get") else None
            print(json.dumps(sc, indent=2, default=str)[:3000])
        except Exception as e:
            print("spec dump err:", e)
except Exception:
    print("make('cabt') FAILED:")
    traceback.print_exc()

# See if the engine's python API (with card DB) is importable offline
print("=== engine api import attempts ===")
for base in [cabt_dir, os.path.dirname(cabt_dir)]:
    if base not in sys.path:
        sys.path.insert(0, base)
candidates = ["cabt", "cabt.api", "api", "cabt.game", "game", "cabt.sim", "sim"]
for name in candidates:
    try:
        m = importlib.import_module(name)
        has = [fn for fn in ("all_card_data", "all_attack", "search_begin",
                             "battle_start") if hasattr(m, fn)]
        print(f"  import {name}: OK  exposes={has}")
    except Exception as e:
        print(f"  import {name}: {type(e).__name__}: {e}")
