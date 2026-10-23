# P2: anonymous CSRF rotation breaks simultaneous tabs

Actual browser evidence: `evidence/upgrade/v5.0/qa/browser-takefix/20261023T062042.556640Z-9c899a5f/`. The generated route, take fix, keyboard/background isolation, R2/R3 viewport checks, victory, three archives, delete/cancel, restore, reload, owned backend restart and relogin completed. The final cross-tab B registration failed with the visible error 请刷新登录页面后重试. The run exited 1 with unchanged source, no page errors or missing assets.

Independent minimal protocol reproduction is `evidence/upgrade/v5.0/qa/anonymous-csrf-independent.json` (exit 0 means the reported counterexample reproduced, not product acceptance). With an isolated TEMP database and one shared cookie jar, GET `/auth/csrf` twice rotates both the anonymous nonce cookie and token. Submitting the earlier page's token then returns 403/CSRF_FAILED; the latest token registers successfully with 201. No token/cookie values were recorded.

Every anonymous csrf GET currently creates a new random nonce/token and overwrites the host-only shared cookie. In the actual logout BroadcastChannel flow, both tabs legitimately refresh anonymous identity, so the second GET invalidates the first page's still-visible login/register form. The request is rejected safely, but ordinary multi-tab account switching is broken.

Expected: reuse a valid anonymous context for its stated ten-minute lifetime, while retaining strict Origin, duplicate-header rejection, expiry and login identity rotation. Do not fix the QA scenario by silently refreshing and resubmitting user credentials or API Keys. A narrow auth protocol regression and only the unfinished cross-tab browser scope are needed after source STOP.
