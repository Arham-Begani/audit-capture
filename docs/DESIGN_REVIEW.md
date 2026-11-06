# Interface design record

The first November 6 interface revision used a warm editorial review-window motif.
The current Signal edition / 02 uses navy, lime and cobalt with locally served
Space Grotesk and Manrope. See [Signal edition](SIGNAL_EDITION.md).

Audit Capture serves researchers and technical readers inspecting a bounded synthetic
review-allocation mechanism. This is an expert usability inspection, not participant research.
The original phone layout put settings ahead of the result; the revision adds example
presets, a real replay preview, compact-screen disclosures, readable outcomes, keyboard
shortcuts, uncertainty rows and recoverable loading/error states. Existing controls,
import/export, policy comparisons and the complete numeric chart alternative remain.

## References inspected November 6

- [Hack Club](https://hackclub.com): warmth, strong editorial headlines and an approachable first action.
- [PostHog](https://posthog.com): a consistent visual concept across product surfaces.
- [Raycast](https://www.raycast.com): direct actions and discoverable keyboard shortcuts.
- [Linear](https://linear.app): hierarchy and progressive disclosure of complex detail.

These sites were visually inspected. Their layouts, logos, text and artwork are not
included. Reference screenshots remain private research notes. The app's visual marks
are original HTML/CSS/SVG; fonts and notices are documented in [NOTICES](../NOTICES.md).

## Verification and limits

`python tools/design_check.py` exercises local API flows, explicitly intercepted
failure/loading fixtures, fonts, finite motion, preference persistence, reduced motion,
focus, targets, bounded text contrast and responsive layouts at 1440, 768, 390 and
320 pixels. Receipts are in `results/design-checks.json`; generated full-page images
are under `output/design-review/`. `python tools/verify.py` covers regression, oracle
and browser workflows. There is no Node build or TypeScript pipeline in this stack.

Chromium viewport emulation does not establish physical-device, screen-reader or full
WCAG conformance. No external usability study or live-model evidence is claimed.
