# Review findings - November 5, 2026

This is the historical review of the November 5 baseline. November 6 readiness corrections are recorded separately in [EVENT_WORK.md](EVENT_WORK.md).

This is a second review by the same Codex session with an independently implemented mathematical oracle, not independent human peer review. All changes remain pre-sprint work. The original release is preserved locally in output/history/audit-capture-review-20261105-initial.zip.

## Fixed defects

- Imported model provenance was discarded, and importing replayed with current controls instead of saved settings. Provenance now survives, is bound to the scenario hash, and stays explicitly unverified. Saved policy, budget, audit seed and hard-block threshold are restored. Displayed replay settings are identified separately from the controls used to generate a new scenario.
- Metadata and grant validation was incomplete. Malformed containers and values now receive clean errors. Duplicate JSON keys are rejected, host checks complement origin checks, and the importer creates output exclusively to avoid overwriting evidence in a race.
- Passing tests did not identify tested source. Test, browser, exact-enumeration and report receipts now bind to source and study hashes; packaging rejects stale evidence. These are reproducibility checks, not signed attestations against a malicious editor rewriting receipts.
- Randomized results lacked a second implementation. audit_capture/exact.py enumerates possible choices without using core.run or core._schedule. Tests compare every shuffle of selected unit-cost, heterogeneous-cost, multiple-violation, mandatory-hold and hard-block fixtures against this separate specification.

## Exact validation and its limits

For constructed seed 42 at budget two, exact prohibited-effect probabilities are 1 (highest risk), 2/3 (uniform), 4/5 (risk plus random), 1 (root-fair), and 0 (hold exports). These are finite-protocol calculations, not empirical attack rates. results/exact-validation.json also averages exact probabilities over the saved scenarios, separating Monte Carlo error from the assumed score distribution.

The budget/action_count formula requires equal costs. If the target costs three units and the budget is two, the implemented skip-if-too-expensive random scheduler never reviews it. A mandatory hold remains respected. A regression test preserves this boundary.

## Research judgment

This is a conditional, familiar allocation mechanism, not an established novel swarm failure. Actor-name invariance shows no multi-agent-specific causal effect in this model. More synthetic trials and more tests cannot fill that gap.

If authorization can be checked cheaply for every action using a grant table, enforce it directly. Selective auditing matters for properties requiring costly interpretation. Hiding an inexpensive authorization ledger from a monitor would manufacture an artificial weakness; this artifact is not evidence against deterministic access control.

The strongest next question is whether independently verified permitted contenders, selected using a frozen surrogate monitor, reduce coverage of an unchanged violation on a held-out monitor at matched workload and total cost. A negative result remains useful. A swarm claim also needs a meaningful distributed information or capability constraint, not renamed workers.

## Scope and remaining gates

No live-model inference is represented by this release. Fixture outputs are explicitly labeled.
The November 5 baseline is preexisting work; later interface work is recorded separately.
Competition eligibility, author declarations and human manuscript review remain unverified.
The local historical archives are retained privately and are not included in this public copy.

Official pages and four cited papers were rechecked November 5. This is not an exhaustive novelty search.

- [Sprint rules](https://apartresearch.com/sprints/swarm-alignment-2026)
- [Prize terms](https://apartresearch.com/sprints/prize-terms)
- [BRA-Audit](https://arxiv.org/abs/2608.14668)
- [Attack Selection](https://arxiv.org/abs/2606.06529)
- [Blindfold](https://arxiv.org/abs/2610.37055)
- [Efficient Auditing](https://arxiv.org/abs/2610.07256)

## Astra review and v0.3.0 changes

A distinct Astra agent reviewed the source and methodology at the user's request. This is an independent AI review pass, not human peer review. It found that the original selected-versus-ordinary contrast mixed candidate distribution changes with selection. The evaluator now also reports paired selected-versus-random deltas as the primary selection comparison. At overlapping scores and budget two, highest-risk rates are 15.625% ordinary, 37.5% random, and 87.5% selected: selection contributes 50 percentage points versus random; the 71.875-point secondary contrast also includes distribution change. All values remain constructed, with no live monitor inference.

Astra reproduced duplicate-key acceptance in the CLI importer; the root agent fixed all entry points to share a strict JSON parser. Verification now fingerprints and packages the local capture runner, and the combined test suite includes its explicitly fake-server transport tests. The separate UI pass improves replay-state clarity, three-condition comparison and mobile/keyboard access.
