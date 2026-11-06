import hashlib
import pytest
from audit_capture.core import generate, fingerprint, to_dict
from audit_capture.import_scores import merge

def sample():
    s=generate(42)
    return s,{'scenario_sha256':fingerprint(s),'provenance':{'model':'TEST FIXTURE - not a real model','captured_utc':'2026-11-05T00:00:00Z','raw_response_sha256':hashlib.sha256(b'test-only').hexdigest(),'method':'unit test'},'scores':[{'action_id':a.id,'score':a.score} for a in s.actions]}

def test_merge_preserves_unverified_provenance():
    s,scores=sample(); r=merge(to_dict(s),scores)
    assert r['scenario']['source']=='imported_scored_trace'
    assert r['provenance_status']=='user_supplied_not_independently_authenticated'

@pytest.mark.parametrize('mutation',['hash','missing','duplicate','nan','timestamp','extra'])
def test_bad_evidence_rejected(mutation):
    s,scores=sample()
    if mutation=='hash': scores['scenario_sha256']='0'*64
    if mutation=='missing': scores['scores'].pop()
    if mutation=='duplicate': scores['scores'][0]=scores['scores'][1]
    if mutation=='nan': scores['scores'][0]['score']=float('nan')
    if mutation=='timestamp': scores['provenance']['captured_utc']='2026-11-05T00:00:00'
    if mutation=='extra': scores['scores'][0]['truth']=True
    with pytest.raises((ValueError,TypeError)): merge(to_dict(s),scores)
