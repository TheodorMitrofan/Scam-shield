# scam_detector

Local scam detector for Scam Shield. **No cloud LLM; no message leaves the laptop.**
Approach tier 6 (ensemble / multi-signal): deterministic rules, link/number checks against the official
catalog, and a fine-tuned multi-task XLM-RoBERTa (red flags per message + scam type per thread) with
temperature calibration. Score, verdict and first alert always come from the official formula.

## Install / run
```bash
pip install -e detector            # rules-only, no heavy deps
pip install torch "transformers>=4.44,<5" sentencepiece   # + model

python -m scam_detector.cli Scam_Shield_Public_Kit/validation_set            # dashboard-style table
python -m scam_detector.cli <folder> --csv out.csv --json                    # CSV / full JSON
python -m scam_detector.evaluate Scam_Shield_Public_Kit/validation_set Scam_Shield_Public_Kit/validation_expected_results.csv
python -m pytest detector/tests -q
```
Add `--rules-only` (or env `SCAM_RULES_ONLY=1`) to disable the model.

## API (CLAUDE.md §4.2)
```python
import scam_detector as sd
sd.load()                 # once at startup (FastAPI lifespan); False => weights missing, rules-only
res = sd.analyze(scenario_dict)
res = sd.analyze_text("text pasted by the user", channel="sms")   # blank line = new message, "Reader:" = reply
```
`res` = `{id, verdict, scam_type, risk_score, first_alert, red_flags, flags_by_message:[{n, flags, new_flags, score_after}],
warning:{ro, en}, evidence:[{n, flag, span:[start,end]|null, source:"rule"|"contact"|"model"}], engine}`.
`span` is a character range in that message's original `text` (for highlighting dangerous words).

## Model weights
Weights are gitignored (`models/scam-bert/`, ~1.1 GB). Rebuild them locally (about 10 min on an RTX 4060):
```bash
python ml/gen_synthetic.py --n 6000     # hand-written Romanian templates, hard negatives; no validation data
python ml/train.py --epochs 3           # -> models/scam-bert/{model, tokenizer, heads.pt, meta.json}
```
Override the location with `MODEL_DIR`. If the weights are missing, the detector runs rules-only, which still
scores 11/11 on the validation set.

## How a decision is made
1. `normalize`: lowercase, strip diacritics (offsets are kept, so spans stay valid).
2. `contacts`: links, e-mails and phones are checked against the official list → `RF_SUSPICIOUS_CONTACT`.
3. `rules`: per-flag Romanian patterns with negation guards ("nu comunicați codul nimănui" is advice, not a request).
4. `model`: adds a flag only when the calibrated probability is ≥ 0.9 (never adds contact or identity flags).
5. `fusion`:
   - `RF_IMPERSONATION` = an org/authority claim plus an unverified sender or other risk.
   - A verified official sender with only official links and no "never-official" requests counts as genuine.
   - Score = sum of the points of the unique flags (capped at 100), recomputed after every message → `first_alert`.
   - The type is chosen by keyword/flag votes plus the model's type probabilities.
6. `warnings`: ≤3 sentences in Romanian, one action via an official channel from the catalog, never a link or number from the message.
