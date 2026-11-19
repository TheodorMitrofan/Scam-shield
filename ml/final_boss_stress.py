from typing import Dict, List
from scam_detector.pipeline import ScamShieldPipeline

# 22 brand-new, unseen jury-style scenarios mimicking the Secret Test Set structure:
# - Long gradual multi-turn threads (7-10 msgs) testing exact first_alert windows
# - Subtle genuine traps (bank 2FA/anti-fraud, legit courier tracking, clinic MRI, intercom pin, Bitcoin chat)
# - Look-alike domains (bancadunareaa.ro, curier-expres.ro), mixed RO/EN, QR marketplace, notary romance
FINAL_BOSS_SCENARIOS: List[Dict] = [
    # --- 1. Long Gradual Multi-Turn Scam Threads ---
    {
        "id": "FB_THREAD_BANK_01",
        "channel": "call_transcript",
        "sender": {"name": None, "address": "+40 318 221 900", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună ziua, doamnă Ionescu. Mă numesc Radu și sun de la Banca Dunărea."},
            {"n": 2, "from": "reader", "text": "Bună ziua, s-a întâmplat ceva?"},
            {"n": 3, "from": "sender", "text": "Verificăm câteva operațiuni de rutină pe conturile din București."},
            {"n": 4, "from": "reader", "text": "Înțeleg."},
            {"n": 5, "from": "sender", "text": "Tocmai am detectat o plată suspectă de 3.900 lei din Cluj și trebuie să o blocăm urgent."},
            {"n": 6, "from": "reader", "text": "Doamne ferește! Nu am fost eu la Cluj!"},
            {"n": 7, "from": "sender", "text": "Liniștiți-vă. Instalați acum aplicația TeamViewer pe telefon ca să oprim tranzacția de la distanță."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["BANK_IMPERSONATION", "TECH_SUPPORT"],
        "alert_window": (5, 7),
    },
    {
        "id": "FB_THREAD_MARKET_01",
        "channel": "chat",
        "sender": {"name": "Cumpărător", "address": "buyer_9912", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună seara, mai aveți frigiderul de vânzare pe PiațaMea?"},
            {"n": 2, "from": "reader", "text": "Da, este încă disponibil."},
            {"n": 3, "from": "sender", "text": "Are vreo problemă tehnică sau funcționează bine?"},
            {"n": 4, "from": "reader", "text": "Funcționează perfect, are doar 2 ani."},
            {"n": 5, "from": "sender", "text": "Minunat, îl cumpăr sigur. Trimit curierul mâine dimineață să îl preia."},
            {"n": 6, "from": "sender", "text": "Am plătit deja suma prin curier-piatamea.org. Scanați codul QR de pe pagină și introduceți datele cardului să primiți banii."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["MARKETPLACE"],
        "alert_window": (6, 6),
    },
    {
        "id": "FB_THREAD_FAMILY_FRIEND_01",
        "channel": "whatsapp",
        "sender": {"name": None, "address": "+40 7xx xxx 604", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună ziua, doamna Maria."},
            {"n": 2, "from": "reader", "text": "Bună ziua, cine sunteți?"},
            {"n": 3, "from": "sender", "text": "Sunt Dragoș, colegul nepotului dumneavoastră, Andrei."},
            {"n": 4, "from": "reader", "text": "A, bună ziua. S-a întâmplat ceva cu Andrei?"},
            {"n": 5, "from": "sender", "text": "A căzut pe scări și telefonul lui s-a spart. Sunt cu el la urgență și trebuie să plătim azi 2.200 lei pentru investigații, nu spuneți părinților să nu se sperie."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["FAMILY_EMERGENCY"],
        "alert_window": (5, 5),
    },
    {
        "id": "FB_THREAD_ROMANCE_NOTARY_01",
        "channel": "chat",
        "sender": {"name": "Laurent", "address": "laurent_fr", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună, suflet frumos. Mi-au plăcut mult pozele tale din grădină."},
            {"n": 2, "from": "reader", "text": "Mulțumesc frumos!"},
            {"n": 3, "from": "sender", "text": "Vorbim deja de două luni și simt o legătură specială între noi."},
            {"n": 4, "from": "reader", "text": "Și eu mă bucur că ne înțelegem."},
            {"n": 5, "from": "sender", "text": "Vreau să mă mut în România lângă tine, iubirea mea."},
            {"n": 6, "from": "sender", "text": "Mi-am vândut apartamentul, dar banii sunt blocați la notar în Paris și am nevoie urgent de 600 € prin Western Union pentru taxe ca să pot veni la tine."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["ROMANCE"],
        "alert_window": (6, 6),
    },
    {
        "id": "FB_THREAD_COURIER_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 819", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "CurierExpres: Aveți un colet programat pentru livrare mâine."},
            {"n": 2, "from": "reader", "text": "Bine, la ce oră ajunge?"},
            {"n": 3, "from": "sender", "text": "Adresa este incompletă. Achitați taxa de corecție de 4,50 lei pe curier-expres.ro altfel coletul se întoarce azi."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["COURIER_FEE"],
        "alert_window": (3, 3),
    },

    # --- 2. Hard Obfuscation & Look-Alike Single Messages ---
    {
        "id": "FB_TYPOSQUAT_BANK_01",
        "channel": "sms",
        "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Banca Dunărea: Accesul la aplicație a fost limitat. Verificați identitatea imediat pe bancadunareaa.ro"}],
        "expected_verdict": "SCAM",
        "expected_types": ["BANK_IMPERSONATION"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_MIXED_RO_EN_01",
        "channel": "email",
        "sender": {"name": "Banca Dunarea", "address": "alerts@bancadunarea-verify.com", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Security Alert: Your Banca Dunarea card is blocked. Enter your card details and PIN within 24h at hxxps://bancadunarea-verify[.]com"}],
        "expected_verdict": "SCAM",
        "expected_types": ["BANK_IMPERSONATION"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_CYRILLIC_ANAF_01",
        "channel": "email",
        "sender": {"name": "ANAF", "address": "rambursari@anaf-portal.net", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "ANAF: Aveți o restituire de 1.150 lei. Completați CNP-ul și datele cardului pe аnaf.ro/restituire"}],
        "expected_verdict": "SCAM",
        "expected_types": ["AUTHORITY_IMPERSONATION"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_POLICE_FINE_01",
        "channel": "email",
        "sender": {"name": "Politia Romana", "address": "citatie@politie-amenzi.info", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Poliția Română: S-a emis o amendă de 1.500 lei pe numele dvs. pentru infracțiuni online. Achitați azi pe politie-amenzi.info pentru a evita dosarul penal."}],
        "expected_verdict": "SCAM",
        "expected_types": ["AUTHORITY_IMPERSONATION"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_JOB_SLANG_01",
        "channel": "whatsapp",
        "sender": {"name": None, "address": "+40 7xx xxx 955", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Oferim job remote super simplu: dați subscribe și like la videoclipuri, câștigați 400 lei pe zi garantat! Haideți pe Telegram, depuneți doar garanția de 100 lei."}],
        "expected_verdict": "SCAM",
        "expected_types": ["JOB_OFFER"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_CRYPTO_PROFIT_01",
        "channel": "chat",
        "sender": {"name": "InvestRO", "address": "invest_pro", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Expert financiar: investiți 300 € în Bitcoin și primiți venit garantat de 2.500 € lunar. Depuneți acum pe bit-castig.online"}],
        "expected_verdict": "SCAM",
        "expected_types": ["INVESTMENT"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_CHARITY_FAKE_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 301", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Urgență umanitară! Donați acum 100 lei pe cont-ajutor-24.site pentru victimele inundațiilor, nu amânați!"}],
        "expected_verdict": "SCAM",
        "expected_types": ["OTHER"],
        "alert_window": (1, 1),
    },
    {
        "id": "FB_PRIZE_CUSTOMS_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 409", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Felicitări! Ați câștigat un televizor la tombola MegaShop! Achitați taxa de curierat de 19 lei pe megashop-premiu.com"}],
        "expected_verdict": "SCAM",
        "expected_types": ["PRIZE_LOTTERY"],
        "alert_window": (1, 1),
    },

    # --- 3. Sneaky Genuine Traps (ALL MUST STAY SAFE!) ---
    {
        "id": "FB_SAFE_THREAD_COURIER_01",
        "channel": "sms",
        "sender": {"name": "CurierExpres", "address": "CurierExpres", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "CurierExpres: Coletul AWB 774100 va fi livrat astăzi între 14:00 și 17:00."},
            {"n": 2, "from": "reader", "text": "Cât am de plată la curier?"},
            {"n": 3, "from": "sender", "text": "Ramburs: 0 lei. Urmărire detalii pe curierexpres.ro/tracking sau la 0800 300 400."},
        ],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_BANK_YESNO_01",
        "channel": "sms",
        "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Banca Dunărea: S-a încercat o plată de 450 lei online. Răspundeți DA dacă ați autorizat-o sau sunați la 0800 100 200. Nu vă vom cere niciodată codul PIN."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_INTERCOM_CODE_01",
        "channel": "whatsapp",
        "sender": {"name": "Vecina Elena", "address": "+40 7xx xxx 115", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Bună! Codul de la interfonul scării este 4521#, hai sus când ajungi!"}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_CRYPTO_CHAT_01",
        "channel": "whatsapp",
        "sender": {"name": "Sorin (fratele)", "address": "+40 7xx xxx 211", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Ai văzut la știri cât a crescut Bitcoin săptămâna asta? Eu nu bag niciun ban în așa ceva, e prea riscant."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_FAMILY_THANKS_01",
        "channel": "whatsapp",
        "sender": {"name": "Nepotul Vlad", "address": "+40 7xx xxx 333", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Bună buni! Mulțumesc mult pentru banii de ziua mea, mi-am cumpărat adidașii doriți. Te pup!"}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_CLINIC_MRI_01",
        "channel": "sms",
        "sender": {"name": "Clinica MedLife", "address": "+40 21 9646", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Clinica MedLife: Vă reamintim programarea la cardiologie și RMN de joi, ora 09:30. Pentru anulare sunați la recepție."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_MEGASHOP_ORDER_01",
        "channel": "email",
        "sender": {"name": "MegaShop", "address": "comenzi@megashop.ro", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "MegaShop: Comanda dvs. #88321 a fost plătită cu succes (299 lei). Puteți descărca factura din contul dvs. pe megashop.ro."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_ANAF_INFO_01",
        "channel": "email",
        "sender": {"name": "ANAF", "address": "informare@anaf.ro", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "ANAF vă informează că declarația unică se depune exclusiv în Spațiul Privat Virtual pe anaf.ro. Nu solicitați coduri prin SMS."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
    {
        "id": "FB_SAFE_SHORT_GREETING_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 007", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Bună ziua! Aveți cumva numărul domnului administrator de la scara B?"}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "alert_window": None,
    },
]


def run_final_boss_stress():
    pipeline = ScamShieldPipeline()
    passed = 0
    print("=" * 85)
    print(f"FINAL BOSS JURY STRESS SUITE ({len(FINAL_BOSS_SCENARIOS)} BRAND-NEW UNSEEN SCENARIOS)")
    print("=" * 85)

    for s in FINAL_BOSS_SCENARIOS:
        res = pipeline.analyze_scenario(s)
        v_ok = res["verdict"] == s["expected_verdict"]
        t_ok = res["scam_type"] in s["expected_types"]
        w = s["alert_window"]
        if w is None:
            a_ok = res["first_alert"] is None
        else:
            a_ok = res["first_alert"] is not None and w[0] <= res["first_alert"] <= w[1]
        ok = v_ok and t_ok and a_ok
        if ok:
            passed += 1
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"[{s['id']:<26}] {res['verdict']:<10} ({res['risk_score']:>3}p) | {res['scam_type']:<24} | fa={str(res['first_alert']):<4} | {status}")
        if not ok:
            print(f"   EXP: {s['expected_verdict']} / {s['expected_types']} / window={w}")
            print(f"   GOT: {res['verdict']} / {res['scam_type']} / fa={res['first_alert']} flags={res['red_flags']}")

    print("-" * 85)
    print(f"FRANCESCO FINAL BOSS RESULT: {passed}/{len(FINAL_BOSS_SCENARIOS)} ({passed/len(FINAL_BOSS_SCENARIOS)*100:.1f}%)")
    print("=" * 85)
    return passed, len(FINAL_BOSS_SCENARIOS)


if __name__ == "__main__":
    run_final_boss_stress()
