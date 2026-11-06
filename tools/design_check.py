"""Focused browser verification for the November 6 interface redesign.

Uses real local API responses except explicitly intercepted failure/loading cases.
No inference or external networking. This is engineering evidence, not a model study.
"""
from datetime import datetime, timezone
import hashlib
import json
import os
from pathlib import Path
import sys
import threading
from http.server import ThreadingHTTPServer

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT))
from audit_capture.server import Handler
from audit_capture.evidence import source_hash
from playwright.sync_api import sync_playwright, expect

# Resolve transparent backgrounds through ancestors. Exclude hidden text and SVG
# (the SVG is checked separately for labels, fitting, and its numeric alternative).
# This is a bounded text-contrast check, not a claim of complete WCAG conformance.
CONTRAST = r"""() => {
  const rgb = value => (value.match(/[\d.]+/g)||[]).map(Number);
  const luminance = c => c.slice(0,3).map(v => v/255).map(v => v<=.04045?v/12.92:((v+.055)/1.055)**2.4).reduce((a,v,i)=>a+v*[.2126,.7152,.0722][i],0);
  const failures=[], checked=[];
  for(const el of document.querySelectorAll('body *')) {
    if(el.closest('svg,.sr-only,.skip-link') || !el.checkVisibility({checkVisibilityCSS:true,checkOpacity:true}) || ![...el.childNodes].some(n=>n.nodeType===3&&n.textContent.trim())) continue;
    const style=getComputedStyle(el), fg=rgb(style.color);
    let parent=el,bg;
    while(parent) { const color=rgb(getComputedStyle(parent).backgroundColor); if(color.length===3||color[3]===1){bg=color;break;} parent=parent.parentElement; }
    if(!bg)bg=[255,255,255];
    const a=luminance(fg),b=luminance(bg),ratio=(Math.max(a,b)+.05)/(Math.min(a,b)+.05);
    const large=parseFloat(style.fontSize)>=24||(parseFloat(style.fontSize)>=18.66&&Number(style.fontWeight)>=700);
    const item={text:el.textContent.trim().slice(0,65),ratio:Number(ratio.toFixed(2)),required:large?3:4.5,foreground:style.color,background:bg.slice(0,3)};
    checked.push(item); if(ratio<(large?3:4.5))failures.push(item);
  }
  return {checked:checked.length,failures};
}"""

def main():
    server = ThreadingHTTPServer(('127.0.0.1', 0), Handler)
    thread = threading.Thread(target=server.serve_forever, daemon=True)
    thread.start()
    url = f'http://127.0.0.1:{server.server_port}'
    out = ROOT / 'output/design-review'
    out.mkdir(exist_ok=True, parents=True)
    checks, errors, viewports, contrasts = [], [], [], []
    try:
        with sync_playwright() as p:
            candidates = [Path(os.environ.get('PROGRAMFILES','C:/Program Files'))/'Google/Chrome/Application/chrome.exe',Path(os.environ.get('PROGRAMFILES(X86)','C:/Program Files (x86)'))/'Microsoft/Edge/Application/msedge.exe']
            browser = p.chromium.launch(headless=True, executable_path=next((str(x) for x in candidates if x.exists()), None))
            page = browser.new_page(viewport={'width':1440,'height':1000}, reduced_motion='reduce')
            page.on('pageerror', lambda error: errors.append(str(error)))
            page.goto(url, wait_until='networkidle')
            expect(page.locator('#violations')).to_have_text('1')
            page.evaluate('document.fonts.ready')
            loaded=page.evaluate("[...document.fonts].filter(f=>f.status==='loaded').map(f=>f.family)")
            assert 'Manrope' in loaded and 'Space Grotesk' in loaded,loaded
            assert page.locator('h1').evaluate("el=>getComputedStyle(el).fontFamily").startswith('"Space Grotesk"')
            checks.append('Self-hosted Manrope and Space Grotesk fonts load successfully and the heading uses Space Grotesk')
            expect(page.locator('.preview-row.is-reviewed')).to_have_count(2)
            expect(page.locator('.preview-row.prohibited')).to_have_count(1)
            assert page.locator('.preview-row.prohibited .preview-score').inner_text() == page.locator('#queue .target .score').inner_text().split()[0]
            checks.append('Landing visualization derives review marks, target and scores from the displayed API replay')
            for name, violation, completed in [('ordinary','0','0 / 5'),('hold','0','5 / 5'),('selected','1','5 / 5')]:
                button=page.locator(f'[data-preset={name}]')
                button.click()
                expect(button).to_have_attribute('aria-pressed','true')
                expect(button).to_be_enabled()
                expect(page.locator('#violations')).to_have_text(violation)
                expect(page.locator('#completed')).to_have_text(completed)
                expect(page.locator('.presets [aria-pressed=true]')).to_have_count(1)
            checks.append('All three examples use real replay responses and accurately mark the displayed example')
            page.locator('#truth').uncheck()
            expect(page.locator('.preview-row.prohibited')).to_have_count(0)
            assert 'Prohibited action' not in page.locator('#attention-preview').inner_text()
            page.locator('#truth').check()
            checks.append('Ground-truth toggle applies consistently to the queue and landing visualization')
            page.locator('#condition').select_option('ordinary')
            page.keyboard.press('Control+Enter')
            expect(page.locator('#violations')).to_have_text('0')
            expect(page.locator('#run')).to_be_enabled()
            page.locator('#condition').select_option('selected_decoys')
            page.keyboard.press('Meta+Enter')
            expect(page.locator('#violations')).to_have_text('1')
            checks.append('Ctrl+Enter and Command+Enter run the draft settings')
            # Hold one request to inspect an actual pending interaction, then fail it.
            pending=[]
            page.route('**/api/run',lambda route:pending.append(route))
            page.locator('#run').click()
            expect(page.locator('#run')).to_be_disabled()
            expect(page.locator('#run')).to_have_text('Running replay……')
            expect(page.locator('#import-button')).to_be_disabled()
            expect(page.locator('[data-preset=hold]')).to_be_disabled()
            assert pending
            pending.pop().fulfill(status=503,content_type='application/json',body='{"error":"Simulated test-only server failure"}')
            expect(page.locator('#error')).to_have_text('Simulated test-only server failure')
            expect(page.locator('#run')).to_be_enabled()
            expect(page.locator('#violations')).to_have_text('1')
            page.unroute('**/api/run')
            page.locator('#run').click()
            expect(page.locator('#error')).to_be_hidden()
            expect(page.locator('#run')).to_be_enabled()
            checks.append('Pending replay disables conflicting actions; server failure preserves the prior result; retry recovers')
            page.locator('#seed').fill('-1')
            page.locator('#run').click()
            assert page.locator('#seed').evaluate('(el)=>!el.validity.valid')
            expect(page.locator('#violations')).to_have_text('1')
            page.locator('#seed').fill('42')
            checks.append('Invalid scenario seeds use native validation and preserve the displayed replay')
            saved=json.loads((ROOT/'results/summary.json').read_text())
            expected=[r for r in saved['paired_selection_deltas'] if r['profile']=='overlap' and r['budget']==2]
            for row in expected:
                idx=list({'top_risk':0,'uniform':1,'mixed':2,'root_fair':3,'hold_sensitive':4}).index(row['policy'])
                # CSSOM serializes percentages to limited decimal precision.
                assert abs(float(page.locator('.interval-dot').nth(idx).evaluate("el=>parseFloat(el.style.left)"))-(50+50*row['delta']))<1e-4
                assert abs(float(page.locator('.interval-band').nth(idx).evaluate("el=>parseFloat(el.style.width)"))-50*(row['ci'][1]-row['ci'][0]))<1e-4
            checks.append('Every uncertainty bar and estimate uses saved paired results on a fixed -100 to +100 pp scale')
            failure=browser.new_page(viewport={'width':390,'height':844},reduced_motion='reduce')
            failure.route('**/api/results',lambda route:route.fulfill(status=503,content_type='application/json',body='{"error":"Test-only unavailable study"}'))
            failure.goto(url,wait_until='networkidle')
            expect(failure.locator('#study-status')).to_contain_text('Saved study unavailable')
            expect(failure.locator('#violations')).to_have_text('1')
            expect(failure.locator('#study-retry')).to_be_visible()
            failure.unroute('**/api/results')
            failure.locator('#study-retry').click()
            expect(failure.locator('.estimate')).to_have_count(5)
            expect(failure.locator('#study-retry')).to_be_hidden()
            failure.close()
            checks.append('Saved-study failure is explicit, leaves replay usable, and recovers through Retry')
            # Capture default results at all sizes, plus the actual primary entry view.
            for width,name in [(1440,'desktop'),(768,'tablet'),(390,'mobile'),(320,'small-mobile')]:
                page.set_viewport_size({'width':width,'height':1000 if width>400 else 844})
                page.evaluate('window.scrollTo(0,0)')
                assert page.evaluate('document.documentElement.scrollWidth<=innerWidth')
                if width<=850: assert not page.locator('#settings').evaluate('(el)=>el.open')
                else: assert page.locator('#settings').evaluate('(el)=>el.open')
                contrast=page.evaluate(CONTRAST)
                contrasts.append({'width':width,**contrast})
                assert not contrast['failures'],contrast['failures']
                position=page.evaluate("({height:document.documentElement.scrollHeight,outcome_y:document.getElementById('violations').getBoundingClientRect().top,lab_y:document.getElementById('experiment').getBoundingClientRect().top})")
                viewports.append({'width':width,**position})
                page.screenshot(path=str(out/f'after-{name}.png'),full_page=True)
                if width==1440: page.screenshot(path=str(out/'after-desktop-hero.png'))
                page.locator('.intro-actions .primary').click()
                assert page.locator('#violations').bounding_box()['y']< (1000 if width>400 else 844)
                page.screenshot(path=str(out/f'after-{name}-replay.png'))
                # Interactive targets have at least a 24px hit area. Native checkbox
                # labels count as their hit area; inline prose links are exempt.
                small=page.evaluate("""() => [...document.querySelectorAll('button,input,select,summary,nav a,.intro-actions a')].filter(el=>el.checkVisibility({checkVisibilityCSS:true})).map(el=>{const box=(el.type==='checkbox'?el.closest('label'):el).getBoundingClientRect();return {name:el.id||el.textContent.trim().slice(0,35),w:box.width,h:box.height};}).filter(x=>x.w<24||x.h<24)""")
                assert not small,small
            checks.append('1440/768/390/320px: no page overflow, outcome reachable from primary CTA, settings adapted, interactive targets at least 24px')
            checks.append('Computed visible HTML text contrast meets tested 4.5:1 normal / 3:1 large thresholds at all four widths')
            page.locator('#settings > summary').focus()
            # Enter keyboard modality; programmatic focus after a pointer click
            # intentionally does not require :focus-visible in Chromium.
            page.keyboard.press('Tab')
            page.keyboard.press('Shift+Tab')
            expect(page.locator('#settings > summary')).to_be_focused()
            assert page.locator('#settings > summary').evaluate("el=>getComputedStyle(el).outlineStyle")=='solid'
            page.keyboard.press('Enter')
            expect(page.locator('#condition')).to_be_visible()
            page.locator('#condition').select_option('ordinary')
            page.locator('#run').click()
            expect(page.locator('#replay-title')).to_be_focused()
            assert not page.locator('#settings').evaluate('(el)=>el.open')
            assert page.locator('#replay-title').bounding_box()['y']>=0
            assert page.evaluate("getComputedStyle(document.documentElement).scrollBehavior")=='auto'
            assert page.locator('#run').evaluate("el=>getComputedStyle(el).transitionDuration")=='0s'
            checks.append('Mobile keyboard settings open/run/close returns focus to the result; focus outline and reduced-motion styles verified')
            page.locator('.sensitivity > summary').focus()
            page.keyboard.press('Enter')
            chart=page.locator('#chart svg').bounding_box()
            assert chart and chart['x']>=0 and chart['x']+chart['width']<=320
            page.locator('.chart-data > summary').focus()
            page.keyboard.press('Enter')
            expect(page.locator('#chart-values')).to_be_visible()
            checks.append('All-budget chart and complete numeric alternative remain keyboard accessible at 320px')
            # Accessible names and DOM identity checks include controls in disclosures.
            assert page.evaluate("""() => [...document.querySelectorAll('input:not([type=file]),select')].every(el=>el.labels.length||el.getAttribute('aria-label'))""")
            ids=page.locator('[id]').evaluate_all('(els)=>els.map(el=>el.id)')
            assert len(ids)==len(set(ids))
            assert page.locator('main').count()==1 and page.locator('h1').count()==1
            checks.append('Controls are labeled; unique IDs, main landmark and single page heading verified')
            # Test real motion separately from the deterministic reduced-motion captures.
            motion=browser.new_page(viewport={'width':1440,'height':1000},reduced_motion='no-preference')
            motion.on('pageerror',lambda error:errors.append(str(error)))
            outbound=[]
            motion.on('request',lambda request:outbound.append(request.url) if not request.url.startswith(url) else None)
            motion.goto(url,wait_until='networkidle')
            motion.evaluate('document.fonts.ready')
            motion.wait_for_timeout(1400)
            assert motion.evaluate('document.getAnimations().length')==0
            expect(motion.locator('#motion-toggle')).to_have_text('Motion on')
            motion.screenshot(path=str(out/'signal-desktop.png'))
            motion.locator('#animate-preview').click()
            assert motion.evaluate('document.getAnimations().length')>0
            expect(motion.locator('.review-sweep')).to_have_count(1)
            motion.wait_for_timeout(1400)
            assert motion.evaluate('document.getAnimations().length')==0
            expect(motion.locator('.review-sweep')).to_have_count(0)
            motion.locator('#animate-preview').click()
            motion.locator('#motion-toggle').click()
            expect(motion.locator('#motion-toggle')).to_have_text('Motion off')
            assert motion.evaluate('document.getAnimations().length')==0
            expect(motion.locator('.review-sweep')).to_have_count(0)
            motion.reload(wait_until='networkidle')
            expect(motion.locator('#motion-toggle')).to_have_text('Motion off')
            motion.locator('#motion-toggle').click()
            motion.locator('#animate-preview').click()
            assert motion.evaluate('document.getAnimations().length')>0
            motion.emulate_media(reduced_motion='reduce')
            expect(motion.locator('#motion-toggle')).to_have_text('Reduced motion')
            assert motion.evaluate('document.getAnimations().length')==0
            expect(motion.locator('#animate-preview')).to_be_disabled()
            assert not outbound,outbound
            motion.close()
            checks.append('Real finite replay animations start and finish, manual Motion off cancels and persists, system reduced motion cancels active effects')
            checks.append('The redesigned app makes no external requests: fonts, scripts, styles and data are local')
            assert not errors,errors
            browser.close()
    finally:
        server.shutdown();server.server_close();thread.join()
    result={'status':'passed','verified_utc':datetime.now(timezone.utc).isoformat(),'checks':checks,'page_errors':errors,'viewports':viewports,'text_contrast':contrasts,'source_sha256':source_hash(),'study_sha256':hashlib.sha256((ROOT/'results/summary.json').read_bytes()).hexdigest(),'limitations':['Not a complete WCAG audit or screen-reader test.','Desktop Chromium viewport emulation; no physical mobile device testing.','Failure responses are explicit test fixtures, not empirical model results.']}
    (ROOT/'results/design-checks.json').write_text(json.dumps(result,indent=2))
    print(json.dumps(result,indent=2))

if __name__=='__main__': main()
