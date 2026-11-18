# Raster reference reconstruction (optional)

Unlike new-figure creation, reconstruction's reference itself is the target visible surface. Normalize and preserve a canonical source; inventory visible regions and uncertainty; classify text, simple native shape, data graphics, scene/subject, and ambiguous regions.

For text, use OCR only to propose regions and line metrics; verify against reference or authoritative provided wording. For new scientific diagrams, NEVER use reference-image OCR as the new figure's truth. For clean-base inpainting, protect source pixels outside exactly controlled masks; edits inside masks require scientific and visual inspection. A true separated source layer must be registered to canonical coordinates (e.g. compare shifted overlap error) and preserve zIndex. Unknown layout/identity should remain pending, not hallucinated.

Reference implementation ideas from PPT Master: `image_ocr.py`, `image_layers.py`, `image-to-pptx.md`; these are auxiliary techniques, not evidence of full automated decomposition. Respect copyrights and publication image integrity policies.
