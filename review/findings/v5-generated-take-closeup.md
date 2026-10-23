# P1: taking a generated item leaves invisible closeup state blocking the scene

Independent production browser QA reproduced this on `v5.0-browserfix2-2b40ecf294d07e16`. Evidence: `evidence/upgrade/v5.0/qa/browser-remaining2/20261023T061406.194090Z-cccf7e62/` (`browser.json`, `failure.png`, `summary.json`). Exit 1; source remained unchanged. The generator is an explicitly injected offline three-room hard fixture, while auth, API, Store and UI are actual production paths. No paid call occurred.

Reproduction: generate the isolated three-room hard level, start it, open the key item and click 拿取. The API succeeds, the item moves to inventory, and its closeup disappears. Next tap 查看数据纸 remains disabled for the full 30-second timeout. The actual screenshot shows no visible closeup or close button, but every scene hotspot and inventory control is disabled.

In `frontend/src/v5/GeneratedPlay.tsx`, `view` remains the taken object's ID. The updated state's objects no longer contain it, so `object` is undefined and no overlay is rendered. `GeneratedScene` and inventory still receive `!!view` as a disabling condition. `apply` clears view for room/generation changes, but not when a same-room updated state removes the viewed object.

Expected: a successfully taken object may disappear, while the closeup state is cleared and ordinary scene input immediately works. Clear only the invalid viewed-object state after applying the authoritative state; preserve valid closeups, selected-item behavior, rules and persistence. Do not repair this by pressing Escape in the QA route, since ordinary input after taking must work without that workaround.

Already verified in this epoch before the defect: successful generation/status/key clearing, early UI archive, generated room G1 44px controls and no horizontal overflow at 1280x720/390x844/812x375. Subsequent generated circuit/sequence/remaining rooms/selected restore/restart/cross-identity checks have not yet executed. Earlier classic three-viewport evidence is retained separately. The offline gate remains blocked pending repair and affected build/browser verification.
