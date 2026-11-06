"""Regression: every file-based evidence path must reject duplicate JSON keys."""
import json
from pathlib import Path
import subprocess
import sys
import pytest
from audit_capture.core import to_dict
from test_import import sample

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('target', ['scenario', 'scores'])
def test_cli_rejects_duplicate_keys_without_writing_output(tmp_path, target):
    scenario, scores=sample()
    scenario_path=tmp_path/'scenario.json'; scores_path=tmp_path/'scores.json'
    scenario_text=json.dumps(to_dict(scenario))
    scores_text=json.dumps(scores)
    if target=='scenario':
        scenario_text=scenario_text.replace('"seed": 42', '"seed": 0, "seed": 42')
    else:
        score=scenario.actions[0].score
        scores_text=scores_text.replace(f'"score": {score}',f'"score": 0.0, "score": {score}',1)
    scenario_path.write_text(scenario_text);scores_path.write_text(scores_text)
    result=subprocess.run([sys.executable,'-m','audit_capture.import_scores',
        '--scenario',str(scenario_path),'--scores',str(scores_path),'--out',str(tmp_path/'out.json')],
        cwd=ROOT,capture_output=True,text=True)
    assert result.returncode!=0 and 'Duplicate JSON key' in result.stderr
    assert not (tmp_path/'out.json').exists()
