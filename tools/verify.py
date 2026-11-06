"""Run executed checks and bind their receipts to the exact project inputs."""
from datetime import datetime, timezone
import json
from pathlib import Path
import subprocess
import sys
import uuid

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_capture.evidence import source_hash


def main():
    before=source_hash()
    (ROOT/'tmp').mkdir(exist_ok=True)
    temporary=(ROOT/'tmp'/('pytest-'+uuid.uuid4().hex)).resolve()
    assert temporary.is_relative_to((ROOT/'tmp').resolve())
    subprocess.run([sys.executable,'-m','pytest','-q','--junitxml=results/tests.xml',
                    '--basetemp='+str(temporary)],cwd=ROOT,check=True)
    if source_hash()!=before:
        raise RuntimeError('Project inputs changed during the tests; rerun verification')
    (ROOT/'results/test-checks.json').write_text(json.dumps({'status':'passed',
        'verified_utc':datetime.now(timezone.utc).isoformat(),'source_sha256':before},indent=2))
    for script in ('tools/exact_check.py','tools/browser_check.py'):
        subprocess.run([sys.executable,script],cwd=ROOT,check=True)
    if source_hash()!=before:
        raise RuntimeError('Project inputs changed during verification; rerun verification')
    print('All executed verification checks passed against source '+before)


if __name__=='__main__':main()
