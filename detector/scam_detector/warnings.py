"""Plain-language warnings (RO first, EN optional).

Rules from the brief: at most 3 short sentences (what / why / one action), "dumneavoastră",
no jargon, the action uses ONLY official channels from the catalog, and we never repeat a link
or phone number taken from the suspicious message. Numbers below come from official_catalog.json.
"""
import re

from .catalog import get_catalog

_OPEN = {
    "SCAM": ("Atenție, pare o țeapă!", "Warning, this looks like a scam!"),
    "SUSPICIOUS": ("Atenție, verificați înainte să răspundeți.", "Careful, check before you reply."),
    "SAFE": ("Pare în regulă.", "This looks fine."),
}


def _official(org_key):
    cat = get_catalog()
    return cat.orgs.get(org_key) if org_key else None


def _channel_ro(c):
    if not c:
        return None
    parts = []
    if c.get("phone"):
        parts.append(f"la {c['phone']}")
    if c.get("website"):
        parts.append(f"pe {c['website']}")
    return " sau ".join(parts) if parts else None


def _channel_en(c):
    if not c:
        return None
    parts = []
    if c.get("phone"):
        parts.append(f"call {c['phone']}")
    if c.get("website"):
        parts.append(f"use {c['website']}")
    return " or ".join(parts) if parts else None


def _family_name(texts):
    """A first name the impostor used ('Eu, Andrei' / 'sunt Andrei'). Names are safe to repeat; numbers are not."""
    for t in texts:
        m = re.search(r"\b(?:[Ee]u|[Ss]unt|[Ss]unt eu)\s*,?\s+([A-ZĂÂÎȘȚ][a-zăâîșț]{2,15})\b", t)
        if m and m.group(1).lower() not in {"bine", "acasa", "acasă", "aici", "mama", "tata", "eu"}:
            return m.group(1)
    return None


def _contact_first_name(sender):
    name = (sender or {}).get("name") or ""
    m = re.match(r"\s*([A-ZĂÂÎȘȚ][a-zăâîșț]{2,15})\b", name)
    return m.group(1) if m else None


def build(result: dict, scenario: dict) -> dict:
    verdict = result["verdict"]
    t = result["scam_type"]
    flags = set(result["red_flags"])
    sender = scenario.get("sender") or {}
    texts = [str(m.get("text") or "") for m in scenario.get("messages") or []
             if isinstance(m, dict) and (m.get("from") or "sender") == "sender"]
    orgs = result.get("_claim_orgs") or []
    org = next((o for o in orgs if _official(o)), None)
    off = _official(org)
    o_ro, o_en = _OPEN[verdict]

    if verdict == "SAFE":
        why_ro = "Mesajul nu vă cere bani, coduri sau date personale și nu are adrese de internet false."
        why_en = "It does not ask for money, codes or personal data and has no fake web addresses."
        act_ro = "Dacă totuși aveți îndoieli, întrebați o persoană de încredere înainte să răspundeți."
        act_en = "If you still have doubts, ask someone you trust before replying."
        return {"ro": f"{o_ro} {why_ro} {act_ro}", "en": f"{o_en} {why_en} {act_en}"}

    link = "RF_SUSPICIOUS_CONTACT" in flags
    if t == "BANK_IMPERSONATION":
        why_ro = "Mesajul se dă drept banca dumneavoastră" + (", dar adresa de internet este falsă." if link else
                                                            " și vă cere să acționați în grabă.")
        why_en = "It pretends to be your bank" + (", but the web address is fake." if link else " and rushes you.")
        act_ro = "Nu apăsați pe nimic din mesaj; sunați la numărul de pe spatele cardului."
        act_en = "Do not click anything in it; call the number on the back of your card."
    elif t == "COURIER_FEE":
        why_ro = "Mesajul se dă drept firma de curierat și vă cere o taxă" + (" pe o adresă de internet falsă." if link else ".")
        why_en = "It pretends to be a courier and asks for a fee" + (" on a fake web address." if link else ".")
        ch = _channel_ro(off) if org == "curierexpres" else None
        act_ro = "Nu plătiți nimic; verificați coletul doar " + (ch if ch else "pe site-ul oficial al firmei de curierat") + "."
        ch_en = _channel_en(off) if org == "curierexpres" else None
        act_en = "Do not pay; check the parcel only via the courier's official site" + (f" ({ch_en})." if ch_en else ".")
    elif t == "AUTHORITY_IMPERSONATION":
        txt = " ".join(texts).lower()
        if "pensi" in txt:
            who_ro, who_en = "Casa de Pensii", "the pension office"
            act_ro = "Nu dați niciun cod sau date; închideți și mergeți la ghișeul Casei de Pensii sau întrebați pe cineva apropiat."
            act_en = "Do not give any code or data; hang up and go to the pension office counter in person."
        elif "politi" in txt:
            who_ro, who_en = "Poliția", "the police"
            act_ro = "Nu dați bani sau date; închideți și sunați la 112 dacă vă simțiți în pericol."
            act_en = "Do not give money or data; hang up and call 112 if you feel in danger."
        elif "anaf" not in orgs and "contribuabil" not in txt and "fisc" not in txt:
            who_ro, who_en = "o instituție a statului", "a public institution"
            act_ro = "Nu dați bani sau date; închideți și verificați direct la instituție, la ghișeu, sau întrebați pe cineva apropiat."
            act_en = "Do not give money or data; hang up and check with the institution in person."
        else:
            who_ro, who_en = "ANAF", "the tax office (ANAF)"
            a = _official("anaf")
            act_ro = f"Nu completați nimic; verificați doar pe {a['website']} sau la {a['phone']}."
            act_en = f"Do not fill anything in; check only on {a['website']} or call {a['phone']}."
        if flags & {"RF_DATA_REQUEST", "RF_CODE_REQUEST"}:
            why_ro = f"Cineva se dă drept {who_ro} și vă cere date personale, ale cardului sau coduri."
            why_en = f"Someone pretends to be {who_en} and asks for your personal data, card data or codes."
        else:
            why_ro = f"Cineva se dă drept {who_ro} și vă cere bani, punându-vă presiune."
            why_en = f"Someone pretends to be {who_en} and pressures you for money."
    elif t == "FAMILY_EMERGENCY":
        name = _family_name(texts)
        why_ro = "Cineva de pe un număr nou se dă drept copilul sau nepotul dumneavoastră și cere bani"
        why_ro += ", în secret." if "RF_SECRECY" in flags else (" urgent." if "RF_URGENCY" in flags else ".")
        why_en = "Someone on a new number pretends to be your child or grandchild and asks for money."
        if name:
            act_ro = f"Nu trimiteți bani: sunați-l pe {name} la numărul lui vechi, pe care îl cunoașteți."
            act_en = f"Do not send money: call {name} on the old number you already know."
        else:
            act_ro = "Nu trimiteți bani: sunați-vă copilul la numărul vechi, pe care îl cunoașteți."
            act_en = "Do not send money: call your child on the old number you already know."
    elif t == "TECH_SUPPORT":
        why_ro = "Firmele de calculatoare nu sună niciodată oamenii, iar cine vă cere să instalați un program vrea să vă controleze calculatorul."
        why_en = "Computer companies never call people; whoever asks you to install a program wants to control your computer."
        act_ro = "Închideți imediat, nu intrați în contul de bancă și cereți ajutorul unei persoane de încredere."
        act_en = "Hang up now, do not open your bank account and ask someone you trust for help."
    elif t == "MARKETPLACE":
        why_ro = "Ca să primiți bani nu trebuie să dați niciodată datele cardului, iar adresa de internet este falsă." if link else \
            "Ca să primiți bani nu trebuie să dați niciodată datele cardului."
        why_en = "You never need to give card details to receive money" + (", and the web address is fake." if link else ".")
        act_ro = "Nu introduceți nimic; vorbiți cu cumpărătorul doar în aplicația oficială PiațaMea."
        act_en = "Do not enter anything; talk to the buyer only inside the official PiațaMea app."
    elif t == "ACCOUNT_TAKEOVER":
        who = _contact_first_name(sender) if sender.get("known_contact") else None
        why_ro = ("Chiar dacă mesajul pare de la cineva cunoscut, contul probabil a fost furat, "
                  "iar codul ar da acces la contul dumneavoastră.")
        why_en = "Even if it seems to come from someone you know, the account was probably stolen and the code would unlock yours."
        if who:
            act_ro = f"Nu trimiteți codul; vorbiți cu {who} la telefon, la numărul pe care îl știți deja."
            act_en = f"Do not send the code; call {who} on the number you already know."
        else:
            act_ro = "Nu trimiteți codul nimănui; sunați persoana la numărul pe care îl știți deja."
            act_en = "Do not send the code to anyone; call the person on the number you already know."
    elif t == "INVESTMENT":
        why_ro = "Nimeni nu poate garanta câștiguri, iar banii depuși așa se pierd de obicei."
        why_en = "No one can guarantee profits, and money sent this way is usually lost."
        act_ro = "Nu trimiteți bani; întrebați la banca dumneavoastră, la ghișeu, înainte de orice investiție."
        act_en = "Do not send money; ask your bank in person before any investment."
    elif t == "ROMANCE":
        why_ro = "O persoană cunoscută doar online vă cere bani, iar așa încep des înșelătoriile sentimentale."
        why_en = "Someone you only know online is asking for money, a common romance scam."
        act_ro = "Nu trimiteți bani și vorbiți despre asta cu cineva din familie."
        act_en = "Do not send money, and talk about it with a family member."
    elif t == "JOB_OFFER":
        why_ro = "Un loc de muncă adevărat nu vă cere bani sau o garanție ca să începeți."
        why_en = "A real job never asks you to pay or leave a deposit to start."
        act_ro = "Nu plătiți nimic și nu mai răspundeți acestor mesaje."
        act_en = "Do not pay anything and stop replying to these messages."
    elif t == "PRIZE_LOTTERY":
        why_ro = "Mesajul spune că ați câștigat un premiu la care nu v-ați înscris" + (
            ", de pe un număr care nu este al magazinului." if "RF_IMPERSONATION" in flags else ".")
        why_en = "It says you won a prize you never entered for."
        a = off if org == "megashop" else None
        if a:
            act_ro = f"Nu răspundeți și nu dați date; dacă vreți, verificați pe {a['website']} sau la {a['phone']}."
            act_en = f"Do not reply or give data; if you want, check on {a['website']} or call {a['phone']}."
        else:
            act_ro = "Nu răspundeți și nu dați date; verificați doar pe site-ul oficial al magazinului."
            act_en = "Do not reply or give data; check only on the shop's official website."
    else:
        why_ro = "Mesajul vă presează să dați bani, coduri sau date personale."
        why_en = "It pressures you to give money, codes or personal data."
        act_ro = "Nu răspundeți și cereți părerea unei persoane de încredere."
        act_en = "Do not reply and ask someone you trust."

    return {"ro": f"{o_ro} {why_ro} {act_ro}", "en": f"{o_en} {why_en} {act_en}"}
