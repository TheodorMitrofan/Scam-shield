from scam_detector.pipeline import ScamShieldPipeline

def run_creative_traps():
    pipeline = ScamShieldPipeline()

    traps = [
        # 1. Reverse psychology (Attacker warns against scams to trick victim)
        {
            "id": "CR_REV_PSYCH_01",
            "channel": "sms",
            "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Atenție la escrocherii! Banca Dunărea vă informează că circulă mesaje false. Pentru a verifica dacă sunteți în siguranță, introduceți datele cardului pe: bancadunarea-protectie.com"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "BANK_IMPERSONATION"
        },
        # 2. HTTP Basic Auth link trick (http://bancadunarea.ro@evil.com)
        {
            "id": "CR_AUTH_URL_01",
            "channel": "sms",
            "sender": {"name": None, "address": "+40 711 222 333", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "CurierExpres: Coletul dvs. e blocat. Plătiți taxa de 3 lei pe: http://curierexpres.ro@plata-colet.net/taxa"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "COURIER_FEE"
        },
        # 3. The Classic "Accidentul" Grandma Scam
        {
            "id": "CR_ACCIDENT_SCAM_01",
            "channel": "call_transcript",
            "sender": {"name": None, "address": "+40 311 000 999", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Sărut mâna buni! Sunt Vlad... Plâng de nu mai pot!"},
                {"n": 2, "from": "reader", "text": "Vlăduț? Ce s-a întâmplat maică?"},
                {"n": 3, "from": "sender", "text": "Am făcut un accident grav cu mașina, am lovit un om pe trecere și sunt la poliție!"},
                {"n": 4, "from": "reader", "text": "Doamne apără și păzește! Cum adică?"},
                {"n": 5, "from": "sender", "text": "Avocatul zice că dacă plătim 15.000 lei daune acum scăp de arest! Te rog nu-i spune mamei că moare de inimă! Poți să-mi transferi banii urgent?"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "FAMILY_EMERGENCY"
        },
        # 4. Legit bank fraud check (asking YES/NO, warning never to give PIN/CVV)
        {
            "id": "CR_LEGIT_FRAUD_CHECK_01",
            "channel": "sms",
            "sender": {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Banca Dunărea: A fost detectată o încercare de plată de 200 lei la magazinul X. Răspundeți cu DA dacă ați fost dvs. sau cu NU pentru blocarea cardului. Nu vă vom cere niciodată codul PIN sau CVV."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 5. Legit dentist appointment
        {
            "id": "CR_LEGIT_DENTIST_01",
            "channel": "sms",
            "sender": {"name": "DentalPlus", "address": "DentalPlus", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Clinica DentalPlus: Vă amintim de programarea la stomatologie de mâine, ora 15:00. Vă rugăm confirmați cu DA sau sunați la 021 999 888."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 6. Legit job interview (mentions building ID card at reception)
        {
            "id": "CR_LEGIT_INTERVIEW_01",
            "channel": "email",
            "sender": {"name": "HR Tech Solutions", "address": "recrutare@techsolutions.ro", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua! Am selectat CV-ul dvs. pentru postul de analist. Vă așteptăm la interviu marți la birou. Vă rugăm să aveți cartea de identitate pentru accesul la recepție."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 7. Electricity cutoff extortion
        {
            "id": "CR_ELEC_CUTOFF_01",
            "channel": "sms",
            "sender": {"name": None, "address": "+40 777 666 555", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Electrica Notificare: Factura dvs. este restantă cu 450 lei. Dacă nu achitați în 24 de ore, curentul va fi întrerupt. Achitați urgent pe: plata-curent-rapid.info"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "OTHER"
        },
        # 8. Charity / Emotional donation scam
        {
            "id": "CR_CHARITY_SCAM_01",
            "channel": "whatsapp",
            "sender": {"name": "Salvați o viață", "address": "+40 733 999 111", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Ajutați un copil bolnav! Strângem fonduri urgente pentru operația micuțului Luca. Vă implorăm din suflet, trimiteți orice sumă pe cont-donatii-urgente.org până vineri!"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "OTHER"
        },
        # 9. Fake buyer "I paid, you just enter card to receive money"
        {
            "id": "CR_MARKET_INVERSE_01",
            "channel": "chat",
            "sender": {"name": "Cumpărător OLX", "address": "buyer_olx_44", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Nu trebuie să plătești nimic, am plătit eu curierul! Ca să primești banii în contul tău, introdu datele cardului aici: livrare-olx-sigura.net"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "MARKETPLACE"
        },
        # 10. Long 8-message chat with late hook at message 7
        {
            "id": "CR_LATE_HOOK_01",
            "channel": "chat",
            "sender": {"name": "Cumpărător Andrei", "address": "andrei_biker", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua! Mai e de vânzare bicicleta?"},
                {"n": 2, "from": "reader", "text": "Bună, da, este disponibilă."},
                {"n": 3, "from": "sender", "text": "Ce mărime are cadrul?"},
                {"n": 4, "from": "reader", "text": "Este mărimea L, roți de 29."},
                {"n": 5, "from": "sender", "text": "Super, exact ce căutam. Are zgârieturi pe furcă?"},
                {"n": 6, "from": "reader", "text": "Nu, e aproape nouă, folosită de câteva ori."},
                {"n": 7, "from": "sender", "text": "Perfect, o iau sigur! Am trimis banii prin Livrare Sigură, introduceți datele cardului aici să intrați în posesia sumei: piatamea-transfer.com"},
                {"n": 8, "from": "sender", "text": "Grăbiți-vă, linkul e valabil o oră!"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "MARKETPLACE",
            "expected_alert": 7
        },
        # 11. Short link URL trap (bit.ly)
        {
            "id": "CR_SHORT_URL_01",
            "channel": "sms",
            "sender": {"name": "ANAF", "address": "ANAF", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "ANAF: Restituire disponibilă de 1.400 lei. Accesați în 24h formularul securizat: bit.ly/anaf-bani-2024"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "AUTHORITY_IMPERSONATION"
        },
        # 12. Channel switch prompt (moving to Telegram)
        {
            "id": "CR_TELEGRAM_SWITCH_01",
            "channel": "chat",
            "sender": {"name": "Client_77", "address": "client_77", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Nu-mi merge aplicația aici deloc. Hai să continuăm discuția pe Telegram la @invest_crypto_fast ca să facem plata."}
            ],
            "expected_verdict": "SUSPICIOUS",
            "expected_type": "INVESTMENT"
        },
        # 13. Legit Netflix subscription renewal notice
        {
            "id": "CR_LEGIT_SUB_01",
            "channel": "email",
            "sender": {"name": "Serviciu Streaming", "address": "info@streaming.ro", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Abonamentul dvs. lunar a fost reînnoit automat cu suma de 49 lei. Factura este disponibilă în contul dvs. Nu este necesară nicio acțiune."}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 14. Military Romance Customs Scam
        {
            "id": "CR_ROMANCE_CUSTOMS_01",
            "channel": "whatsapp",
            "sender": {"name": "Căpitan John", "address": "+44 7700 900123", "known_contact": False},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună iubito, mă gândesc la tine mereu în misiune militară."},
                {"n": 2, "from": "reader", "text": "Bună John!"},
                {"n": 3, "from": "sender", "text": "Ți-am trimis un pachet cu aur și economiile mele. Vama cere o taxă urgentă de 1.200 lei pentru eliberare. Te rog plătește tu pe: vama-diplomatica.com, îți dau înzecit când ajung!"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "ROMANCE"
        },
        # 15. Genuine friendly recipe exchange (Long 8-message chat)
        {
            "id": "CR_LEGIT_RECIPE_01",
            "channel": "whatsapp",
            "sender": {"name": "Bunica Maria", "address": "+40 722 111 999", "known_contact": True},
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună puiule, cum se face aluatul de cozonac?"},
                {"n": 2, "from": "reader", "text": "Bună buni! Pui făină, ouă, lapte călduț și drojdie."},
                {"n": 3, "from": "sender", "text": "Cât lapte pui la un kilogram de făină?"},
                {"n": 4, "from": "reader", "text": "Cam 500 ml buni, să fie călduț, nu fierbinte."},
                {"n": 5, "from": "sender", "text": "Am înțeles maică. Și zahăr pui mult?"},
                {"n": 6, "from": "reader", "text": "Cam 250 de grame, după gust."},
                {"n": 7, "from": "sender", "text": "Mulțumesc mult dragul bunicii!"},
                {"n": 8, "from": "reader", "text": "Cu mare drag buni, abia aștept să gust!"}
            ],
            "expected_verdict": "SAFE",
            "expected_type": "NONE"
        },
        # 16. Recorder Investigation: 12-message health miracle cure story
        {
            "id": "CR_RECORDER_HEALTH_01",
            "channel": "call_transcript",
            "sender": {
                "name": "Institutul de Sanatate Vasculara",
                "address": "+40 372 999 444",
                "known_contact": False
            },
            "messages": [
                {"n": 1, "from": "sender", "text": "Bună ziua, doamnă Popescu. Vă contactez din partea Institutului European de Sănătate Vasculară."},
                {"n": 2, "from": "reader", "text": "Bună ziua. Cu ce ocazie mă căutați?"},
                {"n": 3, "from": "sender", "text": "Am văzut că ați completat un formular despre dureri articulare și oboseală cronică. Cum vă mai simțiți în ultima perioadă?"},
                {"n": 4, "from": "reader", "text": "Mă dor genunchii rău când urc scările și am tensiunea cam mare maică."},
                {"n": 5, "from": "sender", "text": "Exact cum mă temeam. Vă spun cu toată sinceritatea, ca medic: medicii de la policlinică vă ascund adevărul ca să vă țină dependentă de pastile chimice scumpe."},
                {"n": 6, "from": "reader", "text": "Aoleu, chiar așa? Mi-e frică să nu fac vreun atac cerebral..."},
                {"n": 7, "from": "sender", "text": "Și aveți toate motivele să vă temeți! Vasele dumneavoastră sunt înfundate în proporție de 85% cu depozite de calcar. Riscați o paralizie sau infarct în următoarele săptămâni dacă nu curățați vasele imediat!"},
                {"n": 8, "from": "reader", "text": "Doamne ferește! Ce pot să fac, domnule doctor? Spuneți-mi vă rog!"},
                {"n": 9, "from": "sender", "text": "Din fericire, profesorul universitar elvețian Keller a dezvoltat o formulă nanotehnologică unică, 100% naturală, care topește instant plăcile de colesterol și reface cartilajele."},
                {"n": 10, "from": "sender", "text": "În mod normal, tratamentul complet pentru 3 luni costă 4.800 de lei. Dar pentru că avem o campanie subvenționată pentru pensionari, astăzi plătiți doar 1.450 de lei pentru întregul pachet!"},
                {"n": 11, "from": "reader", "text": "E o sumă mare pentru pensia mea... Oare chiar funcționează?"},
                {"n": 12, "from": "sender", "text": "Dacă nu începeți tratamentul de mâine, săptămâna viitoare s-ar putea să fie prea târziu! Trimitem coletul acum prin curier expres, plătiți direct curierului când ajunge la ușă. Dați-mi adresa completă să blocăm promoția!"}
            ],
            "expected_verdict": "SCAM",
            "expected_type": "OTHER",
            "expected_alert": 7
        }
    ]

    print("=" * 80)
    print("RUNNING 16 HIGHLY CREATIVE ADVERSARIAL TRAP TESTS")
    print("=" * 80)

    passed = 0
    total = len(traps)

    for tc in traps:
        res = pipeline.analyze_scenario(tc)
        v_match = (res["verdict"] == tc["expected_verdict"])
        t_match = (res["scam_type"] == tc["expected_type"])
        a_match = True
        if "expected_alert" in tc:
            a_match = (res["first_alert"] == tc["expected_alert"])

        ok = v_match and t_match and a_match
        if ok: passed += 1
        status = "✅ PASS" if ok else "❌ FAIL"

        alert_info = f"Alert: #{res['first_alert']}" if res['first_alert'] else "Alert: None"
        print(f"[{tc['id']:<23}] {tc['expected_type']:<22} | Verdict: {res['verdict']:<10} ({res['risk_score']}p) | {alert_info:<12} | {status}")
        if not ok:
            print(f"   Expected: {tc['expected_verdict']} / {tc['expected_type']}")
            print(f"   Got:      {res['verdict']} / {res['scam_type']}, Flags: {res['red_flags']}")
            print(f"   Warning:  {res['warning']}\n")

    print("-" * 80)
    print(f"CREATIVE TRAPS RESULT: {passed}/{total} ({passed/total*100:.1f}%) Passed Successfully!")
    print("=" * 80)

if __name__ == "__main__":
    run_creative_traps()
