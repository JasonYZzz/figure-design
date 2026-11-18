# Rendering, image routes, QA and repair

## Route preference

Select `plan --mode text` for a Diagram Design HTML architecture diagram or research roadmap with native SVG labels and connectors. Select `plan --mode mixed` to require approved illustrations in the rendered figure. Both modes deliver SVG, PNG, standalone HTML and the quality report.

1. `text_structured`: high-density text or exact workflow; controlled composition grammar, native typography.
2. `asset_composite`: main illustrated scientific roadmap route; native text + arrows + approved pictograms/AI assets.
3. `image_first`: low-density concept picture or user-selected aesthetic exploration. If generated figure contains text/critical lines that are unverified, it is a draft. Post hoc layer separation/OCR are optional experimental workflows, not guaranteed production.
4. `strict_scientific`: dense math, high-risk causal structure, exact quantitative data; plot directly from values or verified assets. No generated data marks.

## Composition ownership

FigureScene owns x/y/bounds/zIndex. Native scientific labels and connectors must be generated from FigureContent instances and relation IDs. Images can be illustrated layers or backgrounds, with explicit crop, alpha and focus points; image assets do not get to invent labels or critical arrows.

## Text

Render exact Unicode strings from approved Label IDs. Preserve units, minus symbols, Greek chars, spaces and domain terminology. Use actual target font measurement (Chromium or a shaping engine) and check line breaks against approved policy. Keep text-slot preflight before costly image generation; repeat rendered fit validation after export. A perfect SVG source string does not imply the rendered glyph is readable if the font is absent.

## QA levels

- HARD: all required claims grounded; no invented causal relation, no omitted mandatory task, exact label instances, no unresolved excess text on delivered Image-First output; critical arrow endpoints; actual font/glyph support; no source image misuse.
- GEOMETRIC: clipped text, offcanvas shapes, label-arrow collisions, reading order, meaningful safe whitespace, image focal areas.
- AESTHETIC: panel hierarchy, consistency, domain appropriateness, legibility at final size. VLM judgement cannot overrule a hard failure.

## Repair protocol

Classify failure by source: content, composition, text, connector, asset, provider, visual. Patch specific scene IDs; recalc dependency graph. Bounded retries (default at most 2 for paid image generation, 1 local layout reflow per candidate) and diagnose instead of looping. If a direct image's text cannot be separated without harm, discard as final and use asset-composite/text-structured fallback with the already-approved content.

## Latency tracking

Record model calls and actual wall time: extraction, planning, retrieval, image generation, compositing, QA, repairs; include queue and downloads. Preview can be shown before illustrative assets if valid; the default image quality mode is not a guaranteed time limit.
