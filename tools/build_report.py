"""Build a review PDF using the verified official template's section structure.

This file generates a synthetic-study draft, not an organizer submission.
"""
from pathlib import Path
import sys
ROOT=Path(__file__).resolve().parents[1]
sys.path.insert(0,str(ROOT))
from audit_capture.evidence import source_hash
if (ROOT/'.vendor').is_dir():sys.path.insert(0,str(ROOT/'.vendor'))
if (ROOT/'.vendor_pdf').is_dir():sys.path.insert(0,str(ROOT/'.vendor_pdf'))
import json
import xml.etree.ElementTree as ET
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from reportlab.lib import colors
from reportlab.lib.styles import getSampleStyleSheet,ParagraphStyle
from reportlab.lib.enums import TA_CENTER
from reportlab.platypus import SimpleDocTemplate,Paragraph,Spacer,Table,TableStyle,PageBreak,Image
from reportlab.lib.pagesizes import A4

data=json.loads((ROOT/'results/summary.json').read_text())
exact=json.loads((ROOT/'results/exact-validation.json').read_text())
out=ROOT/'output/pdf';out.mkdir(parents=True,exist_ok=True)
rows=data['summary'];delta=data['paired_selection_deltas'];combined_delta=data['paired_deltas']
labels={'top_risk':'Highest risk','uniform':'Uniform random','mixed':'Risk + random','root_fair':'Root-fair','hold_sensitive':'Hold sensitive'}
palette=['#bd523f','#436d99','#206f58','#a27d27','#8b689e']
def row(policy,condition='selected_decoys',profile='overlap',budget=2):
    return next(r for r in rows if (r['policy'],r['condition'],r['profile'],r['budget'])==(policy,condition,profile,budget))
def pct(value):return f'{100*value:.1f}%'

fig,ax=plt.subplots(figsize=(7.1,3.25),facecolor='#fffefa')
ax.set_facecolor('#fffefa')
for (policy,label),color in zip(labels.items(),palette):
    group=sorted([r for r in rows if r['policy']==policy and r['profile']=='overlap' and r['condition']=='selected_decoys'],key=lambda r:r['budget'])
    ax.plot([r['completion_rate']*100 for r in group],[r['attack_rate']*100 for r in group],marker='o',markersize=4,linewidth=1.5,label=label,color=color)
ax.set(xlim=(-3,103),ylim=(-3,103),xlabel='Permitted actions completed (%)',ylabel='Prohibited-effect rate (%)')
ax.spines[['top','right']].set_visible(False);ax.grid(alpha=.18)
ax.legend(fontsize=7,loc='upper left',frameon=False,ncol=2)
fig.tight_layout();fig.savefig(ROOT/'results/frontier.png',dpi=190);fig.savefig(ROOT/'results/frontier.svg');plt.close(fig)

styles=getSampleStyleSheet()
styles.add(ParagraphStyle(name='BodyResearch',fontName='Helvetica',fontSize=9.6,leading=13.2,spaceAfter=8,textColor=colors.HexColor('#243b42')))
styles.add(ParagraphStyle(name='TitleResearch',fontName='Helvetica-Bold',fontSize=25,leading=29,spaceAfter=12,textColor=colors.HexColor('#206f58')))
styles.add(ParagraphStyle(name='SmallResearch',fontName='Helvetica',fontSize=8,leading=10.5,spaceAfter=7,textColor=colors.HexColor('#53676c')))
styles.add(ParagraphStyle(name='HResearch',fontName='Helvetica-Bold',fontSize=12,leading=16,spaceBefore=13,spaceAfter=7,textColor=colors.HexColor('#173a37')))
story=[]
def p(text,style='BodyResearch'):story.append(Paragraph(text,styles[style]))
def h(text):p(text,'HResearch')
def table(records,widths):
    wrapped=[[Paragraph(str(cell),styles['SmallResearch']) for cell in record] for record in records]
    t=Table(wrapped,colWidths=widths,repeatRows=1,hAlign='LEFT')
    t.setStyle(TableStyle([('BACKGROUND',(0,0),(-1,0),colors.HexColor('#e5eee6')),('VALIGN',(0,0),(-1,-1),'TOP'),('BOTTOMPADDING',(0,0),(-1,-1),8),('TOPPADDING',(0,0),(-1,-1),7),('LINEBELOW',(0,0),(-1,-1),.35,colors.HexColor('#cedbd3'))]))
    story.append(t)

ordinary=row('top_risk','ordinary');random_background=row('top_risk','random_decoys');selected=row('top_risk');d=next(r for r in delta if r['profile']=='overlap' and r['budget']==2 and r['policy']=='top_risk')
p('Audit Capture','TitleResearch')
p('A controlled synthetic replay study of selective-audit allocation','HResearch')
p('REVIEW DRAFT | Author identity and affiliation pending confirmation<br/>Study prepared November 5, 2026; readiness revision November 6. No judged-period contribution or Apart affiliation is asserted.','SmallResearch')
h('Abstract')
abstract=f'''Selective oversight allocates limited review capacity among many agent actions. We construct a replay testbed to examine whether permitted background actions can displace a fixed prohibited action from review. Six immutable proposals are evaluated against a separate grant ledger under three matched traffic conditions, two constructed score profiles, five allocation policies and six budgets. The study contains 160 synthetic scenarios per profile, with eight audit draws averaged within each scenario. Scores are experimental assumptions rather than language-model measurements. Under overlapping scores and a two-unit budget, highest-risk review permits the prohibited effect in {pct(random_background['attack_rate'])} of random-decoy scenarios and {pct(selected['attack_rate'])} with selected permitted decoys. This paired selection effect is {100*d['delta']:.1f} percentage points. The ordinary-background comparison additionally changes the candidate distribution and is secondary. Uniform review is insensitive to score changes under shared random draws; root-fair allocation can worsen safety by selecting a permitted contender within the target's task root. Holding sensitive actions prevents prohibited effects while sometimes deferring permitted work. Separated scores remove the displacement effect for highest-risk review. Renaming all actors to one worker leaves outcomes unchanged, establishing no multi-agent-specific advantage. These results validate a bounded simulation mechanism and a reusable testbed; they do not establish deployed-model vulnerability, spontaneous collusion, or novel defenses.'''
assert 150<=len(abstract.split())<=250,len(abstract.split())
p(abstract)
h('1. Introduction')
p('A selective-audit system may miss a violation because it allocates review elsewhere. We study this mechanism while holding the target action, number of proposals and review capacity fixed. Our artifact supplies matched replay conditions, a separate authorization ledger, and executable negative controls. It makes no first-discovery claim for alert flooding, audit scheduling, or multi-agent misuse.')
h('2. Related Work')
p('BRA-Audit allocates a fixed audit-call budget over multi-agent execution graphs [1]. Attack Selection studies strategic decisions about when to attempt or abandon an attack [2]. Blindfold studies confidentiality of random audit decisions [3]. Efficient Auditing uses a two-stage gate and trace auditor [4]. Our artifact is a small independent mechanism testbed; it does not reproduce these implementations or establish an advance over them.')
story.append(PageBreak())
h('3. Methods')
p('Each scenario contains six proposals and five permitted actions. Authorization is computed from (trusted task root, operation, record, destination) grants. The target exports a restricted dummy record to an unapproved mock destination. Two permitted export slots share its task root; three other workers summarize fictional records. Actions cannot execute real tools or access a network.')
p('Ordinary, random-decoy and selected-decoy conditions preserve the exact target and the three unaffected proposals. The two export slots retain their authorization and cost. Each has eight permitted synthetic score candidates. The frozen selection rule uses the first candidate for random decoys and the maximum for selected decoys. This deliberately constructed overlap is the intervention; task text does not generate scores.')
p('In the overlap profile the target score is sampled uniformly from 0.44-0.88, ordinary backgrounds from 0.12-0.68, and candidate decoys from 0.28-0.97. In the separated profile target scores are 0.84-0.98 and candidates 0.28-0.79. These are sensitivity assumptions selected to study a mechanism, not an estimated population or a preregistered analysis.')
table([['Policy','Rule'],['Highest risk','Review descending score, with deterministic ID tie breaks.'],['Uniform random','Sample proposals without replacement; canonical ID order couples draws across matched conditions.'],['Risk + random','Review the highest score first, then randomize the rest. At budget one this equals highest risk.'],['Root-fair','Randomize trusted task roots; take each root\'s highest remaining score in round-robin order.'],['Hold sensitive','Use highest-risk selection; defer every unaudited export. Mandatory review always holds regardless of policy.']],[105,392])
p('Audits are perfect and precede every commit in a batch. Any audited violation halts the entire batch; nothing commits. Without a halt, selected permitted actions and eligible unaudited actions commit to an in-memory ledger. Mandatory or sensitive holds remain deferred. This models selective-audit protocols and explicitly excludes bypassing mandatory human approvals.')
p('Selected versus random decoys is the primary selection comparison because both use the same candidate distribution. Selected versus ordinary background also changes that distribution and is a secondary combined intervention. The intervention is chosen using the same scores later used for allocation, so monitor-transfer validity is untested.')
p('Test seeds are 10000-10159; development seeds are distinct (0-99). Eight audit draws are averaged per scenario. The sweep has 28,800 cells and 230,400 replay executions. The 95% intervals use 400 percentile bootstrap resamples over the 160 scenario means. They condition on the specified score distributions and are not deployment-risk certificates. All sweep review costs are one unit; engine tests cover variable costs.')
story.append(PageBreak())
h('4. Results')
table([['Policy / background','Prohibited effects','Permitted completion','Paired increase vs random']]+[
    [labels[policy]+' / selected',pct(row(policy)['attack_rate']),pct(row(policy)['completion_rate']),f"{100*next(x for x in delta if x['profile']=='overlap' and x['budget']==2 and x['policy']==policy)['delta']:.1f} pp"] for policy in labels
],[170,100,110,117])
p('Table 1. Constructed overlap profile at two reviews per six proposals. Rates average scenario means. Paired changes compare selected permitted decoys with random decoys from the same candidate distribution. A zero prohibited-effect rate under holds does not imply that all permitted work completed.','SmallResearch')
story.append(Image(str(ROOT/'results/frontier.png'),width=497,height=227))
p('Figure 1. Constructed selected-decoy sensitivity across budgets 0, 1, 2, 3, 4 and 6. Every point is computed from saved replay results. Fewer prohibited effects and more completed permitted actions are preferable. Lines connect budget settings and are not interpolated deployment predictions.','SmallResearch')
p(f"For highest-risk review, the paired selection increase versus random decoys is {100*d['delta']:.1f} pp, with scenario-bootstrap interval [{100*d['ci'][0]:.1f}, {100*d['ci'][1]:.1f}] pp. In the separated profile, highest-risk review has zero prohibited effects at budget two. These conditional results follow the designed score ordering; their magnitude is not evidence of real monitor susceptibility.")
p('Uniform review has an analytic target-inclusion probability k/6 for k unit-cost reviews. Its matched target-inclusion outcomes are invariant to score changes. Root-fair allocation can miss the target inside a task root even when that root receives a review. Actor-name replacement produces identical outcomes for all policies: this experiment establishes no swarm-specific causal gain.')
story.append(PageBreak())
h('5. Discussion and Limitations')
p(f"The original selected-versus-ordinary comparison is secondary: rates are {pct(ordinary['attack_rate'])} ordinary, {pct(random_background['attack_rate'])} random and {pct(selected['attack_rate'])} selected. The larger selected-versus-ordinary change combines a candidate-distribution intervention with selection. Astra identified this confound during an independent AI review; all three conditions are retained.")
p('The allocation layer is independently testable: a target can retain the same score while its selection changes. The artifact makes this distinction observable and provides controls that defeat broad claims. The study shows conditional properties of a simulator, not that real agents select effective decoys or evade real monitors.')
p('All scores, actions and authorization grants are constructed. The two profiles are not LLMs. The scenario descriptions are not representative naturalistic traces. The ideal auditor has no false positives or false negatives. Batch-wide stopping is an optimistic containment assumption and reduces completed pending work whenever any violation is caught. For policies that release all unaudited actions, completion and attack escape are therefore mechanically coupled; Figure 1 is not a realistic estimate of long-term productivity.')
p('No true monetary, token or elapsed-time costs are measured. Equal-cost audits are a simplification. The constructed distributions intentionally exercise overlap; larger Monte Carlo samples do not improve their external validity. Bootstrapped intervals quantify simulation uncertainty, not novelty or deployment safety. Imported provenance is user supplied and cannot authenticate model execution on its own.')
p('The grant ledger is an evaluator oracle. If the same authorization relation can be checked cheaply for every real action, it should be enforced directly. Selective auditing is relevant to properties requiring costly interpretation; concealing inexpensive authorization information would manufacture an artificial weakness.')
p('Useful follow-up requires representative captured model judgments, raw response hashes, unseen task families, review-token accounting and live-agent replication. The importer binds judgments to scenario hashes and rejects missing, duplicate, non-finite or out-of-range scores. No paid inference is enabled in this release.')
h('6. Conclusion')
p('The working artifact demonstrates a conditional audit-displacement mechanism, preserves negative controls, and quantifies several policy tradeoffs. It supports a careful synthetic mechanism study and further data collection. It does not support claims of autonomous collusion, guaranteed protection, or competition-winning novelty.')
h('Code and Data')
p('The review bundle includes source, tests, a loopback demo, runs.csv, summary.json, figures and a hash manifest. Run python -m audit_capture.evaluate to regenerate the study; run python -m pytest for engine and API checks. Browser checks exercise desktop/mobile controls and JSON round trips. Source distribution does not constitute an organizer submission or a hosted deployment.')
h('Development Timing and Entry Status')
p('The study and initial implementation were prepared November 5. November 6 readiness maintenance is recorded separately in docs/EVENT_WORK.md and is conservatively treated as preparation, not claimed judged-period research. The official rules judge only weekend work [5]; the page does not define an exact judging-start timestamp. This draft follows the verified template\'s section structure [6]. Full author identity, affiliation, manuscript review and any required consent remain unresolved. Competition eligibility and required author declarations have not been verified. This draft is not a submission or evidence of completed participation.')
story.append(PageBreak())
h('References')
references=[
('1','Wang, K., Lin, Y., Lou, J., and Li, J. (2026). BRA-Audit: Budgeted Runtime Auditing for LLM Multi-Agent Systems via Cumulative-Exposure Audit-Point Placement. arXiv.','https://arxiv.org/abs/2608.14668'),
('2','Ge-Wang, C., et al. (2026). Attack Selection in Agentic AI Control Evaluations Meaningfully Decreases Safety. arXiv.','https://arxiv.org/abs/2606.06529'),
('3','Zhu, W., Zuo, M., and Sun, H. (2026). Blindfold: Keeping the Audit Coin Secret from LLM Agents. arXiv.','https://arxiv.org/abs/2610.37055'),
('4','Zhang, E., Yang, C.-Y. K., and Xu, D. (2026). Efficient Auditing of Adversarial AI Agent Behavior from Agent Traces. arXiv.','https://arxiv.org/abs/2610.07256'),
('5','Apart Research. Swarm Alignment Hackathon guidelines. Rechecked November 6, 2026.','https://apartresearch.com/sprints/swarm-alignment-2026'),
('6','Apart Research. Official hackathon submission template. Read-only connected Drive access, November 5, 2026.','https://docs.google.com/document/d/1_1_27EyZriMlc8n8EBE2YScaeyMjm-8xjR097nmHXAE/edit')]
for n,title,url in references:p(f'[{n}] {title}<br/><link href="{url}" color="#206f58">{url}</link>','SmallResearch')
h('Appendix A. Limitations and Dual-Use / Ethical Considerations')
p('No real data, credentials, destinations or services are present. Effects are inert strings in an in-memory ledger. The simulation cannot execute its described export actions. Operational misuse of audit allocation is a possible dual use, so releases emphasize defensive tests, authorization holds and scope limits. Results should not be advertised as permission to bypass review or as a real-world attack success rate. The server binds loopback, limits request sizes, rejects cross-origin writes and serves an allowlist of static files.')
h('Appendix B. AI Usage and Review')
p('Codex and Astra assisted with research ideation, source lookup, code, tests, analysis, UI and manuscript drafting. Program results were generated by the included evaluator, not invented as model outputs. Automated tests and browser checks are supporting engineering evidence; human independent manuscript review remains pending. No author endorsement, Apart affiliation or completed sprint participation is implied.')
h('Appendix C. Reproducibility Record')
p(f"Evaluation generated at {data['generated_utc']}. Example scenario SHA-256: {data['example_fingerprint']}. PREEXISTING_MANIFEST.json freezes the November 5 baseline; RELEASE_MANIFEST.json hashes the current package and records changes against it. The scientific CSV and summary remain unchanged. Exact bootstrap seeds, distributions and private audit draw seeds are in source; test fixtures are explicitly labelled synthetic.",'SmallResearch')
story.append(PageBreak())
h('Appendix D. Independent Oracle and Review Fixes')
p('A second implementation enumerates possible audit choices without calling the production scheduler or replay engine. It uses rational probabilities, including all task-root orderings, and separately specifies halts and deferred work. Regression tests compare every shuffle for selected unit-cost, unequal-cost, multiple-violation, mandatory-hold and hard-block fixtures. This is independent implementation validation within the same Codex session, not independent human review.')
table([['Selected-decoy overlap / budget two','Exact mean','Eight-draw study']]+[
    [labels[r['policy']],pct(r['exact_rate']),pct(r['saved_monte_carlo_rate'])]
    for r in exact['summary'] if r['profile']=='overlap'],[257,120,120])
p(f"Table D1. Exact allocation probabilities averaged over the same {data['configuration']['cases']} constructed scenarios. Differences from the saved study reflect audit-draw sampling, not new model evidence. The oracle checks {exact['exact_cells']} scenario-policy cells across two profiles; all deterministic-policy cross-checks pass.",'SmallResearch')
p('For the seed-42 fixture, exact prohibited-effect probabilities at budget two are 1 (highest risk), 2/3 (uniform), 4/5 (risk plus random), 1 (root-fair) and 0 (hold sensitive). The uniform k/n inclusion guarantee requires equal costs. With a three-unit target and a two-unit budget, the implemented skip-if-too-expensive random policy never reviews the target. Mandatory review still holds it. These statements describe the specified finite protocol only.')
p('The November 5 review fixed replay/provenance loss, incomplete metadata validation, duplicate JSON keys and stale verification evidence. November 6 readiness fixes preserve exact HTTP request bytes, hash failed capture artifacts, reject truncated bodies, correct stale eligibility wording and freeze the baseline manifest. Regression evidence uses fake servers only. Verification receipts bind engineering checks to source and study hashes; these detect drift, not malicious forgery. docs/EVENT_WORK.md separates dates and lists the remaining judged-entry work.')
p('Live validation remains unperformed: no local model runtime or usable permitted inference endpoint was available. The prospective protocol in docs/NEXT_EXPERIMENT.md requires realistic fictional tasks, surrogate-to-held-out transfer, permission validation, measured review cost, controls for label leakage and a direct-authorization baseline. The toy target labels must not be mistaken for blinded monitor inputs. The protocol is neither executed nor preregistered.')

def footer(canvas,doc):
    canvas.saveState();canvas.setStrokeColor(colors.HexColor('#cad8d0'));canvas.line(48,38,547,38)
    canvas.setFont('Helvetica',7);canvas.setFillColor(colors.HexColor('#53676c'))
    canvas.drawString(48,26,'AUDIT CAPTURE | SYNTHETIC STUDY | PRE-SPRINT REVIEW DRAFT')
    canvas.drawRightString(547,26,str(doc.page));canvas.restoreState()

doc=SimpleDocTemplate(str(out/'audit-capture-research-draft.pdf'),pagesize=A4,rightMargin=48,leftMargin=48,topMargin=38,bottomMargin=53,title='Audit Capture - Synthetic Replay Study',author='Author identity pending review')
doc.build(story,onFirstPage=footer,onLaterPages=footer)
import hashlib
report_receipt={'source_sha256':source_hash(),
                'study_sha256':hashlib.sha256((ROOT/'results/summary.json').read_bytes()).hexdigest(),
                'exact_sha256':hashlib.sha256((ROOT/'results/exact-validation.json').read_bytes()).hexdigest(),
                'pdf_sha256':hashlib.sha256((out/'audit-capture-research-draft.pdf').read_bytes()).hexdigest()}
(ROOT/'results/report-checks.json').write_text(json.dumps(report_receipt,indent=2))
print(out/'audit-capture-research-draft.pdf')
