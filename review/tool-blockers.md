# Environment and remote blockers (2026-10-01)

- Project was empty; local initialization executed. Interpreter Python 3.14.7 at required path. No environment replaced.
- GitHub connector returned authenticated login `liy222`; `get_repo(liy222/campus-lab-escape)` returned HTTP 404. This proves unavailable to this connector, not universally absent.
- Exposed GitHub tools support files/commits/issues/PRs but no repository-creation operation. `gh` is absent. `git credential-manager github list` produced no account names. No GH_TOKEN/GITHUB_TOKEN environment variable was present (values never printed).
- Browser automation initialization failed before opening any page: windows sandbox failed, helper_unknown_error, setup refresh had errors. No UI validation has occurred.
- Ordinary terminal calls initially worked then failed with the same sandbox initialization failure. Approved elevated calls work. Git needs per-command `-c safe.directory=D:/深度能力` because initial .git was created by sandbox account. Do not add blanket global safe.directory.
- Request to user sent: create private empty remote and authenticate local Git if possible. Development continues. No repository URL or pushed SHA is claimed as a completed artifact.
- API model, credentials and paid budget requested. Mock only until configured and approved; no paid experiment will run automatically.

Correction after user question: GitHub Connector DOES expose create_blob/create_tree/create_commit/update_ref/create_file. Repository creation itself is absent. An accessible pre-created repository may be synchronized via Connector without local Git login; do not require local login as the only route.
