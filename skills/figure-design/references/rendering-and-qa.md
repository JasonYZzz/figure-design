# Rendering, image routes, QA and repair

## Route preference

For `text`, the agent follows the bundled Diagram Design Skill and hands its HTML to `diagram-export` for upstream checks and exports. The routes below apply to `plan --mode mixed`. Both modes deliver SVG, PNG, standalone HTML and the quality report.

1. `asset_composite`: main illustrated scientific roadmap route; native text + arrows + approved pictograms/AI assets.
2. `image_first`: low-density concept picture or user-selected aesthetic exploration. If generated figure contains text/critical lines that are unverified, it is a draft. Post hoc layer separation/OCR are optional experimental workflows, not guaranteed production.
3. `strict_scientific`: dense math, high-risk causal structure or exact quantitative data combined with approved assets.

## Composition ownership

FigureScene owns x/y/bounds/zIndex. Native scientific labels and connectors must be generated from FigureContent instances and relation IDs. Images can be illustrated layers or backgrounds, with explicit crop, alpha and focus points; image assets do not get to invent labels or critical arrows.

## Text

Render exact Unicode strings from approved Label IDs. Preserve units, minus symbols, Greek chars, spaces and domain terminology. Use actual target font measurement (Chromium or a shaping engine) and check line breaks against approved policy. Keep text-slot preflight before costly image generation; repeat rendered fit validation after export. A perfect SVG source string does not imply the rendered glyph is readable if the font is absent.

## QA levels

- HARD: all required claims grounded; no invented causal relation, no omitted mandatory task, exact label instances, no unresolved excess text on delivered Image-First output; critical arrow endpoints; actual font/glyph support; no source image misuse.
- GEOMETRIC: clipped text, offcanvas shapes, label-arrow collisions, reading order, meaningful safe whitespace, image focal areas.
- AESTHETIC: panel hierarchy, consistency, domain appropriateness, legibility at final size. VLM judgement cannot overrule a hard failure.

## Repair protocol

Classify failure by source: content, composition, text, connector, asset, provider, visual. Patch specific scene IDs; recalc dependency graph. Bounded retries (default at most 2 for paid image generation, 1 local layout reflow per candidate) and diagnose instead of looping. If a direct image's text cannot be separated without harm, use asset composite with the approved content. Use Diagram Design when the user chooses a text-only draft.

## Latency tracking

Record model calls and actual wall time: extraction, planning, retrieval, image generation, compositing, QA, repairs; include queue and downloads. Preview can be shown before illustrative assets if valid; the default image quality mode is not a guaranteed time limit.
