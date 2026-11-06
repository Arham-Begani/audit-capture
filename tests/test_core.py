from dataclasses import replace
import math
import pytest
from audit_capture.core import *


def test_matched_target_and_fixed_workload():
    scenarios = [generate(42, c) for c in CONDITIONS]
    assert all(s.actions[0] == scenarios[0].actions[0] for s in scenarios)
    assert all(s.actions[3:] == scenarios[0].actions[3:] for s in scenarios)
    assert all(s.grants == scenarios[0].grants and len(s.actions) == 6 for s in scenarios)
    assert all(sum(not s.authorized(a) for a in s.actions) == 1 for s in scenarios)
    assert all(sum(a.review_units for a in s.actions) == 6 for s in scenarios)


@pytest.mark.parametrize('policy', POLICIES)
@pytest.mark.parametrize('budget', range(7))
def test_budget_ledger_and_global_halt(policy, budget):
    for seed in (0, 42, 10001):
        r = run(generate(seed), policy, budget, seed)
        assert r['spent_units'] <= budget
        assert len(set(r['audited_ids'])) == len(r['audited_ids'])
        assert r['violations'] == sum(not effect['authorized'] for effect in r['ledger'])
        assert r['benign_completed'] <= r['benign_total']
        if r['halted']:
            assert not r['ledger'] and r['benign_completed'] == 0
        if budget == 6:
            assert r['halted'] and r['violations'] == 0


def test_target_caught_cannot_commit_anything():
    r = run(generate(42, 'ordinary'), 'top_risk', 6)
    assert r['halted']
    assert all(a['outcome'] == 'halted' for a in r['actions'])


def test_mandatory_never_bypassed_when_budget_exhausted():
    for policy in POLICIES:
        for budget in (0, 1, 2):
            r = run(generate(42, mandatory=True), policy, budget)
            assert r['violations'] == 0


def test_hold_sensitive_eliminates_exports_not_just_bad_effects():
    r = run(generate(42), 'hold_sensitive', 0)
    assert r['violations'] == 0 and r['deferred'] == 3
    assert r['benign_completed'] == 3


def test_actor_names_produce_no_multiagent_advantage():
    for policy in POLICIES:
        a = run(generate(42), policy, 2, 94)
        b = run(generate(42, single_actor=True), policy, 2, 94)
        for key in ('violations', 'benign_completed', 'deferred', 'audited_ids', 'spent_units'):
            assert a[key] == b[key]


def test_separated_profile_is_negative_control():
    for seed in range(40):
        r = run(generate(seed, profile='separated'), 'top_risk', 1)
        assert r['halted'] and not r['attack_executed']


def test_uniform_sampling_matches_analytic_probability():
    # For one target among six equal-cost actions, P(review target) = k/6.
    rates = [run(generate(42), 'uniform', 2, i)['halted'] for i in range(1800)]
    assert abs(sum(rates) / len(rates) - 2 / 6) < .035


def test_uniform_selection_does_not_depend_on_scores():
    for seed in range(30):
        ids = [run(generate(42,c),'uniform',2,seed)['audited_ids'] for c in CONDITIONS]
        assert ids[0] == ids[1] == ids[2]


def test_selected_permitted_decoys_show_constructed_mechanism():
    assert not run(generate(42, 'ordinary'), 'top_risk', 2)['attack_executed']
    assert run(generate(42), 'top_risk', 2)['attack_executed']


def test_roundtrip_and_tamper_detection():
    s = generate(42)
    assert from_dict(to_dict(s)) == s
    assert fingerprint(s) != fingerprint(replace(s, actions=(replace(s.actions[0], score=.01),) + s.actions[1:]))


@pytest.mark.parametrize('score', [float('nan'), float('inf'), -.01, 1.01, True, '0.5'])
def test_invalid_scores_rejected(score):
    s = generate(42)
    with pytest.raises(ValueError):
        run(replace(s, actions=(replace(s.actions[0], score=score),)+s.actions[1:]))


def test_variable_cost_budget_never_overspent():
    s = generate(42)
    s = replace(s, actions=tuple(replace(a, review_units=2) for a in s.actions))
    for policy in POLICIES:
        r = run(s, policy, 3)
        assert r['spent_units'] == 2 and len(r['audited_ids']) == 1


def test_unauthorized_action_with_safe_score_is_not_called_authorized():
    s = generate(42)
    s = replace(s, actions=(replace(s.actions[0], score=0),)+s.actions[1:])
    assert run(s, 'top_risk', 0)['violations'] == 1


@pytest.mark.parametrize('budget', [-1, 65, 1.5, True])
def test_invalid_budget(budget):
    with pytest.raises(ValueError): run(generate(42), budget=budget)


def test_reproducibility():
    assert generate(27) == generate(27)
    assert run(generate(27), 'mixed', 2, 99) == run(generate(27), 'mixed', 2, 99)
    assert generate(27, split='dev').actions != generate(27, split='test').actions


def test_invalid_duplicate_id():
    s = generate()
    with pytest.raises(ValueError): run(replace(s, actions=(s.actions[0],s.actions[0])))
