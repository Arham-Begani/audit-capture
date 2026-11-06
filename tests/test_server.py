import json
from http.server import ThreadingHTTPServer
import threading
from urllib.error import HTTPError
from urllib.request import Request, urlopen
import pytest
from audit_capture.server import Handler
from audit_capture.core import generate, to_dict

@pytest.fixture(scope='module')
def base():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    yield f'http://127.0.0.1:{server.server_port}'
    server.shutdown();server.server_close();thread.join()

def post(base,path,data,origin=None):
    headers={'Content-Type':'application/json'}
    if origin: headers['Origin']=origin
    return urlopen(Request(base+path,data=json.dumps(data).encode(),headers=headers),timeout=3)

def test_run_api_and_static(base):
    with post(base,'/api/run',{'budget':2}) as response:
        d=json.load(response)
        assert len(d['comparisons'])==5 and d['result']['spent_units']<=2
        assert response.headers['X-Content-Type-Options']=='nosniff'
    with urlopen(base) as response: assert b'Audit Capture' in response.read()

@pytest.mark.parametrize('data',[{'budget':True},{'seed':'42'},{'profile':'fake'},{'unexpected':'x'},{'hard_block':float('nan')}])
def test_invalid_inputs(base,data):
    with pytest.raises(HTTPError) as error: post(base,'/api/run',data)
    assert error.value.code==400

def test_cross_origin_rejected(base):
    with pytest.raises(HTTPError) as error: post(base,'/api/run',{},'https://unrelated.example')
    assert error.value.code==403

def test_file_traversal_rejected(base):
    with pytest.raises(HTTPError) as error: urlopen(base+'/../audit_capture/core.py')
    assert error.value.code==404

@pytest.mark.parametrize('name',['manrope-latin.woff2','space-grotesk-latin.woff2'])
def test_local_font_assets_are_woff2(base,name):
    with urlopen(base+'/fonts/'+name) as response:
        assert response.headers.get_content_type()=='font/woff2'
        assert response.read(4)==b'wOF2'
        assert "default-src 'self'" in response.headers['Content-Security-Policy']

def test_font_directory_does_not_expand_file_access(base):
    for path in ['/fonts/../../audit_capture/core.py','/fonts/SOURCES.json']:
        with pytest.raises(HTTPError) as error: urlopen(base+path)
        assert error.value.code==404

def test_import_roundtrip_and_invalid_score(base):
    scenario=to_dict(generate(42))
    with post(base,'/api/import',{'scenario':scenario}) as response:
        assert json.load(response)['result']['evidence_type']=='constructed_synthetic'
    scenario['actions'][0]['score']=2
    with pytest.raises(HTTPError) as error: post(base,'/api/import',{'scenario':scenario})
    assert error.value.code==400
