#!/usr/bin/env python3
"""Stress set for money requests + deadlines in formal AND informal Romanian, with hard negatives.

    python tools/stress/gen_payment_urgency.py --out stress_data/payment_urgency.json [--n 300 --seed 1]
    PYTHONPATH=detector python detector/tests/stress_test.py --file stress_data/payment_urgency.json

Labels follow the official formula: payment request 25 (+ urgency 15) -> SUSPICIOUS; genuine/past-tense -> SAFE.
"""
import argparse, json, random, unicodedata

OPENERS = ["am primit comanda dvs de {item}", "salut, legat de comanda ta de {item}", "buna ziua, comanda de {item} e gata",
           "hey, pt {item}ul de pe site", "va scriu de la magazin pentru {item}", "comanda ta de {item} a fost inregistrata"]
ITEMS = ["calculatoare", "laptop", "telefon", "bicicleta", "frigider", "pantofi", "televizor"]
VERBS_FORMAL = ["trimiteti", "virati", "transferati", "depuneti", "achitati", "platiti", "alimentati"]
VERBS_INFORMAL = ["trimite-mi", "trimite", "baga", "da-mi", "vireaza", "pune", "fa-mi un transfer de"]
AMOUNTS = ["{n} RON", "{n} lei", "{n} de lei", "{n} ron", "{n} euro", "{n}€", "{n} eur", "{n}.000 lei"]
ACCOUNTS = ["in contul {acc}", "pe contul {acc}", "in contu meu {acc}", "pe revolut la {acc}", "in IBAN-ul {acc}",
            "la contul {acc}", "pe cont {acc}", ""]
DEADLINES = ["Mai aveti {h} ore", "mai ai {h} ore", "ai doar {h} ore", "aveti doar {m} minute", "mai ai o ora",
             "in urmatoarele {h} ore", "pana diseara", "urgent", "in maxim {m} minute", ""]
NEGATIVES = [
    "V-am trimis {amt} in contul dvs, verificati cand puteti.",
    "Am platit deja factura de {amt}, multumesc!",
    "ti-am trimis ieri {amt} pe revolut, zi-mi daca au intrat",
    "Coletul va fi livrat in {d} zile lucratoare. Ramburs: 0 lei.",
    "Mai aveti {d} zile pana la programarea la dentist.",
    "trimite-mi te rog poza cu {item}ul",
    "Comanda de {item} a fost achitata cu succes. Livrare in {d} zile.",
    "am primit banii, multumesc mult!",
]

def strip(t):
    return "".join(c for c in unicodedata.normalize("NFD", t) if unicodedata.category(c) != "Mn")

def scenario(i, text, channel):
    return {"id": f"PU{i:04d}", "channel": channel,
            "sender": {"name": None, "address": "+40 7xx xxx " + str(100 + i % 900), "known_contact": False},
            "messages": [{"n": 1, "from": "sender", "text": text}]}

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--out", default="stress_data/payment_urgency.json")
    ap.add_argument("--n", type=int, default=300)
    ap.add_argument("--seed", type=int, default=1)
    a = ap.parse_args()
    rng = random.Random(a.seed)
    out = []
    for i in range(a.n):
        ch = rng.choice(["sms", "whatsapp", "chat"])
        if rng.random() < 0.25:  # hard negative
            t = rng.choice(NEGATIVES).format(amt=rng.choice(AMOUNTS).format(n=rng.randint(50, 2000)),
                                             d=rng.randint(2, 5), item=rng.choice(ITEMS))
            exp = {"verdict": "SAFE", "scam_type": "NONE", "first_alert": None}
            cat, note = "negative", "past tense / info / reminder: must stay SAFE"
        else:
            informal = rng.random() < 0.5
            verb = rng.choice(VERBS_INFORMAL if informal else VERBS_FORMAL)
            amt = rng.choice(AMOUNTS).format(n=rng.randint(50, 3000))
            acc = rng.choice(ACCOUNTS).format(acc=rng.choice(["REV1123", "RO49AAAA1B31007593840000", "ana_m", "0722xxx"]))
            dl = rng.choice(DEADLINES).format(h=rng.randint(1, 12), m=rng.choice([15, 30, 45]))
            opener = rng.choice(OPENERS).format(item=rng.choice(ITEMS))
            t = f"{opener}, pentru confirmare {verb} {amt} {acc}".strip() + (f". {dl}" if dl else "")
            flags = ["RF_PAYMENT_REQUEST"] + (["RF_URGENCY"] if dl else [])
            exp = {"verdict": "SUSPICIOUS", "scam_type": ["OTHER", "MARKETPLACE", "COURIER_FEE"], "first_alert": 1}
            cat = ("informal" if informal else "formal") + (" + deadline" if dl else "")
            note = "money request" + (" + deadline" if dl else "") + f" (expected flags {flags})"
        if rng.random() < 0.5:
            t = strip(t)
        if rng.random() < 0.3:
            t = t.lower()
        out.append({"category": cat, "note": note, "expected": exp, **scenario(i, t, ch)})
    import os
    os.makedirs(os.path.dirname(a.out) or ".", exist_ok=True)
    json.dump(out, open(a.out, "w", encoding="utf-8"), ensure_ascii=False, indent=1)
    print(f"wrote {len(out)} scenarios to {a.out}")

if __name__ == "__main__":
    main()
