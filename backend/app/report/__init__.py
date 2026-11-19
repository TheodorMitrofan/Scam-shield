"""Fraud report: generated when risk_score ≥ 50, completed by the user, e-mailed to a DEMO inbox."""

# HACK: demo only — reports must never reach the real Police / DNSC during the hackathon.
REPORT_RECIPIENT = "francescomartinut18@gmail.com"
REPORT_MIN_SCORE = 50
