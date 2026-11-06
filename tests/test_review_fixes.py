from copy import deepcopy
import json
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest
from audit_capture.core import from_dict, to_dict, generate, fingerprint
from audit_capture.import_scores import merge, replay_evidence
from test_server import base, post
from test_import import sample


@pytest.mark.parametrize('field,value', [('id', []), ('id', ''), ('seed', True), ('seed', -1),
    ('split', {}), ('condition', []), ('profile', 'other'), ('source', 'live_llm'),
    ('actions', None), ('actions', {}), ('actions', [None]), ('grants', None),
    ('grants', [['root', 'unknown_op', 'r', 'd']]), ('grants', [['', 'export', 'r', 'd']])])
def test_invalid_metadata_is_a_clean_http_error(base, field, value):
    data = to_dict(generate())
    data[field] = value
    with pytest.raises((ValueError, TypeError)): from_dict(data)
    with pytest.raises(HTTPError) as error: post(base, '/api/import', {'scenario': data})
    assert error.value.code == 400


def test_provenance_and_nondefault_configuration_survive_roundtrip(base):
    s, scores = sample()
    trace = merge(to_dict(s), scores)
    cfg = {'policy': 'mixed', 'budget': 3, 'audit_seed': 93, 'hard_block': .97}
    with post(base, '/api/import', {**trace, **cfg}) as response:
        replay = json.load(response)
    assert replay['provenance'] == trace['provenance']
    assert replay['replay_config'] == cfg
    assert replay['scenario_sha256'] == fingerprint(from_dict(replay['scenario']))
    payload = {key: replay[key] for key in trace}
    with post(base, '/api/import', {**payload, **replay['replay_config']}) as response:
        repeated = json.load(response)
    assert repeated == replay
    payload['scenario']['actions'][0]['score'] = .001
    with pytest.raises(HTTPError) as error: post(base, '/api/import', {**payload, **cfg})
    assert error.value.code == 400


def test_missing_provenance_never_becomes_authenticated():
    s, scores = sample()
    trace = merge(to_dict(s), scores)
    del trace['provenance']
    trace['provenance_status'] = 'authenticated_live_model'
    assert replay_evidence(trace, from_dict(trace['scenario']))['provenance_status'] == 'missing'


@pytest.mark.parametrize('path', ['/', '/api/meta', '/api/run'])
def test_untrusted_host_rejected(base, path):
    data = b'{}' if path == '/api/run' else None
    with pytest.raises(HTTPError) as error:
        urlopen(Request(base+path, data=data, headers={'Host': 'untrusted.example', 'Content-Type': 'application/json'}), timeout=3)
    assert error.value.code == 403


def test_duplicate_json_key_rejected(base):
    with pytest.raises(HTTPError) as error:
        urlopen(Request(base+'/api/run', data=b'{"budget":2,"budget":0}', headers={'Content-Type': 'application/json'}), timeout=3)
    assert error.value.code == 400


def test_uploaded_document_rejects_duplicate_keys_before_normalizing(base):
    scenario=to_dict(generate(42))
    raw=json.dumps(scenario).replace('"seed": 42','"seed": 0, "seed": 42')
    data={'document':raw,'fallback_config':{'policy':'uniform','budget':2,'audit_seed':42,'hard_block':None}}
    with pytest.raises(HTTPError) as error: post(base,'/api/import',data)
    assert error.value.code==400


def test_uploaded_document_restores_saved_settings(base):
    scenario=to_dict(generate(42))
    saved={'policy':'top_risk','budget':3,'audit_seed':93,'hard_block':.97}
    data={'document':json.dumps({'scenario':scenario,'replay_config':saved}),
          'fallback_config':{'policy':'uniform','budget':0,'audit_seed':0,'hard_block':None}}
    with post(base,'/api/import',data) as response:
        assert json.load(response)['replay_config']==saved


@pytest.mark.parametrize('scores', [None, [], 42])
def test_invalid_score_envelope_clean_error(scores):
    with pytest.raises(ValueError): merge(to_dict(generate()), scores)
