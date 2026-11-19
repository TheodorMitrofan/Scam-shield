# scam_detector

Local scam detector for Scam Shield (`scam_shield` SOTA v3 engine). **No cloud LLM; no message leaves the laptop.**
Approach **Tier 6** (ensemble / multi-signal):
1. **De-obfuscation & Homoglyph Defense** (`text_utils.py`): diacritics stripping, Cyrillic/Greek homoglyph detection, spaced-word rejoining (`A n y D e s k`), leet-speak decoding.
2. **Official Contact Verification** (`contact_verifier.py`): whitelist check against `official_catalog.json` (domains, defanged links `[.]`, HTTP basic-auth `user@host`, phones).
3. **Deterministic + Context-Aware Rules** (`red_flags.py`): 13 official red flags with word-boundary precision, conversation-history context tracking, and safety-advice guards.
4. **SOTA Neural-SVD + Linear Calibrated ML Ensemble** (`trained_model.joblib`, **3.9 MB**, bundled offline): Word (1–2) + Char-WB (3–5) TF-IDF + Dense `TruncatedSVD` Neural `MLPClassifier` + `LogisticRegression` soft voting (3 calibrated heads: 13-class type, multi-label 12 red flags, and malicious-intent safety gate), plus TF-IDF cosine semantic anchor matching (`semantic_nli.py`).
5. **Grandparent-Friendly Bilingual Warnings** (`warning_generator.py`): ≤3 short sentences in Romanian (`ro` + `en`), zero technical jargon, official channels only.

## Install / run
```bash
pip install -e detector

python -m scam_detector.cli Scam_Shield_Public_Kit/validation_set
python -m scam_detector.evaluate Scam_Shield_Public_Kit/validation_set Scam_Shield_Public_Kit/validation_expected_results.csv
python detector/tests/stress_test.py --with-challenge
python ml/adversarial_stress.py
python ml/final_boss_stress.py
```

## Rebuild weights
Weights live directly in `detector/scam_detector/trained_model.joblib` (3.9 MB, no Git LFS or GPU needed):
```bash
PYTHONPATH=detector python3 -m ml.train_model
```

## API (CLAUDE.md §4.2)
```python
import scam_detector as sd
sd.load()                 # loads rules + semantic index + trained_model.joblib (~0.3s)
res = sd.analyze(scenario_dict)
res = sd.analyze_text("text pasted by the user", channel="sms")
```
