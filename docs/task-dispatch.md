# Dispatch ledger

All paths are relative to D:\深度能力. Every task reads AGENTS.md and accepted docs/execution-plan.md, uses contract v1 when frozen, returns changed files / commands / actual exit codes / evidence / limitations. Main alone commits. No child spawns permitted by these task cards.

| Task | Agent / requested actual tool config | Dependencies | Allowed writes | Acceptance |
|---|---|---|---|---|
| T02 | spec_content / gpt-6.1-sol high | T01 registered | docs/SPEC.md, docs/level_design.md, contracts/ | Exact shared schemas, strict tools, visible projection, positive route + negative cases, R/A map; main reviews freeze |
| T03 | delivery_docs / gpt-6.1-sol high | T01 | scripts/, README.md, release/, .gitignore, .env.example; temporary backend entry/deps and frontend scaffold | Required Python environment, actual /api/health and front-page HTTP smoke, build, dependency lock, dev/check/reset entrances |
| T04 | ai_integration / gpt-6.1-sol high | T01; real config absent | backend/app/ai/, docs/provider.md, evidence/provider/ | Isolated normal and adverse mock probes actually run; real call status explicitly unverified |

T03 temporary paths transfer only after explicit owner handoff. T05/T06 backend and T07 frontend wait for contract freeze and runnable scaffold. T08 independent QA waits for stable implementation. Formal UI/browser acceptance stays open while browser tool is unavailable.
