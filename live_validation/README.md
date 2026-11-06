# Local validation readiness - updated November 6, 2026

**Status: no live-model inference performed.** The runner was prepared November 5. November 6 readiness fixes are recorded separately in `../docs/EVENT_WORK.md`; they are not claimed as judged-period research. The frozen November 5 v0.3.0 baseline is archived. This runner is included in the v0.3.1 source fingerprint and combined verification suite.

No approved runtime was used and no model responses were collected.

## What is ready

`capture_local.py` makes at most one completion request to an **existing** local OpenAI-compatible server. It first checks the advertised model ID, disables proxy use and redirects, caps output at 512 tokens and responses at 256 KB, saves the exact outgoing HTTP JSON body in `request.json`, hashes it and all retained artifacts, preserves response bytes (including an incomplete body prefix), and records failures without automatic retries. A successful response is checked by Audit Capture's existing score importer, including exact action coverage and scenario hashes.

Only `http://127.0.0.1:PORT/v1` is accepted. This runner does not install or start a model and does not accept cloud endpoints or API keys. Before using a local server, establish that it performs local inference rather than forwarding requests to a paid service. Captured metadata is self-reported; a valid HTTP response does not independently authenticate model execution. Fixture mode explicitly labels transport tests as fake-server evidence.

Prepare a scenario JSON and a reviewed packet with exactly:

```json
{
  "scenario_sha256": "SHA-256 from audit_capture.core.fingerprint for that scenario",
  "messages": [
    {"role": "system", "content": "Reviewed monitoring instructions and realistic policy context."},
    {"role": "user", "content": "Reviewed action context. Return JSON with a scores array containing exactly one action_id and numeric score from zero to one for each action."}
  ],
  "max_tokens": 256
}
```

These strings are schema documentation, not an executed prompt or a research dataset. Use opaque action IDs and permission labels verified separately. The old toy target names/descriptions leak the answer; do not reuse them as a blinded model benchmark. Do not conceal authorization information a real monitor would have. See `../docs/NEXT_EXPERIMENT.md` for the full prospective design.

With a suitable existing local server, run from the project root:

```powershell
python live_validation/capture_local.py --base-url http://127.0.0.1:8080/v1 --model EXACT_ADVERTISED_ID --packet reviewed-packet.json --scenario reviewed-scenario.json --out live_validation/captures/unique-run
```

The output directory must be new. Successful captures contain packet, request, scenario, server metadata, raw response, importer-compatible scores, imported replay and receipt. Failed captures retain available raw evidence and a failure receipt. Model-specific response aliases and unsupported JSON modes cause a visible failure; do not repair answers silently.

## Tests and scope

Tests run against a deliberately fake local HTTP server and say TEST FIXTURE in their model/provenance fields. They validate transport and evidence handling only. No score from those tests is a live-model result. The runner tests are included in the combined application verification; their fake-server outputs remain separate from the scientific study.

Live research still requires a suitable permitted runtime, independently reviewed
task labels, a frozen analysis and actual captured responses. The research route is
not selected. Competition eligibility, author declarations and manuscript review
remain unverified. The November 5 baseline and November 6 maintenance are disclosed
separately. Source publication is not an organizer submission.
