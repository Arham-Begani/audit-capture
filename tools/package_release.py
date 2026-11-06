"""Create an allowlisted release, excluding credentials, vendor packages and caches."""
from datetime import datetime, timezone
import hashlib
import json
from pathlib import Path
import zipfile
import xml.etree.ElementTree as ET
from pypdf import PdfReader
import sys

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_capture.evidence import source_hash
test_tree=ET.parse(ROOT/'results/tests.xml')
suites=list(test_tree.iter('testsuite'))
tests=sum(int(s.get('tests','0')) for s in suites)
failures=sum(int(s.get('failures','0'))+int(s.get('errors','0')) for s in suites)
assert tests>0 and failures==0,'Passing test evidence is required'
browser=json.loads((ROOT/'results/browser-checks.json').read_text())
study_hash=hashlib.sha256((ROOT/'results/summary.json').read_bytes()).hexdigest()
assert browser['status']=='passed' and not browser['page_errors'],'Passing browser evidence is required'
assert browser['study_sha256']==study_hash,'Browser evidence refers to stale study results'
current_source=source_hash()
test_receipt=json.loads((ROOT/'results/test-checks.json').read_text())
exact=json.loads((ROOT/'results/exact-validation.json').read_text())
assert test_receipt['status']=='passed' and test_receipt['source_sha256']==current_source,'Unit-test evidence is stale'
assert browser['source_sha256']==current_source,'Browser source evidence is stale'
assert exact['status']=='passed' and exact['source_sha256']==current_source and exact['study_sha256']==study_hash,'Exact validation is stale'
pdf=PdfReader(ROOT/'output/pdf/audit-capture-research-draft.pdf')
report=json.loads((ROOT/'results/report-checks.json').read_text())
assert report['source_sha256']==current_source and report['study_sha256']==study_hash,'Report inputs are stale'
assert report['exact_sha256']==hashlib.sha256((ROOT/'results/exact-validation.json').read_bytes()).hexdigest(),'Report exact results are stale'
assert report['pdf_sha256']==hashlib.sha256((ROOT/'output/pdf/audit-capture-research-draft.pdf').read_bytes()).hexdigest(),'Report hash mismatch'
assert 1<=len(pdf.pages)<=8 and all('PRE-SPRINT REVIEW DRAFT' in page.extract_text() for page in pdf.pages)
verification={'verified_utc':datetime.now(timezone.utc).isoformat(),'tests_passed':tests,
              'test_failures':failures,'browser_checks_passed':len(browser['checks']),
              'page_errors':browser['page_errors'],'study_sha256':study_hash,'report_pages':len(pdf.pages),
              'source_sha256':current_source,'exact_cells':exact['exact_cells'],
              'evidence_type':'constructed_synthetic','live_model_runs':False,'submission_ready':False,
              'eligibility_basis':'Competition eligibility has not been verified',
              'remaining':['Competition eligibility requires verification before submission',
                           'Author identity, affiliation and required declarations need confirmation',
                           'November 5 baseline and November 6 readiness maintenance are disclosed separately; no judged-period contribution claimed',
                           'Representative live-model evidence absent; retain a synthetic-only claim unless collected',
                           'Author review and authority to accept final submission terms remain']}
(ROOT/'results/verification.json').write_text(json.dumps(verification,indent=2))
files=[]
for glob in ('audit_capture/*.py','web/*','web/fonts/*','tests/*.py','tools/*.py','docs/*.md','live_validation/*.py','live_validation/*.md','README.md','requirements-dev.txt','run.py','start.cmd','.gitignore','PREEXISTING_MANIFEST.json','results/*.json','results/*.csv','results/*.xml','results/*.png','results/*.svg','output/pdf/*.pdf'):
    files.extend(p for p in ROOT.glob(glob) if p.is_file())
files=sorted(set(files))
baseline_path=ROOT/'PREEXISTING_MANIFEST.json'
baseline_hash=hashlib.sha256(baseline_path.read_bytes()).hexdigest()
assert baseline_hash=='c008d0c2cd49dfc533d290398e3970de0f2641f0c680759941bf0ac4b6fa508e','Frozen November 5 baseline changed'
baseline=json.loads(baseline_path.read_text())
digests={p.relative_to(ROOT).as_posix():hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
comparison={name:('added' if name not in baseline['files'] else
                  'unchanged' if digest==baseline['files'][name] else 'changed')
            for name,digest in digests.items() if name!='PREEXISTING_MANIFEST.json'}
manifest={'created_utc':datetime.now(timezone.utc).isoformat(),
          'development_status':'November 5 pre-event baseline plus separately documented November 6 readiness maintenance; no judged-period work claimed',
          'baseline_manifest':'PREEXISTING_MANIFEST.json','baseline_manifest_sha256':baseline_hash,
          'baseline_archive_sha256':'d0a488b884ac51c21ce4161dba7851dae59cbc2f70a5d8d900058e423a67c3c2',
          'work_record':'docs/EVENT_WORK.md','comparison_to_baseline':comparison,
          'removed_since_baseline':sorted(set(baseline['files'])-set(digests)),
          'files':digests}
(ROOT/'RELEASE_MANIFEST.json').write_text(json.dumps(manifest,indent=2))
out=ROOT/'output';out.mkdir(exist_ok=True)
with zipfile.ZipFile(out/'audit-capture-review.zip','w',zipfile.ZIP_DEFLATED) as archive:
    for path in files+[ROOT/'RELEASE_MANIFEST.json']:
        archive.write(path,'audit-capture/'+path.relative_to(ROOT).as_posix())
print(out/'audit-capture-review.zip')
print(f'{len(files)+1} files; SHA-256 {hashlib.sha256((out/"audit-capture-review.zip").read_bytes()).hexdigest()}')
