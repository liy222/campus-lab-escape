# Authenticated API 2.0.0

This is additive to the classic 1.4 contract. `routes.json` binds the 20 business routes; health and local static assets are separate. Mutation calls use same-origin JSON, the HttpOnly session cookie and CSRF/auth-context headers. Registration/login use the anonymous CSRF nonce, without an authenticated context. API Keys are ephemeral headers and never schema data.

`level-draft.schema.json` describes untrusted generator data. Schema validity alone does not admit a level: the compiler also checks references, semantics, dependency/room reachability, material sufficiency, layout and a bounded real-rule replay witness. Solutions and snapshot game fields are private.

`api.schema.json` reuses classic DTO definitions and adds strict generated projections. Dynamic sequence options and circuit rotations are public after inspection; compiled answers, witness, ownership, credentials and internal state are absent. The old anonymous routes are not mounted on the V5 host.

Rebuild explicitly with the configured Python and `contracts/v2/build_contracts.py`. Validate into a fresh evidence path with `contracts/v2/check_contracts.py --output <new-path>`. It checks schema reproducibility, exact router bindings, full Draft2020-12 fixtures and real-action projections. This development check is not independent API/browser/security QA.
