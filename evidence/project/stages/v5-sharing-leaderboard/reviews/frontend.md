# Frontend Owner development report

Recorded UTC: 2026-11-04T08:30:05.644763+00:00. Stage: v5-sharing-leaderboard; requested baseline 8bd46aa. Product source is SOURCE STOP. This is implementation/development evidence, not formal QA or human acceptance.

## Files

- `frontend/src/v5/client.ts`: SharingState, SharedLevel/SharedPage, Challenge, Leaderboard types and the five specified sharing API methods; Run optionally carries share_id/challenge_status. Existing authentication, CSRF, epoch and classic-adapter mechanics remain.
- `frontend/src/v5/Workspace.tsx`: mine/hall/joined navigation; author publish/unpublish/leaderboard/participation controls; shared metadata/joined-session launch; private run lookup explicitly excludes share_id. Publication uses the current revision and refreshes after stale/unknown outcomes without repeating the write. Key clears on sharing navigation, publication, starting a shared challenge and opening a leaderboard. Identity invalidation clears shared metadata and dialogs too.
- `frontend/src/v5/SharedLibrary.tsx` (new): authenticated hall/joined pagination, publication and author labels, separate shared progress, existing canceled-share continuation, refresh/error/empty states. Cards use the original level_id/created_at for the existing art selector.
- `frontend/src/v5/Leaderboard.tsx` (new): readable first-50 table, own best outside the top 50, rank/author/assistance/completion time; native dashboard dialog and reusable in-game panel. Duration is total minutes:two-digit seconds.three-digit milliseconds. Read failure stays inside the leaderboard, with refresh and an explicit note that it does not invalidate game completion.
- `frontend/src/v5/ChallengeBanner.tsx` (new): server-provided active/practice/finished status, author/assistance counters and a local live estimate from started_at. Official time comes only from returned elapsed_ms. No client score submission exists.
- `frontend/src/v5/GeneratedPlay.tsx`: sharing challenge banner, leaderboard drawer, shared victory official duration and own-best panel, practice explanation, restart entry and explicit restore/reset eligibility descriptions. Every action, archive, reset and AI response still applies the returned visible state through the existing revision/generation guard.
- `frontend/src/v5/visual/types.ts`: optional share_id and Challenge on GeneratedState; art selection and renderer behavior unchanged.
- `frontend/src/v5/v5.css`: desktop sharing cards/navigation, brass/paper leaderboard table/dialog and challenge banner using the existing visual palette. Existing hotspot active exclusion and 44px controls remain. No phone layout or new assets.

## Actual development commands

| Command / operation | Actual outcome |
|---|---|
| Read full docs/v5-sharing-leaderboard-plan.md and current frontend sources | exit 0 (b633c9, 501a95); initial combined source output was truncated after the full plan, then targeted reads completed the necessary components |
| Source edits through local Python / PowerShell | exit 0 (175c04, 46ca16, d3a855) |
| `frontend/node_modules/.bin/tsc.cmd --noEmit --project frontend/tsconfig.json` | first execution exit 2 (6f091f): new SharedLibrary description conditional lacked one closing brace |
| Narrow brace fix and same tsc command | exit 0 (2590e8) |
| Main-requested duration-format / visible terminology correction and small existing-palette style cleanup | exit 0 (164c4f); no further build or browser run |

The first development failure was not treated as a product or browser pass. No formal QA, frontend build, browser, backend request, player database read, model/provider invocation, paid call, dependency/art mutation, Git write or sub-agent creation was performed by this Frontend task. Backend confirmed the documented response wrappers/fields directly, including original publication time, elapsed_ms null during active/practice, and total_players counting distinct players with valid results.

## Actual visible entry points for independent QA

- Dashboard navigation: “我的关卡”, “共享大厅”, “我的参与”.
- Private cards: existing “开始探索/继续探索”; new “发布关卡/取消共享”, “查看排行榜”, “参加计时挑战”. Cards have data-level-id/data-published. A shared run must not turn the private card into “继续探索”.
- Shared cards: “开始计时挑战/继续计时挑战”, “查看排行榜”; data-share-id/data-level-id. Both list views have “上一页/下一页”, total/page labels and refresh.
- Dashboard board: native dialog named by the level title, “关闭排行榜”, inner section aria-label “通关排行榜”.
- Shared game: aria-label “计时挑战状态”, data-share-id/data-challenge-status. “排行榜”, “重开挑战” and existing “进度与存档”. A return from a shared game goes to “我的参与”.
- Shared victory: official duration from server plus “个人最佳成绩” section; leaderboard read failure is independent. In-game leaderboard is an existing-style drawer with “关闭面板”.
- Save/restore/reset retain the existing request paths and confirmation buttons, including “确认读取” and “确认重新开始”. Shared descriptions explain continued time, cross-round practice, assistance accumulation and preserved best scores before the user confirms.

## Remaining validation and limitations

Formal integration and desktop visual/keyboard checks are pending Main's GO and independent QA. The development typecheck does not prove publication access control, exact timing, transactional settlement, save eligibility, epoch isolation or actual layout. Test only the changed scope at 1280×720 and 1920×1080; do not describe reused historical tests as new executions.

The live display uses the local clock as an estimate; the leaderboard and official victory duration use server elapsed_ms. Native local-account sharing is not public hosting. Shared metadata passes the original level_id and creation time into the existing art pipeline so authors and players select the same eligible artwork. No real paid generation or companion quality was exercised.

User/human and peer acceptance have not occurred in this task. Main owns the final build/independent QA, effect entry, actual screenshots and invitation for the user to inspect the complete phase.
