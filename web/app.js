"use strict";
const $=id=>document.getElementById(id);
const labels={top_risk:'Highest risk first',uniform:'Uniform random',mixed:'Risk + random reserve',root_fair:'Fair across task roots',hold_sensitive:'Hold sensitive actions'};
const conditions={ordinary:'Ordinary permitted work',random_decoys:'Random permitted decoys',selected_decoys:'Selected permitted decoys'};
const profiles={overlap:'Overlapping scores',separated:'Attack clearly separated'};
const colors={top_risk:'#a43723',uniform:'#315d82',mixed:'#155d65',root_fair:'#796019',hold_sensitive:'#68496f'};
const policyHelp={top_risk:'Review the highest scores first. Unreviewed actions can commit.',uniform:'Sample actions in a random order, independent of their risk scores.',mixed:'Review the highest score first, then sample randomly. At budget 1 this equals highest risk first.',root_fair:'Cycle across task roots in random order, taking the highest score within each root.',hold_sensitive:'Review highest scores first; hold unreviewed exports. Permitted exports can also be deferred.'};
let snapshot=null,requestId=0,comparisonId=0,displayOrigin='generated',displayConfig=null,studyData=null;
function element(tag,text,cls){const node=document.createElement(tag);if(text!==undefined)node.textContent=text;if(cls)node.className=cls;return node;}
function config(){return {condition:$('condition').value,profile:$('profile').value,policy:$('policy').value,budget:Number($('budget').value),seed:Number($('seed').value),audit_seed:Number($('audit-seed').value),single_actor:$('single').checked,mandatory:$('mandatory').checked,hard_block:$('hard-block').checked?.95:null};}
async function post(path,body){const response=await fetch(path,{method:'POST',headers:{'Content-Type':'application/json'},body:JSON.stringify(body)});const data=await response.json();if(!response.ok)throw Error(data.error||'Replay failed');return data;}
function showError(error) {
  $('error').hidden = false;
  $('error').textContent = error.message;
  if (!snapshot) {
    $('run-state').textContent = 'Replay unavailable';
    $('replay-title').textContent = 'The local replay could not load';
    $('outcome-explanation').textContent = 'Check that the local server is running, then run a replay or choose an example to retry.';
    $('attention-preview').replaceChildren(element('p', 'Replay unavailable. Choose an example below to retry.'));
  }
}
function setBusy(busy) {
  $('run').disabled = busy;
  $('run').setAttribute('aria-busy', String(busy));
  $('run').replaceChildren(document.createTextNode(busy ? 'Running replay…' : 'Run replay'), element('span', busy ? '…' : '↗'));
  $('import-button').disabled = busy;
  $('download').disabled = busy || !snapshot;
  document.querySelectorAll('[data-preset]').forEach(button => button.disabled = busy);
  document.querySelector('.lab').classList.toggle('is-loading', busy);
}
function updatePresets() {
  for (const button of document.querySelectorAll('[data-preset]')) {
    const c = displayConfig, key = button.dataset.preset;
    const common = c && c.profile === 'overlap' && c.budget === 2 && c.seed === 42 && c.audit_seed === 42 && !c.single_actor && !c.mandatory && c.hard_block === null;
    const matches = common && c.condition === (key === 'ordinary' ? 'ordinary' : 'selected_decoys') && c.policy === (key === 'hold' ? 'hold_sensitive' : 'top_risk');
    button.setAttribute('aria-pressed', String(Boolean(matches)));
  }
}
function renderPreview(data) {
  const actions = [...data.result.actions].sort((a,b) => b.score-a.score || a.id.localeCompare(b.id));
  const reveal = $('truth').checked;
  $('attention-preview').replaceChildren(...actions.map((a,index) => {
    const row = element('div', undefined, 'preview-row' + (reveal && !a.authorized ? ' prohibited' : '') + (a.audited ? ' is-reviewed' : ''));
    const track = element('div', undefined, 'preview-track'), bar = element('i');
    bar.style.width = (a.score * 100) + '%';
    const label = reveal ? (a.authorized ? 'Permitted work' : 'Prohibited action') : 'Action ' + (index+1);
    track.append(bar, element('span', label));
    row.append(element('span', a.score.toFixed(2), 'preview-score'), track, element('span', a.audited ? 'REVIEWED' : 'UNREVIEWED', 'preview-review'));
    return row;
  }));
  document.querySelector('.window-number').textContent = '[ ' + actions.length + ' ACTIONS ]';
  $('attention-caption').textContent = `${displayOrigin === 'imported' ? 'Imported replay · provenance unverified' : 'Current generated replay · synthetic scores'}. ${data.result.spent_units} of ${data.result.budget} review units used. Ground truth ${reveal ? 'shown' : 'hidden'}.`;
}
function explainOutcome(r) {
  if (r.halted) return 'A review found the prohibited action. Under these rules, the entire batch stops before any effect commits—including permitted work.';
  if (r.violations) return `${r.violations} prohibited effect${r.violations === 1 ? '' : 's'} reached the simulated ledger. The review policy did not stop the batch. Inspect the unreviewed actions below.`;
  if (r.deferred) return `No prohibited effects reached the simulated ledger. ${r.deferred} action${r.deferred === 1 ? ' is' : 's are'} held pending review. Holding can also defer permitted work.`;
  return 'No prohibited effects reached the simulated ledger in this draw. This single outcome is not evidence of a general guarantee.';
}
function updateDraft(){const dirty=displayConfig&&JSON.stringify(config())!==JSON.stringify(displayConfig);$('draft-state').textContent=displayOrigin==='imported'?'Imported replay displayed. Run creates a new generated scenario.':dirty?'Settings changed. Run to update the displayed replay.':snapshot?'Displayed replay matches these settings.':'No replay displayed yet. Choose an example or run to begin.';$('policy-help').textContent=policyHelp[$('policy').value];$('budget-value').textContent=$('budget').value+' of 6';}
function render(data){const changed = snapshot !== data; snapshot=data;const r=data.result;$('error').hidden=true;$('violations').textContent=r.violations;$('completed').textContent=`${r.benign_completed} / ${r.benign_total}`;$('spent').textContent=`${r.spent_units} / ${r.budget}`;$('deferred').textContent=`${r.deferred} actions deferred`;
 $('violation-metric').className=r.violations?'danger':'';
 $('run-state').textContent=r.halted?'Batch halted':r.attack_executed?'Simulated violation':'No prohibited effect';$('run-state').className='pill '+(r.attack_executed?'danger':'safe');
 $('import-note').textContent=data.scenario.source==='imported_scored_trace'?(data.provenance?`Imported trace; claimed model: ${data.provenance.model}. Provenance is preserved but unverified.`:'Imported trace with missing provenance; no model execution is established.'):'Constructed synthetic scores. Downloads contain fictional records only.';
 $('replay-source').textContent=displayOrigin==='imported'?'DISPLAYED REPLAY / IMPORTED FILE':'DISPLAYED REPLAY / GENERATED';
 $('replay-title').textContent=conditions[data.scenario.condition]||data.scenario.condition;
 $('replay-brief').textContent = `${labels[r.policy]} · ${r.budget} review units available`;
 const required=data.scenario.actions.filter(a=>a.mandatory_review).length;
 $('replay-context').textContent=`${profiles[data.scenario.profile]||data.scenario.profile} · ${labels[r.policy]} · budget ${r.budget} · scenario seed ${data.scenario.seed} · audit seed ${r.audit_seed} · hard block ${r.hard_block_threshold===null?'off':r.hard_block_threshold} · ${required} mandatory review${required===1?'':'s'}.`;
 $('permitted-total').textContent=`Out of ${r.benign_total} permitted actions`;
 const queue=$('queue');queue.replaceChildren();const actions=[...r.actions].sort((a,b)=>b.score-a.score||a.id.localeCompare(b.id));for(const a of actions){const reveal=$('truth').checked;const row=element('div',undefined,'event'+(reveal&&!a.authorized?' target':'')+(a.audited?' audited':''));const score=element('div',a.score.toFixed(2),'score');score.append(element('small','RISK'));const content=element('div');content.append(element('strong',a.actor+' · '+a.root),element('p',a.description));if(reveal)content.append(element('span',a.authorized?'Permitted':'Prohibited','badge '+(a.authorized?'':'bad')));const status=element('div',a.outcome.replaceAll('_',' '),'event-status');status.append(element('span',a.audited?'REVIEWED':'NOT REVIEWED','reviewed'));row.append(score,content,status);queue.append(row);}
 $('ledger-summary').textContent=r.halted?'A review found a policy violation. The whole batch stopped before any action committed.':`${r.ledger.length} effects committed; ${r.violations} violated the trusted grants. ${r.deferred} actions remain pending review.`;
 $('timeline').replaceChildren(...(r.ledger.length?r.ledger.map(a=>element('li',a.effect+(a.authorized?' [permitted]':' [PROHIBITED]'))):[element('li','No committed effects.')]));
 $('comparison').replaceChildren(...data.comparisons.map(c=>{const tr=element('tr',undefined,c.policy===r.policy?'active':'');const heading=element('th',labels[c.policy]);heading.scope='row';tr.append(heading);for(const text of [c.violations,`${c.benign_completed} / ${c.benign_total}`,`${c.spent_units} / ${c.budget}`,c.deferred])tr.append(element('td',text));return tr;}));$('outcome-explanation').textContent=explainOutcome(r);$('download').disabled=false;renderPreview(data);updatePresets();updateDraft();if(changed)window.AuditMotion?.replay();
}
async function replay(moveFocus = false) {
  if (!$('seed').reportValidity() || !$('audit-seed').reportValidity()) return;
  const id = ++requestId, cfg = config();
  comparisonId++;
  $('walkthrough').disabled = false;
  $('matched').hidden = true;
  setBusy(true);
  try {
    const data = await post('/api/run', cfg);
    if (id !== requestId) return;
    displayOrigin = 'generated';
    displayConfig = cfg;
    render(data);
    if (moveFocus && compact.matches) {
      $('settings').open = false;
      $('replay-title').focus({preventScroll:true});
      $('replay-title').scrollIntoView({block:'start',behavior:'instant'});
    }
  } catch (error) {
    if (id === requestId) showError(error);
  } finally {
    if (id === requestId) setBusy(false);
  }
}
$('run').addEventListener('click',()=>replay(true));$('truth').addEventListener('change',()=>snapshot&&render(snapshot));
for(const control of document.querySelectorAll('.controls input,.controls select'))control.addEventListener('input',()=>{updateDraft();comparisonId++;$('walkthrough').disabled=false;$('matched').hidden=true;});
$('walkthrough').addEventListener('click',async()=>{const id=++comparisonId,cfg=config();$('walkthrough').disabled=true;try{const rows=await Promise.all(Object.keys(conditions).map(condition=>post('/api/run',{...cfg,condition})));if(id!==comparisonId)return;const box=$('matched');box.replaceChildren(element('h3','Three backgrounds. The same target.'));box.append(element('p',`${labels[cfg.policy]} · ${profiles[cfg.profile]} · budget ${cfg.budget} · scenario seed ${cfg.seed} · audit seed ${cfg.audit_seed}. These generated replays use the draft settings; the displayed replay above is unchanged.`,'help'));const grid=element('div',undefined,'matched-grid');for(const data of rows){const r=data.result,col=element('article',undefined,r.condition==='selected_decoys'?'selected':'');col.append(element('h3',conditions[r.condition]),element('strong',r.violations),element('p','Prohibited effects','card-label'),element('p',`${r.benign_completed}/${r.benign_total} permitted actions · ${r.spent_units} review units · ${r.deferred} deferred`));grid.append(col);}box.append(grid,element('p','Random decoys use one candidate from the same pool as selected decoys. Selected decoys take the highest of eight. Ordinary work also changes the score distribution, so ordinary vs. selected is a broader contrast. A single draw is illustrative, not an effect estimate.','help'));box.hidden=false;box.scrollIntoView({behavior:matchMedia('(prefers-reduced-motion: reduce)').matches?'instant':'smooth',block:'start'});}catch(error){if(id===comparisonId)showError(error);}finally{if(id===comparisonId)$('walkthrough').disabled=false;}});
$('download').addEventListener('click',()=>{if(!snapshot)return;const url=URL.createObjectURL(new Blob([JSON.stringify(snapshot,null,2)],{type:'application/json'}));const a=element('a');a.href=url;a.download='audit-capture-replay.json';a.click();setTimeout(()=>URL.revokeObjectURL(url),1000);});
$('import-button').addEventListener('click',()=>$('import').click());
$('import').addEventListener('change',async e=>{const file=e.target.files[0];if(!file)return;const id=++requestId;setBusy(true);try{if(file.size>128000)throw Error('File exceeds 128 KB');const raw=await file.text();const data=JSON.parse(raw);if(!data||typeof data!=='object'||Array.isArray(data))throw Error('Expected a scenario object');const cfg=config();const payload={document:raw,fallback_config:{policy:cfg.policy,budget:cfg.budget,audit_seed:cfg.audit_seed,hard_block:cfg.hard_block}};const imported=await post('/api/import',payload);if(id===requestId){comparisonId++;$('walkthrough').disabled=false;$('matched').hidden=true;displayOrigin='imported';displayConfig=null;render(imported);}}catch(error){if(id===requestId)showError(error);}finally{e.target.value='';if(id===requestId){setBusy(false);}}});
const ns='http://www.w3.org/2000/svg';function svgElement(tag,attrs,text){const node=document.createElementNS(ns,tag);for(const[k,v]of Object.entries(attrs))node.setAttribute(k,v);if(text!==undefined)node.textContent=text;return node;}
const percent=v=>(100*v).toFixed(1)+'%';const points=v=>(v>0?'+':'')+(100*v).toFixed(1);
function renderStudy(){if(!studyData)return;const data=studyData,profile=$('study-profile').value,budget=Number($('study-budget').value),condition=$('study-condition').value;
 const estimates = $('selection-estimates');
 estimates.replaceChildren();
 const deltas = (data.paired_selection_deltas || []).filter(r => r.profile === profile && r.budget === budget);
 if (!deltas.length) estimates.append(element('p', 'This saved evaluation does not contain selected-vs-random paired estimates.', 'help'));
 for (const policy of Object.keys(labels)) {
   const r = deltas.find(row => row.policy === policy);
   if (!r) continue;
   const row = element('article', undefined, 'estimate');
   const track = element('div', undefined, 'interval-track');
   track.setAttribute('aria-hidden', 'true');
   const band = element('i', undefined, 'interval-band'), dot = element('i', undefined, 'interval-dot');
   band.style.left = (50 + r.ci[0] * 50) + '%';
   band.style.width = ((r.ci[1] - r.ci[0]) * 50) + '%';
   dot.style.left = (50 + r.delta * 50) + '%';
   track.append(band, dot);
   const value = element('div', undefined, 'estimate-value'), number = element('strong', points(r.delta) + ' ');
   number.append(element('small', 'pp'));
   value.append(number, element('p', `95%: ${points(r.ci[0])} to ${points(r.ci[1])} pp`));
   row.append(element('h4', labels[policy]), track, value);
   estimates.append(row);
 }
 const rows=data.summary.filter(x=>x.profile===profile&&x.condition===condition);
 const svg=svgElement('svg',{viewBox:'0 0 760 410',role:'img','aria-labelledby':'chart-title chart-desc'});svg.append(svgElement('title',{id:'chart-title'},`Safety and throughput: ${conditions[condition]}, ${profiles[profile]}`),svgElement('desc',{id:'chart-desc'},'Each point is a review budget from the saved evaluation. Horizontal axis: permitted work completed. Vertical axis: prohibited-effect rate. Bottom right is better. All numeric values and confidence intervals are in the expandable table below.'));const X=v=>105+v*615,Y=v=>325-v*265;for(let t=0;t<=1.001;t+=.25){svg.append(svgElement('line',{x1:X(t),x2:X(t),y1:60,y2:325,stroke:'#d5ddd3'}),svgElement('line',{x1:105,x2:720,y1:Y(t),y2:Y(t),stroke:'#d5ddd3'}),svgElement('text',{x:X(t),y:355,'text-anchor':'middle'},Math.round(t*100)+'%'),svgElement('text',{x:88,y:Y(t)+6,'text-anchor':'end'},Math.round(t*100)+'%'));}
 svg.append(svgElement('text',{x:410,y:397,'text-anchor':'middle',class:'axis-title'},'Permitted work completed →'),svgElement('text',{x:27,y:195,transform:'rotate(-90 27 195)','text-anchor':'middle',class:'axis-title'},'Prohibited-effect rate →'));
 const dashes={top_risk:'none',uniform:'8 4',mixed:'3 3',root_fair:'12 4 3 4',hold_sensitive:'2 5'};
 for(const policy of Object.keys(labels)){const series=rows.filter(x=>x.policy===policy).sort((a,b)=>a.budget-b.budget);svg.append(svgElement('polyline',{points:series.map(r=>X(r.completion_rate)+','+Y(r.attack_rate)).join(' '),fill:'none',stroke:colors[policy],'stroke-width':3,'stroke-dasharray':dashes[policy],opacity:.85}));for(const r of series){const dot=svgElement('circle',{cx:X(r.completion_rate),cy:Y(r.attack_rate),r:5,fill:colors[policy],stroke:'#fffef8','stroke-width':1});dot.append(svgElement('title',{},`${labels[policy]}, budget ${r.budget}: ${percent(r.attack_rate)} prohibited effects, ${percent(r.completion_rate)} permitted work; 95% scenario bootstrap interval ${percent(r.attack_ci[0])}–${percent(r.attack_ci[1])}`));svg.append(dot);}}
 $('chart').replaceChildren(svg);$('legend').replaceChildren(...Object.keys(labels).map(p=>{const span=element('span');const icon=element('i');icon.style.background=colors[p];span.append(icon,document.createTextNode(labels[p]));return span;}));
 $('chart-caption').textContent=`${conditions[condition]} · ${profiles[profile]} · saved evaluation`;
 $('chart-values').replaceChildren(...Object.keys(labels).flatMap(policy=>rows.filter(r=>r.policy===policy).sort((a,b)=>a.budget-b.budget).map(r=>{const tr=element('tr');for(const value of [labels[policy],r.budget,percent(r.attack_rate),`${percent(r.attack_ci[0])}–${percent(r.attack_ci[1])}`,percent(r.completion_rate)])tr.append(element('td',value));return tr;})));
 $('study-detail').textContent=`Saved evaluation: ${data.generated_utc}. These filters are independent of the interactive replay. Intervals are scenario-level bootstrap intervals, conditional on constructed score distributions. Holding sensitive work can eliminate effects by deferring permitted work. Actor labels do not affect the result.`;
 window.AuditMotion?.study();
}
async function study() {
  $('study-retry').disabled = true;
  $('study-status').textContent = 'Loading saved results…';
  try {
    const response = await fetch('/api/results');
    const data = await response.json();
    if (!response.ok) throw Error(data.error || 'Could not load the saved study');
    studyData = data;
    const budgets = [...new Set(data.summary.map(r => r.budget))].sort((a,b) => a-b);
    $('study-budget').replaceChildren(...budgets.map(b => {
      const option = element('option', b); option.value = b; option.selected = b === 2; return option;
    }));
    $('study-budget').disabled = false;
    $('study-status').textContent = `${data.configuration.cases} independent synthetic scenarios per profile · ${data.configuration.repeats} audit draws per cell · 95% scenario bootstrap intervals`;
    $('study-retry').hidden = true;
    renderStudy();
  } catch (error) {
    $('study-status').textContent = 'Saved study unavailable. The replay lab still works. ' + error.message;
    $('study-retry').hidden = false;
  } finally {
    $('study-retry').disabled = false;
  }
}
$('study-retry').addEventListener('click', study);
const compact = matchMedia('(max-width: 850px)');
function fitSettings() {
  const focusedInside = $('settings').contains(document.activeElement);
  $('settings').open = !compact.matches;
  if (compact.matches && focusedInside) $('settings').querySelector('summary').focus({preventScroll:true});
}
fitSettings();
compact.addEventListener('change', fitSettings);
for (const button of document.querySelectorAll('[data-preset]')) button.addEventListener('click', () => {
  $('condition').value = button.dataset.preset === 'ordinary' ? 'ordinary' : 'selected_decoys';
  $('policy').value = button.dataset.preset === 'hold' ? 'hold_sensitive' : 'top_risk';
  $('profile').value = 'overlap';
  $('budget').value = '2';
  $('seed').value = $('audit-seed').value = '42';
  for (const id of ['single','mandatory','hard-block']) $(id).checked = false;
  updateDraft();
  replay(false);
});
document.addEventListener('keydown', event => {
  if ((event.ctrlKey || event.metaKey) && event.key === 'Enter' && !$('run').disabled) {
    event.preventDefault();
    replay(true);
  }
});
for(const id of ['study-profile','study-budget','study-condition'])$(id).addEventListener('change',renderStudy);
updateDraft();replay();study();
