# Reference library

The canonical library is `assets/reference-library/`: `catalog.sqlite` contains searchable records and review events, `library.json` describes provenance/status, and `images/` holds private original pixels. Catalog paths are relative to `images/`. The full private package preserves this layout; the default package excludes pixels. `refs-search` resolves the image path and verifies its hash; use `--images` for an external image directory.

The following ingestion stages describe the review workflow, not proof that human gold/OCR/segmentation have been completed.

No claim may be made about actual distribution until the directory is scanned. Offline input is a user-authorized directory or manifest. Do not download third-party images merely to fill counts.

The current CLI requires output outside the input directory, rejects symlinks, atomically replaces each output, and always writes an `.errors.json` sidecar (including `[]` on success). A failed expected-count check or bad image returns exit code 2 and retains the diagnostic output. Multi-frame formats are inventoried using their first frame; dHash is a similarity hint, never proof of an exact duplicate. IDs are assigned by sorted path for this initial inventory; the SQLite catalog uses content-hash IDs and preserves duplicate-path aliases.

## Ingest stages

0. Inventory: exact path, dimensions, orientation, SHA256, near-duplicate hash, origin and license state; immutable originals.
1. OCR/VLM proposals: domain, figure kind, primary grammar, regions, label density, asset candidates, art quality. Separate observed pixels from inferred metadata and store model/version/confidence.
2. Human gold review for a stratified 20–30 cases; correct classification ontology; then batch the remaining 161.
3. Extract abstract design concepts (spatial topology, panel roles, text slots, crop rules, style tokens) into master candidates. Do not embed original figure as template background.
4. Asset extraction candidates use segmentation only as a preview. Publish assets only after provenance/rights and scientific anatomy verification; when unlicensed, store style descriptors but no distributable derived pixels.
5. De-duplicate compositional masters. Keep 8–12 validated masters initially, not 161 copies.
6. Index records, approved masters and approved assets separately. For 161 assets SQLite + JSONL is adequate; add vector retrieval only if empirical recall suffers.

## Classification dimensions

`domain[]`, `figure_types[]`, `layout_families[]`, `primary_visual`, `text_density`, `text_count`, `region_tree`, `reading_order`, `relation_topology`, `asset_types[]`, `style_signature`, `reusability`, `license_status`, `review_status`.

## Rights policy

`unknown|internal_reference|style_only|authorized_reuse|restricted`. Every original pixel derivative inherits rights constraints until legally cleared. Third-party logos, actual microscope photographs and experimental raw data must not be repurposed as generic embellishment.

## Index recommendations

Hybrid retrieval over semantic domain, scientific figure intent, topology signature, density and reading path. Second-stage VLM only for small shortlisted candidates. The reference is a design example, never source evidence for scientific statements in the user's document.

当前逐图分析、中文检索、增量失效、人工修订入口见 [知识库工作流](reference-knowledge.md)。
