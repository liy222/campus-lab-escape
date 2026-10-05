# T23 measured pilot cost and T24 planning estimate

Source: six real rows in this directory. Raw summary SHA256: `a6ee9d903668c0285d30619c0b43d93f2ca7e231560118664ebfb2e0a38fa79a`. The six requests reported `deepseek-flash`, HTTP 200, known usage and settled original shared-ledger reservations. No retries or additional probes were used.

| Quantity | Full history A | Structured summary B | Total |
| --- | ---: | ---: | ---: |
| Prompt tokens | 7,608 | 6,330 | 13,938 |
| Completion tokens | 458 | 435 | 893 |
| Cache hit input tokens | 2,048 | 640 | 2,688 |
| Settled ledger charge, CNY | 0.01486592 | 0.01488560 | 0.02975152 |
| Completed / planned | 3/3 | 3/3 | 6/6 |
| Correct / completed | 2/3 | 2/3 | 4/6 |

Measured mean charge is 0.0049585867 CNY/request. Scaling this six-row mean to 72 requests gives **0.35701824 CNY**, an estimate rather than a guaranteed bound. Repricing all pilot input tokens at cache-miss 2 CNY/million and outputs at 8 CNY/million gives 0.03502000 CNY for the pilot, or **0.42024000 CNY** for 72 requests at the same token distribution. This does not assume future cache hits. Both estimates use only three checkpoints and one repeat per variant; the remaining nine checkpoints and formal output lengths can differ.

The frozen 72-row formal plan has a sum of pre-reservation bounds of **7.757232 CNY** and maximum single-request reservation **0.162920 CNY**. The sum is an admission upper bound, not measured cost. Settled calls release unused reservation, but a phase gate must leave enough headroom for the next whole reservation. Main must choose a separate finite formal phase cap after review. The current original shared ledger remaining is **9.959894 CNY**; this is shared across all phases, and does not create another allowance.

C06 A and B both proposed `inspect(r2_monitor)` while power was off; the frozen acceptable next actions are `take(fuse)` or `inspect(r2_drawer)`. The model output was legal and its references existed, but it was judged `LEGAL_BUT_NOT_USEFUL_NEXT_ACTION`. These two results are retained. This pilot does not establish superiority, free-text factual accuracy, autonomous completion, or general model performance.

The T24 frozen settings remain unchanged: 12 checkpoints × 2 variants × 3 repeats, 72 rows, balanced order; one request per row; 1000 maximum output tokens, 20-second timeout, no temperature/seed field, no retry and no suggestion execution. Unknown usage, timeout or Provider/model abnormality stops the phase; remaining rows stay not_called. T24 was not executed in this report and requires a new Main GO bound to this pilot summary and formal plan hash `bb9d603d75d16dcf9473e534a38687ce7a90d548035a6ad76ad682a16b459539`.
