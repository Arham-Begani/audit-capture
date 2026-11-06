"""Validate external judgments without calling a paid model service.

python -m audit_capture.import_scores --scenario example.json --scores scores.json --out imported.json
Input provenance is preserved, but user-supplied claims are not independently authenticated.
"""
import argparse
from datetime import datetime
import json
from pathlib import Path
import re
from dataclasses import replace
from .core import fingerprint, from_dict, to_dict, validate
from .json_io import loads as strict_loads


def validate_provenance(provenance):
    if not isinstance(provenance, dict) or set(provenance) != {'model', 'captured_utc', 'raw_response_sha256', 'method'}:
        raise ValueError('Provenance requires model, captured_utc, raw_response_sha256, and method')
    if not all(isinstance(value, str) and 0 < len(value) <= 512 for value in provenance.values()):
        raise ValueError('Invalid provenance strings')
    if not re.fullmatch('[a-f0-9]{64}', provenance['raw_response_sha256']):
        raise ValueError('Raw response hash must be a lowercase SHA-256 hex digest')
    timestamp = datetime.fromisoformat(provenance['captured_utc'].replace('Z', '+00:00'))
    if timestamp.tzinfo is None or timestamp.utcoffset().total_seconds() != 0:
        raise ValueError('captured_utc must be timezone-aware UTC')
    return dict(provenance)


def replay_evidence(data, scenario):
    """Preserve supplied evidence without authenticating its claimed origin."""
    supplied_hash = data.get('scenario_sha256')
    current_hash = fingerprint(scenario)
    if supplied_hash is not None and supplied_hash != current_hash:
        raise ValueError('Replay hash mismatch; scenario was changed')
    result = {'scenario_sha256': current_hash}
    if 'provenance' in data:
        if scenario.source != 'imported_scored_trace' or supplied_hash is None:
            raise ValueError('Provenance requires an imported trace and its scenario_sha256')
        result['provenance'] = validate_provenance(data['provenance'])
        result['provenance_status'] = 'user_supplied_not_independently_authenticated'
        original = data.get('original_scenario_sha256')
        if original is not None:
            if not isinstance(original, str) or not re.fullmatch('[a-f0-9]{64}', original):
                raise ValueError('Invalid original scenario hash')
            result['original_scenario_sha256'] = original
    else:
        result['provenance_status'] = ('missing' if scenario.source == 'imported_scored_trace'
                                       else 'not_applicable_synthetic')
    return result


def merge(scenario_data, scores):
    if not isinstance(scenario_data, dict):
        raise ValueError('Scenario must be an object')
    scenario = from_dict(scenario_data.get('scenario', scenario_data))
    if not isinstance(scores, dict) or set(scores) != {'scenario_sha256', 'provenance', 'scores'}:
        raise ValueError('Scores require scenario_sha256, provenance, and scores')
    if scores['scenario_sha256'] != fingerprint(scenario):
        raise ValueError('Scenario hash mismatch; judgments belong to another input')
    provenance = validate_provenance(scores['provenance'])
    records = scores['scores']
    if not isinstance(records, list) or len(records) != len(scenario.actions):
        raise ValueError('Every action needs exactly one judgment')
    if any(not isinstance(item, dict) or set(item) != {'action_id', 'score'} for item in records):
        raise ValueError('Each judgment requires action_id and score')
    ids = [item['action_id'] for item in records]
    if any(not isinstance(i, str) for i in ids) or len(set(ids)) != len(ids) or set(ids) != {a.id for a in scenario.actions}:
        raise ValueError('Missing, duplicate, or unknown action IDs')
    mapping = {item['action_id']: item['score'] for item in records}
    imported = replace(scenario, actions=tuple(replace(a, score=mapping[a.id]) for a in scenario.actions),
                       source='imported_scored_trace')
    validate(imported)
    return {'scenario': to_dict(imported), 'provenance': provenance,
            'provenance_status': 'user_supplied_not_independently_authenticated',
            'scenario_sha256': fingerprint(imported),
            'original_scenario_sha256': fingerprint(scenario)}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--scenario', type=Path, required=True)
    parser.add_argument('--scores', type=Path, required=True)
    parser.add_argument('--out', type=Path, required=True)
    args = parser.parse_args()
    try:
        result = merge(strict_loads(args.scenario.read_text(encoding='utf-8-sig')),
                       strict_loads(args.scores.read_text(encoding='utf-8-sig')))
        with args.out.open('x', encoding='utf-8') as stream:
            stream.write(json.dumps(result, indent=2))
    except (ValueError, TypeError, KeyError, OSError) as exc:
        parser.error(str(exc))
    print(args.out)


if __name__ == '__main__':
    main()
