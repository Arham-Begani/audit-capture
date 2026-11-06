"""Fake-server integration tests. These never execute a language model."""
import hashlib
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
import json
from pathlib import Path
import sys
import threading
import pytest

sys.path.insert(0,str(Path(__file__).resolve().parent))
from capture_local import capture, validate_base, strict_json
from audit_capture.core import generate, to_dict, fingerprint


@pytest.fixture
def endpoint():
    state={'mode':'valid','calls':[]}
    scenario=generate(42)
    class Handler(BaseHTTPRequestHandler):
        def log_message(self,*args): pass
        def send(self,code,value):
            raw=json.dumps(value).encode()
            self.send_response(code);self.send_header('Content-Length',str(len(raw)));self.end_headers();self.wfile.write(raw)
        def do_GET(self):
            state['calls'].append(self.path)
            if state['mode']=='redirect':
                self.send_response(302);self.send_header('Location','http://outside.invalid/v1/models');self.end_headers();return
            self.send(200,{'data':[{'id':'TEST-FIXTURE-NO-MODEL'}]})
        def do_POST(self):
            state['calls'].append(self.path)
            state['request_bytes']=self.rfile.read(int(self.headers['Content-Length']))
            state['request']=json.loads(state['request_bytes'])
            if state['mode']=='broken_body':
                raw=b'{"model":'
                self.send_response(200);self.send_header('Content-Length',str(len(raw)+50))
                self.end_headers();self.wfile.write(raw);self.close_connection=True;return
            content=json.dumps({'scores':[{'action_id':a.id,'score':a.score} for a in scenario.actions]})
            if state['mode']=='invalid': content='not JSON'
            if state['mode']=='missing': content=json.dumps({'scores':[]})
            if state['mode']=='error': self.send(503,{'error':'TEST FIXTURE offline'});return
            self.send(200,{'model':'wrong-model' if state['mode']=='wrong_model' else 'TEST-FIXTURE-NO-MODEL',
                          'choices':[{'finish_reason':'length' if state['mode']=='truncated' else 'stop',
                                      'message':{'content':content}}], 'usage':{'test_fixture':True}})
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}/v1',state,scenario
    server.shutdown();server.server_close();thread.join()


def packet(s):
    return {'scenario_sha256':fingerprint(s),'max_tokens':256,
            'messages':[{'role':'user','content':'Transport test only; do not interpret as research.'}]}


def test_capture_preserves_raw_evidence_and_import_binding(endpoint,tmp_path):
    base,state,scenario=endpoint
    out=tmp_path/'capture'
    receipt=capture(base,'TEST-FIXTURE-NO-MODEL',packet(scenario),to_dict(scenario),out,True)
    assert receipt['evidence_type']=='test_fixture'
    assert receipt['model_execution_independently_authenticated'] is False
    assert receipt['status']=='captured_and_validated'
    assert state['calls']==['/v1/models','/v1/chat/completions']
    assert state['request']['max_tokens']==256
    assert (out/'request.json').read_bytes()==state['request_bytes']
    assert receipt['request_sha256']==hashlib.sha256(state['request_bytes']).hexdigest()
    for name,digest in receipt['artifacts_sha256'].items():
        assert hashlib.sha256((out/name).read_bytes()).hexdigest()==digest
    raw_hash=hashlib.sha256((out/'raw-response.json').read_bytes()).hexdigest()
    imported=json.loads((out/'imported.json').read_text())
    assert imported['provenance']['raw_response_sha256']==raw_hash
    assert imported['provenance_status']=='user_supplied_not_independently_authenticated'
    assert imported['provenance']['method']=='TEST FIXTURE; no inference'
    with pytest.raises(FileExistsError): capture(base,'TEST-FIXTURE-NO-MODEL',packet(scenario),to_dict(scenario),out,True)
    assert len(state['calls'])==2


@pytest.mark.parametrize('mode',['invalid','missing','truncated','wrong_model','error','broken_body'])
def test_failure_is_retained_and_never_retried(endpoint,tmp_path,mode):
    base,state,scenario=endpoint;state['mode']=mode
    out=tmp_path/mode
    with pytest.raises(ValueError): capture(base,'TEST-FIXTURE-NO-MODEL',packet(scenario),to_dict(scenario),out,True)
    receipt=json.loads((out/'receipt.json').read_text())
    assert receipt['status']=='failed' and receipt['completion_requests_attempted']==1
    assert (out/'raw-response.json').exists() and not (out/'imported.json').exists()
    assert receipt['request_sha256']==hashlib.sha256(state['request_bytes']).hexdigest()
    assert receipt['artifacts_sha256']['raw-response.json']==hashlib.sha256((out/'raw-response.json').read_bytes()).hexdigest()
    if mode=='broken_body':
        assert (out/'raw-response.json').read_bytes()==b'{"model":'
        assert 'Incomplete HTTP response' in receipt['error']
    assert state['calls']==['/v1/models','/v1/chat/completions']


def test_redirect_and_unadvertised_model_never_call_completion(endpoint,tmp_path):
    base,state,scenario=endpoint
    with pytest.raises(ValueError): capture(base,'different',packet(scenario),to_dict(scenario),tmp_path/'missing',True)
    assert state['calls']==['/v1/models']
    state['mode']='redirect';state['calls']=[]
    with pytest.raises(ValueError): capture(base,'TEST-FIXTURE-NO-MODEL',packet(scenario),to_dict(scenario),tmp_path/'redirect',True)
    assert state['calls']==['/v1/models']


@pytest.mark.parametrize('url',['https://api.openai.com/v1','http://localhost:8080/v1','http://127.0.0.1/v1',
    'http://user:secret@127.0.0.1:8000/v1','http://127.0.0.1:8080/v1?x=1','http://192.168.1.1:8080/v1'])
def test_nonlocal_or_ambiguous_routes_rejected(url):
    with pytest.raises(ValueError): validate_base(url)


def test_hash_mismatch_fails_before_any_network_request(endpoint,tmp_path):
    base,state,scenario=endpoint;p=packet(scenario);p['scenario_sha256']='0'*64
    with pytest.raises(ValueError): capture(base,'TEST-FIXTURE-NO-MODEL',p,to_dict(scenario),tmp_path/'bad',True)
    assert state['calls']==[] and not (tmp_path/'bad').exists()


@pytest.mark.parametrize('budget',[0,513,True])
def test_token_limit_rejected_before_network(endpoint,tmp_path,budget):
    base,state,scenario=endpoint;p=packet(scenario);p['max_tokens']=budget
    with pytest.raises(ValueError): capture(base,'TEST-FIXTURE-NO-MODEL',p,to_dict(scenario),tmp_path/'bad',True)
    assert state['calls']==[]


def test_invalid_scenario_container_is_clean_error(tmp_path):
    with pytest.raises(ValueError): capture('http://127.0.0.1:1234/v1','TEST',{},None,tmp_path/'bad',True)


@pytest.mark.parametrize('text',['{"x":1,"x":2}','{"x":NaN}'])
def test_ambiguous_json_rejected(text):
    with pytest.raises(ValueError): strict_json(text)
