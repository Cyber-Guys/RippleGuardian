# CLAUDE.md: shared agent policy for our IXH26 Track 2 repo

**Policy version: 1.0 (2026-11-20 20:00 CET).** This file is the single shared policy for **every** agent working in this repo: Claude Code sessions, subagents, and any other AI tool. Link it for non-Claude tools: `ln -s CLAUDE.md AGENTS.md`.
Every agent follows it. If it conflicts with a task file or with an agent's own judgment, **this file wins**. Only an explicit instruction from one of our humans overrides it, and that override applies only to that human's task.

---

## 0. Contest facts (source: decifris.it/ixh26 + on-site Welcome Slides)

- **Event:** IXH26, Bari. Coding started **Fri 20 Nov 12:00 CET**. **Hard deadline: Sat 21 Nov 12:00 CET** for project + pitch submission on the hackathon app (hackathons.xrpl-commons.org).
- **Track 2, XRPL applications:** the project *must involve the XRP Ledger*, through integrations, apps, DeFi or smart contracts. Creative use of XRPL is "highly encouraged". One project per team, one track.
- **Judging:** **Innovation**, **Execution** (technical depth, solid engineering), **Impact** (real value to a community or industry), **Pitch** (clear, convincing demo; a live demo is encouraged).
- **Rules that bind our code:**
  1. **New work only.** Everything is built during the hackathon. Anything done earlier **must be declared** in the submission.
  2. **Third-party software or assets** are allowed only if licensed, and **must be declared** in the submission.
  3. **All code must be in a version-controlled repo that judges can access at submission time.**
  4. **Disqualification for:** IP or copyright violations; offensive or harmful content; cheating, *including tampering with other teams' projects*; disrespectful behaviour.
- **Unresolved discrepancies, ask the organisers and record the answer in `docs/CHALLENGE.md`:**
  - Pitch length: the website says 5 min + 2 min Q&A; the slides say 3 + 2. Prepare a **3-minute** pitch that can stretch to 5.
  - The website says Track 2's exact challenge is "announced on-site"; the slides say "no fixed theme, open track". **`docs/CHALLENGE.md` holds the official wording.** Re-read it before any scope decision.
- **Current direction:** a federated learning project with XRPL as membership registry, audit trail and payout layer. See `brainstorming/ixh26/track2-fl-paths.md`. The binding decision is recorded as D-001 in `docs/DECISIONS.md`.

---

## 1. The Agent Compact (non-negotiable)

Every agent follows these. If a rule blocks you, **stop and ask your human**; never work around it.

1. **Work only on a claimed task** (`tasks/T-*.md`) with you as owner, and **only inside its `scope`** (§2).
2. **Never read, print, log, paste or commit secrets.** That covers seeds, private keys, `.env*` and API tokens (§6).
3. **Testnet by default; never mainnet.** Devnet only for features marked "devnet extra".
4. **Never fabricate ledger evidence.** No hard-coded or fake tx hashes or balances. Anything simulated is labelled `SIMULATED` in both the code and the UI.
5. **Never claim what isn't built.** README, slides and pitch claims each need evidence: a test, a tx hash or a demo step (§8).
6. **`main` is always demo-able.** Merge only after `make check` passes, plus `make smoke` if the demo path is touched (§3).
7. **Python first.** Use JS, TS or Rust only under the exception in §4.
8. **Declare everything reused.** Every new dependency, copied snippet or asset gets an entry in `THIRD_PARTY.md` in the same commit (§7).
9. **Never interact with other teams.** That means their repos, wallets, accounts and platform entries. Use the hackathon platform read-only (§7).
10. **Outward-facing or irreversible actions are for humans only.** These include making the repo public, submitting on the platform, posting or emailing, force-pushing `main`, and rewriting shared history (§3).
11. **Don't change shared contracts silently.** `contracts.py`, `config.py`, `pyproject.toml`/`uv.lock`, `Makefile` and this file change only through their own task (§2).
12. **Leave a handoff.** Before stopping for any reason, append status, the next step and any gotchas to the task's Log.
13. **Fail loudly.** No bare `except`, and no fallback that hides a failure as success.
14. **Prioritise the demo.** The demo and the judging criteria take precedence over completeness, generality or refactoring.

At the start of each session, state in one line: `Policy 1.0 acknowledged · task T-xxx · scope <paths>`.

---

## 2. Work model: Objectives → Tasks

We work toward **objectives**, not open-ended chats. Humans own objectives. Agents execute tasks.

- **Objective** (`tasks/O-<n>-<slug>.md`, human-owned): one outcome that a judge sees in the demo or the docs. It names the judging criterion it serves and lists its tasks.
- **Task** (`tasks/T-<nnn>-<slug>.md`): one agent-sized unit of work, about 30–120 minutes, with verifiable acceptance criteria and an explicit file scope.

### Task file template
```markdown
---
id: T-012
objective: O-2
status: todo            # todo | claimed | in-progress | review | done | blocked
owner: <human>/<agent-id>   # e.g. doliv/a1
branch: t/T-012-batch-settlement
depends_on: [T-003]
scope: [src/ixh26/ledger/batch.py, tests/ledger/test_batch.py]
contracts_used: [RoundSettlement]   # read-only unless the task is a contract task
policy: "1.0"
---
## Objective
One sentence describing the outcome, not the activity.
## Acceptance criteria
- [ ] Verifiable check 1 (test name / command / tx on Testnet)
## Out of scope
## Log   (append-only; "HH:MM agent: note")
## Evidence   (test names, tx hashes + explorer links, screenshot paths)
```

### Claiming protocol (lock-free, git-based)
1. Run `git pull --rebase` on `main`.
2. Pick a `todo` task. Its `depends_on` tasks must be `done`, and it must be assigned to your human (or your human told you to take it).
3. On `main`, set `status: claimed`, `owner` and `branch`. Commit as `chore(tasks): claim T-012` and push.
   - If the push is rejected, pull with rebase. If someone else claimed the task, pick another.
   - **Task files are the only files ever committed directly to `main`.**
4. Create your worktree and branch (§3) and set `status: in-progress`.

### Scope locks
- You may modify only the paths in your task's `scope`. The exceptions are appending to `THIRD_PARTY.md` and `artifacts/tx_log.jsonl`.
- Need another file?
  - If no in-progress task holds it, add it to your `scope` with a claim-commit on `main`.
  - If another task holds it, set `status: blocked`, explain why in the Log, and tell your human. **Never edit, fix, or revert another agent's in-progress work.**
- Shared contract files (`src/ixh26/contracts.py`, `config.py`, `pyproject.toml`, `uv.lock`, `Makefile`, `CLAUDE.md`) change only via a **dedicated, small task that is merged quickly**. Announce it to the humans.

### Definition of Done
- Every acceptance criterion is ticked, with evidence in the task file.
- `make check` passes. `make smoke` passes if the task touches the demo path.
- The branch is rebased on the latest `main`.
- The README claim→evidence table and `THIRD_PARTY.md` are updated if relevant.
- Status is set to `review`, and **your human approves the merge**. Then set status to `done`.

---

## 3. Git workflow

- **One task = one branch = one worktree.** Create it with `git worktree add ../wt-T-012 -b t/T-012-<slug> main`. Parallel agents never share a working directory.
- **Commits:** keep them small and frequent. A visible incremental history supports the "new work only" rule.
  - Format: `<type>(<area>): <summary> [T-012]`.
  - Types: `feat`, `fix`, `test`, `docs`, `chore`, `refactor`, `policy`.
  - Keep the tool's default AI co-author trailer (it supports AI-use transparency).
- **Sync:** rebase your branch on `main` before asking to merge.
- **Merging:**
  - Squash or fast-forward into `main`, only after checks pass and your human says OK.
  - Never force-push `main`. Force-push only your own task branch.
- **Pushing:** agents may push their own `t/*` branches.
- **Reverting** someone else's commit on `main` needs a human OK, and must be done with `git revert`, never a history rewrite.
- **Never commit:**
  - `.env*` files, other than `.env.example`
  - `data/` (datasets are fetched by script)
  - model binaries over 5 MB
  - notebooks with output cells
  - IDE or OS junk

### Timeline gates (Sat 21 Nov, CET)
| Time | Gate |
|---|---|
| Fri 23:00 | Skeleton, contracts, `make check`/`smoke` and the CI script are on `main` (T-000) |
| 01:00 | First end-to-end happy path on `main` |
| 05:00 | From now on, every merge must keep `make demo` working |
| **06:00** | **FEATURE FREEZE**: only fixes, tests, docs and pitch work after this |
| 09:00 | Backup demo video recorded (Testnet or Wi-Fi can fail) |
| **10:30** | **MERGE FREEZE**: only `README.md`, `docs/SUBMISSION.md` and slides change |
| 11:30 | A human makes the repo accessible to judges and submits on the platform |
| **12:00** | Hard deadline. Nothing pushed after this counts |

---

## 4. Python stack & code standards

- **Language:**
  - Python 3.12 for everything: backend, ML, XRPL, CLI, and the dashboard (Streamlit by default).
  - **Exception for JS/TS/Rust:** allowed only if no viable Python path exists. Examples: browser-side wallet signing, xrpl.js-only experimental features, Smart-Escrow WASM in Rust.
  - The exception needs a merged `docs/DECISIONS.md` entry *before* the work starts. The code is then isolated in `web/` or `wasm/`, with its own README and `make` target.
- **Tooling:**
  - **uv** for the environment and dependencies (`uv sync`, `uv add <pkg>`).
  - **ruff** for linting and formatting (line length 100).
  - **pytest** for tests.
- **Make targets** (created by T-000):
  - `make setup`
  - `make check`: ruff check, ruff format --check, offline tests and the secret scan
  - `make test-network`: tests marked `@pytest.mark.network`, run against Testnet
  - `make smoke`: a fast, headless run of the demo path
  - `make demo`
- **Style:**
  - Type hints on all public functions.
  - Shared data types are `@dataclass(frozen=True)` in `contracts.py`; use pydantic only at I/O boundaries.
  - Use `logging`, not `print`, except for CLI output.
  - Small pure functions; no global mutable state.
- **Module boundaries** (keep them to avoid agent collisions):
  - `core/` (domain/ML logic) **never imports** `ledger/` or `app/`.
  - `ledger/` (all XRPL code) never imports `core/` or `app/`.
  - `flows/` composes `core` with `ledger`.
  - `app/` calls only `flows/` and never signs anything.
  - **Only `ledger/` imports `xrpl`.** Only `config.py` reads environment variables.
- **Tests:**
  - Every task adds at least one test that proves its acceptance criterion.
  - Offline tests never hit the network: inject a fake client.
  - Fix random seeds through `config.DEMO_SEED` so the demo is reproducible.
- **Dependencies:**
  - Prefer packages with ready wheels for Python 3.12.
  - Add each dependency in its own commit, together with its `THIRD_PARTY.md` entry.
  - Heavy or risky packages (torch, openfhe, anything compiled from source) need a DECISIONS entry first.
  - On a `uv.lock` conflict, take `main`'s version and re-run `uv add`.

---

## 5. XRPL rules

- **SDK:** `xrpl-py >= 5.1` (required for Batch signing). One client module, `ledger/client.py`. **Every submission goes through a single helper** that:
  1. autofills the transaction and sets `SourceTag = config.SOURCE_TAG`. That is the tag the hackathon platform assigns our project; if there is none, use the team constant.
  2. adds a Memo with the app id and the purpose. **Memos hold hashes or IDs only, never data, model weights or personal data.**
  3. submits with `submit_and_wait` and **requires `tesSUCCESS` in validated metadata**; anything else raises an error.
  4. appends `{time, network, tx_type, hash, purpose, explorer_url}` to `artifacts/tx_log.jsonl`. That log is our evidence trail.
- **Networks:**
  - `XRPL_NETWORK=testnet` is the default.
  - Devnet or WASM devnet only for clearly labelled extras. Check amendment availability with the `feature` RPC before relying on one.
  - **Mainnet is forbidden.**
- **Amounts:** integer drops or `Decimal` only, never `float`. Convert with `xrpl.utils.xrp_to_drops`/`drops_to_xrp`. For received payments, read `delivered_amount`, never `Amount`.
- **Setup scripts** (`scripts/`) must be **idempotent**: query the ledger first, then create only what is missing. Remember the owner reserve (0.2 XRP per object).
- **No personal or sensitive data on-ledger, ever.** The ledger is public and permanent.
- **Resilience:** retry public endpoints with backoff. Keep a local-sandbox fallback documented in the README.

---

## 6. Secrets & safety

- Seeds live only in `.env`, which is git-ignored, and are loaded only by `config.py`. Wallets come from `scripts/new_wallets.py` (Testnet faucet), which writes straight to `.env`.
- **Agents must not open, `cat`, `grep`, `echo` or paste `.env*` or any seed.** Keep them out of prompts, task files, logs, screenshots and commits. To check that a variable is set, test for its presence only.
- Signing happens **server-side only**. The dashboard or browser never receives a seed.
- `make check` runs a secret scan that fails on XRPL seed patterns (`\bs[1-9A-HJ-NP-Za-km-z]{28}\b`, `sEd…`) and on private-key headers.
- **If a secret leaks:** stop, tell your human, and replace the wallet with a new faucet wallet. Don't rewrite shared history yourself.
- No destructive commands outside your worktree, such as `rm -rf`, `git clean -fdx` or `git reset --hard` on shared branches.

---

## 7. Contest compliance

- **Prior work:** anything not written during the hackathon goes in the "Prior work" section of `docs/SUBMISSION.md`. That includes templates, starter kits and snippets from earlier projects. The research in `brainstorming/` is reference material only; don't put it in `src/`.
- **Third-party material:** each library, copied snippet (more than 5 lines), dataset, image, font or icon needs a `THIRD_PARTY.md` row: name, URL, licence and where it is used. Unknown or incompatible licence means **don't use it**.
- **Other teams' and previous-edition code:** public IXH25 repos are for reading and inspiration only. Copying from them requires a compatible licence, attribution, and your human's OK. Never access, fork-modify, message or touch other teams' repos, wallets or platform entries.
- **Hackathon platform** (MCP `hackathon` server or the website): agents may use **read-only** calls only (get/list). Joining or creating teams, editing projects and submitting are human actions.
- **AI disclosure:** `docs/SUBMISSION.md` lists the AI tools we used and what for.
- **Content:** nothing offensive or discriminatory in code, data, UI copy or slides. Use public, licensed datasets only, never real personal data.

---

## 8. Evidence, docs & honesty

- **`README.md`** contains, in order:
  1. one-paragraph pitch
  2. architecture diagram
  3. quickstart (`make setup && make demo`)
  4. **claim → evidence table**, where each claim links to a tx hash, test or demo step
  5. what is SIMULATED
  6. roadmap
  7. team
- **`docs/PROTOCOL.md`:** a 1–2 page protocol and threat model with honest limitations. A crypto judge is on the jury.
- **`docs/DECISIONS.md`:** append-only, one entry per decision (`D-00n · date · decision · why · alternatives`).
- **`docs/SUBMISSION.md`:** submission text, track, links (repo, video, slides), prior work, third-party summary and AI disclosure.
- **Hard rules:**
  - Numbers and units in UI and slides must be consistent and come from real runs.
  - Anything not built goes under "Roadmap".
  - Mocks carry a `# SIMULATED:` code comment and a visible UI label.

---

## 9. Subagents

- When a parent spawns a subagent, it passes on the **task id, the objective, the exact write scope and the policy version**. Subagents inherit this whole file.
- **Writing subagents running in parallel** must each use their own worktree (`isolation: worktree`), or take provably disjoint file sets within the parent's scope.
- **Read-only subagents** (research, review, exploration) may read anything except secrets. They write only to the parent's task file or to `brainstorming/`.
- Subagents never push, merge, claim tasks or edit `tasks/` front-matter. Only the parent agent does, and the parent reviews every subagent diff before committing it.
- Maximum nesting depth is 2: agent → subagent, and no further.

---

## 10. Repository layout

```
CLAUDE.md  (AGENTS.md → symlink)   README.md   THIRD_PARTY.md
pyproject.toml  uv.lock  Makefile  .env.example  .gitignore
src/ixh26/
  config.py        # the ONLY env/secret reader; SOURCE_TAG, XRPL_NETWORK, DEMO_SEED
  contracts.py     # shared frozen dataclasses / Protocols between modules
  core/            # domain + ML logic (e.g. FL engine); no xrpl imports
  ledger/          # ALL XRPL code; client.py holds the single submit helper
  flows/           # orchestration: core + ledger → demo scenarios
  app/             # Streamlit dashboard; calls flows only, never signs
  cli.py           # entry points used by the Makefile
scripts/           # idempotent ops: new_wallets.py, bootstrap_ledger.py, fetch_data.py
tests/             # mirrors src/; @pytest.mark.network for Testnet tests
tasks/             # O-*.md objectives, T-*.md tasks (only files committed directly to main)
docs/              # CHALLENGE.md, DECISIONS.md, PROTOCOL.md, SUBMISSION.md
artifacts/         # tx_log.jsonl (Testnet hashes), screenshots/, demo video link
data/              # git-ignored; filled by scripts/fetch_data.py
brainstorming/     # research and IXH25 analysis; reference only
```

---

## 11. Changing this policy

- Only a human changes this file. Do it in a commit prefixed `policy:` that bumps the version line at the top, and announce it to the team.
- When an agent sees a new policy version after pulling, it re-reads this file. It then notes `policy X.Y acknowledged` in its task Log before continuing.
- If an agent thinks a rule is wrong, it **asks its human**. It does not deviate.
