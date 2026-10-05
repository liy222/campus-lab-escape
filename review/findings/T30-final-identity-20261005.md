# T30 later API collector identity — 2026-10-05

**PASS; stable STOP.** One newly authorized narrow independent API run completed: **54 tests, zero failures/errors, actual process exit0**. This new result supplies the complete current collector source identity for later E2/E3 event linkage. It does not replace, edit or retroactively relabel any earlier T30 accepted result.

Actual command, executed from `D:\深度能力`:

```powershell
& 'C:\Users\liyh\.conda\envs\1\python.exe' -B -X utf8 -m tests.qa_ch01_runner
```

Executed once; tool process session82591, completion exit0. Started `2026-10-05T11:13:55.710530+00:00`, ended `2026-10-05T11:14:16.559338+00:00`. The runner's own command field omits interpreter flags; the separate actual process record retains `-B -X utf8` faithfully. Report/index construction and source/hash read-back are metadata work, not additional test executions.

## Identity and evidence

- New actual runner directory: `evidence/qa/T30-20261005T111355675003Z-api/`.
- New process supplement: `evidence/qa/T30-final-identity-20261005T111355675003Z/process.json`, SHA256 `f7118fe22e4166960303b3fd663c1801237e5c027acaf3450999c0a6ab10a745`.
- New `run.json` SHA256 `65c590387554a60e9ceae590258ba2643825af1480beae50775a6078b5e69893`.
- The **entire 153-file collector map** is captured before and after in the actual run and process supplement; maps equal, and independent current-file read-back also matches every recorded hash.
- Rules raw SHA256 `73a77e8bbc9a26d59a9519315af99f8c640c5447e8e41cff303229278d850bbb`; public level `2.0.0`, schema/API/tool `1.0.0`.
- Stable Delivery `scripts/reproduce.py` SHA256 `7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9` is in that actual complete map. It is an identity capture only; this task did not execute or evaluate that script.
- Current CH01 browser helper SHA256 `c09f6d74b532caccf3f2b73678cf737d272fe38852fa128e3e890df8470fc855` matches its earlier accepted final six-route browser result. Current Backend/Frontend product source hashes also match that accepted final browser source map. The new API run did **not** run the browser helper.
- Actual sanitized `http-exchanges.json`, unittest output and stderr hashes are in `process.json.run_artifacts`, matching the runner's hashes. The full actual HTTP/concurrency/process-restart coverage is in the new exchanges; outcome remains 54 pass.

The earlier `T30-20261005T062008898733Z-api` result remains accepted at its recorded historical source map, which included the older, then-uncalled browser helper. The later browser trace-capture correction changed that helper; it cannot be silently substituted into the old API map. This fresh run binds today's complete map through a new actual execution. All old T30 evidence/index/ledger/report files were left untouched.

## Scope and limitations

Changed files are only this new report, the new timestamped runner output directory and the new `T30-final-identity-*` process record. No product source, QA collector, Git, archive, environment, original ledger or other owner helper was edited. No browser/checker/build/rollback suite was repeated; no subagent was spawned. Collector hashing includes stable scripts, API/E2E QA sources, product/contracts and indexed archive bytes; active continuation QA files are outside its selected paths. Current evaluator target code was not read or invoked.

Providers remain deterministic mock/scripted and fake local transport probes. No paid model dispatch, real-language robustness claim, human playtest, teacher approval, human signoff or Main runtime-model identity is inferred. This task is the later E2/E3 event identity supplement only. There is no new implementation defect or pending T30 test. **STOP.**
