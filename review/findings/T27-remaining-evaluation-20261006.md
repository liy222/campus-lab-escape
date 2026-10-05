# T27 remaining six real evaluation results — independent read-only QA

Accepted the stored six-call accounting and failure interpretation within the limits below. Independent QA completed **73/73 checks**, actual exit **0**, chunk `06888f`. No model, target module, credential file, database, service, Git, or network was used by QA.

Actual QA command: `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 evidence/qa/T27-remaining-20261006T002000Z/review.py`. Evidence: `evidence/qa/T27-remaining-20261006T002000Z/{review.py,checks.json,result.json,first-failure.json,process-result.json,source-stop.json,artifact-sha256.json}`. The first QA command exited **1**, chunk `c4b06b`, because the harness assumed every invalid output had a digest. Stored CH01 A23 has both digest and size null because provider-invalid output preceded a suggestion. The corrected QA distinguishes this from received invalid content; the original report remains unchanged.

| Actual run | Calls | Actual program exit | Final interpretation |
|---|---:|---:|---|
| Main remaining K4 helper/result | 1 | 0 (`7a7a51`, Main actual tool evidence) | Valid model FAIL; deterministic NONZERO_EXIT and ASSERTION_FAILURE remain authoritative. |
| E1 `20261005T155830386817Z` | 2 | 2 (`878c8e`, Main tool exit 1) | Both INSUFFICIENT_EVIDENCE: fake/unread reference; schema/provider error. |
| CH01 `20261005T155947272680Z` | 3 | 2 (`3653ea`, Main tool exit 1) | All INSUFFICIENT_EVIDENCE: two fake/unread references; one MODEL_INVALID_OUTPUT with completion_tokens=1000. |

The approved preview is six ordered payloads, gates are finite 1/2/3, max_tokens=1000, timeout=20 seconds, total maximum reservation 1,884,048,000 units within the original CNY10 cap. The exact human approval binds preview raw SHA. QA re-encoded all six preview wire hashes, checked claim/release identity, trusted/target boundaries, known-usage arithmetic, call IDs, registered/read/hash-bound final refs, no PASS or human signature, and immutable stored inputs. All six known usage records are positive and unique; K4 is prompt961/completion142/cache256, cost2,556,240 units. The six observed known usage costs total the value in result.json; this is not an independent supplier invoice.

K4 original audit has no provider call and PRIOR_CALL_UNKNOWN_STOP. Its new append-only started record precedes the result; the static one-shot helper guards unused gate/call IDs and writes its marker before dispatch. The result records the preview-exact wire hash. New six IDs do not overlap original K1/K2 paid IDs. Original calibration report remains 10/11 and only two paid attempts at its historical time; later K4 valid FAIL is separate.

Both generic processes and K4 record complete equal before/after maps of 14 evaluator modules. All three maps and report source maps agree; actual current byte check also matches this old version. Old engine SHA is `6955a59976b6aac197fb222603e6795ae4588841d3eb70d477db0788b53b80e4`. No future prompt correction is included. The Main preparation KeyError/exit1 is preserved in its correction record and caused zero gate/network mutation.

Limits: generic E1/CH01 reports do not preserve actual HTTP wire digests. Their approved preview semantics, fixed evaluator version, source stability, bound event freeze, unique calls and results were checked; independent packet capture or stronger exact-wire observation is not claimed. Four invalid replies retain digest/size only and cannot be rejudged; the last CH01 output retains neither suggestion digest nor size. QA did not open the live ledger: 91 settled calls / upper662,360,080 units / no pending is Main's later statement, not a new independent full-ledger verification. None of these results establishes general language, full-game model calibration, a score, or human acceptance.

QA SOURCE STOP: stored sources and failures are sealed for the subsequent separate Evaluator Owner phase and another agent's independent review.
