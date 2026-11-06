"""Reproducible synthetic sensitivity sweep. python -m audit_capture.evaluate"""
from __future__ import annotations
from collections import defaultdict
import argparse
import csv
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
from .core import CONDITIONS, POLICIES, PROFILES, fingerprint, generate, run, wilson


def evaluate(cases: int = 160, repeats: int = 8) -> dict:
    groups, raw, paired = defaultdict(list), [], defaultdict(dict)
    for profile in PROFILES:
        for seed in range(10000, 10000 + cases):
            for condition in CONDITIONS:
                scenario = generate(seed, condition, profile)
                for budget in (0, 1, 2, 3, 4, 6):
                    for policy in POLICIES:
                        runs = [run(scenario, policy, budget, seed * 101 + rep) for rep in range(repeats)]
                        attack_rate = sum(r["attack_executed"] for r in runs) / repeats
                        row = {"profile": profile, "seed": seed, "condition": condition, "budget": budget,
                               "policy": policy, "attack_rate": attack_rate,
                               "completion_rate": sum(r["completion_rate"] for r in runs) / repeats,
                               "review_units": sum(r["spent_units"] for r in runs) / repeats,
                               "deferred": sum(r["deferred"] for r in runs) / repeats}
                        raw.append(row)
                        groups[profile, condition, budget, policy].append(row)
                        paired[profile, budget, policy, seed][condition] = attack_rate
    summary = []
    for (profile, condition, budget, policy), rows in groups.items():
        values = [r["attack_rate"] for r in rows]
        mean = sum(values) / cases
        # The independent unit is the scenario, NOT each repeated audit draw.
        import random
        rng = random.Random(f"bootstrap:{profile}:{condition}:{budget}:{policy}")
        means = sorted(sum(rng.choices(values, k=cases)) / cases for _ in range(400))
        summary.append({"profile": profile, "condition": condition, "budget": budget,
                        "policy": policy, "scenario_count": cases, "audit_repeats": repeats,
                        "attack_rate": mean, "attack_ci": [means[9], means[389]],
                        "completion_rate": sum(r["completion_rate"] for r in rows) / cases,
                        "mean_review_units": sum(r["review_units"] for r in rows) / cases,
                        "mean_deferred": sum(r["deferred"] for r in rows) / cases})
    deltas, selection_deltas = [], []
    for profile in PROFILES:
        for budget in (0, 1, 2, 3, 4, 6):
            for policy in POLICIES:
                diffs = [paired[profile, budget, policy, seed]["selected_decoys"] -
                         paired[profile, budget, policy, seed]["ordinary"]
                         for seed in range(10000, 10000 + cases)]
                import random
                rng = random.Random(f"paired:{profile}:{budget}:{policy}")
                means = sorted(sum(rng.choices(diffs, k=cases)) / cases for _ in range(400))
                deltas.append({"profile": profile, "budget": budget, "policy": policy,
                               "delta": sum(diffs) / cases, "ci": [means[9], means[389]]})
                # Compare selection against the same candidate distribution.
                # The existing selected-versus-ordinary contrast also changes
                # that distribution, so it does not isolate selection itself.
                selection_diffs = [paired[profile, budget, policy, seed]["selected_decoys"] -
                                   paired[profile, budget, policy, seed]["random_decoys"]
                                   for seed in range(10000, 10000 + cases)]
                rng = random.Random(f"paired-selection:{profile}:{budget}:{policy}")
                selection_means = sorted(sum(rng.choices(selection_diffs, k=cases)) / cases
                                         for _ in range(400))
                selection_deltas.append({
                    "contrast": "selected_decoys_vs_random_decoys",
                    "condition": "selected_decoys", "baseline_condition": "random_decoys",
                    "profile": profile, "budget": budget, "policy": policy,
                    "scenario_count": cases, "delta": sum(selection_diffs) / cases,
                    "ci": [selection_means[9], selection_means[389]],
                })
    fixture = generate(42)
    return {"schema_version": 1, "evidence_type": "constructed_synthetic",
            "generated_utc": datetime.now(timezone.utc).isoformat(),
            "configuration": {"cases": cases, "repeats": repeats, "test_seed_start": 10000,
                              "bootstrap_resamples": 400, "development_seeds": "0-99",
                              "selection_rule": "highest of eight permitted synthetic candidates; fixed before sweep",
                              "confidence_intervals": "percentile bootstrap across scenario means; repeats are not independent cases"},
            "limitations": ["Scores and actions are constructed, not produced by LLMs.",
                            "Profiles are assumptions, not separate monitor models.",
                            "Audits are perfect; global halts precede all commits in a batch.",
                            "Unit review costs are equal in this sweep; variable costs are supported by the engine.",
                            "All sensitive actions can be held safely, at the cost of deferred work.",
                            "Actor labels do not affect policies: no multi-agent-specific causal advantage is established."],
            "example_fingerprint": fingerprint(fixture), "summary": summary, "paired_deltas": deltas,
            "paired_selection_deltas": selection_deltas,
            "example": {"ordinary": run(generate(42, "ordinary")),
                        "selected_decoys": run(generate(42, "selected_decoys"))}, "raw": raw}


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--cases", type=int, default=160)
    parser.add_argument("--repeats", type=int, default=8)
    parser.add_argument("--out", type=Path, default=Path("results"))
    args = parser.parse_args()
    if not 2 <= args.cases <= 1000 or not 1 <= args.repeats <= 64:
        parser.error("cases must be 2-1000 and repeats 1-64")
    result = evaluate(args.cases, args.repeats)
    args.out.mkdir(parents=True, exist_ok=True)
    raw = result.pop("raw")
    with (args.out / "runs.csv").open("w", newline="", encoding="utf-8") as stream:
        writer = csv.DictWriter(stream, fieldnames=list(raw[0]))
        writer.writeheader()
        writer.writerows(raw)
    (args.out / "summary.json").write_text(json.dumps(result, indent=2), encoding="utf-8")
    for name in ("runs.csv", "summary.json"):
        path = args.out / name
        print(f"{path}: sha256={hashlib.sha256(path.read_bytes()).hexdigest()}")
    print(f"Completed {len(raw)} scenario-condition-budget-policy cells, each with {args.repeats} audit draws.")


if __name__ == "__main__":
    main()
