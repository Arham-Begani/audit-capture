from collections import Counter
from dataclasses import replace
from fractions import Fraction
from itertools import permutations
import pytest
import audit_capture.core as core
from audit_capture.exact import review_sets, outcome, expectation


@pytest.mark.parametrize('policy', core.POLICIES)
@pytest.mark.parametrize('variant', ('unit', 'heterogeneous', 'blocked'))
def test_engine_matches_every_random_order_and_independent_outcome(monkeypatch, policy, variant):
    scenario = core.generate(42)
    threshold = .9 if variant == 'blocked' else None
    if variant == 'heterogeneous':
        scenario = replace(scenario, actions=tuple(replace(a, review_units=c, mandatory_review=a.id=='target')
                           for a, c in zip(scenario.actions, (2, 1, 3, 1, 2, 1))),
                           grants=frozenset(g for g in scenario.grants if g[2] != 'approved-dummy-4'))
    eligible = [a for a in scenario.actions if threshold is None or a.score < threshold]
    size = (len(eligible) if policy == 'uniform' else max(0, len(eligible)-1)
            if policy == 'mixed' else len({a.root for a in eligible}) if policy == 'root_fair' else 0)
    class FixedShuffle:
        def shuffle(self, items):
            items[:] = [items[i] for i in order]
    with monkeypatch.context() as patch:
        patch.setattr(core.random, 'Random', lambda seed: FixedShuffle())
        for budget in (0, 1, 2, 4, 6):
            counts = Counter()
            for order in permutations(range(size)):
                actual = core.run(scenario, policy, budget, hard_block_threshold=threshold)
                ids = frozenset(actual['audited_ids'])
                counts[ids] += 1
                independent = outcome(scenario, ids, policy, threshold)
                assert all(actual[key] == value for key, value in independent.items())
            total = sum(counts.values())
            assert {ids: Fraction(n, total) for ids, n in counts.items()} == review_sets(scenario, policy, budget, threshold)


def test_closed_form_boundaries_and_counterexample():
    scenario = core.generate(42)
    expected = {'top_risk': 1, 'uniform': Fraction(2, 3), 'mixed': Fraction(4, 5), 'root_fair': 1, 'hold_sensitive': 0}
    for policy, probability in expected.items():
        assert expectation(scenario, policy, 2)['attack_executed'] == probability
    for budget in range(7):
        assert expectation(scenario, 'uniform', budget)['attack_executed'] == Fraction(6-budget, 6)
        mandatory = replace(scenario, actions=(replace(scenario.actions[0], mandatory_review=True),)+scenario.actions[1:])
        for policy in core.POLICIES:
            assert expectation(mandatory, policy, budget)['attack_executed'] == 0


def test_uniform_k_over_n_does_not_extend_to_unequal_costs():
    s = core.generate(42)
    s = replace(s, actions=(replace(s.actions[0], review_units=3),)+s.actions[1:])
    assert expectation(s, 'uniform', 2)['attack_executed'] == 1


def test_exact_oracle_refuses_combinatorial_explosion():
    s = core.generate(42)
    s = replace(s, actions=tuple(replace(s.actions[0], id=str(i)) for i in range(9)))
    with pytest.raises(ValueError): review_sets(s, 'uniform', 2)
