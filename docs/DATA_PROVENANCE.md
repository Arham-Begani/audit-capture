# Evidence and data provenance

The saved study contains constructed actions and risk scores. It is not an LLM
evaluation, real incident dataset or human-participant study. No live-model runs exist.

| Artifact | Origin and interpretation |
| --- | --- |
| `results/runs.csv`, `results/summary.json` | November 5 synthetic study; conditional simulator behavior |
| `results/exact-validation.json` | Separate finite-state oracle; allocation correctness, not new observations |
| Test/browser/design receipts | Engineering checks of this public copy, bound to its source hash |
| Local capture fixtures | Deliberately fake HTTP responses; transport and evidence handling only |

Unchanged scientific inputs:

- CSV SHA-256: `24cfc888374071de74a749405bf03bcb5d08a46d3ba22291830cfe29d04ef6a4`.
- Summary SHA-256: `fe08432e1876ba964c7e7e31a9a16bee0c97d14da910767b63fb88326e274e58`.
- Summary generated at `2026-11-05T16:59:58.402805+00:00`.

The immutable preexisting manifest lists the baseline, including files absent from
this public distribution. `PUBLIC_SOURCE_MANIFEST.json` compares the reviewed public
files with the completed local source and the November 5 baseline. Old ZIPs, PDFs,
private submission notes and raw test XML are retained locally. A digest detects byte
changes; it does not authenticate ownership, model execution or organizer acceptance.

## Limits

Scores are constructed, labels reveal permission, audits are perfect and effects are
inert strings. Cheap authorization should be enforced directly. Batch stopping couples
completion and escape; the chart is not a measured productivity frontier. Actor renaming
has no effect, so no multi-agent causal advantage is established. Selected versus random
decoys controls their candidate distribution, but selection and evaluation share the same
synthetic scores. Transfer, realistic costs and model errors are unmeasured.

The optional capture runner retains request/response bytes and failures, but supplied
provenance remains unauthenticated. Fixture success cannot establish model execution.
The prospective protocol is not executed or preregistered. No new research route is
selected by releasing this source.
