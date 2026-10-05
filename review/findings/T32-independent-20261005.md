# T32 independent clean-release identity review — 2026-10-05

**PASS in the read/hash identity-review scope; stable STOP.** QA independently inspected the committed-source ZIP, Main's explicit pins, clean source bytes and existing Delivery records. QA did not rerun API tests, build, browser, services, evaluator or reproduction helper. No identity defect found.

## Actual QA work and command

Only new files: `tests/review_clean_release.py`, `review/findings/T32-independent-20261005.md`, and `evidence/qa/T32-independent-20261005T113707029429Z/`.

Actual executed QA command from `D:\深度能力`:

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 tests/review_clean_release.py
```

Actual exit **0**, started `2026-10-05T11:37:07.029615+00:00`, ended `2026-10-05T11:37:12.237060+00:00`. Standard-library byte/JSON checker only; no target-helper/module import, Git, DB query, package query/install, service process, network/model call, paid call or subagent. Preliminary read/JSON-shape/hash inspections and the later supplemental fixture/report-record read/hash command each exited0; two preliminary outputs were oversized/truncated and were replaced with bounded structural summaries, not treated as verification evidence.

QA helper raw SHA256 `2fba749d8f66daa392f6a79c3968607245853357ce51593a28e631f9f171dee7`. Result `evidence/qa/T32-independent-20261005T113707029429Z/result.json`, raw SHA256 `45881b749ec5feec6c584983896894948a831ebd837db9902ebff04b009a301b`. Supplemental Main fixture/copy hashes and final 23-file evidence read-back: `supplement.json`, raw SHA256 `23d93c9323afca54ff1773c4e12247324b6577eb723e5024546747a32406ad44`. Both records describe new read/hash work, not target execution.

## Main → ZIP → clean byte chain

- Main-recorded committed-source identity **`fc70b15b84d811aec62e2a561c468538844b6edf`** is identical in handoff, pins, Delivery report/index/verification and ZIP comment. QA did not query Git: commit provenance relies on authorized Main metadata; SHA validation independently establishes the provided artifact bytes.
- ZIP `data/reproduction/20261005T111419Z/source.zip` raw SHA256 **`bc8e8f86b0f861762e3247507688c1eb1f85ea1ac5f7e3cc86e830c04f61e40e`** matches Main handoff/pins and Delivery report.
- Main pins `evidence/integration/reproduction-20261005T111419Z-pins.json` raw SHA256 **`25ce6a65f8a134cdd58647275840cc8e32f6dfdd4af674d2dafcbbc62f6883d1`** matches handoff and report. Delivery `materialization.json` equals that exact 6014-entry Main map.
- ZIP has **6014 unique file entries** with precisely the Main-pinned set, plus **1968 directory entries**, **7982 total ZIP entries**. It would be inaccurate to call 6014 the total including directories.
- Every ZIP file raw byte SHA256 equals its Main-recorded `git_blob_sha256`. These are verified against provided pins, not newly fetched Git blobs.
- Independent pure-byte materialization applies only the explicit Main per-file modes: **1032 raw_equal**, **4982 main_pinned_line_endings**. For the latter, CRLF is reduced to LF and CRLF is restored only at Main's fixed zero-based newline indices. Strict index validation, BOM/EOF and all other bytes are preserved by the byte operation and exact resulting raw hash comparison. No target helper or target-selected normalization was used.
- Each independent materialized raw hash equals the Main runtime pin, current file in `data/reproduction/20261005T111419Z/clean`, and Delivery's complete original **6014 before/after maps**. QA also read the entire 6014 clean map before and after its review; maps are equal. All per-file actual ZIP/runtime/clean/Delivery hash mappings are retained in `result.json.all_6014_raw_mapping`.
- The clean helper raw hash is `7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9`. Main's separate M2 history fixture and its clean `data/integration/` copy both hash to `21d992feb895ce5535c6b0b3d731887be9619171351a551935e1d10fc2bfae22`; its recorded old source commit remains metadata, not a new Git check.
- Delivery index lists **23 evidence files**; each current raw SHA256 and byte size matches. The index itself, Main handoff/pins, ZIP and materialization hashes are recorded separately in the QA chain. Source/config/db files outside the Main-approved set were not opened by this audit. Actual `.env` paths were checked only with exists and are absent; public tracked `.env.example` source bytes belong to the declared ZIP file map. No actual `.env` or database content was read.

## Existing run records independently reviewed

The owner reproduction command is recorded in Delivery `report.md` as **Python `-B -m scripts.reproduce …`**, with **no `-X` option**. QA's own `-X utf8` flag must not be projected onto that historical command. Owner overall process exit0 is the existing Delivery record; QA's new exit0 is a separate byte-audit result.

| Recorded check | Independent record/hash checks | Scope |
|---|---|---|
| Python lock/version records | All 28 names and lock-file versions equal recorded expected/actual versions | Recorded package versions; QA did not query the current environment |
| Outer steps | 7 step containers all exit0 and log hashes match | pip-check, Node, npm, npm-ci, unified-check, two evaluator prechecks |
| Leaf commands | Expand unified-check into build + pytest: **8 actual leaf command records**, all exit0 with matching logs | This explains 7 outer versus 8 leaf counts without inventing an eighth outer step |
| Build/pytest | Existing TypeScript/Vite build exit0; pytest log has **73 collected tests, 203 subtests passed, 1 warning** | 19 reused M3 unittest methods are included in collection, so not 73 unique acceptance scenarios; Starlette/HTTPX warning remains |
| Evaluator identity prechecks | `E1-formal-review-v2` and `baseline_v1`: copied/source report raw hashes equal, exit0, issues[], actual_paid_calls0, target_code_executed=false | Strict registered identity only; no new semantic calibration or paid evaluation |
| v2 services | Recorded backend **15564 → 24140**, frontend18860; different backend PIDs at clean cwd | Existing automated mock service/persistence records; no QA HTTP request |
| v1 rollback | Recorded backend **12972 → 2752** at `clean/release/archives/baseline_v1`, different cwd/port from v2 | Existing separate v1 service records; no QA service launch |
| Stops | Exactly **5** owned stops, each taskkill exit0 / process exit1, while owner overall exit0 | Intentional Windows process termination is not relabeled as process exit0 |

v2 public result records show the exact route's terminal summary `won`, revision18, inventory only `access_card`. The original unlock receipt is revision12→13, changed=true and `consumed_item_ids=[emergency_key]`; saved revision13 and restored state retain unlocked R3 and no key. Restore revision19 and new generation preserve the saved gameplay and save summary. The service result includes the before-restart and restored states; Delivery also records that state after restart equaled the previous won state. This audit checks those provided records and their hashes; it does not independently observe 18 individual live requests or reissue an after-restart GET.

v1 public saved/before-restart/restored states all retain `emergency_key`, original receipt consumption is empty; restore revision14 changes generation and preserves saved gameplay. Read-only path existence checks find distinct `clean/data/rollback/game-v1.sqlite` and `clean/data/runtime/game-v2.sqlite`. Delivery `report.md` identifies their runtime assignment; service ledgers independently identify different cwd/ports/PIDs. QA did not inspect either DB, reconnect to a running process, or infer DB content from filenames.

## Limits and STOP

This certifies the **fc70 clean package and its supplied historical records**. Later root HEAD/release changes, including another owner's ongoing `evaluation/events.py` work, are a separate identity. Neither 6014-file materialization nor the two strict identity prechecks certify that later root tree or any new semantic evaluation/calibration. The reviewer did not change source pins, trusted rules, historical reports/metadata, original ledger, archive, environments or other owner paths.

The existing Windows/designated Conda environment is reused; there is no clean-OS/new-Python-environment claim. No paid/real-language robustness, human player study, teacher approval, human signoff or Main model introspection is inferred. Teacher/human fields remain null. No required independent T32 identity-review work remains pending. **Stable STOP.**
