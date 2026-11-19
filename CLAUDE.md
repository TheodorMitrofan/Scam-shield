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
| Event | Scam Shield — R Systems side challenge @ EESTEC LC Bucharest. **Code freeze 2026-11-19 17:00 (Europe/Bucharest)** |
| One-line pitch | A calm friend that reads a message/conversation and tells a grandparent, in plain Romanian, "stop, this is a scam, do this instead". |
| Problem | Older, non-technical people in Romania get fake bank/courier/ANAF/"new number" messages. See `Scam_Shield_Public_Kit/Scam_Shield_Participant_Brief.docx`. |
| Solution / demo story | Load a folder of scenario JSONs → dashboard (verdict, type, score, first alert, red flags) → open a scenario rendered like the original app (chat / e-mail / call) with the alert message highlighted and a ≤3-sentence warning → paste a new message live. |
| Judging criteria | Test-set accuracy 30, ease of use 20, warning quality 25, pitch 15, innovation 10. **+10% bonus for tier 6 (local model + rules ensemble). Sending messages to a cloud LLM = disqualified.** |
| Full plan | **`PLAN.md`** (stages, tasks per person, timeline) |

### Scope
- **MVP (must work for the demo):** brief requirements M1–M9: open JSON/folder/paste, red flags per message, score+verdict, scam type, first alert, Romanian warning, friendly GUI, dashboard, scenario detail. Detector = local only.
- **Nice to have (only after MVP works end-to-end):** audio input (.wav/.mp4 → local transcription → `call_transcript`), voice location detection (open-source repo), CSV export, EN toggle, read-aloud.
- **Out of scope (do NOT build):** auth flows beyond what the demo needs, admin panels, i18n, exhaustive tests, perfect error handling.

### Tech stack
| Layer | Choice | Notes |
|---|---|---|
| Frontend | Angular 21 (standalone components, signals) | `frontend/` |
| Backend | FastAPI, Python 3.12 | `backend/` |
| Database / storage | PostgreSQL 16 (docker-compose); audio files on disk, metadata in DB | opt-in history only |
| AI / external APIs | **Local only.** Rules + fine-tuned Romanian BERT / XLM-R (`detector/`, `ml/`); faster-whisper for audio later | **NO cloud LLM APIs** |
| Hosting / deploy | Local laptops (demo runs on our machine) | |

Do not introduce a new framework, language or major dependency without adding it here and noting it in §7 Decisions.

---

## 2. Team & ownership

Each area has **one owner**. Only the owner's agent edits files in that area. If you need a change in
someone else's area, (a) change the contract in §4 via a small PR and tell the owner, or (b) ask the owner.

| Person | Area / role | Owns paths | Contact |
|---|---|---|---|
| Giulio | A — Frontend | `frontend/**` | |
| Theodor | B — Backend / DB / infra / audio pipeline | `backend/**`, `db/**`, `docker-compose.yml` | |
| Francesco | C — ML / detector / warnings text | `detector/**`, `ml/**`, `models/` | |

_(Assignment is a proposal from `PLAN.md` — swap names here if the team decides otherwise.)_
`Scam_Shield_Public_Kit/` is **read-only** official data.

Shared files (anyone may edit, keep diffs small, pull right before editing): `CLAUDE.md`, `README.md`,
`.env.example`, `.gitignore`, root config files.

---

## 3. Repo layout & commands

```
/frontend                Angular app                                (A)
/backend                 FastAPI app; imports `scam_detector`       (B)
/detector                Python package `scam_detector` (rules, model inference, scoring, warnings)  (C)
/ml                      training scripts + synthetic dataset       (C)
/models                  trained weights (gitignored)               (C)
/db                      SQL init / migrations                      (B)
/Scam_Shield_Public_Kit  official kit (read-only)
```
Backend ↔ detector boundary is ONLY `scam_detector.load()` and `scam_detector.analyze(scenario: dict) -> dict` (see §4.2).

| Task | Command |
|---|---|
| Install | `cd frontend && npm install` · backend/detector: TODO (B/C) |
| Run locally | `cd frontend && npm start` → http://localhost:4200 (demo shortcut: `/?load=validation&id=V04`) · backend: TODO (B) |
| Run tests | backend: `cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements.txt && .venv/bin/python -m pytest -q` · C: `pytest detector/` |
| Lint / format | TODO |
| Seed demo data | TODO |
| Deploy | TODO |

Local ports: frontend `4200`, backend `8000`, postgres `5432`.

---

## 4. Contracts (the sync point between agents)

**Rule: define the contract here before implementing either side.** Frontend and backend agents build
against what's written here, not against what they guess the other side does. Changing a contract =
update this section in the same PR and notify the affected owner.

### 4.1 API endpoints
All under `http://localhost:8000/api`. CORS allows `http://localhost:4200`.

| Method | Path | Request body | Response | Owner | Status |
|---|---|---|---|---|---|
| GET | `/health` | – | `{ status: "ok", model_loaded: bool }` | B | planned |
| GET | `/scenarios/validation` | – | `Scenario[]` (from `Scam_Shield_Public_Kit/validation_set`, sorted by id) | B | planned |
| POST | `/analyze` | `Scenario` | `AnalysisResult` | B (calls C) | planned |
| POST | `/analyze/batch` | `Scenario[]` | `AnalysisResult[]` sorted by `id` | B (calls C) | planned |
| POST | `/analyze/text` | `{ text: string, channel?: Channel }` | `AnalysisResult` (wrapped as 1-message scenario, id `"PASTE"`) | B | planned |
| POST | `/audio` (stage 4) | multipart `file` (.wav/.mp3/.mp4/.m4a), `save: bool` | `{ scenario: Scenario, result: AnalysisResult }` | B | later |
| GET | `/audio/{audio_id}` (stage 4) | – | audio bytes (for the player) | B | later |
| GET | `/history` | header `X-Client-Id` | `HistoryList` (no message text) | B | planned |
| GET | `/history/{id}` | header `X-Client-Id` | `HistoryItemDetail` | B | planned |
| DELETE | `/history/{id}` · `/history` | header `X-Client-Id` | `{ deleted: number }` (also deletes audio file) | B | planned |

**Saving = opt-in.** Any analyze/audio endpoint stores NOTHING by default. To save, the caller adds
query `?save=true&retention_hours=24` **and** header `X-Client-Id: <uuid>` (random UUID the browser keeps in
localStorage; no accounts). Then the response is `AnalyzeResponse { result, history_id }`; without consent it's
the plain `AnalysisResult`. Records expire (`expires_at`) and are deleted by a cleanup job.
DTO source of truth (Pydantic): `backend/app/schemas/` · DB tables: `backend/app/db/models.py`.

### 4.2 Data models
```ts
// Input — official format from the brief. Do not rename fields.
type Channel = "sms" | "whatsapp" | "email" | "chat" | "call_transcript";
Scenario {
  id: string;                         // "V04", "T05", "PASTE"
  channel: Channel;
  sender: { name: string | null; address: string | null; known_contact: boolean };
  messages: Message[];                // single message = thread of length 1
  audio?: AudioRef;                   // OUR extension, stage 4 only
}
Message { n: number; from: "sender" | "reader"; text: string;
          start_s?: number; end_s?: number }   // OUR extension: audio timestamps
AudioRef { audio_id: string; mime: string; duration_s: number;
           location?: { region: string; confidence: number } }

// Output — produced by scam_detector.analyze()
type Verdict = "SAFE" | "SUSPICIOUS" | "SCAM";
AnalysisResult {
  id: string;
  verdict: Verdict;
  scam_type: string;                  // one of official_catalog.json scam_types; "NONE" if SAFE
  risk_score: number;                 // 0..100 = sum of unique flag points, capped
  first_alert: number | null;         // message n; null if SAFE
  red_flags: string[];                // unique RF_* codes for the whole thread
  flags_by_message: { n: number; flags: string[]; score_after: number }[];  // score_after = cumulative score of prefix 1..n
  warning: { ro: string; en?: string };          // ≤3 short sentences, no links/numbers from the message
  evidence?: { n: number; flag: string; span: [number, number] }[];  // char offsets for "why" highlighting (optional)
}
// NOTE: the backend re-applies the official formula on every detector response:
// risk_score = Σ unique flag points (cap 100), verdict from bands, SAFE ⇒ scam_type "NONE" + first_alert null,
// non-SAFE with "NONE" ⇒ "OTHER". The detector only has to get flags / type / first_alert right.

// Opt-in history (only with consent)
HistoryItemSummary { id: uuid; created_at: ISO; expires_at: ISO; scenario_id: string; channel: Channel;
                     verdict: Verdict; scam_type: string; risk_score: number; first_alert: number | null }
HistoryItemDetail  extends HistoryItemSummary { scenario: Scenario; result: AnalysisResult; audio_id?: uuid }
HistoryList        { items: HistoryItemSummary[]; total: number }
```

### 4.3 Environment variables
All env vars must be listed here **and** in `.env.example` (with dummy values). Never commit real secrets.

| Variable | Used by | Purpose |
|---|---|---|
| `DATABASE_URL` | backend | `postgresql+psycopg://scam:scam@localhost:5432/scamshield` |
| `MODEL_DIR` | backend → detector | path to fine-tuned weights, default `models/scam-bert` |
| `STORAGE_DIR` | backend | where audio files are stored (stage 5), default `data/` |
| `CORS_ORIGINS` | backend | default `http://localhost:4200` |

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
| 1 | Plan (`PLAN.md`) + fill §1–§4 | shared | Giulio | review | giulio/plan-and-viewer | all 3 confirm §4 |
| 2 | Angular scaffold + scenario import + channel viewers (chat/email/call) | frontend | Giulio | review | giulio/plan-and-viewer | PLAN 1.2, 2.1–2.4 |
| 3 | FastAPI scaffold + docker-compose Postgres + `/health` | backend | Theodor | todo | | PLAN 1.3 |
| 4 | `/scenarios/validation`, `/analyze`, `/analyze/batch`, `/analyze/text` | backend | Theodor | todo | | PLAN 2.5, 2.6 |
| 5 | `scam_detector` package + rules + scoring + first_alert (11/11 on validation) | detector | Francesco | todo | | PLAN 1.4, 3.1–3.3, 3.11 |
| 6 | Warning templates RO/EN | detector | Francesco | todo | | PLAN 3.7 |
| 7 | Synthetic dataset + fine-tune + ensemble | ml | Francesco | todo | | PLAN 3.4–3.6 |
| 8 | Dashboard + scenario detail + paste screen | frontend | Giulio | todo | | PLAN 3.8–3.10 |
| 9 | Model kept in memory (lifespan) | backend | Theodor | todo | | PLAN 5.1–5.2 |
| 10 | Audio upload + transcription + storage (stage 4/5) | backend | Theodor | todo | | after MVP |
| 11 | Voice note view (stage 4) | frontend | Giulio | todo | | after MVP |
| 12 | Backend DTOs (Pydantic) + DB models + detector client adapter | backend | Giulio | review | giulio/backoffice | helping B; Theodor to confirm ownership |

---

## 7. Decisions log

Append-only. Record anything another agent would otherwise get wrong or re-decide.

| When (UTC) | Decision | Why | By |
|---|---|---|---|
| 2026-11-19 | `CLAUDE.md` is the shared coordination file for all agents | Agents on different machines sync only through git | Theodor |
| 2026-11-19 | Stack: Angular + FastAPI + PostgreSQL; detector is a separate Python package `scam_detector` | Keeps the 3 owners in separate folders | Giulio |
| 2026-11-19 | No cloud LLM anywhere in detection; training data generated locally (templates), validation set never used for training | Cloud LLM = disqualification; avoid leaking eval data | Giulio |
| 2026-11-19 | `risk_score`/verdict/first_alert computed deterministically from flags, not predicted by the model | Official formula; repeatability | Giulio |
| 2026-11-19 | Backend normalises detector output with the official formula instead of rejecting it; history is opt-in via `?save=true` + `X-Client-Id`, message text stored as JSONB only with consent | Demo must not 500 on a detector slip; privacy requirement | Giulio |
| 2026-11-19 | Audio files on disk (`STORAGE_DIR`), only metadata in Postgres; model loaded once in FastAPI lifespan, 1 uvicorn worker | Memory + privacy (deletable) | Giulio |

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
