# Signal edition / 02 — November 6, 2026

This second interface revision retains the tested workflow and introduces a navy
landing section, lime attention marks, cobalt controls and a light research workspace.

## Typography and assets

- Space Grotesk variable, weights 400–700, for headings and prominent numbers.
- Manrope variable, weights 400–800, for interface text.
- Both Latin WOFF2 files are served from the local allowlist; combined size 46,820
  bytes. The app does not contact Google or any other external service at runtime.
- Font files are unmodified. Original SIL OFL 1.1 copyright/license files and
  download URLs/hashes are retained under `web/fonts/`. The server exposes only the
  two explicitly listed font assets, not an arbitrary file-serving directory.
- Source verification and the future release allowlist include the font assets and
  licenses. The original interface pass did not rebuild the research package or submit an entry.

## Motion with a purpose

The introduction enters in a short sequence. The current replay preview grows its
score bars, shows its review marks, and runs a single decorative scan across the
queue. New results receive brief row and metric movement; evidence bars animate
when a visible study filter changes. Section headings enter once on scroll.
Buttons have short hover and press feedback.

All sequences are finite, at most approximately 1.1 seconds. Effects never change
the numbers, introduce fake progress, imply actual execution timing, or wait before
exposing results. Text remains at full opacity throughout transitions to preserve
contrast. Only the decorative scan fades. Off-screen effects are skipped; repeated
effects on the same element cancel their predecessor.

**Animate this view** repeats the visual preview without generating a new scenario.
**Motion on/off** is a local preference, persisted when browser storage is available.
System reduced motion disables animation and cancels in-flight effects immediately.
Turning motion off also removes smooth scrolling and CSS transitions. Content is
never hidden while waiting for an observer, fonts, or JavaScript.

## Preservation and verification

The first interface revision is preserved at
`output/history/audit-capture-interface-r1.zip`, SHA-256
`79e5242c6029ab0f5fe75f3b04973aeaa18d992f8e9b15f3d5174f54ac595582`.
Simulation/allocation logic, November 5 study data, the pre-existing manifest and
research PDF are unchanged. Server changes only add named static assets; evidence
hashing and future packaging now include nested fonts. New tests check WOFF2 MIME
types, signatures and continued denial of arbitrary font-directory file access.

`python tools/design_check.py` checks loaded fonts, actual finite animations,
cancellation, preference persistence, live preference changes, local-only requests,
responsive layouts and the prior workflow checks. Its reduced-motion captures are
`output/design-review/after-*.png`; `signal-desktop.png` captures normal motion after
settling. The app's CSP remains strict: no unsafe-eval or external font allowances.
`python tools/verify.py` runs the existing regression/oracle/browser suite.

Generated receipts, not this design note, record final check counts and outcomes.
Full accessibility certification, physical-device and screen-reader tests remain
outside the verified scope. This visual revision adds no live-model evidence and
does not resolve author, eligibility, manuscript or submission decisions.

Historical archive paths above refer to the original local workspace; archives are not published.
