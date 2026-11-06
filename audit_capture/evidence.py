"""Bind verification to project inputs, excluding generated outputs and secrets."""
import hashlib
import json
from pathlib import Path

ROOT = Path(__file__).resolve().parents[1]
PATTERNS = ('audit_capture/*.py', 'tests/*.py', 'tools/*.py', 'web/*', 'web/fonts/*',
            'docs/*.md', 'live_validation/*.py', 'live_validation/*.md',
            'README.md', 'requirements-dev.txt', 'run.py', 'start.cmd')


def source_hash(root=ROOT):
    files = sorted({p for pattern in PATTERNS for p in root.glob(pattern) if p.is_file()})
    manifest = {p.relative_to(root).as_posix(): hashlib.sha256(p.read_bytes()).hexdigest() for p in files}
    return hashlib.sha256(json.dumps(manifest, sort_keys=True).encode()).hexdigest()
