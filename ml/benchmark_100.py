import json
import random
from typing import Dict, List, Tuple
from scam_detector.pipeline import ScamShieldPipeline

def build_100_scenarios() -> List[Dict]:
    scenarios = []

    # Template generators for all 13 types and variations
    # -------------------------------------------------------------
    # 1. BANK_IMPERSONATION (10 scenarios)
    # -------------------------------------------------------------
    bank_names = ["Banca Dunărea", "Banca Transilvania", "BCR", "BRD", "ING", "Raiffeisen"]
    fake_bank_domains = ["bancadunarea-sigur.com", "bcr-actualizare.net", "ing-cont-blocat.info", "raiffeisen-autentificare.org"]
    for i in range(10):
        b = bank_names[i % len(bank_names)]
        d = fake_bank_domains[i % len(fake_bank_domains)]
        if i % 2 == 0:
            scenarios.append({
                "id": f"GEN_BANK_{i+1:02d}",
                "channel": "sms",
                "sender": {"name": b.replace(" ", ""), "address": b.replace(" ", ""), "known_contact": False},
                "messages": [
                    {"n": 1, "from": "sender", "text": f"{b}: Contul dvs. a fost restricționat temporar. Pentru deblocare în 24 de ore, accesați: {d}/securitate"}
                ],
                "expected_verdict": "SCAM",
                "expected_type": "BANK_IMPERSONATION"
            })
        else:
            scenarios.append({
                "id": f"GEN_BANK_{i+1:02d}",
                "channel": "call_transcript",
                "sender": {"name": None, "address": f"+40 31{i} 111 222", "known_contact": False},
                "messages": [
                    {"n": 1, "from": "sender", "text": f"Bună ziua, vă sun de la departamentul antifraudă {b}."},
                    {"n": 2, "from": "reader", "text": "Bună ziua, ce problemă este?"},
                    {"n": 3, "from": "sender", "text": "Avem o tranzacție suspectă. Vă rog să-mi citiți numărul cardului și data expirării pentru blocare."}
                ],
                "expected_verdict": "SCAM",
                "expected_type": "BANK_IMPERSONATION"
            })

    # -------------------------------------------------------------
    # 2. COURIER_FEE (8 scenarios)
    # -------------------------------------------------------------
    courier_domains = ["curierexpres-taxa.net", "livrare-urgent.info", "dpd-vamal.com", "posta-reprogramare.biz"]
    for i in range(8):
        d = courier_domains[i % len(courier_domains)]
        amount = f"{2.50 + i*0.80:.2f}".replace(".", ",")
        scenarios.append({
            "id": f"GEN_COURIER_{i+1:02d}",
            "channel": "sms",
            "sender": {"name": None, "address": f"+40 7{i}2 333 444", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"CurierExpres: Pachetul dvs. este reținut în depozit. Achitați taxa vamală de {amount} lei pentru livrare: {d}"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "COURIER_FEE"
        })

    # -------------------------------------------------------------
    # 3. AUTHORITY_IMPERSONATION (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        if i % 2 == 0:
            scenarios.append({
                "id": f"GEN_AUTH_{i+1:02d}",
                "channel": "email",
                "sender": {"name": "ANAF Plati", "address": "notificari@anaf-restituiri.com", "known_contact": False},
                "messages": [
                    {"n": 1, "from": "sender", "text": "Stimate contribuabil, aveți o restituire de impozit în valoare de 850 lei. Completați datele cardului până la 30.11 pe anaf-restituiri.com/form"}
                ],
                "expected_verdict": "SCAM",
                "expected_type": "AUTHORITY_IMPERSONATION"
            })
        else:
            scenarios.append({
                "id": f"GEN_AUTH_{i+1:02d}",
                "channel": "call_transcript",
                "sender": {"name": None, "address": f"+40 21{i} 555 777", "known_contact": False},
                "messages": [
                    {"n": 1, "from": "sender", "text": "Bună ziua, suntem de la Casa de Pensii. Facem recalcularea deciziilor de pensionare."},
                    {"n": 2, "from": "reader", "text": "Sărut mâna, da."},
                    {"n": 3, "from": "sender", "text": "Pensia dumneavoastră va crește cu 420 lei. Pentru confirmare, spuneți-mi CNP-ul și datele cardului pe care primiți banii."}
                ],
                "expected_verdict": "SCAM",
                "expected_type": "AUTHORITY_IMPERSONATION"
            })

    # -------------------------------------------------------------
    # 4. FAMILY_EMERGENCY (8 scenarios)
    # -------------------------------------------------------------
    names = ["Alex", "Matei", "Radu", "Elena", "Mihai", "Cristi", "Ioana", "Andrei"]
    for i in range(8):
        child = names[i]
        scenarios.append({
            "id": f"GEN_FAM_{i+1:02d}",
            "channel": "whatsapp",
            "sender": {"name": None, "address": f"+40 76{i} 999 00{i}", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Bună mami! Mi s-a spart telefonul și ăsta e noul meu număr. Salvează-l te rog ❤️"},
                {"n": 2, "from": "reader", "text": "Doamne, ce s-a întâmplat?"},
                {"n": 3, "from": "sender", "text": f"Sunt {child}. Sunt bine dar trebuie să plătesc o factură urgentă azi de 1.200 lei și nu-mi merge aplicația. Îmi faci tu un transfer?"},
                {"n": 4, "from": "sender", "text": "Te rog nu-i spune lui tata, rezolvăm noi între noi."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "FAMILY_EMERGENCY"
        })

    # -------------------------------------------------------------
    # 5. TECH_SUPPORT (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        scenarios.append({
            "id": f"GEN_TECH_{i+1:02d}",
            "channel": "call_transcript",
            "sender": {"name": None, "address": f"+40 37{i} 444 888", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua, vă sun de la suportul tehnic Microsoft Windows. Calculatorul dvs trimite viruși periculoși în rețea."},
                {"n": 2, "from": "reader", "text": "Ce viruși? Eu doar mă uit la rețete."},
                {"n": 3, "from": "sender", "text": "Vă ajutăm noi acum. Vă rugăm să instalați programul AnyDesk pentru acces de la distanță."},
                {"n": 4, "from": "reader", "text": "Gata, am instalat."},
                {"n": 5, "from": "sender", "text": "Acum introduceți datele bancare pentru a verifica dacă fondurile sunt în siguranță."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "TECH_SUPPORT"
        })

    # -------------------------------------------------------------
    # 6. MARKETPLACE (8 scenarios)
    # -------------------------------------------------------------
    items = ["telefon", "televizor", "cărucior", "chitară", "laptop", "ceas", "mobilă", "aparat foto"]
    for i in range(8):
        item = items[i]
        scenarios.append({
            "id": f"GEN_MARKET_{i+1:02d}",
            "channel": "chat",
            "sender": {"name": f"Cumpărător_{i+100}", "address": f"user_market_{i}", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Bună ziua, mai vindeți {item}ul?"},
                {"n": 2, "from": "reader", "text": "Bună, da, este disponibil."},
                {"n": 3, "from": "sender", "text": f"Super! Am plătit prin Livrare Sigură. Pentru a încasa banii, introduceți datele cardului aici: piatamea-livrare{i}.com"},
                {"n": 4, "from": "sender", "text": "Grăbiți-vă, linkul expiră în 30 de minute."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "MARKETPLACE"
        })

    # -------------------------------------------------------------
    # 7. ACCOUNT_TAKEOVER (8 scenarios)
    # -------------------------------------------------------------
    friends = ["Elena (colega)", "Radu vecinul", "Mihai vărul", "Andreea", "Gheorghe", "Carmen", "Simona", "Dan"]
    for i in range(8):
        fr = friends[i]
        scenarios.append({
            "id": f"GEN_ATO_{i+1:02d}",
            "channel": "whatsapp",
            "sender": {"name": fr, "address": f"+40 72{i} 666 777", "known_contact": True},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Salut! Scuze că te deranjez, ți-am trimis din greșeală un cod de 6 cifre prin SMS. Mi-l poți trimite înapoi te rog? E urgent!"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "ACCOUNT_TAKEOVER"
        })

    # -------------------------------------------------------------
    # 8. INVESTMENT (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        sum_eur = 150 + i * 50
        profit_eur = 2500 + i * 500
        scenarios.append({
            "id": f"GEN_INVEST_{i+1:02d}",
            "channel": "sms",
            "sender": {"name": None, "address": f"+40 73{i} 888 111", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Oportunitate unică de investiții! Depuneți {sum_eur} euro în crypto și obțineți profit garantat de {profit_eur} euro pe lună. Înscrieți-vă acum pe profit-garantat{i}.biz"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "INVESTMENT"
        })

    # -------------------------------------------------------------
    # 9. ROMANCE (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        scenarios.append({
            "id": f"GEN_ROMANCE_{i+1:02d}",
            "channel": "chat",
            "sender": {"name": f"Soldier_Alex_{i}", "address": f"soldier_{i}", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună draga mea, mă gândesc la tine mereu de când vorbim."},
                {"n": 2, "from": "reader", "text": "Bună, cum e acolo?"},
                {"n": 3, "from": "sender", "text": f"Sunt blocat în misiune militară și mi-au blocat contul. Te implor din suflet, transferă-mi {400 + i*100} euro urgent ca să pot plăti biletul de avion și să vin la tine."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "ROMANCE"
        })

    # -------------------------------------------------------------
    # 10. JOB_OFFER (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        scenarios.append({
            "id": f"GEN_JOB_{i+1:02d}",
            "channel": "whatsapp",
            "sender": {"name": "Recrutare Globală", "address": f"+40 74{i} 000 333", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua! Căutăm colaboratori pentru muncă ușoară online: vizionați clipuri pe TikTok și câștigați 300 lei pe zi."},
                {"n": 2, "from": "reader", "text": "Sunt interesat, ce trebuie să fac?"},
                {"n": 3, "from": "sender", "text": f"Pentru a primi pachetul de sarcini, achitați taxa administrativă de {50 + i*10} lei pe job-online-ro{i}.com"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "JOB_OFFER"
        })

    # -------------------------------------------------------------
    # 11. PRIZE_LOTTERY (8 scenarios)
    # -------------------------------------------------------------
    for i in range(8):
        prize = "unui iPhone 16" if i % 2 == 0 else "unui voucher de 5.000 lei"
        scenarios.append({
            "id": f"GEN_PRIZE_{i+1:02d}",
            "channel": "sms",
            "sender": {"name": None, "address": f"+40 75{i} 111 999", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Felicitări! Numărul dvs. a fost extras câștigătorul {prize} la tombola MegaShop! Răspundeți cu DA pentru revendicare."}
            ],
            "expected_verdict": "SUSPICIOUS",
            "expected_type": "PRIZE_LOTTERY"
        })

    # -------------------------------------------------------------
    # 12. SAFE LEGITIMATE MESSAGES / TRAPS (18 scenarios)
    # -------------------------------------------------------------
    # Safe Bank messages (OTP warning, statement, regular notice)
    for i in range(4):
        code = 100000 + i * 2345
        scenarios.append({
            "id": f"GEN_SAFE_BANK_{i+1:02d}",
            "channel": "sms",
            "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"Banca Dunărea: Codul de confirmare este {code}. Nu comunicați acest cod nimănui, nici angajaților băncii."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        })

    # Safe Courier notices (AWB, delivery window, 0 lei ramburs, official site)
    for i in range(4):
        awb = 7891230 + i * 111
        scenarios.append({
            "id": f"GEN_SAFE_COURIER_{i+1:02d}",
            "channel": "sms",
            "sender": {"name": "CurierExpres", "address": "CurierExpres", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": f"CurierExpres: Coletul AWB {awb} va fi livrat azi între 10:00 și 14:00. Ramburs: 0 lei. Urmărire: curierexpres.ro/awb"}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        })

    # Safe Family / Friends everyday conversations
    friend_texts = [
        [("Mihai", "Salut, vii azi la fotbal la ora 19?"), ("reader", "Da, vin sigur."), ("Mihai", "Super, ne vedem la teren!")],
        [("Mama", "Bună puiule, ai ajuns cu bine la birou?"), ("reader", "Da mami, totul e bine."), ("Mama", "Mă bucur, spor la treabă!")],
        [("Ana", "Ne vedem diseară la restaurant? Am făcut eu rezervarea."), ("reader", "Perfect, la cât?"), ("Ana", "La 20:30.")],
        [("George", "Ai terminat proiectul de la facultate?"), ("reader", "Aproape, mai am puțin."), ("George", "Baftă multă!")],
        [("Tati", "Salut, ți-am lăsat cheile pe masă."), ("reader", "Mulțumesc, le-am văzut!"), ("Tati", "Cu drag!")],
        [("Andreea", "Nu uita să cumperi pâine când vii spre casă."), ("reader", "Sigur, iau acum."), ("Andreea", "Mulțumesc mult!")]
    ]
    for i, ft in enumerate(friend_texts):
        msgs = []
        for n, (sender_lbl, txt) in enumerate(ft, 1):
            msgs.append({
                "n": n,
                "from": "reader" if sender_lbl == "reader" else "sender",
                "text": txt
            })
        scenarios.append({
            "id": f"GEN_SAFE_CHAT_{i+1:02d}",
            "channel": "whatsapp",
            "sender": {"name": ft[0][0], "address": f"+40 720 000 00{i}", "known_contact": True},
            "messages": msgs,
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        })

    # Safe Marketplace inquiry (buyer asks normal questions, no phishing link)
    for i in range(4):
        scenarios.append({
            "id": f"GEN_SAFE_MARKET_{i+1:02d}",
            "channel": "chat",
            "sender": {"name": f"Client_{i}", "address": f"client_{i}", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua! Produsul are urme de uzură?"},
                {"n": 2, "from": "reader", "text": "Bună, nu, este în stare impecabilă."},
                {"n": 3, "from": "sender", "text": "Am înțeles, mulțumesc frumos pentru răspuns!"}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        })

    return scenarios

def run_100_benchmark():
    scenarios = build_100_scenarios()
    total = len(scenarios)
    print(f"Total benchmark scenarios generated: {total}\n")

    pipeline = ScamShieldPipeline()

    verdict_correct = 0
    type_correct = 0
    perfect_matches = 0

    failed_cases = []

    for sc in scenarios:
        res = pipeline.analyze_scenario(sc)
        v_ok = (res["verdict"] == sc["expected_verdict"])
        t_ok = (res["scam_type"] == sc["expected_type"])

        if v_ok: verdict_correct += 1
        if t_ok: type_correct += 1
        if v_ok and t_ok:
            perfect_matches += 1
        else:
            failed_cases.append((sc, res))

    print("=" * 80)
    print("SCAM SHIELD: 100 REALISTIC STRESS-BENCHMARK RESULTS")
    print("=" * 80)
    print(f"Total Scenarios Evaluated: {total}")
    print(f"Verdict Accuracy:          {verdict_correct}/{total} ({verdict_correct/total*100:.2f}%)")
    print(f"Scam Type Accuracy:        {type_correct}/{total} ({type_correct/total*100:.2f}%)")
    print(f"Perfect End-to-End Match:  {perfect_matches}/{total} ({perfect_matches/total*100:.2f}%)")
    print("=" * 80)

    if failed_cases:
        print(f"\nDiscrepancies found ({len(failed_cases)}):")
        for sc, res in failed_cases[:10]:
            print(f"[{sc['id']}] Expected: {sc['expected_verdict']} / {sc['expected_type']} | Got: {res['verdict']} ({res['risk_score']}p) / {res['scam_type']}")
            print(f"   Flags detected: {res['red_flags']}")
            print(f"   Warning: {res['warning']}\n")

    return perfect_matches == total

if __name__ == "__main__":
    run_100_benchmark()
