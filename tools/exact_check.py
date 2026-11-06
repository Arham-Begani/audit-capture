"""Cross-check saved simulation using exhaustive review choices (not live models)."""
from datetime import datetime, timezone
from fractions import Fraction
import hashlib
import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_capture.core import generate, POLICIES, run
from audit_capture.exact import expectation
from audit_capture.evidence import source_hash


def main():
    study = json.loads((ROOT/'results/summary.json').read_text())
    cases = study['configuration']['cases']
    start = study['configuration']['test_seed_start']
    rows, deterministic_checks = [], 0
    for profile in ('overlap', 'separated'):
        for policy in POLICIES:
            values = [expectation(generate(seed, profile=profile), policy, 2)['attack_executed']
                      for seed in range(start, start+cases)]
            exact = sum(values, Fraction()) / cases
            observed = next(r['attack_rate'] for r in study['summary'] if
                            (r['profile'], r['condition'], r['policy'], r['budget']) ==
                            (profile, 'selected_decoys', policy, 2))
            if policy in ('top_risk', 'hold_sensitive'):
                assert abs(observed-float(exact)) < 1e-12
                deterministic_checks += cases
            rows.append({'profile': profile, 'condition': 'selected_decoys', 'budget': 2,
                         'policy': policy, 'exact_fraction': str(exact), 'exact_rate': float(exact),
                         'saved_monte_carlo_rate': observed, 'sampling_difference': observed-float(exact)})
    # Formal boundaries: all score orderings are irrelevant to uniform coverage.
    for budget in range(7):
        for condition in ('ordinary', 'random_decoys', 'selected_decoys'):
            value = expectation(generate(42, condition), 'uniform', budget)['attack_executed']
            assert value == Fraction(6-budget, 6)
    fixture = {p: {key: str(value) for key, value in expectation(generate(42), p, 2).items()}
               for p in POLICIES}
    result = {'status': 'passed', 'created_utc': datetime.now(timezone.utc).isoformat(),
              'evidence_type': 'exact_enumeration_of_constructed_scenarios', 'live_model_runs': False,
              'source_sha256': source_hash(),
              'study_sha256': hashlib.sha256((ROOT/'results/summary.json').read_bytes()).hexdigest(),
              'deterministic_scenario_checks': deterministic_checks, 'uniform_boundary_checks': 21,
              'exact_cells': cases * 10, 'fixture_seed_42_budget_2': fixture, 'summary': rows,
              'limits': ['Exactness is conditional on this finite synthetic protocol.',
                         'No naturalistic agent behavior or monitor judgments were measured.',
                         'The oracle enumerates choices independently of core.run and core._schedule.']}
    (ROOT/'results/exact-validation.json').write_text(json.dumps(result, indent=2), encoding='utf-8')
    print(json.dumps({k: result[k] for k in ('status', 'exact_cells', 'deterministic_scenario_checks', 'uniform_boundary_checks')}))


if __name__ == '__main__':
    main()
