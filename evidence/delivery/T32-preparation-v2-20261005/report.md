# T32 Main-directed byte materialization revision — 2026-10-05

Status: helper change and isolated checks PASS; committed source reproduction NOT RUN. Main reported its first package generator exit 1 because `.env.example` contained mixed CRLF/LF; Delivery did not read that file or alter the failed package. Prior six preparation checks and evidence remain intact.

Changed owned source: `scripts/reproduce.py`. Added Main's explicit `main_pinned_line_endings` mode with `crlf_newline_indices`: zero-based LF occurrences in canonical UTF-8 bytes, strictly a sorted unique list of non-boolean integers within range. The mode strictly decodes UTF-8, replaces CRLF with LF, then inserts CR only at the Main-pinned positions. BOM, other bytes, lone CRs and EOF are preserved. The reconstructed runtime SHA256 must equal Main's recorded raw SHA256. Materialization evidence retains those indices. Existing raw equality and all-CRLF modes remain available. The target does not choose the pin file, pin hash or policy; Main supplies them explicitly.

Actual command: `C:\Users\liyh\.conda\envs\1\python.exe -B -c <inline isolated synthetic mixed-line-ending probe>` from `D:\深度能力`; exit **0**. `checks.json` records eight grouped checks: AST parsing; exact mixed CRLF/LF with BOM/no-newline EOF; nine invalid index shapes/types/orders/ranges; wrong runtime hash rejection; canonical CRLF input reconstruction; invalid UTF-8 rejection; trailing-newline/zero-newline preservation; legacy-mode retention. Synthetic ZIP/text assets were created only in this new evidence directory. No original environment, configuration, DB, ledger, Git, Provider or paid execution was accessed or changed.

Source raw SHA256 after the revision: `7dc71165e3d42479884f8c821093c6561e98c240766b03e4a0e69454ea9ec0e9`.

Limitation: these are isolated helper checks, not a T32 candidate/build/pytest/service/evaluator verdict. Source STOP: waiting for Main to commit the helper, regenerate the pinned committed package, approve the new clean directory and send exact GO before formal execution.
