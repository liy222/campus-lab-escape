# Reproduction archive cleanup — independent scope review

**Conclusion:** Main’s deletion scope is limited to the two expanded `frontend/node_modules` trees. The recorded cleanup is consistent with the historical source pins and preserved compatibility paths. I made no filesystem changes.

## What was removed

Main’s [execution receipt](../automated/execution.json) records exit code **0** for the PowerShell removal of:

- `data/reproduction/20261005T111419Z/clean/frontend/node_modules`
- `data/reproduction/20261005T115741Z/clean/frontend/node_modules`

The receipt records 2,687 files and 89,186,397 bytes per tree, 5,374 files and 178,372,794 bytes total. It records both target paths as deleted.

## Compatibility and preservation review

The historical pins [for 20261005T111419Z](../../../../integration/reproduction-20261005T111419Z-pins.json) cover 6,014 files; [for 20261005T115741Z](../../../../integration/reproduction-20261005T115741Z-pins.json) cover 10,778 files. Neither pin set contains `node_modules`; both include `frontend/package.json` and `frontend/package-lock.json`. The release manifest and historical T32 reports continue to point to the source archives, pins, expanded clean source roots, and reports.

The read-only existence check found all 15 expected preserved paths, including:

- all three `source.zip` archives: `20261005T110938Z`, `20261005T111419Z`, and `20261005T115741Z`;
- both expanded clean source roots, the two legacy fixture files, both pin files, and the Main/independent T32 reports;
- all four recorded test-database paths under the two isolated `clean/data/rollback` and `clean/data/runtime` trees.

The check also found both deleted `node_modules` paths absent. It did not read any database contents. The preparation record documents the junction boundary and Main’s [post-cleanup verification](../automated/verification.json) reports `junction_preserved_and_resolves_to_original_data=true`. I did not inspect that junction or any descendants. Main’s verification also records 856,286,317 remaining bytes and 27,596 files, excluding the junction target.

## Read-only commands and exit status

- `Get-ChildItem` on `data/reproduction` direct children plus scoped `rg` searches of documentation and fixed evidence — completed without errors. No recursive listing of the reproduction trees was used.
- A Python read of the two historical pin manifests confirmed the file counts, absence of `node_modules` entries, and presence of the frontend package manifests. No archived source files were read.
- PowerShell `Test-Path` over the 15 preserved paths and two deleted targets — **exit 0**; no preserved path was missing and neither deleted target remained.

No tests, builds, model calls, database reads, or full hashes were performed. This review establishes path and pin compatibility only; it does not recreate either historical build environment or test a fresh dependency installation. The original archives and dependency lockfiles remain available for that purpose.
