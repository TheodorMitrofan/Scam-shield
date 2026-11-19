# PLAN — Scam Shield (`cel-mai-tare-hack`)

> Plan de lucru pentru 3 oameni (fiecare cu agentul lui Claude), gândit ca să **nu ne călcăm pe fișiere în git**.
> Sursa cerințelor: `Scam_Shield_Public_Kit/Scam_Shield_Participant_Brief.docx` + `hacaton_ai_scoring_ 1.docx`.
> Contractele (formatul JSON, API) sunt în `CLAUDE.md §4` — **acolo e sursa adevărului**, nu aici.

---

## 0. Ce construim, pe scurt

O aplicație care primește **scenarii JSON** (un mesaj sau o conversație), le **afișează ca în aplicația originală**
(chat pentru `sms` / `whatsapp` / `chat`, client de e-mail pentru `email`, apel pentru `call_transcript`),
detectează frauda cu un **model local antrenat de noi + reguli** și afișează un avertisment simplu, în română.

Pe viitor intră și **audio (`.wav` / `.mp4`)**: se afișează ca mesaj vocal într-o conversație, se transcrie local
→ devine un `call_transcript` → trece prin același detector. Plus detecția **locației / regiunii din voce** cu un repo open-source.

### Reguli care ne constrâng arhitectura (din brief + AI scoring)
| Regulă | Consecință pentru noi |
|---|---|
| **Niciun mesaj nu pleacă spre un LLM în cloud** → descalificare (tier 0) | Totul rulează local. Nu folosim OpenAI/Anthropic/Gemini în detector. |
| Bonus maxim **+10% = tier 6: ensemble model + reguli + verificare linkuri/numere + calibrare** | Detector = model fine-tunat (tier 4) **+** reguli **+** verificare contra `official_catalog.json`. |
| Același input → același rezultat | Inferență deterministă (`model.eval()`, fără sampling, seed fix). |
| Risk score = suma punctelor red-flag-urilor (max 100), benzi SAFE/SUSPICIOUS/SCAM | Scorul se calculează **determinist din flaguri**, nu îl prezice modelul. |
| `first_alert` = primul mesaj după care scorul ≥ 25 | Rescorăm conversația **după fiecare mesaj** (prefix 1..n). |
| Privacy: nu stocăm mesaje fără opt-in | DB-ul ține istoric doar dacă userul bifează; există ștergere. Nu logăm textul mesajelor. |
| Dashboard: încarcă un folder întreg dintr-o acțiune | Upload multiplu / `webkitdirectory` în Angular → `POST /api/analyze/batch`. |
| Code freeze 17:00 | MVP (etapele 1–3) e prioritar. Etapele 4–5 audio = „nice to have” / pitch. |

---

## 1. Arhitectură

```
                ┌────────────────────────── frontend/ (Angular) ──────────────────────────┐
                │  Import JSON / folder / paste text   →   Dashboard (tabel V01..Vnn)       │
                │  Viewer per canal: ChatView | EmailView | CallView | VoiceNoteView(audio) │
                │  Detaliu scenariu: mesajul first_alert evidențiat, flaguri, avertisment   │
                └───────────────────────────────┬──────────────────────────────────────────┘
                                                │ HTTP/JSON (contract în CLAUDE.md §4)
                ┌───────────────────────────────▼──── backend/ (FastAPI) ──────────────────┐
                │  api/ routes  →  services/  →  detector (interfață)                       │
                │                    │                   │                                   │
                │                    │      ┌────────────▼─────────── detector/ ──────────┐ │
                │                    │      │ rules.py (regex, linkuri, numere, catalog)  │ │
                │                    │      │ model.py (transformer fine-tunat, local)    │ │
                │                    │      │ scoring.py (puncte, benzi, first_alert)     │ │
                │                    │      │ warnings.py (texte RO, șabloane fixe)       │ │
                │                    │      └─────────────────────────────────────────────┘ │
                │  audio/ (etapa 4): ffmpeg → faster-whisper → call_transcript + locație    │
                │  storage/ (etapa 5): fișiere audio pe disc, metadate în Postgres          │
                └───────────────┬──────────────────────────────────────┬───────────────────┘
                                │                                      │
                        PostgreSQL (opt-in history,              models/ (greutăți, gitignored)
                        metadate audio, rezultate)               data/audio/ (gitignored)
```

### Principiul care ne ține separați
**Fiecare om are un folder top-level al lui.** Singurele puncte de contact sunt:
1. `CLAUDE.md §4` — contractul JSON (Scenario, AnalysisResult, endpoint-uri).
2. **O singură interfață Python** între backend și detector:

```python
# detector/scam_detector/__init__.py   (owner: C)  — backend-ul doar importă asta
def analyze(scenario: dict) -> dict: ...          # Scenario JSON  -> AnalysisResult JSON
def load() -> None: ...                           # încarcă modelul în memorie (o singură dată)
```

Backend-ul (B) nu știe nimic despre torch/reguli; detectorul (C) nu știe nimic despre HTTP/DB.
Frontend-ul (A) vorbește doar cu API-ul. Până e gata API-ul, A lucrează cu **mock-uri** generate
din `validation_expected_results.csv`.

---

## 2. Echipa și ownership (propunere — schimbați numele între voi dacă vreți)

| Rol | Persoană | Deține (doar el editează) | Responsabil de |
|---|---|---|---|
| **A — Frontend** | Giulio | `frontend/**` | Angular: import JSON/folder/paste, viewere pe canal, dashboard, detaliu, UI avertisment, accesibilitate, audio player (et. 4) |
| **B — Backend / DB / Infra** | Theodor | `backend/**`, `docker-compose.yml`, `db/**` | FastAPI, endpoint-uri, Postgres, docker, lifecycle model în memorie, stocare audio, pipeline audio (et. 4–5) |
| **C — ML / Detector** | Francesco | `detector/**`, `ml/**`, `models/` (gitignored) | Reguli, dataset sintetic, fine-tuning model local, scoring, first_alert, texte avertisment, evaluare pe validation |

Fișiere comune (oricine, diff-uri mici, `git pull --rebase` înainte): `CLAUDE.md`, `PLAN.md`, `README.md`, `.gitignore`, `.env.example`.
`Scam_Shield_Public_Kit/` = **read-only** (datele oficiale, nu le modificăm).

---

## 3. Structura repo

```
/frontend                Angular app                                  (A)
/backend                 FastAPI app                                  (B)
  app/main.py            FastAPI + lifespan (încarcă detectorul o dată)
  app/api/               routes: scenarios, analyze, history, audio
  app/db/                SQLAlchemy models + sesiune
  app/audio/             (et. 4) ffmpeg, transcriere, locație
  app/storage/           (et. 5) salvare fișiere audio
/detector                pachet Python instalabil `scam_detector`     (C)
  scam_detector/rules.py, model.py, scoring.py, warnings.py, catalog.py
  tests/test_validation.py   → rulează toate V01..V11 contra CSV-ului
/ml                      notebooks/scripturi de antrenare, dataset    (C)
  data/                  dataset sintetic (generat local, fără LLM cloud)
  train.py, eval.py, export_onnx.py
/models                  greutăți antrenate (gitignored; descărcare/copie manuală)
/db                      init.sql / migrații                         (B)
/Scam_Shield_Public_Kit  date oficiale (read-only)
docker-compose.yml       postgres (+ backend)                         (B)
```

Backend-ul instalează detectorul cu `pip install -e ../detector` → nu există import de fișiere între foldere.

**Python 3.12** pentru `backend/` + `detector/` + `ml/` (torch nu e garantat pe 3.14, care e default pe Mac-ul lui Giulio).

---

## 4. Etape și taskuri

Legendă: **[A]** Frontend · **[B]** Backend · **[C]** ML. Taskurile din aceeași etapă se pot face în paralel.

### Etapa 1 — Setup + contracte (primele ~30 min, toți)
| # | Task | Cine | Livrabil |
|---|---|---|---|
| 1.1 | Plan + CLAUDE.md completat (§1–§4, §6) | A | acest fișier ✅ |
| 1.2 | Schelet Angular în `frontend/` | A | `ng serve` merge |
| 1.3 | Schelet FastAPI în `backend/` + `docker-compose.yml` cu Postgres | B | `GET /api/health` → `{"status":"ok"}` |
| 1.4 | Schelet pachet `detector/` cu `analyze()` stub (returnează SAFE) + test pe validation | C | `pytest` rulează (chiar dacă pică) |
| 1.5 | Review contract §4 (Scenario + AnalysisResult) — toți 3 confirmă | toți | §4 marcat `agreed` |

### Etapa 2 — Afișarea conversațiilor (fără detecție)
| # | Task | Cine | Livrabil |
|---|---|---|---|
| 2.1 | Model TS `Scenario` + import JSON (fișier, multiple, folder) + paste text | A | listă de scenarii în UI |
| 2.2 | `ChatView` pentru `sms` / `whatsapp` / `chat` (bule stânga/dreapta, header cu expeditor, badge „contact salvat / necunoscut”, numerotare [n]) | A | V01–V05, V08–V10 arată ca o aplicație de chat |
| 2.3 | `EmailView` pentru `email` (From, adresă, subiect, corp) | A | V06 arată ca un e-mail |
| 2.4 | `CallView` pentru `call_transcript` (ecran apel + transcriere) — **același component va primi și audio la et. 4** | A | V07, V11 |
| 2.5 | `GET /api/scenarios/validation` → listă Scenario din `Scam_Shield_Public_Kit/validation_set` | B | FE poate încărca setul cu un buton |
| 2.6 | `POST /api/analyze` + `POST /api/analyze/batch` care apelează `scam_detector.analyze()` (stub-ul) | B | contract respectat end-to-end |

### Etapa 3 — Detectorul (cel mai important: 30p acuratețe + 25p avertismente)
| # | Task | Cine | Livrabil |
|---|---|---|---|
| 3.1 | `catalog.py`: încarcă `official_catalog.json` (puncte, benzi, tipuri, contacte oficiale) | C | |
| 3.2 | `rules.py`: detectoare per flag — linkuri/domenii/numere vs. catalog (`RF_SUSPICIOUS_CONTACT`), coduri OTP, AnyDesk/TeamViewer, CNP/card/PIN, sume + „achitați/transfer”, „număr nou”, „nu-i spune”, termene, amenințări, Telegram. Robust la **fără diacritice**, emoji, text gol/lung | C | flaguri per mesaj |
| 3.3 | `scoring.py`: scor = Σ puncte (unice) capped 100 → verdict; **re-scor pe fiecare prefix** → `first_alert` | C | V01–V11 verdict + first_alert corecte doar din reguli |
| 3.4 | Dataset sintetic local (`ml/data/`): șabloane × variații (diacritice on/off, sinonime, nume, sume, linkuri), **hard negatives** (mesaje reale de bancă/curier cu coduri și plăți — vezi V03, V05). Validation set **nu** intră în train | C | ~1–3k exemple etichetate (flaguri + tip) |
| 3.5 | Fine-tuning model local multi-task: multi-label red flags + clasificare `scam_type`. Candidat: `dumitrescustefan/bert-base-romanian-cased-v1` sau `xlm-roberta-base` (CPU-friendly; opțional distilare) | C | `models/scam-bert/` + metrici |
| 3.6 | Ensemble: `flags = rules ∪ (model > prag calibrat)`; `scam_type` din model, cu reguli de override; prag calibrat pe un dev split | C | tier 6 justificat în pitch |
| 3.7 | `warnings.py`: șabloane RO per `scam_type` (≤3 propoziții, „dumneavoastră”, o acțiune pe canal oficial, **niciodată** link/număr din mesaj; numerele oficiale doar din catalog) + EN opțional | C | text pentru fiecare tip |
| 3.8 | Dashboard: sumar (total / SCAM / SUSPICIOUS / SAFE) + tabel ID, verdict colorat + cuvânt + icon, tip, scor, first_alert, flaguri; sortat după ID; export CSV | A | M8 |
| 3.9 | Detaliu scenariu: viewer-ul de canal + mesajul first_alert evidențiat + flaguri pe mesaj + avertisment mare | A | M9 |
| 3.10 | Ecran „Verifică un mesaj”: paste + un buton mare + rezultat colorat (font ≥18px, contrast mare) | A | M7, hands-on check |
| 3.11 | Script `make eval` / `pytest`: compară cu `validation_expected_results.csv`, raport diferențe | C | 11/11 verde |

### Etapa 4 — Audio (după MVP; arhitectura e pregătită de acum)
| # | Task | Cine | Livrabil |
|---|---|---|---|
| 4.1 | `POST /api/audio` (multipart `.wav`/`.mp3`/`.mp4`/`.m4a`) → salvează fișierul (et. 5) → `audio_id` | B | |
| 4.2 | ffmpeg → wav mono 16 kHz → **faster-whisper** local (model `small`/`medium`, `language="ro"`) → segmente → Scenario `channel: "call_transcript"` cu `audio` atașat | B | transcriere reutilizează detectorul fără modificări |
| 4.3 | Detecție locație/regiune din voce cu repo open-source (de ales: model de accent/dialect sau speaker-geolocation). Rulează ca **plugin separat** `app/audio/location.py` cu interfață `detect_location(wav_path) -> {region, confidence}` | B (+C pt model) | câmp `audio.location` în rezultat |
| 4.4 | `VoiceNoteView`: conversație deschisă cu bulă de mesaj vocal (play, durată, waveform simplu) + transcriere expandabilă + locația detectată | A | |

### Etapa 5 — Model în memorie + stocare audio
| # | Task | Cine | Livrabil |
|---|---|---|---|
| 5.1 | Modelul se încarcă **o singură dată** în `lifespan` FastAPI (`scam_detector.load()`), ținut ca singleton în proces; warm-up cu un mesaj dummy; `GET /api/health` raportează `model_loaded` | B + C | latență mică per request |
| 5.2 | Uvicorn cu **1 worker** (un model în RAM). Inferență sync în `run_in_threadpool` ca să nu blocheze event loop-ul. Dacă e nevoie de mai mulți workeri: export ONNX + `onnxruntime` (cuantizat int8) — mai puțin RAM | B + C | |
| 5.3 | Whisper: același pattern — încărcat lazy la primul request audio, păstrat în memorie (`faster-whisper`, `compute_type="int8"` pe CPU) | B | |
| 5.4 | Fișiere audio pe **disc** (`STORAGE_DIR/audio/<uuid>.<ext>`, volum Docker), **nu** în Postgres. În DB doar metadate: `id, path, mime, duration_s, sha256, created_at, expires_at` | B | |
| 5.5 | Privacy: audio + istoric doar cu opt-in; job de ștergere la `expires_at` (ex. 24h); `DELETE /api/history/{id}` șterge și fișierul | B | |
| 5.6 | Interfață `Storage` (`save/open/delete`) → azi `LocalStorage`, mâine S3/MinIO fără schimbări în rest | B | |

### Etapa 6 — Demo (ultima oră)
Pitch 3 min (vorbesc toți 3), dashboard pe Test Set, live re-run, hands-on. Vezi `CLAUDE.md §10`.

---

## 5. Ordinea / timeline (zi de hackathon, 10:30 → 17:00)

| Interval | A — Frontend | B — Backend | C — ML |
|---|---|---|---|
| 10:30–11:00 | 1.1, 1.2 | 1.3 | 1.4 |
| 11:00–12:30 | 2.1–2.4 (viewere, cu date locale) | 2.5, 2.6, Postgres | 3.1–3.3 (reguli → validation corect) |
| 12:30–13:30 | 3.8–3.10 pe mock-uri | 5.1, 5.2 (lifespan, health) | 3.4 dataset + 3.7 avertismente |
| 13:30–15:30 | Integrare cu API real | 4.1, 4.2, 5.4 | 3.5 fine-tune, 3.6 ensemble, 3.11 |
| 15:30–17:00 | Polish, accesibilitate, 4.4 | 4.3 dacă e timp, ajutor integrare | Calibrare, verificare hard negatives |

**Regula de aur:** la 12:30 detectorul trebuie să dea 11/11 pe validation **doar cu reguli**. Modelul vine peste,
ca îmbunătățire — dacă fine-tuning-ul nu iese, avem tot un produs care merge.

---

## 6. Cum evităm conflictele în git
1. Fiecare lucrează **doar în folderul lui** (§2). Branch: `<nume>/<task>` (ex. `giulio/chat-view`).
2. Contract schimbat = PR mic doar pe `CLAUDE.md §4` + anunț pe chat. Fără modificări „din mers”.
3. `package.json` / `package-lock.json` sunt în `frontend/` (doar A). `requirements.txt` separat: `backend/requirements.txt` (B), `detector/pyproject.toml` (C), `ml/requirements.txt` (C).
4. Fișierele comune (`CLAUDE.md`, `PLAN.md`): `git pull --rebase` chiar înainte, commit mic, push imediat.
5. Merge pe `main` des (la fiecare ~45 min), `main` trebuie să ruleze mereu.
