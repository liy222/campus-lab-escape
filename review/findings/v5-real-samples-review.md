# V5 finite real samples: generation not accepted

Independent read-only review, 2026-10-23. Main's actual run exited **1**. G1/G2/G3 made three real generation calls and all three were rejected; A1/A2 were skipped because no generated stage was ready. This is a real generator-output finding, not an admission bypass or a solver state/time-limit failure. It does not establish a population-wide model failure rate.

| Sample | Original first rejection | Additional independently inspected violations |
|---|---|---|
| G1, 1/easy | `PUZZLE_COUNT`: 3 instead of 2 | Index selects a clue carrying `symbol_map`; sequence selects a clue carrying `indices`: both `UNUSED_FACTS`. |
| G2, 2/normal | Draft `rooms.0.locked_by`: `extra_forbidden` | Index yields a nonnumeric code; sequence mixes incompatible clue fields. A room-one puzzle requires room-two material, while unsolved room-one puzzles gate forward passage. |
| G3, 3/hard | `PUZZLE_COUNT`: 5 instead of 6 | Reserved puzzle ID `EXIT`; nonnumeric code; circuit carries forbidden clue facts; sequence mixes indices; first-room item puzzle requires an item only available in room two. |

For G2, downstream recipe inspection used an explicitly diagnostic in-memory copy with only the forbidden room field removed. The original response remains rejected and unchanged. No repaired draft was treated as an accepted real sample. Other downstream violations were inspected independently; they do not replace the compiler's actual first rejection.

The existing prompt states the puzzle-count formula and broad recipes but does not give the exact compatible clue fields or code-output constraints. The schema expresses data shape rather than these semantic conditions. The results support a narrow prompt/contract-teaching repair: send the computed count explicitly, spell out each recipe's flatten/map/index operation and mutually compatible fields, require numeric code results and four distinct ASCII sequence IDs, and require necessary materials in the same or an earlier accessible room. Retain strict schema/admission, original failed responses, no automatic repair and no automatic paid retry. The fixed catalog and campus-specific prose appear in all three outputs, but no playable campus level or real companion behavior was demonstrated.

Actual saved ledger snapshots show **3** additional calls and **0.03128048 CNY** additional conservative charged upper bound. Three historical unknown identities remain unchanged, pending is zero, frozen is false. The reservation sum `0.39712` is a different quantity and must not be presented as the charged cost. QA did not open the canonical ledger, read credentials, call a provider, or use a network connection.

Evidence: `evidence/upgrade/v5.0/qa/real-samples-independent-review.json`, its reproducible read-only classifier `review_real_samples.py`, and the hashed original `real-samples/{G1,G2,G3}-{provider-result,api-result,exact-payload}.json`, result and ledger snapshots. No private answer values are copied into the QA report.

Actual review commands and exits:

- First inline classifier: exit 1 after an uncaught G2 Draft validation error; G1's rejection was already printed. Corrected complete inline classifier: exit 0 for all three classifications.
- `PYTHONPATH=. C:\Users\liyh\.conda\envs\1\python.exe evidence/upgrade/v5.0/qa/review_real_samples.py`: initial exit 1 on full-source equality protection, no report written. Main confirmed a separate AI prompt edit epoch had begun.
- The classifier then explicitly bound the unchanged domain compiler and original saved real payload/source map: actual exit **0**, tool chunk `9dd3bc`. This means diagnosis completed, not generation passed. The two failed diagnostic commands remain historical tool evidence.

The real run's AI hash is `ecfdbefaf26bd2926c0e82243210e3887b5d8ccd9ba7363c6b8a26c2cac43fd5`; the independent report records the current AI-only difference and does not certify that new implementation. Its compiler hash matches the real run, and all 401 files were unchanged during the successful read-review itself. The previously sealed offline joint report remains unchanged and limited to its recorded epochs. **GEN01, real A1/A2, and overall release acceptance remain unestablished.** No additional paid action is authorized or performed by this review.
