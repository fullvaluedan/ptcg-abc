"""Council orchestrator: propose, anonymized cross-critique, synthesize one spec.

Three phases. Every available provider proposes one approach to the design
question. The proposals are stripped of author identity and relabeled, then every
provider critiques the anonymized set on the merits only. A single synthesizer
provider merges the anonymized proposals and critiques into one spec. The models
never vote on a best answer; the gauntlet does, by measuring the spec.

A provider with no API key in the environment is skipped, not failed. A provider
that errors mid-run is recorded under "skipped" and the run continues with the
rest. The returned report links no proposal or critique back to its author, and
contains no API key.

This is a development tool. It is never imported by the offline submission.
"""
from __future__ import annotations

import argparse
import json
import os
import string
import sys
from pathlib import Path

_ROOT = Path(__file__).resolve().parents[1]
if str(_ROOT) not in sys.path:
    sys.path.insert(0, str(_ROOT))

from council.providers import (  # noqa: E402
    Provider,
    ProviderError,
    available_providers,
    default_providers,
)

_PROMPTS = Path(__file__).resolve().parent / "prompts"


def _load_prompt(name: str) -> str:
    return (_PROMPTS / name).read_text(encoding="utf-8")


def _labels(n: int) -> list[str]:
    """Stable anonymizing labels: A, B, ... then A2, B2 past 26."""
    out = []
    for i in range(n):
        letter = string.ascii_uppercase[i % 26]
        suffix = "" if i < 26 else str(i // 26 + 1)
        out.append(f"{letter}{suffix}")
    return out


def _format_block(items: list[dict], kind: str) -> str:
    """Render anonymized items into a prompt block keyed by label only."""
    return "\n\n".join(f"{kind} {it['label']}:\n{it['text']}" for it in items)


def _gather(providers: list[Provider], prompt: str) -> tuple[list[dict], list[dict]]:
    """Call each provider once; return (results, skipped) with no author leak yet.

    results carry the real provider name internally for the skipped report; the
    caller anonymizes before anything is returned to the user.
    """
    results, skipped = [], []
    for p in providers:
        try:
            text = p.complete(prompt)
        except ProviderError as exc:
            skipped.append({"name": p.name, "reason": str(exc)})
            continue
        if text.strip():
            results.append({"name": p.name, "text": text.strip()})
        else:
            skipped.append({"name": p.name, "reason": "empty response"})
    return results, skipped


def _anonymize(items: list[dict]) -> list[dict]:
    """Replace author names with opaque labels, dropping the name entirely."""
    labels = _labels(len(items))
    return [{"label": lab, "text": it["text"]} for lab, it in zip(labels, items)]


def run_council(
    question: str,
    providers: list[Provider] | None = None,
    synthesizer: Provider | None = None,
) -> dict:
    """Run the full council over a design question and return a report dict.

    providers defaults to the env-keyed default registry filtered to those with a
    key present. synthesizer defaults to the first available provider. The report
    has anonymized proposals and critiques, the synthesized spec, the participant
    names, and any skips. It never contains an API key.
    """
    pool = available_providers(providers if providers is not None else default_providers())
    report = {
        "question": question,
        "providers_used": [p.name for p in pool],
        "proposals": [],
        "critiques": [],
        "spec": None,
        "skipped": [],
    }
    if not pool:
        report["spec"] = None
        report["note"] = "no providers available; set an API key env var to run the council"
        return report

    # Phase 1: propose.
    propose_prompt = _load_prompt("propose.txt").format(question=question)
    raw_proposals, skipped = _gather(pool, propose_prompt)
    report["skipped"].extend(skipped)
    if not raw_proposals:
        report["note"] = "every provider failed to propose; nothing to synthesize"
        return report
    proposals = _anonymize(raw_proposals)
    report["proposals"] = proposals

    # Phase 2: anonymized cross-critique.
    critique_prompt = _load_prompt("critique.txt").format(
        question=question, proposals=_format_block(proposals, "Proposal")
    )
    raw_critiques, crit_skipped = _gather(pool, critique_prompt)
    report["skipped"].extend(crit_skipped)
    critiques = _anonymize(raw_critiques)
    report["critiques"] = critiques

    # Phase 3: synthesize one spec (no vote, no ranking).
    synth = synthesizer if synthesizer is not None else pool[0]
    synth_prompt = _load_prompt("synthesize.txt").format(
        question=question,
        proposals=_format_block(proposals, "Proposal"),
        critiques=_format_block(critiques, "Critique") if critiques else "(none)",
    )
    try:
        report["spec"] = synth.complete(synth_prompt).strip()
        report["synthesizer"] = synth.name
    except ProviderError as exc:
        report["spec"] = None
        report["skipped"].append({"name": synth.name, "reason": f"synthesis: {exc}"})
    return report


def save_report(report: dict, path) -> Path:
    """Write the report as JSON. The report carries no secret, so this is safe."""
    path = Path(path)
    path.write_text(json.dumps(report, indent=2, ensure_ascii=False), encoding="utf-8")
    return path


def _print_report(report: dict) -> None:
    print(f"council on: {report['question']}")
    print(f"  participants: {', '.join(report['providers_used']) or '(none)'}")
    if report.get("synthesizer"):
        print(f"  synthesizer: {report['synthesizer']}")
    if report["skipped"]:
        for s in report["skipped"]:
            print(f"  skipped {s['name']}: {s['reason']}")
    if report.get("note"):
        print(f"  note: {report['note']}")
    print()
    if report["spec"]:
        print("=== synthesized spec ===")
        print(report["spec"])
    else:
        print("(no spec produced)")


def main():
    ap = argparse.ArgumentParser(description="run the council on a design question")
    ap.add_argument("question", help="the design question to put to the council")
    ap.add_argument("-o", "--out", help="write the full report JSON to this path")
    args = ap.parse_args()

    if not available_providers():
        print(
            "no API keys found in the environment; set ANTHROPIC_API_KEY, "
            "OPENAI_API_KEY, DEEPSEEK_API_KEY, or GLM_API_KEY to run the council",
            file=sys.stderr,
        )
        sys.exit(1)

    report = run_council(args.question)
    _print_report(report)
    if args.out:
        save_report(report, args.out)
        print(f"\nfull report written to {args.out}")


if __name__ == "__main__":
    main()
