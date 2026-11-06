"""Selection contrasts must compare matched scenarios, not audit draws."""
from collections import defaultdict
import random

import pytest

from audit_capture.evaluate import evaluate


@pytest.fixture(scope="module")
def study():
    return evaluate(cases=12, repeats=3)


def test_selection_contrasts_match_raw_paired_scenario_means(study):
    paired = defaultdict(dict)
    for row in study["raw"]:
        key = (row["profile"], row["budget"], row["policy"], row["seed"])
        paired[key][row["condition"]] = row["attack_rate"]

    contrasts = study["paired_selection_deltas"]
    assert len(contrasts) == 2 * 6 * 5
    assert len({(r["profile"], r["budget"], r["policy"]) for r in contrasts}) == len(contrasts)
    for contrast in contrasts:
        assert contrast["contrast"] == "selected_decoys_vs_random_decoys"
        assert contrast["condition"] == "selected_decoys"
        assert contrast["baseline_condition"] == "random_decoys"
        assert contrast["scenario_count"] == study["configuration"]["cases"]
        profile, budget, policy = (contrast[name] for name in ("profile", "budget", "policy"))
        differences = [values["selected_decoys"] - values["random_decoys"]
                       for (p, b, pol, _), values in sorted(paired.items())
                       if (p, b, pol) == (profile, budget, policy)]
        assert len(differences) == contrast["scenario_count"]
        assert contrast["delta"] == pytest.approx(sum(differences) / len(differences))

        # Each resampled item is an entire paired scenario's mean difference.
        # Individual repeated audit draws are deliberately unavailable here.
        rng = random.Random(f"paired-selection:{profile}:{budget}:{policy}")
        means = sorted(sum(rng.choices(differences, k=len(differences))) / len(differences)
                       for _ in range(study["configuration"]["bootstrap_resamples"]))
        assert contrast["ci"] == pytest.approx([means[9], means[389]])


def test_uniform_selection_contrast_is_zero_for_every_scenario(study):
    by_scenario = defaultdict(set)
    for row in study["raw"]:
        if row["policy"] == "uniform":
            by_scenario[row["profile"], row["budget"], row["seed"]].add(row["attack_rate"])
    assert by_scenario
    assert all(len(values) == 1 for values in by_scenario.values())
    for contrast in study["paired_selection_deltas"]:
        if contrast["policy"] == "uniform":
            assert contrast["delta"] == 0
            assert contrast["ci"] == [0, 0]


def test_original_contrast_keeps_ordinary_baseline(study):
    paired = defaultdict(dict)
    for row in study["raw"]:
        paired[row["profile"], row["budget"], row["policy"], row["seed"]][row["condition"]] = row["attack_rate"]
    assert len(study["paired_deltas"]) == 2 * 6 * 5
    for contrast in study["paired_deltas"]:
        assert set(contrast) == {"profile", "budget", "policy", "delta", "ci"}
        differences = [values["selected_decoys"] - values["ordinary"]
                       for (profile, budget, policy, _), values in paired.items()
                       if (profile, budget, policy) ==
                       (contrast["profile"], contrast["budget"], contrast["policy"])]
        assert contrast["delta"] == pytest.approx(sum(differences) / len(differences))
