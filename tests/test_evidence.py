from audit_capture.evidence import source_hash


def test_verification_detects_source_changes_but_ignores_generated_results(tmp_path):
    (tmp_path/'audit_capture').mkdir()
    source=tmp_path/'audit_capture/core.py'
    source.write_text('version = 1')
    original=source_hash(tmp_path)
    (tmp_path/'results').mkdir()
    (tmp_path/'results/summary.json').write_text('{}')
    assert source_hash(tmp_path)==original
    source.write_text('version = 2')
    assert source_hash(tmp_path)!=original
