# scam_detector vs scam_shield (Francesco, `origin/model-train` @ 3366144)

Run on 2026-11-19 with `detector/tests/compare_engines.py`. Both engines, same sets, brief scoring
(verdict 3, type 2, first alert 2, −3 for a scam called SAFE). Each engine was tuned on its own tests, so
the honest numbers are on the **other** author's tests.

| Test set | scam_detector | scam_shield |
|---|---|---|
| Official validation (11) | 30.0 | 30.0 |
| Giulio stress (43) — unseen by Francesco | *(30.0, own)* | 18.4 |
| Giulio blind (15) — unseen by Francesco | *(30.0, own)* | 20.8 |
| Giulio challenge (15) — unseen by Francesco | *(30.0, own)* | 13.3 |
| Francesco stress_test.py (8) — unseen by Giulio | 27.8 → **30.0** after fixes | *(30.0, own)* |
| Francesco creative traps (15) — unseen by Giulio | 23.0 → **30.0** after fixes | *(30.0, own)* |
| Francesco benchmark (108) | 30.0 | 30.0 |
| Scams called SAFE on the other's tests | 1 / 23 → 0 | 9 / 73 |
| False alarms on the other's tests | 1 → 0 | 5 |
| Malformed inputs that crash (of 5) | 0 | 2 |
| Latency | ~25 ms (GPU model) | ~1 ms |

Weaknesses found by Francesco's tests — **fixed** (regression test `test_regressions_from_scam_shield_creative_traps`).
They were fixed after seeing his tests, so the 30.0 there is no longer a blind score:
- "poți să-mi transferi banii" is now a payment request (2nd-person `transferi`/`virezi`, `să-mi ...`).
- "moare de inimă" no longer counts as ROMANCE; `buni`, `avocat`, `daune`, `arest` count as FAMILY_EMERGENCY.
- An unlisted phone number alone no longer raises RF_SUSPICIOUS_CONTACT; it counts only when the thread claims an
  organisation or already carries another risk (same policy as sender e-mails).
- An @handle given together with a channel switch ("pe Telegram la @invest_crypto_fast") is RF_SUSPICIOUS_CONTACT.
- RECORDER_HEALTH_01 was already fixed earlier (type OTHER).
