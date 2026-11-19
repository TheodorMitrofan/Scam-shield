import os
from typing import Dict, List
from scam_detector.pipeline import ScamShieldPipeline

# 24 hard, realistic adversarial & paraphrased scenarios designed to stress-test:
# - Leet-speak, Cyrillic homoglyphs, spaced obfuscation, heavy SMS typos
# - Zero-keyword paraphrased intent scams
# - Conversational slow-burn threads
# - Sneaky hard-negative genuine messages containing scary words (AnyDesk/CVV/hospital/salary/2FA)
ADVERSARIAL_SCENARIOS: List[Dict] = [
    # --- 1. Obfuscation, Homoglyphs, Typos ---
    {
        "id": "ADV_LEET_BANK_01",
        "channel": "sms",
        "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Bаncа Dunarea: C4rdul dvs a f0st bl0cat temporar. D3blocare urgenta pe bаncadunarea-sec.com"}],
        "expected_verdict": "SCAM",
        "expected_types": ["BANK_IMPERSONATION"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_SPACED_REMOTE_01",
        "channel": "chat",
        "sender": {"name": "Suport Tehnic", "address": "tech_help99", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Calculatorul trimite virusi! Descarcati A n y D e s k acum ca sa intram de la distanta."}],
        "expected_verdict": "SCAM",
        "expected_types": ["TECH_SUPPORT"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_TYPO_OTP_01",
        "channel": "whatsapp",
        "sender": {"name": "Ioana", "address": "+40 7xx xxx 412", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Slut, ti-a vnit un c0d prn sms din grseala, trimte-mi-l rpede te r0g!!"}],
        "expected_verdict": "SCAM",
        "expected_types": ["ACCOUNT_TAKEOVER"],
        "expected_alert": 1,
    },

    # --- 2. Paraphrased / Zero-exact-keyword Scams ---
    {
        "id": "ADV_PARA_CODE_01",
        "channel": "whatsapp",
        "sender": {"name": "Elena", "address": "+40 7xx xxx 510", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Am tastat greșit numărul la recuperare și a ajuns la tine un mesaj cu șase cifre de securitate. Spune-mi ce cifre apar acolo, te rog mult, e urgent!"}],
        "expected_verdict": "SCAM",
        "expected_types": ["ACCOUNT_TAKEOVER"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_SAFE_ACC_01",
        "channel": "call_transcript",
        "sender": {"name": None, "address": "+40 311 444 999", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună ziua, vă sun de la siguranța financiară a băncii."},
            {"n": 2, "from": "reader", "text": "Da, ce s-a întâmplat?"},
            {"n": 3, "from": "sender", "text": "S-a încercat o fraudă pe cont. Pentru protecție, mutați toate economiile într-un cont tampon până mâine seară."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["BANK_IMPERSONATION"],
        "expected_alert": 3,
    },
    {
        "id": "ADV_PARA_MARKET_01",
        "channel": "chat",
        "sender": {"name": "Cumpărător", "address": "user_2291", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Mai aveți masa de vânzare?"},
            {"n": 2, "from": "reader", "text": "Da, este disponibilă."},
            {"n": 3, "from": "sender", "text": "Am plătit deja. Validați cardul cu soldul disponibil pe pagina de confirmare ca să intre suma: livrare-sigura-ro.site"},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["MARKETPLACE"],
        "expected_alert": 3,
    },
    {
        "id": "ADV_PARA_ROMANCE_01",
        "channel": "chat",
        "sender": {"name": "Capt. David", "address": "david_peace", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună, suflet drag, mă bucur că vorbim zilnic."},
            {"n": 2, "from": "reader", "text": "Și eu, ai grijă acolo."},
            {"n": 3, "from": "sender", "text": "Sunt într-o bază îndepărtată și nu pot accesa salariul. M-ai putea ajuta cu un card preplătit Paysafe de 500 lei ca să ne putem revedea? Nu mai spune nimănui."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["ROMANCE"],
        "expected_alert": 3,
    },
    {
        "id": "ADV_PARA_REMOTE_01",
        "channel": "call_transcript",
        "sender": {"name": None, "address": "+40 318 000 111", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună ziua, sunt tehnician internet. Aveți o eroare gravă pe calculator, hackerii vă urmăresc."},
            {"n": 2, "from": "sender", "text": "Descărcați aplicația de partajare a ecranului ca să vă văd desktopul de la distanță și să reparăm."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["TECH_SUPPORT"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_FAMILY_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 881", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Bună tăticule, scriu de pe cartela unui coleg, mi s-a închis telefonul vechi. Mă poți ajuta cu 1.400 lei pe Revolut azi?"}],
        "expected_verdict": "SCAM",
        "expected_types": ["FAMILY_EMERGENCY"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_BAILIFF_01",
        "channel": "email",
        "sender": {"name": "Executor Judecătoresc", "address": "notificari@portal-poprire.xyz", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Aveți poprire pe venituri pentru o taxă restantă. Achitați 380 lei azi pe portal-poprire.xyz ca să evităm sechestrul."}],
        "expected_verdict": "SCAM",
        "expected_types": ["AUTHORITY_IMPERSONATION"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_MINISTRY_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 612", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Ministerul Energiei oferă sprijin financiar de 700 lei pentru pensionari. Introduceți datele cardului și seria de CI pe sprijin-energie.info"}],
        "expected_verdict": "SCAM",
        "expected_types": ["AUTHORITY_IMPERSONATION"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_JOB_01",
        "channel": "whatsapp",
        "sender": {"name": "HR Agency", "address": "+40 7xx xxx 719", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Căutăm colaboratori pentru evaluări pe Google Maps, plătim 350 RON pe zi. Scrieți-ne pe Telegram și trimiteți avansul de activare de 150 lei."}],
        "expected_verdict": "SCAM",
        "expected_types": ["JOB_OFFER"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_UTILITY_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 909", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Enel Energie: echipa de teren va sista furnizarea azi la ora 17:00 pentru debit restant dacă nu plătiți 310 lei pe enel-facturi.info"}],
        "expected_verdict": "SCAM",
        "expected_types": ["OTHER"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_PARA_INVEST_01",
        "channel": "chat",
        "sender": {"name": "AI Trading", "address": "bot_invest", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Robotul nostru AI generează randament constant de 18% lunar pe bursa europeană. Depuneți suma inițială de 200 € azi."}],
        "expected_verdict": "SCAM",
        "expected_types": ["INVESTMENT"],
        "expected_alert": 1,
    },
    {
        "id": "ADV_SHORTENER_COURIER_01",
        "channel": "sms",
        "sender": {"name": None, "address": "+40 7xx xxx 215", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "CurierExpres: Coletul este reținut în vamă. Taxa de procesare este 4 lei. Accesați urgent: bit.ly/3xColetRo"}],
        "expected_verdict": "SCAM",
        "expected_types": ["COURIER_FEE"],
        "expected_alert": 1,
    },

    # --- 3. Slow-burn Conversational Thread ---
    {
        "id": "ADV_SLOW_CRYPTO_01",
        "channel": "whatsapp",
        "sender": {"name": "Sofia", "address": "+44 7xxx xxx 901", "known_contact": False},
        "messages": [
            {"n": 1, "from": "sender", "text": "Bună! Scuze, am vrut să îi scriu unei prietene din București."},
            {"n": 2, "from": "reader", "text": "Nicio problemă."},
            {"n": 3, "from": "sender", "text": "Ce drăguță sunteți! Eu locuiesc în Elveția și lucrez în analiză financiară."},
            {"n": 4, "from": "reader", "text": "Frumos."},
            {"n": 5, "from": "sender", "text": "Chiar azi am făcut un profit frumos din tranzacții digitale."},
            {"n": 6, "from": "reader", "text": "Bravo."},
            {"n": 7, "from": "sender", "text": "Haideți pe Telegram, vă arăt cum să obțineți profit garantat de 25% pe lună fără niciun risc."},
            {"n": 8, "from": "sender", "text": "Depuneți doar 1.000 lei astazi pe platforma swiss-crypto-vip.com ca să activăm contul."},
        ],
        "expected_verdict": "SCAM",
        "expected_types": ["INVESTMENT"],
        "expected_alert": 7,
    },

    # --- 4. Hard-Negative Genuine Traps (MUST BE SAFE!) ---
    {
        "id": "ADV_SAFE_NEWS_WARN_01",
        "channel": "whatsapp",
        "sender": {"name": "Andrei (fiul)", "address": "+40 7xx xxx 123", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Mami, ai văzut la știri ce țeapă cu AnyDesk și coduri SMS? Ai grijă să nu instalezi nimic și să nu dai PIN-ul nimănui!"}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_BANK_EDU_01",
        "channel": "email",
        "sender": {"name": "Banca Dunarea", "address": "info@bancadunarea.ro", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Banca Dunărea vă informează: infractorii cer codul CVV și transferul banilor în conturi de siguranță. Banca nu vă va cere niciodată datele cardului pe link."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_COURIER_OK_01",
        "channel": "sms",
        "sender": {"name": "CurierExpres", "address": "CurierExpres", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "CurierExpres: Livrarea coletului AWB 112233 a fost reprogramată pentru mâine, ramburs 0 lei. Modificați intervalul doar pe curierexpres.ro."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_HOSPITAL_OK_01",
        "channel": "whatsapp",
        "sender": {"name": "Nepotul Vlad", "address": "+40 7xx xxx 333", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Buni, am ieșit de la spital după control, totul e bine! Nu am nevoie de bani sau nimic, ne vedem mâine."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_COWORKER_CHAT_01",
        "channel": "chat",
        "sender": {"name": "Coleg Birou", "address": "+40 7xx xxx 444", "known_contact": True},
        "messages": [{"n": 1, "from": "sender", "text": "Bună ziua, haideți pe WhatsApp la ora 14:00 ca să discutăm prezentarea de mâine."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_2FA_EXPIRES_01",
        "channel": "sms",
        "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Codul dvs. unic de autentificare este 991204 și expiră în 5 minute. Nu comunicați acest cod nimănui."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_CARDIO_CLINIC_01",
        "channel": "sms",
        "sender": {"name": "Clinica CardioMed", "address": "+40 314 111 222", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Clinica CardioMed: rezultatele analizelor pentru colesterol sunt gata. Vă așteptăm mâine la cabinet la ora 11:00."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
    {
        "id": "ADV_SAFE_PENSION_CREDIT_01",
        "channel": "sms",
        "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
        "messages": [{"n": 1, "from": "sender", "text": "Banca Dunărea: Contul dvs. a fost alimentat cu suma de 3.200 lei. Sold disponibil pe bancadunarea.ro."}],
        "expected_verdict": "SAFE",
        "expected_types": ["NONE"],
        "expected_alert": None,
    },
]


def run_adversarial_stress():
    pipeline = ScamShieldPipeline()
    passed = 0
    print("=" * 80)
    print(f"RUNNING ADVERSARIAL & PARAPHRASED STRESS SUITE ({len(ADVERSARIAL_SCENARIOS)} SCENARIOS)")
    print("=" * 80)

    for s in ADVERSARIAL_SCENARIOS:
        res = pipeline.analyze_scenario(s)
        v_ok = res["verdict"] == s["expected_verdict"]
        t_ok = res["scam_type"] in s["expected_types"]
        a_ok = (s["expected_alert"] is None) or (res["first_alert"] == s["expected_alert"])
        ok = v_ok and t_ok and a_ok
        if ok:
            passed += 1
        status = "✅ PASS" if ok else "❌ FAIL"
        print(f"[{s['id']:<24}] {res['verdict']:<10} ({res['risk_score']:>3}p) | {res['scam_type']:<24} | alert={str(res['first_alert']):<4} | {status}")
        if not ok:
            print(f"   EXP: {s['expected_verdict']} / {s['expected_types']} / alert={s['expected_alert']}")
            print(f"   GOT: {res['verdict']} / {res['scam_type']} / alert={res['first_alert']} flags={res['red_flags']}")

    print("-" * 80)
    print(f"ADVERSARIAL STRESS RESULT: {passed}/{len(ADVERSARIAL_SCENARIOS)} ({passed/len(ADVERSARIAL_SCENARIOS)*100:.1f}%)")
    print("=" * 80)
    return passed, len(ADVERSARIAL_SCENARIOS)


if __name__ == "__main__":
    run_adversarial_stress()
