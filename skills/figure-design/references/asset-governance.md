# Asset governance and scientific figure safety

An asset record needs stable ID, scientific entity category, explicit intended depiction, origin, creator/provider, original and derivative files, license/permission, allowed uses, style family, dimensions, transparency, validation state, safety notes and content hash.

No permission -> `style_only` or `reference_only`; never `production_approved`.

For a new mixed scientific figure, the executing agent uses its current host image-generation skill to create the illustrative asset, following the operation ledger and the user's scope. Do not claim a generated image is evidence. For biomedical inputs, use only general illustrative scientific objects with author-supplied or verified features. Never generate fake gel bands, microscopy outcomes, molecular structures, charts or readout trends that look like experimental results.

Illustration sheets may batch related icons if each cell can be extracted, has consistent background and safe crop; produce a per-asset QA record. Standalone images for complex tissue/mechanism may be necessary. Cache by scientific entity + approved features + rendering style + prompt model version + asset rights.

All external retrieval and remote model payloads obey confidentiality and provider consent controls. Preserve original path internally; public outputs contain minimally necessary provenance.
