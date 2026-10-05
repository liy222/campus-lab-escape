# T24 observed outcomes; stopped run, T25 review pending

The finite formal runner exited **0**, meaning it recorded the planned terminal rows. It did not complete 72 model responses. Source and request settings were frozen and unchanged; no extra probe, retry, format repair or replacement call was made. Main provided a separate 72-call/8 CNY finite gate, still under the original shared 10 CNY ledger.

The 72 planned rows contain **22 completed, 1 timeout and 49 not_called**. The timeout is row 23, `formal-C12-full_history-1`, call ID `520a5c50b9204960a3f9915952ed9b97`; HTTP response, reported model, delivery and usage remain null. Its original ledger reservation **0.162920 CNY** remains charged as an unknown maximum. No readonly reconciliation is needed for this run because run/raw/journal/completion/summary were recorded normally; readonly reconciliation cannot recover missing upstream response/usage or authorize resending this row.

| Quantity | A full history | B structured summary |
| --- | ---: | ---: |
| Planned | 36 | 36 |
| Confirmed paid attempts | 12 | 11 |
| Confirmed HTTP responses | 11 | 11 |
| Unknown HTTP response/delivery | 1 | 0 |
| Completed | 11 | 11 |
| Timeout | 1 | 0 |
| Not called | 24 | 25 |
| Legal completed actions | 11/11 | 11/11 |
| Correct completed actions | 8/11 | 9/11 |
| Correct per planned | 8/36 | 9/36 |
| Valid references | 11/11 | 11/11 |
| Sufficient code references | 11/11 | 11/11 |
| Known usage coverage | 11/36 | 11/36 |
| Ledger charged upper CNY | 0.18954440 | 0.04795256 |

There are 11 fully observed A/B pairs, all first-repeat C01–C11. These are a prefix of the frozen plan, not the full repeated sample. A's upper cost includes the timeout reservation, so the table does not establish that either context is cheaper. The 22 responses have known total prompt tokens **46,668**, completion tokens **3,394**, cached input tokens **23,424** and total tokens **50,062**. Known settled formal charge is **0.07457696 CNY**, unknown reservation upper is **0.16292000 CNY**, and formal charged upper sum is **0.23749696 CNY**.

Five completed outputs are legal but not accepted useful next actions: C05 A/B inspect `r1_door`, C06 A/B inspect the off `r2_monitor`, and C08 A inspect `r2_door`. These outcomes remain in raw.jsonl and were not replaced. Valid references and legal actions do not certify all narrative claims or progression quality.

Original shared ledger changed from 12 settled calls / **40,106,000 units** to 35 calls / **277,602,960 units**: 34 settled and 1 unknown. Remaining numerical allowance is **9,722,397,040 units** with frozen=false, but pending/unknown=1 blocks subsequent paid phases. This report does not settle the unknown call or grant a new allowance.

Model responses report `deepseek-flash` for the 22 completed rows; the timeout has no reported model. Nominal requested model is not proof of an underlying vendor architecture. Temperature/seed were unsent. Cache behavior, request order and the incomplete prefix constrain token/cost/latency comparisons. No B-superiority, general model intelligence, autonomous completion or human/teacher signoff claim is supported. T24 is incomplete due to the preserved timeout; T25 remains an owner draft until independent QA reviews the raw rows and Main records a scoped decision.

Evidence: raw SHA256 `74c20c72ac39e236bd3e5c48062f71e2c98a92b9368269c3e67a95c841db2e28`; summary raw SHA256 `83870be5f56b8f53a4c5be6a42fe049aee78c8159dac872f20ef04c74a4ecb11`; owner-formal-report raw SHA256 `031d6056afa4eafe6607e0f90ac5c30bbbf5284e876144091ff5bab17736c10d`. The owner report lists all 72 terminal states and original input/artifact hashes. This report is not independent QA.
