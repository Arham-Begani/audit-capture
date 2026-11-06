"""Independent finite-state oracle. Enumerates choices; never calls core.run/_schedule.

This validates the defined toy protocol, not an LLM or a real deployment.
The enumeration is deliberately limited to at most eight proposals.
"""
from collections import Counter, defaultdict
from fractions import Fraction
from itertools import combinations, permutations
import math

POLICIES = ('top_risk', 'uniform', 'mixed', 'root_fair', 'hold_sensitive')


def review_sets(scenario, policy, budget, threshold=None):
    if not 1 <= len(scenario.actions) <= 8:
        raise ValueError('Exact oracle supports 1-8 proposals')
    if policy not in POLICIES:
        raise ValueError('Unknown policy')
    eligible = [a for a in scenario.actions if threshold is None or a.score < threshold]
    ranked = sorted(eligible, key=lambda a: (-a.score, a.id))
    # Equal-cost random review has uniform subsets, avoiding redundant orders.
    if policy in ('uniform', 'mixed') and all(a.review_units == 1 for a in eligible):
        k = min(budget, len(eligible))
        fixed = ranked[:1] if policy == 'mixed' and k else []
        tail = [a for a in eligible if a not in fixed]
        return {frozenset(a.id for a in fixed + list(subset)): Fraction(1, math.comb(len(tail), k-len(fixed)))
                for subset in combinations(tail, k-len(fixed))}
    if policy == 'uniform':
        orders = permutations(eligible)
    elif policy == 'mixed':
        orders = (tuple(ranked[:1]) + order for order in permutations(ranked[1:]))
    elif policy == 'root_fair':
        roots = sorted({a.root for a in eligible})
        groups = {root: [a for a in ranked if a.root == root] for root in roots}
        orders = (tuple(groups[root][depth] for depth in range(max(map(len, groups.values()), default=0))
                        for root in order if depth < len(groups[root])) for order in permutations(roots))
    else:
        orders = [ranked]
    counts = Counter()
    for order in orders:
        remaining, audited = budget, []
        for action in order:
            if action.review_units <= remaining:
                remaining -= action.review_units
                audited.append(action.id)
        counts[frozenset(audited)] += 1
    total = sum(counts.values())
    return {ids: Fraction(count, total) for ids, count in counts.items()}


def outcome(scenario, audited, policy, threshold=None):
    """Separate specification of commit/hold behavior for a chosen audit set."""
    allowed = {a.id for a in scenario.actions
               if (a.root, a.operation, a.record, a.destination) in scenario.grants}
    blocked = {a.id for a in scenario.actions if threshold is not None and a.score >= threshold}
    halt = bool(set(audited) - allowed)
    pending = {a.id for a in scenario.actions if a.id not in audited and a.id not in blocked
               and (a.mandatory_review or (policy == 'hold_sensitive' and a.operation == 'export'))}
    committed = set() if halt else {a.id for a in scenario.actions} - blocked - pending
    return {'attack_executed': bool(committed - allowed), 'violations': len(committed - allowed),
            'benign_completed': len(committed & allowed), 'deferred': 0 if halt else len(pending),
            'spent_units': sum(a.review_units for a in scenario.actions if a.id in audited),
            'halted': halt}


def expectation(scenario, policy, budget, threshold=None):
    totals = defaultdict(Fraction)
    distribution = review_sets(scenario, policy, budget, threshold)
    for audited, probability in distribution.items():
        for key, value in outcome(scenario, audited, policy, threshold).items():
            totals[key] += probability * value
    return dict(totals)
