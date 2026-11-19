# CLAUDE.md — Team sync file for `cel-mai-tare-hack`

> **Audience:** every Claude Code agent working on this repo, on any teammate's machine.
> Claude Code loads this file automatically at session start. It is the **single source of truth**
> for what we're building, who owns what, and how agents avoid stepping on each other.
>
> **All code in this repo is written by Claude agents.** Humans steer; agents implement.
> Several agents run in parallel on different machines, so coordination happens **only through git**
> (this file, commits, branches, PRs). Assume you cannot see what other agents are doing unless it's pushed.

---

## 0. Before you do anything (every session)

1. `git fetch origin && git pull --rebase origin main` — get the latest state.
2. Re-read **§2 Ownership**, **§4 Contracts** and **§6 Task board** below. They change often.
3. Confirm with your human which task (from §6) you're working on. If it isn't on the board, add it first.
4. Work on a branch (see §5), never directly on `main`.

---

## 1. Project

| Field | Value |
|---|---|
| Name | `cel-mai-tare-hack` |
| Repo | `git@github.com:TheodorMitrofan/cel-mai-tare-hack.git` |
| Event | Hackathon — deadline: **TODO (date + time + timezone)** |
| One-line pitch | **TODO** |
| Problem | **TODO** — who has the problem and why it matters |
| Solution / demo story | **TODO** — the 2-minute demo flow, step by step |
| Judging criteria | **TODO** |

### Scope
- **MVP (must work for the demo):** TODO
- **Nice to have (only after MVP works end-to-end):** TODO
- **Out of scope (do NOT build):** auth flows beyond what the demo needs, admin panels, i18n, exhaustive tests, perfect error handling.

### Tech stack
| Layer | Choice | Notes |
|---|---|---|
| Frontend | TODO | |
| Backend | TODO | |
| Database / storage | TODO | |
| AI / external APIs | TODO | |
| Hosting / deploy | TODO | |

Do not introduce a new framework, language or major dependency without adding it here and noting it in §7 Decisions.

---

## 2. Team & ownership

Each area has **one owner**. Only the owner's agent edits files in that area. If you need a change in
someone else's area, (a) change the contract in §4 via a small PR and tell the owner, or (b) ask the owner.

| Person | Area / role | Owns paths | Contact |
|---|---|---|---|
| Theodor | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO |
| TODO | TODO | TODO | TODO |

Shared files (anyone may edit, keep diffs small, pull right before editing): `CLAUDE.md`, `README.md`,
`.env.example`, `.gitignore`, root config files.

---

## 3. Repo layout & commands

```
TODO — fill in once scaffolded, e.g.
/frontend      UI
/backend       API server
/shared        types/schemas shared by frontend + backend (source of truth for §4)
/scripts       seed data, demo helpers
```

| Task | Command |
|---|---|
| Install | TODO |
| Run locally | TODO |
| Run tests | TODO |
| Lint / format | TODO |
| Seed demo data | TODO |
| Deploy | TODO |

Local ports: frontend `TODO`, backend `TODO`.

---

## 4. Contracts (the sync point between agents)

**Rule: define the contract here before implementing either side.** Frontend and backend agents build
against what's written here, not against what they guess the other side does. Changing a contract =
update this section in the same PR and notify the affected owner.

### 4.1 API endpoints
| Method | Path | Request body | Response | Owner | Status |
|---|---|---|---|---|---|
| TODO | TODO | TODO | TODO | TODO | planned |

### 4.2 Data models
```
TODO — e.g.
User   { id: string, name: string, createdAt: ISO string }
```

### 4.3 Environment variables
All env vars must be listed here **and** in `.env.example` (with dummy values). Never commit real secrets.

| Variable | Used by | Purpose |
|---|---|---|
| TODO | TODO | TODO |

---

## 5. Git workflow (parallel agents)

- **Branches:** `<person>/<short-task>` e.g. `theodor/login-page`. One branch per task from §6.
- **Never push to `main` directly.** Open a PR (`gh pr create`) or, if the team agrees to go fast,
  rebase on `main` and fast-forward merge — but always `git pull --rebase origin main` first.
- **Small, frequent commits and pushes.** Push at least every ~30–45 min so others see your work.
- **Rebase often** on `origin/main` to keep conflicts small. Resolve conflicts in your own area only;
  if a conflict touches someone else's area, stop and ask your human.
- **Commit messages:** `<area>: <what changed>` e.g. `backend: add /api/items endpoint`.
- **Don't commit:** `.env`, credentials, API keys, `node_modules`, build output, `.idea/`, `.DS_Store`.
- **`main` must always run.** Don't merge anything that breaks the run command in §3.

---

## 6. Task board

Status: `todo` · `doing` · `review` · `done` · `blocked`.
Rules: one row per task; only edit your own rows; when you pick a task set `doing` + your name and
**commit + push that change on its own immediately** so nobody else picks it up.

| # | Task | Area | Owner | Status | Branch / PR | Notes |
|---|---|---|---|---|---|---|
| 1 | Scaffold repo structure + fill §3 | shared | TODO | todo | | |
| 2 | Fill in §1 project definition | shared | Theodor | todo | | |
| 3 | Define first contracts in §4 | shared | TODO | todo | | |
| 4 | TODO | | | todo | | |

---

## 7. Decisions log

Append-only. Record anything another agent would otherwise get wrong or re-decide.

| When (UTC) | Decision | Why | By |
|---|---|---|---|
| 2026-11-19 | `CLAUDE.md` is the shared coordination file for all agents | Agents on different machines sync only through git | Theodor |

---

## 8. Coding conventions for agents

- **Demo first.** Prefer the simplest thing that works end-to-end. Hardcode / mock when it unblocks the demo, and mark it `// HACK:` with a one-line reason.
- **Stay in your lane.** Only touch files in your owned paths + the task you were given. No drive-by refactors of others' code.
- **Match existing style** in the file you're editing. Follow the stack's formatter/linter once configured (§3).
- **Shared types live in one place** (see §3 `/shared` or equivalent); don't duplicate model definitions.
- **No silent dependency additions** — new packages get a line in the PR description.
- **Keep it runnable:** after your change, the run command in §3 must still work. Say so explicitly in your PR/commit if you couldn't verify.
- **Leave a trail:** when you finish a task, update its row in §6 and add anything surprising to §7 or §9.

---

## 9. Known issues / gotchas

Things that cost someone time — write them down so the next agent doesn't repeat it.

- _(none yet)_

---

## 10. Demo checklist (final hour)

- [ ] `main` runs from a clean clone using only §3 commands
- [ ] Demo data seeded
- [ ] Deployed / reachable URL: TODO
- [ ] Demo script rehearsed (§1 demo story)
- [ ] Backup: screen recording of the working demo
- [ ] README.md has pitch, screenshots, how to run
