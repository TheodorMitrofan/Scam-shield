import json
from scam_detector.pipeline import ScamShieldPipeline

def run_stress_tests():
    pipeline = ScamShieldPipeline()

    test_cases = [
        # 1. INVESTMENT scam
        {
            "id": "ST_INVEST_01",
            "channel": "sms",
            "sender": {"name": None, "address": "+40 799 111 222", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Oportunitate unică! Investește 250 euro în acțiuni crypto cu profit garantat de 3.000 euro pe lună. Înscrie-te acum: bursa-profit.biz"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "INVESTMENT"
        },
        # 2. JOB_OFFER scam
        {
            "id": "ST_JOB_01",
            "channel": "whatsapp",
            "sender": {"name": "Recrutare Online", "address": "+40 788 333 444", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua! Compania noastră oferă job part-time de acasă: dați like-uri pe YouTube și primiți 200 lei pe zi."},
                {"n": 2, "from": "reader", "text": "Cum mă înscriu?"},
                {"n": 3, "from": "sender", "text": "Pentru activarea contului de angajat, achitați taxa administrativă de 49 lei aici: recrutare-joburi.net"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "JOB_OFFER"
        },
        # 3. ROMANCE scam
        {
            "id": "ST_ROMANCE_01",
            "channel": "chat",
            "sender": {"name": "David", "address": "david_soldier99", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună draga mea, mă gândesc la tine mereu."},
                {"n": 2, "from": "reader", "text": "Bună David, ce faci?"},
                {"n": 3, "from": "sender", "text": "Sunt blocat în misiune militară și mi-au blocat contul. Te implor din suflet, transferă-mi 500 euro până mâine ca să pot veni acasă."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "ROMANCE"
        },
        # 4. TRAP SAFE: Legitimate bank account statement (no requests)
        {
            "id": "ST_SAFE_BANK_01",
            "channel": "sms",
            "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Banca Dunărea: Extrasul dvs. de cont pentru luna trecută a fost emis și poate fi consultat în siguranță pe: bancadunarea.ro"}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 5. TRAP SAFE: Friend asking normal question
        {
            "id": "ST_SAFE_FRIEND_01",
            "channel": "whatsapp",
            "sender": {"name": "Mihai", "address": "+40 722 555 666", "known_contact": True},
            "messages": [
                {"n": 1, "from": "sender", "text": "Salut! Ne vedem diseară la film la ora 20:00?"},
                {"n": 2, "from": "reader", "text": "Da, sigur!"},
                {"n": 3, "from": "sender", "text": "Super, iau eu biletele."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 6. Slow build-up conversation (bank imposter asking for card in msg 6)
        {
            "id": "ST_SLOW_BUILDUP_01",
            "channel": "call_transcript",
            "sender": {"name": None, "address": "+40 312 999 888", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua, vă contactăm de la departamentul antifraudă al Băncii Dunărea."},
                {"n": 2, "from": "reader", "text": "Bună ziua, s-a întâmplat ceva?"},
                {"n": 3, "from": "sender", "text": "Am observat o încercare de conectare neobișnuită din străinătate."},
                {"n": 4, "from": "reader", "text": "Aoleu, chiar nu am fost eu!"},
                {"n": 5, "from": "sender", "text": "Nu vă îngrijorați, vă putem proteja fondurile imediat."},
                {"n": 6, "from": "sender", "text": "Pentru securizarea contului, citiți-mi acum numărul cardului și codul de securitate de pe spate."}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "BANK_IMPERSONATION"
        },
        # 7. Diacritic-free message with emojis
        {
            "id": "ST_DIACRITICS_EMOJI_01",
            "channel": "whatsapp",
            "sender": {"name": None, "address": "+40 755 888 999", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Buna mami mi s-a stricat tel 😭 asta e nr meu nou salveaza-l"},
                {"n": 2, "from": "reader", "text": "Cine esti?"},
                {"n": 3, "from": "sender", "text": "Andrei sunt mami! Am o urgenta tre sa platesc 900 lei acum poti sa mi transferi te rog 🙏"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "FAMILY_EMERGENCY"
        },
        # 8. Empty / whitespace message (robustness check)
        {
            "id": "ST_EMPTY_01",
            "channel": "sms",
            "sender": {"name": None, "address": "+40 700 000 000", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "   "}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        }
    ]

    print("=" * 75)
    print("RUNNING ADVANCED STRESS TESTS ON UNSEEN SCENARIOS (ROMANIAN)")
    print("=" * 75)
    passed = 0
    total = len(test_cases)

    for tc in test_cases:
        res = pipeline.analyze_scenario(tc)
        v_match = (res["verdict"] == tc["expected_verdict"])
        t_match = (res["scam_type"] == tc["expected_type"])
        ok = v_match and t_match

        status = "✅ PASS" if ok else "❌ FAIL"
        if ok: passed += 1

        print(f"[{tc['id']}] {tc['expected_type']:<20} -> Verdict: {res['verdict']} ({res['risk_score']}p) | Type: {res['scam_type']} | {status}")
        if not ok:
            print(f"   Expected: {tc['expected_verdict']} / {tc['expected_type']}")
            print(f"   Got:      {res['verdict']} / {res['scam_type']}, Flags: {res['red_flags']}")
            print(f"   Warning:  {res['warning']}")

    print("-" * 75)
    print(f"STRESS TEST RESULTS: {passed}/{total} ({passed/total*100:.1f}%) Passed Successfully!")
    print("=" * 75)

if __name__ == "__main__":
    run_stress_tests()
