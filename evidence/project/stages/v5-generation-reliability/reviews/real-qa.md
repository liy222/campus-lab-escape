# V5 generation reliability: approved run read-only review

**Result:** The approved run evidence is internally consistent across the approval record, final preview, source snapshot, per-case summaries, attempts log, and safe ledger snapshots. This reviewer did not execute or replay any sample.

## Reviewed artifacts

- Approval: `evidence/project/stages/v5-generation-reliability/approval.json` — approved record present; its preview digest and limits match the final preview. The approval reference itself is not copied into this report.
- Final preview: [preview.json](../automated/preflight-20261030T101510Z-b0c69e53/preview.json) — six calls, 1.00 CNY upper bound, total conservative upper estimate 0.99208 CNY.
- Run: [result.json and six safe case records](../automated/real-20261030T103205Z-0e4471d9/).
- Execute marker: `execute-started.json` in the final preview directory.
- Derived cross-check: [real-qa-final-20261030T104200Z.json](real-qa-final-20261030T104200Z.json), exit code 0.

The read-only PowerShell cross-check verified the approval/preview hash and cap, the execute marker’s run path, all 11 source fingerprints, six distinct attempt IDs and six distinct provider call IDs, and a one-to-one match between each case and its reviewed theme, room count, difficulty, seed, and blueprint. It also verified six admissions, `stop_reason=null`, zero retries, zero companion/evaluation calls, and `player_database_access=false`.

All cases completed: A1–A5 each recorded 24 witness steps; A6 recorded 33. These step counts are from Main’s recorded domain replays during execution. This QA did not repeat those replays or perform UI/browser verification.

## Cost and ledger summary

The six recorded usage-based upper charges sum to **0.04783912 CNY**, below the approved 1.00 CNY cap. The execution result’s safe ledger snapshots report 165 calls before and 171 after, a delta of six; charged amount delta matches the six case summaries. The preexisting unknown/pending count stayed at three, and the ledger was not frozen. This review read only those already-exported safe snapshot fields; it did not open the ledger database. The amount is based on returned usage in the run record, not an external invoice.

## Review process and limits

The first derived summary had a false mismatch because its path comparison mixed Windows and POSIX separators. The original summary remains preserved at [real-qa-20261030T104000Z.json](real-qa-20261030T104000Z.json); a normalized comparison then confirmed the marker path and all checks. The final corrected summary is the authoritative derived result linked above.

No private model output, private generated definition, answer data, or real ledger database was read. This checks only the six controlled after-only samples; it does not estimate a general success rate, compare against a prior batch, establish narrative quality, or constitute human acceptance. The user should review the generated levels in the app separately.
