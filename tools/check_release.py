"""Verify every packaged hash, then smoke-test a fresh extraction without site packages."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import socket
import subprocess
import sys
import tempfile
import time
from urllib.request import Request, urlopen
import zipfile

ROOT=Path(__file__).resolve().parents[1]


def main():
    archive_path=ROOT/'output/audit-capture-review.zip'
    (ROOT/'tmp').mkdir(exist_ok=True)
    with tempfile.TemporaryDirectory(prefix='release-check-',dir=ROOT/'tmp') as temporary:
        destination=Path(temporary).resolve()
        # Verify the absolute cleanup/extraction target stays in this workspace.
        assert destination.is_relative_to((ROOT/'tmp').resolve())
        with zipfile.ZipFile(archive_path) as archive:
            assert archive.testzip() is None
            names=archive.namelist()
            assert len(names)==len(set(names))
            for name in names:
                assert name.startswith('audit-capture/') and (destination/name).resolve().is_relative_to(destination)
            manifest=json.loads(archive.read('audit-capture/RELEASE_MANIFEST.json'))
            expected={'audit-capture/'+name for name in manifest['files']}|{'audit-capture/RELEASE_MANIFEST.json'}
            assert set(names)==expected
            for name,digest in manifest['files'].items():
                assert hashlib.sha256(archive.read('audit-capture/'+name)).hexdigest()==digest,name
            baseline_bytes=archive.read('audit-capture/PREEXISTING_MANIFEST.json')
            assert hashlib.sha256(baseline_bytes).hexdigest()==manifest['baseline_manifest_sha256']
            baseline=json.loads(baseline_bytes)
            for name,status in manifest['comparison_to_baseline'].items():
                expected_status=('added' if name not in baseline['files'] else
                                 'unchanged' if manifest['files'][name]==baseline['files'][name] else 'changed')
                assert status==expected_status,name
            assert manifest['comparison_to_baseline']['results/runs.csv']=='unchanged'
            assert manifest['comparison_to_baseline']['results/summary.json']=='unchanged'
            archive.extractall(destination)
        with socket.socket() as sock:
            sock.bind(('127.0.0.1',0));port=sock.getsockname()[1]
        process=subprocess.Popen([sys.executable,'-S','run.py','--port',str(port)],
                                 cwd=destination/'audit-capture',stdout=subprocess.PIPE,stderr=subprocess.PIPE)
        try:
            base=f'http://127.0.0.1:{port}'
            for attempt in range(50):
                try:
                    with urlopen(base+'/api/meta',timeout=1) as response: meta=json.load(response)
                    break
                except OSError:
                    if process.poll() is not None: raise RuntimeError(process.communicate()[1].decode())
                    time.sleep(.1)
            else: raise RuntimeError('Fresh release server did not start')
            assert meta['version']=='0.3.1'
            with urlopen(base,timeout=3) as response: assert b'Audit Capture' in response.read()
            with urlopen(base+'/api/results',timeout=3) as response: assert json.load(response)['configuration']['cases']==160
            for condition,violations in (('ordinary',0),('selected_decoys',1)):
                request=Request(base+'/api/run',data=json.dumps({'condition':condition,'budget':2}).encode(),
                                headers={'Content-Type':'application/json'})
                with urlopen(request,timeout=3) as response: assert json.load(response)['result']['violations']==violations
        finally:
            process.terminate()
            process.communicate(timeout=5)
    result={'status':'passed','verified_utc':datetime.now(timezone.utc).isoformat(),
            'archive_sha256':hashlib.sha256(archive_path.read_bytes()).hexdigest(),
            'files_verified':len(names),'fresh_extraction_smoke_test':'passed',
            'site_packages_disabled':True,'live_model_runs':False}
    (ROOT/'output/release-checks.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))


if __name__=='__main__':main()
