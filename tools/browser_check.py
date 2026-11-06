"""Real desktop/mobile browser checks against a temporary loopback server."""
import json
import os
from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer

ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_capture.server import Handler
from audit_capture.evidence import source_hash
from audit_capture.import_scores import merge
from audit_capture.core import generate, to_dict, fingerprint
from playwright.sync_api import sync_playwright, expect

def main():
    server=ThreadingHTTPServer(('127.0.0.1',0),Handler)
    thread=threading.Thread(target=server.serve_forever,daemon=True);thread.start()
    out=ROOT/'results';out.mkdir(exist_ok=True)
    errors=[]; checks=[]
    try:
        with sync_playwright() as p:
            installed=[Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
            executable=next((str(path) for path in installed if path.exists()),None)
            browser=p.chromium.launch(headless=True,executable_path=executable)
            page=browser.new_page(viewport={'width':1440,'height':1100},device_scale_factor=1)
            page.on('pageerror',lambda error:errors.append(str(error)))
            page.on('console',lambda msg:errors.append(msg.text) if msg.type=='error' else None)
            page.goto(f'http://127.0.0.1:{server.server_port}',wait_until='networkidle')
            expect(page.locator('#violations')).not_to_have_text('—')
            assert page.locator('#violations').inner_text()=='1';checks.append('Selected fixture executes the prohibited dummy effect')
            page.locator('#condition').select_option('ordinary')
            expect(page.locator('#draft-state')).to_contain_text('Settings changed')
            expect(page.locator('#replay-title')).to_have_text('Selected permitted decoys')
            page.locator('#run').click()
            expect(page.locator('#violations')).to_have_text('0')
            checks.append('Ordinary fixture halts the same target before commit')
            page.locator('#condition').select_option('selected_decoys');page.locator('#policy').select_option('hold_sensitive');page.locator('#run').click()
            expect(page.locator('#comparison tr.active th').first).to_have_text('Hold sensitive actions')
            assert page.locator('#violations').inner_text()=='0'; checks.append('Sensitive-action hold prevents the effect')
            page.locator('.advanced summary').click()
            page.locator('#policy').select_option('top_risk');page.locator('#mandatory').check();page.locator('#budget').fill('0');page.locator('#run').click()
            expect(page.locator('#spent')).to_have_text('0 / 0')
            assert page.locator('#violations').inner_text()=='0';checks.append('Mandatory target review survives a zero budget')
            page.locator('#mandatory').uncheck();page.locator('#budget').fill('2');page.locator('#run').click()
            expect(page.locator('#violations')).to_have_text('1')
            page.locator('#walkthrough').click();page.locator('#matched').wait_for(state='visible');expect(page.locator('#walkthrough')).to_be_enabled()
            assert page.locator('#matched article').count()==3
            assert page.locator('#matched article h3').all_text_contents()==['Ordinary permitted work','Random permitted decoys','Selected permitted decoys']
            expect(page.locator('#matched')).to_contain_text('not an effect estimate')
            checks.append('All three matched backgrounds render with contrast limitations')
            with page.expect_download() as download_info:page.locator('#download').click()
            path=out/'browser-download.json';download_info.value.save_as(path)
            replay=json.loads(path.read_text());assert replay['result']['violations']==1
            # Import must restore the exported configuration, not current controls.
            page.locator('#policy').select_option('hold_sensitive')
            page.locator('#budget').fill('0')
            with page.expect_response(lambda response: '/api/import' in response.url) as imported:
                page.locator('#import').set_input_files(path)
            assert imported.value.status==200
            expect(page.locator('#violations')).to_have_text('1')
            expect(page.locator('#spent')).to_have_text('2 / 2')
            assert not page.locator('#error').is_visible();checks.append('JSON download/import roundtrip works')
            expect(page.locator('#replay-source')).to_contain_text('IMPORTED FILE')
            expect(page.locator('#draft-state')).to_contain_text('Run creates a new generated scenario')
            expect(page.locator('#replay-context')).to_contain_text('Highest risk first')
            expect(page.locator('#policy')).to_have_value('hold_sensitive')
            checks.append('Imported replay and saved settings are explicitly separated from draft controls')
            import hashlib
            scenario=generate(42)
            trace=merge(to_dict(scenario),{'scenario_sha256':fingerprint(scenario),
                'provenance':{'model':'BROWSER TEST FIXTURE - NOT A MODEL RUN','captured_utc':'2026-11-05T00:00:00Z',
                              'raw_response_sha256':hashlib.sha256(b'test-only').hexdigest(),'method':'browser fixture'},
                'scores':[{'action_id':a.id,'score':a.score} for a in scenario.actions]})
            trace['replay_config']=replay['replay_config']
            with page.expect_response(lambda response: '/api/import' in response.url):
                page.locator('#import').set_input_files({'name':'test-trace.json','mimeType':'application/json','buffer':json.dumps(trace).encode()})
            expect(page.locator('#import-note')).to_contain_text('BROWSER TEST FIXTURE')
            with page.expect_download() as evidence_download: page.locator('#download').click()
            downloaded=json.loads(Path(evidence_download.value.path()).read_text())
            assert downloaded['provenance']==trace['provenance']
            assert downloaded['scenario_sha256']==trace['scenario_sha256']
            checks.append('Imported provenance and hash survive browser download')
            # Restore the constructed fixture for screenshots, then check errors visibly.
            with page.expect_response(lambda response: '/api/import' in response.url):
                page.locator('#import').set_input_files(path)
            expect(page.locator('#import-note')).to_contain_text('Constructed synthetic')
            page.locator('#import').set_input_files({'name':'broken.json','mimeType':'application/json','buffer':b'null'})
            expect(page.locator('#error')).to_have_text('Expected a scenario object')
            assert page.locator('#violations').inner_text()=='1'
            checks.append('Malformed import shows an error and preserves the displayed replay')
            page.locator('#truth').uncheck();assert page.locator('#queue .badge').count()==0
            page.locator('#truth').check();assert page.locator('#queue .badge').count()==6
            assert page.locator('#chart svg').count()==1
            expect(page.locator('#queue .target')).to_have_count(1)
            # Saved study filters are independent, and every plotted point has a table value.
            page.locator('.sensitivity > summary').click()
            page.locator('#study-profile').select_option('separated')
            page.locator('#study-condition').select_option('random_decoys')
            expect(page.locator('#chart-title')).to_contain_text('Random permitted decoys, Attack clearly separated')
            saved=json.loads((out/'summary.json').read_text())
            assert page.locator('#chart-values tr').count()==len([r for r in saved['summary'] if r['profile']=='separated' and r['condition']=='random_decoys'])
            expect(page.locator('#violations')).to_have_text('1')
            page.locator('.chart-data summary').focus();page.keyboard.press('Enter')
            expect(page.locator('#chart-values')).to_be_visible()
            page.locator('.chart-data summary').press('Enter')
            page.locator('#study-profile').select_option('overlap')
            page.locator('#study-condition').select_option('selected_decoys')
            saved=json.loads((out/'summary.json').read_text())
            if saved.get('paired_selection_deltas'):
                assert page.locator('.estimate').count()==5
                expected=next(r for r in saved['paired_selection_deltas'] if r['profile']=='overlap' and r['budget']==2 and r['policy']=='top_risk')
                assert f"{expected['delta']*100:+.1f}" in page.locator('.estimate').first.inner_text()
                checks.append('Paired selected-versus-random estimates match the saved evaluation')
            else:
                expect(page.locator('#selection-estimates')).to_contain_text('does not contain')
                checks.append('Older saved studies show an explicit unavailable-estimate fallback')
            checks.append('Saved filters and keyboard-accessible chart table preserve all five policies')
            # The import action must be reachable and operable with the keyboard.
            page.locator('#download').focus();page.keyboard.press('Tab')
            expect(page.locator('#import-button')).to_be_focused()
            with page.expect_file_chooser():page.keyboard.press('Enter')
            checks.append('Import is keyboard reachable and opens the native file chooser')
            # Finish on a clean generated replay, with a visible ordinary-versus-random-versus-selected comparison.
            page.locator('#policy').select_option('top_risk');page.locator('#budget').fill('2')
            page.locator('#run').click()
            expect(page.locator('#replay-source')).to_have_text('DISPLAYED REPLAY / GENERATED')
            assert not page.locator('#error').is_visible()
            page.locator('.advanced summary').click()
            page.locator('#walkthrough').click();page.locator('#matched').wait_for(state='visible');expect(page.locator('#walkthrough')).to_be_enabled()
            page.evaluate('window.scrollTo(0,0)')
            page.screenshot(path=str(out/'desktop.png'),full_page=True)
            for width in [390,320]:
                page.set_viewport_size({'width':width,'height':844})
                assert page.evaluate('document.documentElement.scrollWidth <= window.innerWidth')
                chart=page.locator('#chart svg').bounding_box()
                assert chart and chart['x']>=0 and chart['x']+chart['width']<=width
                assert page.locator('#chart').evaluate('(el)=>el.scrollWidth<=el.clientWidth')
                # The chart fits its container; only the explicitly scrollable numeric tables overflow.
                page.locator('#walkthrough').focus();page.keyboard.press('Enter')
                page.locator('#matched').wait_for(state='visible');expect(page.locator('#walkthrough')).to_be_enabled()
                assert page.locator('#matched article').count()==3
                if width==390:
                    page.evaluate('window.scrollTo(0,0)')
                    page.screenshot(path=str(out/'mobile.png'),full_page=True)
            checks.append('390px and 320px layouts, full-width chart, and keyboard comparison work without clipping')
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    import hashlib
    result={'status':'passed','checks':checks,'page_errors':errors,
            'study_sha256':hashlib.sha256((out/'summary.json').read_bytes()).hexdigest(),
            'source_sha256':source_hash()}
    (out/'browser-checks.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__':main()
