"""One bounded request to an existing loopback model server; no installs or paid APIs.

This captures HTTP evidence, not independently authenticated model execution.
The existing synthetic release is not modified.
"""
import argparse
from datetime import datetime, timezone
import hashlib
from http.client import IncompleteRead
import json
from pathlib import Path
import sys
import time
from urllib.error import HTTPError
from urllib.parse import urlsplit
from urllib.request import Request, build_opener, HTTPRedirectHandler, ProxyHandler

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_capture.core import from_dict, fingerprint
from audit_capture.import_scores import merge
from audit_capture.json_io import loads as strict_json

LIMIT=256_000


class NoRedirect(HTTPRedirectHandler):
    def redirect_request(self, req, fp, code, msg, headers, newurl):
        return None


def validate_base(base):
    parts=urlsplit(base)
    if (parts.scheme!='http' or parts.hostname!='127.0.0.1' or parts.username or parts.password
            or parts.port is None or parts.path!='/v1' or parts.query or parts.fragment):
        raise ValueError('Use an existing local server at http://127.0.0.1:PORT/v1')
    return base


def read_json(path):
    raw=path.read_bytes()
    if len(raw)>LIMIT: raise ValueError('Input exceeds 256 KB')
    return strict_json(raw)


def write_json(path,data):
    with path.open('x',encoding='utf-8') as stream:
        json.dump(data,stream,indent=2,allow_nan=False)


def capture(base, model, packet, scenario_data, out, fixture_mode=False):
    validate_base(base)
    if not isinstance(model,str) or not 1<=len(model)<=256:
        raise ValueError('Explicit model identifier required')
    if not isinstance(scenario_data,dict): raise ValueError('Scenario input must be an object')
    if type(fixture_mode) is not bool: raise ValueError('fixture_mode must be boolean')
    scenario=from_dict(scenario_data.get('scenario',scenario_data))
    if not isinstance(packet,dict) or set(packet)!={'scenario_sha256','messages','max_tokens'}:
        raise ValueError('Packet requires scenario_sha256, messages and max_tokens')
    if packet['scenario_sha256']!=fingerprint(scenario): raise ValueError('Input scenario hash mismatch')
    if type(packet['max_tokens']) is not int or not 1<=packet['max_tokens']<=512:
        raise ValueError('max_tokens must be 1-512')
    messages=packet['messages']
    if not isinstance(messages,list) or not 1<=len(messages)<=8:
        raise ValueError('Provide 1-8 reviewed system/user messages')
    for message in messages:
        if (not isinstance(message,dict) or set(message)!={'role','content'}
                or message['role'] not in ('system','user') or not isinstance(message['content'],str)
                or not 1<=len(message['content'])<=16000):
            raise ValueError('Invalid message')
    if len(json.dumps(packet).encode())>LIMIT: raise ValueError('Packet exceeds 256 KB')
    out=Path(out)
    out.mkdir(parents=True,exist_ok=False)
    write_json(out/'packet.json',packet)
    write_json(out/'scenario.json',scenario_data)
    request={'model':model,'messages':messages,'temperature':0,'seed':0,
             'max_tokens':packet['max_tokens'],'response_format':{'type':'json_object'},'stream':False}
    request_bytes=json.dumps(request,allow_nan=False).encode('utf-8')
    with (out/'request.json').open('xb') as stream:
        stream.write(request_bytes)
    receipt={'started_utc':datetime.now(timezone.utc).isoformat(),'status':'started',
             'evidence_type':'test_fixture' if fixture_mode else 'local_http_capture_unverified_model',
             'model_execution_independently_authenticated':False,'requested_model':model,
             'endpoint':base,'scenario_sha256':fingerprint(scenario),
             'packet_sha256':hashlib.sha256((out/'packet.json').read_bytes()).hexdigest(),
             'request_sha256':hashlib.sha256(request_bytes).hexdigest(),
             'source_sha256':hashlib.sha256(Path(__file__).read_bytes()).hexdigest(),
             'maximum_completion_requests':1,'completion_requests_attempted':0,'automatic_retries':0}
    opener=build_opener(ProxyHandler({}),NoRedirect())
    def read_response(response,filename):
        try:
            raw=response.read(LIMIT+1)
        except IncompleteRead as exc:
            (out/filename).write_bytes(exc.partial[:LIMIT+1])
            raise ValueError('Incomplete HTTP response; captured prefix retained') from exc
        (out/filename).write_bytes(raw)
        if len(raw)>LIMIT: raise ValueError('Response exceeds 256 KB; captured prefix retained')
        declared=response.headers.get('Content-Length')
        if declared is not None and len(raw)!=int(declared):
            raise ValueError('Incomplete HTTP response; captured prefix retained')
        return raw
    def fetch(path,filename,payload=None):
        req=Request(base+path,data=payload,
                    headers={'Content-Type':'application/json'})
        try:
            with opener.open(req,timeout=60) as response:
                raw=read_response(response,filename)
        except HTTPError as exc:
            read_response(exc,filename)
            raise ValueError(f'Local endpoint returned HTTP {exc.code}; response retained') from exc
        return strict_json(raw)
    started=time.monotonic()
    try:
        metadata=fetch('/models','models-response.json')
        if not isinstance(metadata,dict) or not isinstance(metadata.get('data'),list):
            raise ValueError('Invalid local model metadata')
        if model not in [item.get('id') for item in metadata['data'] if isinstance(item,dict)]:
            raise ValueError('Requested model not advertised by local endpoint')
        receipt['completion_requests_attempted']=1
        response=fetch('/chat/completions','raw-response.json',request_bytes)
        if not isinstance(response,dict) or response.get('model')!=model:
            raise ValueError('Response model does not match requested model')
        choices=response.get('choices')
        if not isinstance(choices,list) or len(choices)!=1 or not isinstance(choices[0],dict):
            raise ValueError('Expected one model choice')
        choice=choices[0]
        if choice.get('finish_reason')!='stop': raise ValueError('Incomplete response; no repair or retry performed')
        message=choice.get('message')
        if not isinstance(message,dict) or not isinstance(message.get('content'),str) or message.get('tool_calls'):
            raise ValueError('Expected text-only JSON content')
        parsed=strict_json(message['content'])
        if not isinstance(parsed,dict) or set(parsed)!={'scores'}: raise ValueError('Expected a scores object')
        raw_hash=hashlib.sha256((out/'raw-response.json').read_bytes()).hexdigest()
        scores={'scenario_sha256':fingerprint(scenario),'scores':parsed['scores'],
                'provenance':{'model':model,'captured_utc':datetime.now(timezone.utc).isoformat(),
                              'raw_response_sha256':raw_hash,
                              'method':('TEST FIXTURE; no inference' if fixture_mode else
                                        'Captured from local HTTP server; model identity is self-reported')}}
        imported=merge(scenario_data,scores)
        write_json(out/'scores.json',scores)
        write_json(out/'imported.json',imported)
        receipt.update(status='captured_and_validated',raw_response_sha256=raw_hash,
                       response_model=response['model'],usage=response.get('usage'))
    except Exception as exc:
        receipt.update(status='failed',error_type=type(exc).__name__,error=str(exc)[:400])
        raise
    finally:
        receipt['elapsed_seconds']=round(time.monotonic()-started,3)
        receipt['finished_utc']=datetime.now(timezone.utc).isoformat()
        receipt['artifacts_sha256']={p.name:hashlib.sha256(p.read_bytes()).hexdigest()
                                    for p in sorted(out.iterdir()) if p.is_file()}
        write_json(out/'receipt.json',receipt)
    return receipt


def main():
    parser=argparse.ArgumentParser(description=__doc__)
    parser.add_argument('--base-url',required=True)
    parser.add_argument('--model',required=True)
    parser.add_argument('--packet',required=True,type=Path)
    parser.add_argument('--scenario',required=True,type=Path)
    parser.add_argument('--out',required=True,type=Path)
    parser.add_argument('--fixture-mode',action='store_true',help='Label a fake-server transport test explicitly')
    args=parser.parse_args()
    try:
        result=capture(args.base_url,args.model,read_json(args.packet),read_json(args.scenario),args.out,args.fixture_mode)
    except (ValueError,TypeError,OSError,KeyError) as exc: parser.error(str(exc))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
