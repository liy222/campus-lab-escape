# V5 third round: generation still rejected; one real companion exchange delivered

Independent terminal read-review, 2026-10-23. **Main's actual execution remains exit1.** G2/G3/A1/A2 each made one call, with no retry. Both new generations were rejected; A1 and A2 were actually delivered through HTTP200, DeepSeek `model_calls=1` and the Store guard. This partial companion success does not make the run green or establish overall release acceptance. Historical G1 was test setup, not a new generation success.

## Original generation failures

| Case | Original first rejection | Additional independently observed defects |
|---|---|---|
| G2, 2/normal | `INVALID_CODE` | `puzzle_checkin` concatenates selected numeric and nonnumeric device material into a code. `puzzle_panel` chooses `index` but both selected clues contain zero reading positions: `INSUFFICIENT_FACTS`. |
| G3, 3/hard | `PUZZLE_COUNT`: five rather than six | `CLUE_MARK` is defined and required but has no clue object, violating `CLUE_REFERENCE`. The sequence selects a mapping table without source tokens; the last index-code puzzle has no reading positions: both `INSUFFICIENT_FACTS`. Only one puzzle selects two or more clues, below hard's required two: `COMBINATION_COUNT`. |

Both raw JSON objects pass Draft shape validation. Original compiler failures and downstream static defects are reported separately. No raw draft was edited, repaired into success or admitted by relaxing validation, and no invalid sample reached solver proof. This round is **0/2 new generation admissions**, with the historical G1 explicitly excluded.

The current prompt already explicitly requires numeric code results, the exact numeric requested puzzle count, nonempty source tokens with a covering symbol map and the required number of distinct multi-clue puzzles. The model still violated those requirements. Two teaching gaps can be stated more directly if Main chooses a narrow follow-up: the combined index positions must be nonempty, and each defined clue must have exactly one discoverable clue object. The existing index-reading and kind/reference instructions imply parts of these conditions but do not state both cardinalities as explicitly. More wording is not evidence of future model adherence, and no new paid retry is authorized here.

## Actual A1/A2 exchange

Both replies use natural public labels, valid refs to the two discovered materials, and the observed index-rule relation. They contain neither the complete compiled input nor internal IDs in prose; the current validator accepts the original saved replies. A1 correctly relates the first material's source sequence to the second material's reading positions. A2 receives the **exact newly delivered A1 question and answer**, then adds that the positions address source entries rather than independently generating an input. This is a modest explanation beyond A1, although it remains close to restating the displayed rule and offers limited new local reasoning.

Both replies append advice to inspect the unobserved access terminal. That terminal is in the public catalog, remains unobserved and legally supports inspection, so this is not invented evidence or a forbidden action claim. It is nevertheless an unnecessary, repeated detour from the requested relation/explanation. The exchange supports a finite conclusion of grounded, guarded real delivery with remaining focus/depth limitations, **not an all-quality PASS**.

A1's outgoing payload exactly matches its independently reviewed preview. A2's outgoing payload is newly constructed from actual successful A1 history and differs from the preview placeholder. Independent reconstruction with the current `public_context` and `bounded_messages` matches both actual payloads. A1 retains three action-history entries. Budget selection removes two older action entries from A2, preserving the complete latest A1 dialogue plus one action; no dialogue was invented or substituted. The actual A2 upper bound is 0.049736 CNY, still within 0.05.

Both actual response bodies satisfy the registered AI-turn response schema. Gameplay projections before/after are equal; A1 changes revision13→14 and hint_count0→1, A2 changes revision14→15 and hint_count1→2. Generated current_hint_level remains1. Only these established hint metadata changes occur. The saved historical reconstruction still matches round-two G1's exact definition/witness and original public-stage projection; it contributes no new paid generation.

## Execution, cost and privacy evidence

All 45 frozen inputs/source hashes match the preflight preview, actual execution's source-after map and current bytes. The 403 product-source map also remains unchanged. Original round-two and preflight artifact hashes remain intact. The result binds 26 current raw JSON/journal artifacts.

All four full-payload hashes and integer cost bounds were independently recomputed. G2/G3 equal their reviewed generation payloads. Actual authorization binds the preview hash, source bundle and four-call/0.50 ceilings; the journal contains exactly four before-dispatch and four after-dispatch records, with no retry. Requested/reported model, finish reason, usage bounds and provider-content hashes are consistent.

The **reservation bound is 0.389912 CNY**; the additional conservative **charged usage upper bound is 0.0294056 CNY**, independently matching `(1072378880 - 1042973280) / 1e9` in the saved ledger snapshots. Four ledger calls were added. Three historical unknown identities remain unchanged, with no new unknown, pending0 and frozenfalse. Reservation is not charged expenditure.

No credential/cookie assignment pattern was found in the saved artifacts, and all provider captures record `secret_detected=false`. QA did not read the actual Key or open the canonical ledger, database or network. These finite pattern checks plus executor secret guards do not constitute a universal secret audit. No provider or evaluator was invoked by QA.

Actual independent command: `C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -`, inline source/payload/fee/schema/guard/domain diagnostic, tool **a67df3**, **exit0**. The exact probe is retained in that invocation. Read-only diagnoses c44be9, 49f517 and cb6cf8 also exited0. The earlier shape-only inspector 0d823c exited1 because it assumed every defined clue had a placed object; the later inspection established the genuine missing CLUE_MARK placement. It changed no raw or product bytes and is not relabelled as a product run.

The report is `evidence/upgrade/v5.0/qa/round3-real-review.json`, SHA256 **`e2d6e483b5f678a4b8ce69e1f3d4363d47483193e9465d58539da96ee62c1efa`**. It contains exact first rejections, shape-only downstream observations, source-before/after maps, four payload/usage observations, response/guard/state checks, per-reply finite manual quality assessments and artifact hashes. No private solution values are copied.

This is terminal review of the approved round: no extra call, unused-slot reuse, formal suite, build, browser, evaluator or product change occurred. Earlier failures stay historical. A real two-turn companion delivery has now been observed on the exact historical G1 stage; reliable new 2/normal and 3/hard generation and broad companion quality remain unestablished. **SOURCE STOP; overall release remains unaccepted.**
