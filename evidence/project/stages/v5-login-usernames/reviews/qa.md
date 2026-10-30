# V5 local login username picker: focused QA

**Status:** Focused API, contract, build, and isolated browser checks completed. Human review is still pending.

## API and contract checks

Final command:

```text
C:\Users\liyh\.conda\envs\1\python.exe -B -X utf8 -m pytest -q tests/v5/test_login_usernames.py tests/v5/test_auth.py::test_wrong_password_rate_and_cooldown tests/v5/test_auth.py::test_anonymous_csrf_expiry_missing_and_duplicates
```

With `PYTHONUTF8=1` and `PYTHONDONTWRITEBYTECODE=1`, the final run passed **5 tests**, exit 0, with one Starlette/httpx deprecation warning. It checked the empty anonymous list, normalized sorted names without user IDs or credential fields, authenticated CSRF/login response compatibility, separate passwords for two accounts, wrong-password 401 without an authenticated identity, cross-account session 404, the parsed schema build matching `api.schema.json`, and the 20-route surface. The two existing CSRF and rate-limit nodes were included.

- Final log: [pytest.log](../automated/api-20261030T114139634Z/pytest.log)
- Exit: [exit-code.txt](../automated/api-20261030T114139634Z/exit-code.txt)
- The initial API run exited 1 because the new synthetic login helper did not attach the returned auth-context before creating a classic session. That test-helper issue was corrected; the initial record remains at [first API attempt](../automated/api-20261030T114113644Z/pytest.log).

## Build

One V5 frontend build ran with `VITE_GAMEPLAY_VERSION=v5` and `CAMPUS_BACKEND_URL=http://127.0.0.1:8001`:

```text
npm --prefix frontend run build
```

Exit 0; output is saved at [npm-build.log](../automated/build-20261030T114154456Z/npm-build.log). Vite emitted its existing warning that the Phaser chunk exceeds 500 kB after minification.

## Browser checks

The isolated browser used the existing Synthetic fixture, owned temporary database, and port 8002. No generation request or external request occurred; the owned server stopped after each run.

- The first browser attempt exited 1 because the checker used an exact accessible-label query that did not match the select’s dynamic accessible name. It is preserved at [first browser attempt](../automated/browser-2026-10-30T11-42-20-602Z-bcf60287/).
- The full flow then passed **13 checks**, exit 0: empty-list guidance and disabled login; registration for `synth_alpha` and `synth_beta`; sorted list and default choice; password clearing on account selection and after wrong-password 401; list retention through auth invalidation and successful correct-password login; no Synthetic password in localStorage; zero generation and external requests. Its two auth-only desktop captures are [1280×720](../automated/browser-2026-10-30T11-43-52-442Z-a57b28cc/login-names-1280x720.png) and [1920×1080](../automated/browser-2026-10-30T11-43-52-442Z-a57b28cc/login-names-1920x1080.png). Full result: [result.json](../automated/browser-2026-10-30T11-43-52-442Z-a57b28cc/result.json).
- A later checklist review found the full flow did not explicitly verify clearing on login/register mode toggle. A narrow branch reused the same owned TEMP fixture and checked both directions, retained list/default selection, and zero auth/generation/external requests. **4 checks passed**, exit 0: [mode-switch result](../automated/browser-2026-10-30T11-45-37-369Z-3629c535/result.json). No registration or login request was made in that narrow follow-up.

The browser runner’s select locator was narrowed to the auth panel’s actual select. The initial browser failure is retained; the later full run and mode-only run are separate evidence, not a single attempt.

## Scope and limits

All accounts and passwords used in browser/API tests were Synthetic test values in an isolated temporary database. Password values are not stored in result records or screenshots. No player database, generation, real model, or paid call was used. These checks cover authentication and UI handling only; they do not exercise generated levels, saves, or mobile layouts. The screenshots are automated QA captures, not human acceptance. Please inspect the desktop login screen and confirm the local username list is useful for your account-security testing.
