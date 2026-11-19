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
| Francesco stress_test.py (8) — unseen by Giulio | 27.8 | *(30.0, own)* |
| Francesco creative traps (15) — unseen by Giulio | 23.0 | *(30.0, own)* |
| Francesco benchmark (108) | 30.0 | 30.0 |
| Scams called SAFE on the other's tests | 1 / 23 | 9 / 73 |
| False alarms on the other's tests | 1 | 5 |
| Malformed inputs that crash (of 5) | 0 | 2 |
| Latency | ~25 ms (GPU model) | ~1 ms |

Known weaknesses of scam_detector found by Francesco's tests (not fixed yet):
- "poți să-mi transferi banii" is not detected as a payment request.
- The romance keyword weighting pushes "moare de inimă" to ROMANCE.
- A dentist SMS with an unlisted phone number gets RF_SUSPICIOUS_CONTACT.
- RECORDER_HEALTH_01 (fake miracle supplement): the verdict and first alert are correct, but the type is wrong
  (COURIER_FEE instead of OTHER), so the warning talks about a courier.
