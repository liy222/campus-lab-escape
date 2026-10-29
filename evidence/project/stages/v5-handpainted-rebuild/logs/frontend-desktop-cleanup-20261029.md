# Frontend Owner · desktop-only source cleanup

Recorded UTC: 2026-10-29T05:24:35.237964+00:00. This is an implementation note, not independent QA or human acceptance.

## Actual changes

- `frontend/src/style.css`: removed 12 phone-specific max-width 760/480, portrait and short-landscape media blocks. Promoted the 2 existing desktop-only CRT sizing/powerbox-position rules to normal rules. Removed the short HUD label style and phone-specific comments. Kept the existing 1450/1120 desktop rules, reduced-motion, button sizing and shared layouts.
- `frontend/src/components/RoomChrome.tsx`: removed `useCompactStage` and the phone-only short assistant label.
- `frontend/src/components/Room2.tsx`: uses the existing desktop CRT login form only.
- `frontend/src/App.tsx`: tracks standard window dimensions/resizing; removed visualViewport following and numeric virtual-keyboard hint. Numeric validation and API actions stay in place.
- `frontend/src/components/Room1.tsx`, `frontend/src/Assistant.tsx`: removed phone keyboard hints (`inputMode`, `autoCapitalize`). Input fields, credential clearing and validation remain.
- `frontend/src/game/Room2Scene.ts`, `frontend/src/game/Room3Scene.ts`: removed the small-canvas camera magnification/translation branch, using the same coordinates as the previous desktop branch. Shared ResizeObserver, 44px hit-area scaling, pointer/click and keyboard operation remain.
- `frontend/index.html`: removed device-width viewport configuration.
- `frontend/src/v5/GeneratedPlay.tsx`, `frontend/src/v5/v5.css`: instruction says clicking, and the 14px-rule comment describes desktop use. Earlier four UI fixes, hand-painted cover path, generic desktop 980px flow and reduced-motion remain.

## Actual development checks

- Targeted source inventory and final source review via `rg`/PowerShell/Python: executed. One initial inventory read used an incorrect `src/game/components/RoomChrome.tsx` path and exited 1; subsequent read used the real `src/components/RoomChrome.tsx` path and exited 0. No product behavior was inferred from that failed read.
- One typecheck: `frontend/node_modules/.bin/tsc.cmd --noEmit --project frontend/tsconfig.json`, actual exit 0 (tool output 79fb58).
- Final source inventory shows only desktop media rules (1450/1120 and V5 980) plus reduced-motion; no useCompactStage, portrait/landscape, mobile viewport/keyboard hints or phone-specific mode remains in current product sources. Generic pointer events and shared hit-area scaling intentionally remain.
- No browser, build, model/provider call, database operation, dependency removal, Git mutation or asset/manifest change was performed by this cleanup.

## Remaining checks and scope

Main will run one central build and independent desktop QA. Typecheck is not proof of classic/V5 route behavior or a human visual check. Current phase remains pending independent review and human review.

Historical evidence and tests were not edited. The still-executable `frontend/owner-evidence/v5-owner-smoke.mjs` contains historical 390x844/812x375 phone checks; QA/Main should remove phone execution from current entry points while retaining original run results/screenshots. This Owner did not modify that historical controller.
