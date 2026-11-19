"""Generate a synthetic, locally-authored Romanian training set for the scam model.

No cloud LLM is used: every phrase below is hand-written by the team and slot-filled at random.
The official Validation Set is NOT used here (it stays a clean evaluation set).

Output: ml/data/synth.jsonl — one scenario per line, in the official input format, plus labels:
    {"id", "channel", "sender", "messages": [{n, from, text, flags: [...]}], "scam_type": "..."}
Usage: python ml/gen_synthetic.py [--n 4000] [--seed 13] [--out ml/data/synth.jsonl]
"""
import argparse
import json
import random
import unicodedata
from pathlib import Path

R = random.Random()

# ------------------------------------------------------------------ slot values
ORGS_BANK = ["Banca Dunărea", "BancaDunarea", "Banca Dunarea", "banca dumneavoastră", "Departamentul de securitate al băncii"]
ORGS_COURIER = ["CurierExpres", "Curier Expres", "Poșta", "firma de curierat"]
BAD_DOMAINS = {
    "bank": ["bancadunarea-securitate.com", "bancadunarea-verificare.net", "dunarea-online.info", "secure-bancadunarea.co",
             "bancadunarea.ro-confirmare.xyz", "bit.ly/bd-deblocare", "deblocare-card.online"],
    "courier": ["curierexpres-livrare.info", "curierexpres-taxa.com", "colet-reprogramare.net", "curier-express.top",
                "awb-tracking.site", "bit.ly/colet-ro"],
    "anaf": ["anaf-rambursari.net", "anaf-ro.info", "rambursare-anaf.com", "spv-anaf.online", "ghiseul-plati.net"],
    "market": ["piatamea-plati.com", "piatamea-livrare.net", "livrare-sigura-piatamea.info", "plata-securizata.shop"],
    "shop": ["megashop-premii.com", "megashop-tombola.net", "castiguri-megashop.info", "premiu-azi.click"],
    "invest": ["profit-sigur.online", "crypto-romania.top", "investitii-garantate.net", "bursa-ro.xyz"],
    "job": ["joburi-acasa.online", "task-plata.site", "angajari-rapide.info"],
    "generic": ["verificare-cont.net", "secure-login.online", "confirmare-date.info", "t.me/suport_ro"],
}
OK_LINKS = {"bank": ["bancadunarea.ro", "bancadunarea.ro/contact"], "courier": ["curierexpres.ro/awb", "curierexpres.ro"],
            "anaf": ["anaf.ro", "anaf.ro/spv"], "market": ["piatamea.ro", "piatamea.ro/comenzi"],
            "shop": ["megashop.ro", "megashop.ro/comenzi", "megashop.ro/oferte"]}
NAMES_M = ["Andrei", "Mihai", "Vlad", "Radu", "Alex", "Ionuț", "Cristi", "Bogdan", "Dani", "Sorin"]
NAMES_F = ["Ioana", "Maria", "Elena", "Ana", "Cristina", "Alina", "Diana", "Raluca", "Mihaela", "Andreea"]
FAMILY_ADDR = ["mami", "mamă", "tati", "bunico", "bunicule", "mamaie", "tataie"]
PRODUCTS = ["bicicleta", "canapeaua", "telefonul", "căruciorul", "frigiderul", "mașina de spălat", "laptopul", "geaca"]
APPS = ["Telegram", "WhatsApp", "Signal", "Viber"]
REMOTE_APPS = ["AnyDesk", "TeamViewer", "QuickSupport", "RustDesk"]


def amount():
    return R.choice(["2,99", "4,50", "9,99", "150", "300", "500", "850", "1.200", "1.850", "2.500", "3.000", "4.700"])


def slots(kind="generic"):
    m, f = R.choice(NAMES_M), R.choice(NAMES_F)
    return {
        "bank": R.choice(ORGS_BANK), "courier": R.choice(ORGS_COURIER),
        "bad": R.choice(BAD_DOMAINS.get(kind, BAD_DOMAINS["generic"])),
        "ok": R.choice(OK_LINKS.get(kind, ["megashop.ro"])),
        "sum": amount(), "h": R.choice(["24", "12", "48", "2", "6"]), "m": m, "f": f, "name": R.choice([m, f]),
        "fam": R.choice(FAMILY_ADDR), "prod": R.choice(PRODUCTS), "app": R.choice(APPS), "rapp": R.choice(REMOTE_APPS),
        "code": str(R.randint(100000, 999999)), "awb": str(R.randint(1000000, 9999999)),
        "date": f"{R.randint(1, 28):02d}.{R.randint(1, 12):02d}", "pct": R.choice(["15", "20", "30", "40"]),
    }


# ------------------------------------------------------------------ flag phrase banks: (text, flags)
F = {
    "CODE": [
        ("Trimite-mi te rog codul primit prin SMS.", ["RF_CODE_REQUEST"]),
        ("Mi-l poți trimite înapoi, te rog?", ["RF_CODE_REQUEST"]),
        ("Vă rog să-mi citiți codul de 6 cifre primit acum.", ["RF_CODE_REQUEST"]),
        ("Spuneți-mi codul de confirmare ca să finalizăm.", ["RF_CODE_REQUEST"]),
        ("Vă trimit un SMS cu un cod, pe care mi-l citiți.", ["RF_CODE_REQUEST"]),
        ("Dictați-mi vă rog codul din mesaj.", ["RF_CODE_REQUEST"]),
        ("Am nevoie de codul care ți-a venit pe telefon.", ["RF_CODE_REQUEST"]),
        ("Comunicați-ne codul de verificare primit.", ["RF_CODE_REQUEST"]),
        ("Dă-mi repede codul ăla de pe SMS.", ["RF_CODE_REQUEST"]),
        ("Scrie-mi aici codul primit, e pentru verificare.", ["RF_CODE_REQUEST"]),
    ],
    "REMOTE": [
        ("Instalați programul {rapp}, ca să vă putem ajuta de la distanță.", ["RF_REMOTE_ACCESS"]),
        ("Descărcați aplicația {rapp} și dați-mi numărul care apare.", ["RF_REMOTE_ACCESS"]),
        ("Trebuie să ne dați acces la distanță pe calculator.", ["RF_REMOTE_ACCESS"]),
        ("Instalează {rapp} din Magazin Play, e gratuit.", ["RF_REMOTE_ACCESS"]),
        ("Acceptați conexiunea, preluăm controlul de la distanță.", ["RF_REMOTE_ACCESS"]),
    ],
    "DATA": [
        ("Completați datele cardului pe: {bad}", ["RF_DATA_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
        ("Introduceți datele cardului aici: {bad}", ["RF_DATA_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
        ("Confirmați numărul cardului, data expirării și CVV-ul.", ["RF_DATA_REQUEST"]),
        ("Am nevoie de CNP-ul dumneavoastră pentru dosar.", ["RF_DATA_REQUEST"]),
        ("Trimiteți-ne o poză cu buletinul, față-verso.", ["RF_DATA_REQUEST"]),
        ("Spuneți-mi PIN-ul cardului ca să verificăm.", ["RF_DATA_REQUEST"]),
        ("Intrați în contul de bancă și spuneți-mi ce vedeți.", ["RF_DATA_REQUEST"]),
        ("Numele complet, CNP-ul și numărul cardului, vă rog.", ["RF_DATA_REQUEST"]),
        ("Trebuie doar să vă confirmăm datele bancare.", ["RF_DATA_REQUEST"]),
        ("Logați-vă în internet banking cu userul și parola pe: {bad}", ["RF_DATA_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
    ],
    "PAY_FAM": [
        ("Poți să-mi faci un transfer de {sum} lei?", ["RF_PAYMENT_REQUEST"]),
        ("Trimite-mi {sum} lei, ți-i dau înapoi mâine.", ["RF_PAYMENT_REQUEST"]),
        ("Mă poți împrumuta cu {sum} lei până la salariu?", ["RF_PAYMENT_REQUEST"]),
        ("Am nevoie să-mi trimiți {sum} lei în contul unui prieten.", ["RF_PAYMENT_REQUEST"]),
        ("Fă-mi te rog un transfer de {sum} lei, îți dau IBAN-ul acum.", ["RF_PAYMENT_REQUEST"]),
        ("Poți să plătești tu factura de {sum} lei? Îți trimit datele.", ["RF_PAYMENT_REQUEST"]),
        ("Trebuie să plătesc {sum} lei cauțiune, trimite-mi banii.", ["RF_PAYMENT_REQUEST"]),
    ],
    "PAY_COURIER": [
        ("Achitați taxa de {sum} lei: {bad}", ["RF_PAYMENT_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
        ("Trebuie să achitați o taxă vamală de {sum} lei.", ["RF_PAYMENT_REQUEST"]),
        ("Plătiți {sum} lei ca să deblocăm coletul.", ["RF_PAYMENT_REQUEST"]),
        ("Pentru livrare, achitați costul de {sum} lei pe: {bad}", ["RF_PAYMENT_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
    ],
    "PAY_JOB": [
        ("Depuneți o garanție de {sum} lei ca să începeți.", ["RF_PAYMENT_REQUEST"]),
        ("Ca să deblocați comisionul, alimentați contul cu {sum} lei.", ["RF_PAYMENT_REQUEST"]),
        ("Pentru următoarea sarcină trebuie să depuneți {sum} lei, îi primiți înapoi cu bonus.", ["RF_PAYMENT_REQUEST"]),
        ("Plătiți taxa de înscriere de {sum} lei.", ["RF_PAYMENT_REQUEST"]),
    ],
    "PAY_INV": [
        ("Investiți doar {sum} euro și vedeți rezultatele.", ["RF_PAYMENT_REQUEST"]),
        ("Depuneți minim {sum} lei în contul de tranzacționare.", ["RF_PAYMENT_REQUEST"]),
        ("Virați suma de {sum} lei în contul indicat de broker.", ["RF_PAYMENT_REQUEST"]),
        ("Pentru a retrage profitul trebuie să plătiți un comision de {sum} lei.", ["RF_PAYMENT_REQUEST"]),
    ],
    "PAY_AUTH": [
        ("Virați suma de {sum} lei în contul indicat.", ["RF_PAYMENT_REQUEST"]),
        ("Ca să închidem dosarul, achitați amenda de {sum} lei.", ["RF_PAYMENT_REQUEST"]),
        ("Transferați economiile într-un cont sigur, vă dau eu IBAN-ul.", ["RF_PAYMENT_REQUEST"]),
        ("Retrageți {sum} lei cash, vine un coleg să-i ridice.", ["RF_PAYMENT_REQUEST"]),
    ],
    "PAY_ROM": [
        ("Vreau să vin la tine, dar am nevoie de {sum} euro pentru biletul de avion.", ["RF_PAYMENT_REQUEST"]),
        ("Ți-am trimis un cadou, dar trebuie plătită taxa vamală de {sum} lei.", ["RF_PAYMENT_REQUEST"]),
        ("Poți să-mi trimiți {sum} euro prin Western Union? Ți-i dau înapoi când ajung.", ["RF_PAYMENT_REQUEST"]),
    ],
    "NEWNUM": [
        ("Bună {fam}, mi s-a stricat telefonul, ăsta e numărul nou. Salvează-l 😘", ["RF_NEW_NUMBER"]),
        ("Salut {fam}, sunt eu, {m}, am număr nou.", ["RF_NEW_NUMBER"]),
        ("{fam}, mi s-a furat telefonul, îți scriu de pe numărul unui prieten.", ["RF_NEW_NUMBER"]),
        ("Bună {fam}! Ăsta e noul meu număr, șterge-l pe cel vechi.", ["RF_NEW_NUMBER"]),
        ("Hei {fam}, mi-am schimbat numărul, ăsta e cel nou ❤️", ["RF_NEW_NUMBER"]),
    ],
    "SECRET": [
        ("Te rog nu-i spune lui tata, se enervează.", ["RF_SECRECY"]),
        ("Să rămână între noi, bine?", ["RF_SECRECY"]),
        ("Nu spuneți nimănui despre această verificare, este confidențială.", ["RF_SECRECY"]),
        ("Nu anunțați banca, ancheta este secretă.", ["RF_SECRECY"]),
        ("Nu vorbiți cu nimeni din familie până nu terminăm.", ["RF_SECRECY"]),
    ],
    "GOOD_PRIZE": [
        ("Felicitări! Ați fost ales câștigătorul unui telefon nou.", ["RF_TOO_GOOD"]),
        ("Ați câștigat un premiu la tombola noastră!", ["RF_TOO_GOOD"]),
        ("Numărul dvs. a fost extras la marea tombolă de sărbători.", ["RF_TOO_GOOD"]),
        ("Ați câștigat un voucher de 1.000 lei!", ["RF_TOO_GOOD"]),
    ],
    "GOOD_PENS": [
        ("Vești bune: pensia dumneavoastră va crește cu {sum} lei.", ["RF_TOO_GOOD"]),
        ("Aveți dreptul la o majorare a pensiei de {sum} lei.", ["RF_TOO_GOOD"]),
        ("Pensia dvs. se mărește cu {sum} lei de luna viitoare.", ["RF_TOO_GOOD"]),
    ],
    "GOOD_INV": [
        ("Profit garantat de {pct}% pe lună, fără niciun risc.", ["RF_TOO_GOOD"]),
        ("Platforma este recomandată de experți, randament sigur.", ["RF_TOO_GOOD"]),
        ("Cu doar 250 € puteți câștiga 5.000 € în câteva săptămâni, garantat.", ["RF_TOO_GOOD"]),
        ("Mulți români și-au dublat banii, câștiguri garantate zilnic.", ["RF_TOO_GOOD"]),
    ],
    "GOOD_JOB": [
        ("Câștigați 3.000 € garantat, lucrând de acasă.", ["RF_TOO_GOOD"]),
        ("Poți câștiga {sum} lei pe zi doar dând like-uri.", ["RF_TOO_GOOD"]),
        ("Plătim 50 lei pentru fiecare sarcină simplă, bani ușor.", ["RF_TOO_GOOD"]),
    ],
    "URG": [
        ("Accesați în {h}h, altfel se anulează.", ["RF_URGENCY"]),
        ("E urgent!", ["RF_URGENCY"]),
        ("Grăbiți-vă, linkul expiră într-o oră.", ["RF_URGENCY"]),
        ("Trebuie făcut azi, neapărat.", ["RF_URGENCY"]),
        ("Aveți termen până la {date}.", ["RF_URGENCY"]),
        ("Răspundeți imediat, vă rog.", ["RF_URGENCY"]),
        ("Cât mai repede, te rog!", ["RF_URGENCY"]),
        ("Ultima zi în care puteți confirma.", ["RF_URGENCY"]),
    ],
    "THREAT_BANK": [
        ("Cardul dvs. a fost blocat temporar din motive de securitate.", ["RF_THREAT"]),
        ("Contul dumneavoastră va fi suspendat.", ["RF_THREAT"]),
        ("Am detectat o tranzacție suspectă pe cardul dumneavoastră.", ["RF_THREAT"]),
        ("Cineva a încercat să vă golească contul.", ["RF_THREAT"]),
    ],
    "THREAT_TECH": [
        ("Calculatorul dvs. trimite viruși pe internet.", ["RF_THREAT"]),
        ("Telefonul dumneavoastră a fost infectat și hackerii vă văd parolele.", ["RF_THREAT"]),
        ("Calculatorul dvs. este piratat, riscați să pierdeți toate datele.", ["RF_THREAT"]),
    ],
    "THREAT_AUTH": [
        ("Altfel veți primi o amendă de {sum} lei.", ["RF_THREAT"]),
        ("Pe numele dvs. s-a deschis un dosar penal.", ["RF_THREAT"]),
        ("Riscați executare silită și poprire pe pensie.", ["RF_THREAT"]),
    ],
    "EMO": [
        ("Am făcut un accident și sunt la poliție.", ["RF_EMOTIONAL_PRESSURE"]),
        ("Sunt la spital, te rog ajută-mă.", ["RF_EMOTIONAL_PRESSURE"]),
        ("Sunt disperat, doar tu mă poți ajuta.", ["RF_EMOTIONAL_PRESSURE"]),
        ("Te iubesc atât de mult, mi-e dor de tine.", ["RF_EMOTIONAL_PRESSURE"]),
        ("Te implor, sunt într-un mare necaz.", ["RF_EMOTIONAL_PRESSURE"]),
    ],
    "SWITCH": [
        ("Hai să vorbim pe {app}, e mai simplu.", ["RF_CHANNEL_SWITCH"]),
        ("Scrie-mi pe {app}, acolo îți explic.", ["RF_CHANNEL_SWITCH"]),
        ("Adaugă-mă pe {app}, continuăm acolo.", ["RF_CHANNEL_SWITCH"]),
        ("Intrați pe grupul nostru de {app}: t.me/castig_ro", ["RF_CHANNEL_SWITCH", "RF_SUSPICIOUS_CONTACT"]),
    ],
}

# trust-building / neutral openers & reader replies (no flags)
OPENERS = {
    "call": ["Bună ziua, doamnă. Vă deranjez doar un minut.", "Bună ziua, vorbesc cu doamna {f}?", "Bună ziua, domnule. Aveți un minut?"],
    "chat": ["Bună ziua, mai este disponibil(ă) {prod}?", "Salut! Ce mai faci?", "Bună! Te mai ții minte de mine?"],
}
READER = ["Da, bună ziua.", "Cine e?", "Da, spuneți.", "Ce s-a întâmplat?", "Bine.", "Ce trebuie să fac?", "Ce date?",
          "Da, este.", "A, bine.", "Nu înțeleg.", "Bine, l-am instalat.", "Ok", "Cum adică?", "Da, eu sunt."]


def fill(t, s):
    try:
        return t.format(**s)
    except (KeyError, IndexError):
        return t


def frag(key, s):
    t, fl = R.choice(F[key])
    return fill(t, s), list(fl)


def msg(parts, s):
    """parts: list of either str (neutral text) or flag-bank keys (UPPER)."""
    texts, flags = [], []
    for p in parts:
        if isinstance(p, str) and p in F:
            t, fl = frag(p, s)
            texts.append(t)
            flags += fl
        else:
            ft, ffl = (p if isinstance(p, tuple) else (p, []))
            if ft:
                texts.append(fill(ft, s))
            flags += ffl
    return " ".join(texts), sorted(set(flags))


IMP = ["RF_IMPERSONATION"]


# ------------------------------------------------------------------ scenario builders: return (channel, sender, steps, type)
def phone(prefix="+40 7xx xxx "):
    return prefix + str(R.randint(100, 999))


def maybe(p, x):
    return [x] if R.random() < p else []


def bank():
    s = slots("bank")
    ch = R.choice(["sms", "sms", "email", "call_transcript"])
    if ch == "call_transcript":
        opener = R.choice([f"Bună ziua, vă sun de la {s['bank']}, departamentul de fraude.",
                           f"Bună ziua, sunt {s['f']}, de la serviciul clienți al băncii.",
                           "Bună ziua, vă contactăm din partea băncii dumneavoastră, departamentul antifraudă."])
        steps = [("S", [(opener, IMP)]), ("R",), ("S", ["THREAT_BANK"]), ("R",),
                 ("S", [R.choice(["DATA", "CODE"])])] + maybe(.6, ("S", [R.choice(["URG", "SECRET", "CODE", "PAY_AUTH"])]))
        sender = {"name": None, "address": phone("+40 3xx xxx "), "known_contact": False}
    else:
        head = R.choice([f"{s['bank']}:", "Banca Dunărea informează:"])
        body = [(head, IMP), "THREAT_BANK",
                R.choice([(f"Pentru deblocare accesați: {s['bad']}", ["RF_SUSPICIOUS_CONTACT"]),
                          (f"Confirmați identitatea pe {s['bad']}", ["RF_SUSPICIOUS_CONTACT"]),
                          "DATA"])] + maybe(.7, "URG")
        if ch == "sms":
            sender = R.choice([{"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
                               {"name": None, "address": phone(), "known_contact": False}])
        else:
            sender = {"name": "Banca Dunărea Securitate", "address": f"securitate@{s['bad'].split('/')[0]}", "known_contact": False}
            body.append(("", ["RF_SUSPICIOUS_CONTACT"]))
        steps = [("S", body)]
    return ch, sender, steps, "BANK_IMPERSONATION", s


def courier():
    s = slots("courier")
    head = R.choice([f"{s['courier']}: Coletul dvs. nu a putut fi livrat.", f"{s['courier']}: Coletul dvs. este reținut în depozit.",
                     f"{s['courier']}: Adresa de livrare este incompletă, coletul a fost oprit."])
    steps = [("S", [(head, IMP), "PAY_COURIER"] + maybe(.5, "URG"))]
    return R.choice(["sms", "whatsapp", "email"]), {"name": None, "address": phone(), "known_contact": False}, \
        steps, "COURIER_FEE", s


def authority():
    s = slots("anaf")
    kind = R.choice(["anaf", "pensii", "pensii", "politie"])
    if kind == "anaf":
        steps = [("S", [("Stimate contribuabil, aveți de primit o rambursare de {sum} lei.", ["RF_IMPERSONATION"]),
                        (f"Pentru a o primi, completați datele cardului pe: {s['bad']}", ["RF_DATA_REQUEST", "RF_SUSPICIOUS_CONTACT"]),
                        "URG"])]
        return "email", {"name": "ANAF Rambursări", "address": f"notificari@{s['bad'].split('/')[0]}", "known_contact": False}, \
            steps, "AUTHORITY_IMPERSONATION", s
    if kind == "pensii":
        opener = R.choice(["Bună ziua, doamnă. Sunt {f}, de la Casa de Pensii. Facem o actualizare a dosarelor.",
                           "Bună ziua, vă sun de la Casa de Pensii, sectorul 3, în legătură cu indexarea.",
                           "Bună ziua, sunt {f} de la Casa Națională de Pensii. Verificăm dosarele pensionarilor."])
        steps = [("S", [(opener, IMP)]), ("R",)]
        steps += maybe(.5, ("S", [("Cum vă mai simțiți? Totul bine cu sănătatea?", [])]))
        steps += maybe(.5, ("R",))
        steps += [("S", ["GOOD_PENS", ("Ca să nu pierdeți diferența, trebuie doar să vă confirmăm datele.", ["RF_DATA_REQUEST"])]),
                  ("R",), ("S", ["DATA"] + maybe(.7, "CODE"))]
    else:
        steps = [("S", [("Bună ziua, sunt agentul {m} de la Poliția Capitalei.", IMP)]), ("R",), ("S", ["THREAT_AUTH"]), ("R",),
                 ("S", ["PAY_AUTH"] + maybe(.6, "SECRET"))]
    return "call_transcript", {"name": None, "address": phone("+40 2xx xxx "), "known_contact": False}, \
        steps, "AUTHORITY_IMPERSONATION", s


def family():
    s = slots()
    steps = [("S", ["NEWNUM"]), ("R",), ("S", [("Eu, {m}, cine să fie 😅", [])]), ("R",)]
    for _ in range(R.randint(0, 2)):
        steps.append(("S", [(R.choice(["Ce faci? Ați mâncat?", "Cum e pe acasă?", "Mi-e dor de voi.", "Sunt la serviciu acum."]), [])]))
        steps.append(("R",))
    hook = [("{fam}, am o problemă, trebuie să plătesc azi o factură și nu-mi merge aplicația.", ["RF_URGENCY"]), "PAY_FAM"]
    if R.random() < .4:
        hook = ["EMO", "PAY_FAM"] + maybe(.7, "URG")
    steps.append(("S", hook))
    steps += maybe(.7, ("S", ["SECRET"]))
    return "whatsapp", {"name": None, "address": phone(), "known_contact": False}, steps, "FAMILY_EMERGENCY", s


def tech():
    s = slots()
    opener = R.choice(["Bună ziua, vă sun de la suportul tehnic Microsoft.", "Bună ziua, sunt de la departamentul tehnic Windows.",
                       "Alo, vă sunăm de la suportul tehnic al furnizorului de internet."])
    steps = [("S", [(opener, IMP), "THREAT_TECH"]), ("R",), ("S", ["REMOTE"]), ("R",),
             ("S", [R.choice(["DATA", "PAY_AUTH", "CODE"])])]
    return "call_transcript", {"name": None, "address": phone("+40 3xx xxx "), "known_contact": False}, steps, "TECH_SUPPORT", s


def marketplace():
    s = slots("market")
    steps = [("S", [("Bună ziua, mai este disponibil(ă) {prod}?", [])]), ("R",)]
    steps += maybe(.5, ("S", [(R.choice(["Ce stare are? Se vede bine în poze.", "Ultimul preț?", "Perfect, mă interesează."]), [])]))
    steps += maybe(.5, ("R",))
    steps.append(("S", [(R.choice(["O iau. Am plătit deja prin Livrare Sigură.", "Am făcut plata, curierul vine mâine.",
                                   "Vă trimit banii prin PiațaMea Pay."]), []),
                        (R.choice([f"Ca să primiți banii, introduceți datele cardului aici: {s['bad']}",
                                   f"Pentru a încasa suma, completați datele cardului pe {s['bad']}"]),
                         ["RF_DATA_REQUEST", "RF_SUSPICIOUS_CONTACT"])]))
    steps += maybe(.7, ("S", ["URG"]))
    steps += maybe(.3, ("S", ["SWITCH"]))
    return "chat", {"name": "Cumpărător PiațaMea", "address": f"buyer_{R.randint(10000, 99999)}", "known_contact": False}, \
        steps, "MARKETPLACE", s


def ato():
    s = slots()
    a = R.choice([("Bună! Ți-am trimis din greșeală un cod de 6 cifre prin SMS.", "Mi-l poți trimite înapoi, te rog?"),
                  ("Salut, scuze, am pus numărul tău din greșeală și ți-a venit un cod.", "Poți să mi-l trimiți și mie?"),
                  ("Hei, ți-a venit un SMS cu un cod de la WhatsApp?", "Dă-mi-l te rog, e pentru contul meu.")])
    steps = [("S", [(a[0], []), (a[1], ["RF_CODE_REQUEST"])] + maybe(.7, "URG"))]
    name = R.choice(NAMES_F + NAMES_M)
    return "whatsapp", {"name": name + R.choice(["", " (vecina)", " serviciu"]), "address": phone(), "known_contact": True}, \
        steps, "ACCOUNT_TAKEOVER", s


def investment():
    s = slots("invest")
    steps = [("S", [(R.choice(["Bună ziua! Vă scriu despre o oportunitate de investiții în crypto.",
                               "Bună ziua, sunt consultant financiar la o platformă de trading."]), [])]), ("R",),
             ("S", ["GOOD_INV"]), ("R",), ("S", ["PAY_INV", (f"Înregistrați-vă pe {s['bad']}", ["RF_SUSPICIOUS_CONTACT"])])]
    steps += maybe(.7, ("S", [R.choice(["URG", "SWITCH"])]))
    return R.choice(["whatsapp", "chat", "call_transcript"]), {"name": None, "address": phone("+44 7xxx xxx "),
                                                               "known_contact": False}, steps, "INVESTMENT", s


def romance():
    s = slots()
    steps = [("S", [("Bună, {f}! Mă bucur că ne-am cunoscut aici, ești o persoană minunată.", [])]), ("R",),
             ("S", [("Sunt inginer pe o platformă petrolieră, dar mă gândesc doar la tine.", [])]), ("R",),
             ("S", [("Te iubesc atât de mult, mi-e dor de tine.", ["RF_EMOTIONAL_PRESSURE"])]), ("R",),
             ("S", ["PAY_ROM"])]
    steps += maybe(.7, ("S", [R.choice(["SECRET", "URG", "SWITCH"])]))
    return R.choice(["chat", "whatsapp"]), {"name": R.choice(["David", "James", "Marco"]), "address": phone("+1 xxx xxx "),
                                            "known_contact": False}, steps, "ROMANCE", s


def job():
    s = slots("job")
    steps = [("S", [(R.choice(["Bună ziua! Căutăm colaboratori pentru un job de acasă, câteva ore pe zi.",
                               "Bună, sunt recrutor. Avem un loc de muncă part-time, lucrați de pe telefon."]), [])]), ("R",),
             ("S", ["GOOD_JOB"]), ("R",)] + maybe(.6, ("S", ["SWITCH"])) + [("S", ["PAY_JOB"])]
    return R.choice(["whatsapp", "sms", "chat"]), {"name": None, "address": phone(), "known_contact": False}, steps, "JOB_OFFER", s


def prize():
    s = slots("shop")
    body = [("Felicitări! Ați fost ales câștigătorul unui telefon nou la tombola MegaShop.", ["RF_TOO_GOOD", "RF_IMPERSONATION"])]
    r = R.random()
    if r < .4:
        body.append(("Răspundeți cu DA pentru detalii.", []))
    elif r < .7:
        body.append((f"Revendicați premiul pe {s['bad']}", ["RF_SUSPICIOUS_CONTACT"]))
        body.append("URG")
    else:
        body.append((f"Plătiți doar taxa de transport de {s['sum']} lei.", ["RF_PAYMENT_REQUEST"]))
    return "sms", {"name": None, "address": "+40 7xx xxx " + str(R.randint(100, 999)), "known_contact": False}, \
        [("S", body)], "PRIZE_LOTTERY", s


# ------------------------------------------------------------------ hard negatives (genuine, no flags)
GENUINE = [
    ("sms", {"name": "BancaDunarea", "address": "BancaDunarea", "known_contact": False},
     ["Banca Dunărea: Codul de confirmare este {code}. Nu comunicați acest cod nimănui, nici angajaților băncii.",
      "Banca Dunărea: Plata de {sum} lei la MegaShop a fost efectuată. Dacă nu o recunoașteți, sunați la 0800 100 200.",
      "Banca Dunărea: Extrasul de cont pentru luna aceasta este disponibil în aplicație.",
      "Banca Dunărea nu vă va cere niciodată PIN-ul sau parola prin telefon sau SMS.",
      "Banca Dunărea: Codul dvs. de autentificare este {code}. Nu îl dați nimănui."]),
    ("sms", {"name": "CurierExpres", "address": "CurierExpres", "known_contact": False},
     ["CurierExpres: Coletul AWB {awb} va fi livrat azi, între 12:00 și 16:00. Ramburs: 0 lei. Urmărire: curierexpres.ro/awb",
      "CurierExpres: Coletul dvs. a fost livrat. Mulțumim!",
      "CurierExpres: Curierul ajunge mâine între 9 și 13. Detalii: curierexpres.ro"]),
    ("email", {"name": "ANAF", "address": "notificari@anaf.ro", "known_contact": False},
     ["Stimate contribuabil, vă reamintim că termenul pentru declarația unică este 25.05. Detalii pe anaf.ro.",
      "Aveți un mesaj nou în Spațiul Privat Virtual. Autentificați-vă direct pe anaf.ro."]),
    ("email", {"name": "MegaShop", "address": "comenzi@megashop.ro", "known_contact": False},
     ["Comanda dvs. a fost confirmată și va fi livrată în 2-3 zile. Detalii: megashop.ro/comenzi",
      "Reduceri de {pct}% la electrocasnice în acest weekend, pe megashop.ro/oferte."]),
    ("whatsapp", {"name": "Mama", "address": "+40 7xx xxx 101", "known_contact": True},
     ["Bună, puiule! Ai ajuns acasă?", "Ți-am pus mâncare în frigider, să nu uiți.",
      "Mi-ai trimis banii pentru întreținere? Mersi mult!", "Duminică venim la voi la masă."]),
    ("whatsapp", {"name": "Andrei", "address": "+40 7xx xxx 202", "known_contact": True},
     ["Bună mami, am ajuns cu bine la Cluj. Te sun diseară.",
      "Mami, am dat examenul, am luat 9! 😊", "Am făcut un mic accident cu bicicleta, dar sunt bine, nu-ți face griji."]),
    ("chat", {"name": "Cumpărător PiațaMea", "address": "buyer_11111", "known_contact": False},
     ["Bună ziua, mai este disponibilă {prod}?", "Pot să vin s-o văd mâine după-amiază?", "Plătesc cash la ridicare, e ok?"]),
    ("sms", {"name": None, "address": "+40 7xx xxx 303", "known_contact": False},
     ["Bună ziua, sunt curierul. Sunt în fața blocului cu coletul dvs., coborâți vă rog.",
      "Programarea dvs. la cabinetul stomatologic este mâine la ora 10.",
      "Bună, sunt {f}, colega de la cor. Mâine repetiția e la 18."]),
    ("call_transcript", {"name": None, "address": "+40 2xx xxx 404", "known_contact": False},
     ["Bună ziua, sunt de la cabinetul medicului de familie. Vă reamintim de vaccinul de mâine.",
      "Bună ziua, vă sun de la service. Mașina dvs. este gata, o puteți ridica de azi."]),
]


def genuine():
    ch, sender, texts = R.choice(GENUINE)
    s = slots()
    k = R.randint(1, min(3, len(texts)))
    picks = R.sample(texts, k)
    steps = []
    for i, t in enumerate(picks):
        steps.append(("S", [(t, [])]))
        if i < k - 1 and R.random() < .5:
            steps.append(("R",))
    return ch, dict(sender), steps, "NONE", s


BUILDERS = [(bank, 10), (courier, 8), (authority, 10), (family, 10), (tech, 7), (marketplace, 7), (ato, 6), (investment, 5),
            (romance, 4), (job, 4), (prize, 6), (genuine, 30)]


# ------------------------------------------------------------------ augmentation
def strip_diacritics(t):
    return "".join(c for c in unicodedata.normalize("NFKD", t) if not unicodedata.combining(c))


NO_AUG = False


def augment(text):
    if NO_AUG:
        return text
    r = R.random()
    if r < .35:
        text = strip_diacritics(text)
    if R.random() < .1:
        text = text.lower()
    if R.random() < .08 and len(text) > 20:
        words = text.split(" ")
        cand = [k for k, w in enumerate(words) if len(w) > 4 and w.isalpha()]
        if cand:
            k = R.choice(cand)
            i = R.randrange(len(words[k]))
            words[k] = words[k][:i] + words[k][i + 1:]
            text = " ".join(words)
    return text


def build_one(i):
    fn = R.choices([b for b, _ in BUILDERS], weights=[w for _, w in BUILDERS])[0]
    ch, sender, steps, stype, s = fn()
    msgs, n = [], 0
    for step in steps:
        n += 1
        if step[0] == "R":
            msgs.append({"n": n, "from": "reader", "text": augment(fill(R.choice(READER), s)), "flags": []})
            continue
        text, flags = msg(step[1], s)
        msgs.append({"n": n, "from": "sender", "text": augment(text), "flags": flags})
    return {"id": f"S{i:05d}", "channel": ch, "sender": sender, "messages": msgs, "scam_type": stype}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument("--n", type=int, default=4000)
    ap.add_argument("--seed", type=int, default=13)
    ap.add_argument("--out", default=str(Path(__file__).parent / "data" / "synth.jsonl"))
    ap.add_argument("--no-aug", action="store_true", help="no diacritic stripping / typos (for checking rules)")
    a = ap.parse_args()
    global NO_AUG
    NO_AUG = a.no_aug
    R.seed(a.seed)
    Path(a.out).parent.mkdir(parents=True, exist_ok=True)
    with open(a.out, "w", encoding="utf-8") as f:
        for i in range(a.n):
            f.write(json.dumps(build_one(i), ensure_ascii=False) + "\n")
    print(f"wrote {a.n} scenarios -> {a.out}")


if __name__ == "__main__":
    main()
