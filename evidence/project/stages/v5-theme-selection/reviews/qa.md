# V5 theme selection QA

**Status:** Technical checks completed for the scoped selector change. Human review is pending; this report does not record acceptance.

## Executed scope

- One V5 frontend build completed with exit code 0. The actual command was `npm --prefix frontend run build` with `VITE_GAMEPLAY_VERSION=v5` and `CAMPUS_BACKEND_URL=http://127.0.0.1:8001`. `frontend/package.json` exposes `build` (not `build:v5`). Build log and result: [build output](../automated/build-2026-10-30T07-13-55-522Z-d58c44e2/).
- The first full browser attempt exited 1 before checks because the label locator matched two controls. Preserved at [first browser result](../automated/qa-2026-10-30T07-14-21-763Z-e5eec62f/).
- The second full browser attempt exited 1 with 15 of 16 recorded checks passing. It verified the default and five exact options, no freeform textarea/count, pointer-driven coverage for each theme, a single Synthetic submission with `化学实验室`, two rooms and normal difficulty, cleared temporary key input, no key in the request JSON, public job readiness and list refresh, matching loaded scene at 1280×720 and 1920×1080, zero external requests, and owned server cleanup. The only failed assertion was keyboard selection after cycling through the options in that same native select. Preserved at [second browser result and screenshots](../automated/qa-2026-10-30T07-15-21-008Z-1be7124e/).
- A fresh isolated keyboard-only follow-up exited 0: starting from the default option, mouse focus plus Home/ArrowDown/Enter selected `图书馆档案`, and the matching coverage appeared. It submitted zero generation requests, made zero external requests, and stopped its owned server. Result: [keyboard-only result](../automated/qa-2026-10-30T07-17-09-784Z-903ba870/).

The follow-up isolates the control from prior selection history; it does not erase or replace the earlier failure. The overall evidence is therefore a failed full browser attempt followed by a successful narrow keyboard check, not one all-green full browser run.

## Commands and evidence

- Build: `npm --prefix frontend run build` with the V5 environment values above; exit 0. Log: `evidence/project/stages/v5-theme-selection/automated/build-2026-10-30T07-13-55-522Z-d58c44e2/npm-build.log`.
- Full browser: `node tests/v5/run_theme_selection_browser.mjs`; two attempts, both exit 1 for the distinct checker issues described above.
- Follow-up: `node tests/v5/run_theme_selection_browser.mjs --keyboard-only`; exit 0.
- Browser output directories are under `evidence/project/stages/v5-theme-selection/automated/`. The full run’s 1280×720 form/scene screenshots and 1920×1080 scene screenshot are in the second run directory.
- `node --check tests/v5/run_theme_selection_browser.mjs` exited 0 before execution. The existing variation runner was adapted from freeform `.fill()` to `.selectOption('图书馆档案')` for the new select; its historical suite was not rerun.
- After this report’s execution, the variation runner’s theme locator was narrowed from a broad label query to `getByRole('combobox', {name: /校园主题/})` to avoid matching the section’s accessible name as well. This is a static compatibility edit only; the variation browser suite, theme-selection browser, and build were not rerun for it.

## Limits and safety

The browser checks used a temporary local Synthetic fixture and owned port 8002. No player database was accessed; no real model or paid call was made. The one full-run dummy key was not included in the submitted JSON and the UI field cleared; only safe field-presence/boolean evidence was retained. No full gameplay, save/load, or five separate generation runs were performed. The observed Synthetic scene confirms the selected theme’s UI path only, not generated-content quality. The large Phaser bundle warning emitted by the build remains an existing build-size observation.

Please review the five-option selector and the attached desktop screenshots in the app. Human review has not yet occurred.
