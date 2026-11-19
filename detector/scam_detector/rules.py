"""Deterministic red-flag rules over normalised (lowercase, no diacritics) Romanian text.

Each detector returns a list of (flag, (start, end)) evidence spans for ONE message.
RF_SUSPICIOUS_CONTACT lives in contacts.py; RF_IMPERSONATION is decided in fusion.py
from the org claims found here (it depends on the sender and on the other flags).
"""
import re

from .normalize import sentences


def _c(*parts):
    return re.compile("|".join(parts))


# ---------------------------------------------------------------- negation guards
# "do not share this code with anyone" style safety advice (genuine banks write this)
NEG_ADVICE = _c(
    r"\bnu\s+(?:il\s+|le\s+|o\s+|va\s+)?(?:comunicati|comunica|dati|da|spuneti|spune|transmiteti|transmite|divulgati|"
    r"oferiti|trimiteti|trimite|furnizati|introduceti)\b",
    r"\bnu\s+(?:va\s+)?(?:vom|va|vor|o\s+sa)\s+(?:cere|solicita)", r"\bniciodata\b", r"\bnimanui\b",
    r"\bnu\s+(?:va\s+)?(?:cerem|solicitam|cere|solicita)\b",
)

# ---------------------------------------------------------------- RF_CODE_REQUEST
CODE_NOUN = _c(r"\bcod(?:ul|uri|urile|ului)?\b", r"\botp\b", r"\bparola\s+unica\b", r"\bcifre(?:le)?\b",
               r"\bcod(?:ul)?\s+(?:de\s+)?(?:confirmare|verificare|activare|securitate|acces|autentificare)")
CODE_REQ_STRONG = _c(
    r"\b(?:da|dati|trimite|trimiteti|spune|spuneti|citeste|cititi|zi|ziceti|scrie|scrieti)-mi-l\b",
    r"\b(?:sa\s+)?(?:ne|mi|imi)\s+(?:comunicati|spuneti|dati|cititi|dictati|transmiteti|trimiteti|spui|dai|citesti|trimiti|"
    r"comunici|transmiti)\b[^.!?]{0,40}\b(?:cod\w*|cifre\w*|otp)",
    r"\b(?:send|give|tell|read)\s+(?:me|us)\s+(?:the\s+)?(?:\w+\s+)?(?:code|otp|pin)\b",
    r"\bmi-l\s+(?:poti|puteti|cititi|citesti|citeste|spui|spuneti|dai|dati|trimiti|trimiteti|transmiti|transmiteti|"
    r"dictezi|dictati|zici|scrii|scrieti)\b",
    r"\bpe\s+care\s+(?:mi|ni)-?l\b",
    r"\b(?:trimite|trimiteti|da|dati|spune|spuneti|citeste|cititi|dicteaza|dictati|comunica|comunicati|transmite|"
    r"transmiteti|zi|scrie|scrieti|trimite-l|trimiteti-l)-?(?:mi|ne)\b(?:[^.!?]{0,60})\b(?:cod|codul|otp|cifre)",
    r"\b(?:trimite|trimiteti|trimite-l|trimiteti-l|da|dati)(?:-?l)?\s+(?:-?mi\s+)?inapoi\b",
    r"\b(?:citi|cititi|citeste|spuneti|spune|comunicati|dictati|transmiteti|trimiteti|trimite|introduceti|"
    r"confirmati|da|dati)(?:-mi|-ne)?\s+(?:si\s+)?(?:te\s+rog\s+)?(?:codul|codurile|otp-ul|otp)\b",
    r"\b(?:cod(?:ul)?|otp)(?:\s+\w+){0,4}\s+(?:primit|venit|sosit)\b[^.!?]{0,40}(?:trimite|spune|citi|da|dict|comunic|transmit)",
    r"\b(?:am\s+nevoie|avem\s+nevoie|ne\s+trebuie|imi\s+trebuie)\s+de\s+(?:acel\s+|acest\s+)?cod",
)

# ---------------------------------------------------------------- RF_REMOTE_ACCESS
REMOTE = _c(
    r"\bany\s?desk\b", r"\bteam\s?viewer\b", r"\bquick\s?support\b", r"\brust\s?desk\b", r"\bammyy\b",
    r"\bsupremo\b", r"\bultra\s?viewer\b", r"\blogmein\b", r"\bsplashtop\b", r"\bairdroid\b",
    r"\b(?:control|acces|conectare|asistenta)(?:ul)?\s+(?:\w+\s+)?(?:de\s+la\s+distanta|remote)\b",
    r"\b(?:de\s+)?la\s+distanta\b",
    r"\b(?:partajati|partajeaza|share)\s+(?:\w+\s+)?ecran", r"\bpartajare(?:a)?\s+(?:a\s+)?ecran",
    r"\.apk\b",
)

# ---------------------------------------------------------------- RF_DATA_REQUEST
DATA_STRONG = _c(
    r"\bdatele\s+(?:de\s+pe\s+)?(?:cardului|card|bancare|personale|de\s+autentificare|de\s+logare|contului|de\s+acces|"
    r"de\s+login|de\s+identificare|dumneavoastra\s+bancare)\b",
    r"\bnumarul\s+(?:complet\s+)?(?:al\s+)?(?:cardului|de\s+card)\b", r"\bnumar(?:ul)?\s+de\s+card\b",
    r"\bcvv\b", r"\bcvc\b", r"\bcodul\s+(?:de\s+)?(?:pe\s+)?(?:din\s+)?spate(?:le)?\b", r"\bdata\s+(?:de\s+)?expirar",
    r"\bpin(?:-ul|ul)?\b", r"\bparol(?:a|ele|ei)\b", r"\bcnp(?:-ul|ul)?\b", r"\bcod(?:ul)?\s+numeric\s+personal\b",
    r"\bseria\s+(?:si\s+numarul\s+)?(?:de\s+)?(?:la\s+)?buletin", r"\b(?:poza|fotografie|copie|scan)\s+(?:\w+\s+){0,2}"
    r"(?:buletin|cartea\s+de\s+identitate|actul\s+de\s+identitate|ci)\b",
    r"\b(?:user(?:name)?|utilizator(?:ul)?)\s+si\s+parol", r"\bdate(?:le)?\s+de\s+(?:acces|logare|login)\b",
    r"\bintrati\s+(?:acum\s+)?in\s+(?:contul|aplicatia)\s+(?:\w+\s+)?(?:de\s+banca|bancii|bancar|de\s+internet\s+banking)",
    r"\b(?:logati|autentificati|conectati)-va\s+(?:\w+\s+)?(?:in|pe)\s+(?:contul|aplicatia|internet\s+banking)",
    r"\bintrati\s+in\s+(?:internet|mobile)\s+banking\b", r"\bcredentiale(?:le)?\b",
    r"\bcard\s+(?:details|number)\b", r"\bpassword\b",
)
DATA_WEAK = _c(r"\biban(?:-ul|ul)?\b", r"\bbuletin(?:ul)?\b", r"\bcartea\s+de\s+identitate\b", r"\bdatele\b",
               r"\bcontul\s+(?:de\s+)?(?:banca|bancar)\b")
DATA_DESCRIPTIVE = re.compile(r"\b(?:va\s+vad|v-au\s+furat|au\s+furat|au\s+acces|hackeri|nu\s+va\s+cer|furat)")
DATA_VERB = _c(
    r"\b(?:completati|completeaza|introduceti|introdu|trimiteti|trimite|confirmati|confirma|furnizati|spuneti|spune|"
    r"dati|da-mi|dictati|comunicati|scrieti|scrie|actualizati|actualizeaza|verificam|verifica|validati|valideaza|"
    r"accesati|incarcati|atasati|avem\s+nevoie|am\s+nevoie|ne\s+trebuie|ne\s+confirmati|sa\s+va\s+confirmam|"
    r"autentificati-va|autentifica-te|logati-va|logheaza-te|conectati-va|enter|verify|confirm|provide|update)\b",
)

# ---------------------------------------------------------------- RF_PAYMENT_REQUEST
PAYMENT = _c(
    r"\bachitati\b", r"\bachita\b", r"\bplatiti\b", r"\bplateste\b", r"\bplatesti\b",
    r"\bsa\s+(?:imi\s+|ne\s+|mi\s+)?(?:platiti|achitati|transferati|virati|depuneti|trimiteti|alimentati|investiti)\b",
    r"\b(?:fa|faci|faceti|face|poti\s+face|puteti\s+face)(?:-mi|-ne)?\s+(?:te\s+rog\s+|va\s+rog\s+)?(?:tu\s+|dvs\.?\s+)?(?:un\s+)?"
    r"(?:transfer|virament|depunere|plata)\b",
    r"\b(?:faci|faceti|fa|da|dai|dati|da-mi|poti\s+da)(?:-mi|-ne)?\s+(?:tu\s+)?(?:un\s+)?(?:transfer|virament)\b",
    r"\b(?:transferati|transfera|vireaza|virati|depuneti|depune|alimentati|alimenteaza|investiti|investeste)\b",
    r"\b(?:trimite|trimiteti|trimiti|imprumuta|imprumutati|imprumuti|da|dai|dati)(?:-mi|-ne)?\s+"
    r"(?:\S+\s+){0,3}(?:bani|banii|suma|lei|euro|eur|ron|dolari|€|\d[\d.,]*\s*(?:lei|ron|euro|eur|€))\b",
    r"\b(?:imprumut|un\s+imprumut)\b", r"\b(?:depui|depune|investesti|investeste|alimentezi)\s+(?:doar\s+|numai\s+)?\d",
    r"\b(?:pay|send|transfer)\s+(?:the\s+|a\s+|us\s+)?(?:\S+\s+){0,3}(?:fee|eur|euro|usd|\$|€|money|payment)",
    r"\b(?:customs|delivery|shipping)\s+fee\b", r"\b(?:poti|puteti)\s+(?:sa\s+)?(?:\w+\s+)?(?:imprumuta|trimite\s+bani|plati)\b",
    r"\b(?:western\s+union|moneygram|paysafe|card(?:uri)?\s+cadou|gift\s?card)\b",
    r"\bcumparati\s+(?:\w+\s+)?(?:voucher|card|cupon)",
    r"\b(?:o\s+)?(?:taxa|comision|garantie|avans|depozit|cautiune)\s+(?:\w+\s+){0,3}de\s+\d[\d.,]*\s*(?:lei|ron|euro|eur|€)",
    r"\btrebuie\s+(?:sa\s+)?(?:\w+\s+)?(?:platit|platita|achitat|achitata|platiti|achitati|depus|depuneti|transferat)\b",
    r"\bretrage(?:ti)?\s+(?:\S+\s+){0,4}(?:cash|numerar|bani|banii|lei|euro)\b",
    r"\bam\s+nevoie\s+de\s+(?:\d[\d.,]*\s*(?:lei|ron|euro|eur|€|dolari)|bani)\b",
    r"\b(?:vine|trimit)\s+(?:un\s+)?(?:coleg|curier|om)\s+(?:sa\s+)?(?:-i\s+)?(?:ridice|ia|preia)\s+(?:banii)?",
)
PAYMENT_PAST = re.compile(r"\b(?:a\s+fost|au\s+fost|am|ati|s-a)\s+(?:deja\s+)?(?:achitat|achitata|platit|platita|"
                          r"efectuat|efectuata|transferat|depus|virat)")

# ---------------------------------------------------------------- RF_NEW_NUMBER
NEW_NUMBER = _c(
    r"\bnumar(?:ul)?\s+(?:meu\s+)?nou\b", r"\bnoul\s+(?:meu\s+)?numar\b", r"\b(?:un\s+)?alt\s+numar\b",
    r"\bschimbat\s+numarul\b", r"\b(?:telefonul|mobilul)\s+(?:meu\s+)?(?:mi\s+)?(?:s-a\s+)?(?:stricat|spart|furat|pierdut|"
    r"cazut|defectat)", r"\bmi\s*(?:s-a|-a)\s+(?:stricat|spart|furat|pierdut|cazut|defectat)\s+(?:\w+\s+)?(?:telefonul|mobilul)",
    r"\bsalveaza(?:-l|-ma|ti-l|ti-ma)?\s+(?:noul\s+)?(?:numar|asta|acesta)", r"\b(?:asta|acesta|acum)\s+e\s+numarul\s+(?:meu|nou)",
    r"\bde\s+pe\s+(?:numarul|telefonul)\s+(?:unui|unei)\s+(?:prieten|prietene|coleg|colege|amic)",
)
FAMILY = re.compile(r"\b(?:mami|mama|mamico|tati|tata|tataie|bunico|bunicule|buni|mamaie|bunica|bunicu|matusa|unchiule|"
                    r"fiul|fiica|nepotul|nepoata|puiule|sunt\s+eu|eu\s*,)\b")

# ---------------------------------------------------------------- RF_SECRECY
SECRECY = _c(
    r"\bnu\s*-?\s*(?:ii|i|le|lui|ei)?\s*-?\s*(?:spune|spuneti|zice|ziceti|zi|povesti|povestiti)\s+(?:nimic\s+)?"
    r"(?:lui|nimanui|la\s+nimeni|la\s+banca|celorlalti|familiei|tatalui|mamei|sotului|sotiei|copiilor|bancii)",
    r"\bnu-i\s+(?:spune|zice|zi|spuneti)\b", r"\bnu\s+le\s+(?:spune|spuneti|zice)\b",
    r"\b(?:sa\s+)?ramana\s+(?:doar\s+)?intre\s+noi\b", r"\bintre\s+noi\b", r"\b(?:e|este)\s+(?:un\s+|o\s+)?(?:\w+\s+)?secret(?:a|e)?\b",
    r"\bsecret(?:ul)?\s+(?:nostru|total)\b", r"\bstrict\s+confidential\b", r"\bconfidential(?:a|itate)?\b",
    r"\bnu\s+(?:vorbiti|vorbi|discutati|discuta)\s+(?:\w+\s+)?cu\s+(?:nimeni|altcineva|familia|banca|copiii)",
    r"\bnu\s+(?:anuntati|anunta|sunati|suna|contactati)\s+(?:\w+\s+)?(?:banca|politia|pe\s+nimeni|familia|copiii)",
    r"\bfara\s+sa\s+(?:stie|afle|spuneti|spui)\b", r"\bnimeni\s+(?:nu\s+trebuie\s+sa|sa\s+nu)\s+(?:stie|afle)\b",
    r"\bnu\s+spune(?:ti)?\s+(?:nimanui|la\s+nimeni)\b",
)

# ---------------------------------------------------------------- RF_TOO_GOOD
TOO_GOOD = _c(
    r"\b(?:ati|ai)\s+(?:castigat|fost\s+(?:ales|aleasa|selectat|selectata|desemnat|desemnata|extras|extrasa))",
    r"\bcastigator(?:ul|ului|ii)?\b", r"\b(?:un\s+)?premiu(?:l)?\b", r"\btombola\b", r"\bloteri(?:a|e)\b",
    r"\bextragere(?:a)?\b", r"\bgarantat(?:a|e)?\b", r"\bprofit(?:ul|uri)?\s+(?:garantat|sigur|zilnic|lunar|de\s+\d)",
    r"\brandament(?:ul)?\b", r"\bcastig(?:uri|ati|i)?\s+(?:\w+\s+)?(?:zilnic|lunar|pe\s+zi|pe\s+luna|sigur|garantat|de\s+pana)",
    r"\bbani\s+(?:usor|rapid|gratis)", r"\bvenit\s+pasiv\b", r"\bfara\s+(?:niciun\s+)?risc\b",
    r"\b(?:pensia|salariul|ajutorul|alocatia|indemnizatia)\s+(?:\S+\s+){0,3}(?:va\s+|se\s+)?(?:creste|cresc|majora|mari|mareste|majoreaza)",
    r"\b(?:majorare|marire|crestere|bonus)\s+(?:a\s+|la\s+)?(?:pensiei|pensie|salariului)\b", r"\bdublat\s+banii\b",
    r"\bvesti\s+bune\b", r"(?<!card\s)\b(?:bonus|cadou)\s+de\s+\d", r"\bvoucher\s+de\s+\d", r"\bcastigati\b", r"\bpoti\s+castiga\b", r"\bputeti\s+castiga\b",
    r"\bmostenire\b", r"\bdespagubire\s+de\b", r"\bde\s+\d+\s*(?:ori|x)\s+(?:mai\s+mult|banii)",
    r"\b(?:recomandat|recomandata)\s+de\s+(?:experti|specialisti)",
    r"\b(?:am\s+)?(?:facut|castigat|scos)\s+\d[\d.,]*\s*(?:de\s+)?(?:lei|ron|euro|eur|€|dolari)\s+(?:in|intr-o)\s+(?:o\s+|doar\s+o\s+)?"
    r"(?:zi|saptamana|luna|ora)\b",
    r"\byou\s+(?:have\s+)?won\b", r"\bwinner\b", r"\bguaranteed\b",
)

# ---------------------------------------------------------------- RF_URGENCY
URGENCY = _c(
    r"\burgent(?:a|e)?\b", r"\bimediat\b", r"\bchiar\s+acum\b", r"\bcat\s+mai\s+(?:repede|curand)\b",
    r"\bin\s+(?:cel\s+mult\s+|maxim\s+|urmatoarele\s+)?\d+\s*(?:h|ore|ora|minute|min|zile)\b", r"\b\d+\s*h\b",
    r"\bintr-o\s+(?:ora|zi)\b", r"\bpana\s+(?:azi|astazi|diseara|maine|la\s+ora|la\s+sfarsitul\s+zilei|la\s+\d|in\s+\d)",
    r"\btermen(?:ul)?\s+(?:limita|de\s+\d)", r"\bexpira\b", r"\bexpirat?\b\s+in\b", r"\bultima\s+(?:zi|sansa|ocazie|notificare)\b",
    r"\bgrabiti(?:-va)?\b", r"\bgrabeste(?:-te)?\b", r"\brepede\b", r"\bnu\s+mai\s+(?:amanati|asteptati)\b",
    r"\btrebuie\s+(?:\S+\s+){0,4}(?:azi|astazi|acum)\b", r"\b(?:azi|astazi)\s+(?:\S+\s+){0,2}(?:trebuie|ultima)\b",
    r"\bin\s+(?:aceasta|seara\s+asta|ziua\s+de\s+azi)\b", r"\bdoar\s+azi\b", r"\bastazi\s+este\s+ultima\b",
    r"\bin\s+cateva\s+(?:minute|ore)\b",
    r"\b(?:immediately|asap|within\s+\d+\s*(?:h|hours|minutes))\b", r"\bexpires?\b",
)

# ---------------------------------------------------------------- RF_THREAT
THREAT = _c(
    r"\b(?:cont|card)(?:ul)?\s+(?:\S+\s+){0,5}(?:blocat|suspendat|inchis|dezactivat|restrictionat|sters|anulat)",
    r"\bblocat(?:a|e)?\b", r"\bsuspendat(?:a|e)?\b", r"\bsuspendare(?:a)?\b", r"\bamenzi?\b", r"\bamenda\b",
    r"\bpenalitat", r"\bexecutare\s+silita\b", r"\bpoprire\b", r"\bdosar\s+penal\b", r"\binchisoare\b",
    r"\bmandat\s+de\b", r"\bsanctiun", r"\bvirus(?:i|ul|uri|urile)?\b", r"\binfectat", r"\bpiratat",
    r"\b(?:cont|calculator|telefon)(?:ul)?\s+(?:\S+\s+){0,3}(?:spart|compromis|hackuit|atacat)",
    r"\bactivitate\s+suspecta\b", r"\b(?:tranzacti(?:e|i)|plat(?:a|i)|operatiun(?:e|i)|retrager(?:e|i)|transfer)\s+(?:\S+\s+){0,2}suspect", r"\bacces\s+neautorizat\b",
    r"\bveti\s+pierde\b", r"\bva\s+fi\s+(?:sters|anulat|inchis|blocat|suspendat)", r"\bfurat\s+bani",
    r"\bv-au\s+furat\b", r"\bincearca\s+sa\s+(?:va\s+)?(?:transfere|retraga|fure|goleasca|acceseze)\b",
    r"\b(?:on\s+hold|suspended|blocked|locked)\b", r"\b(?:goleasca|golit|goli)\s+(?:\w+\s+)?contul\b", r"\bplangere\s+penala\b", r"\bin\s+instanta\b",
)

# ---------------------------------------------------------------- RF_EMOTIONAL_PRESSURE
EMOTIONAL = _c(
    r"\baccident(?:at|ata|ul)?\b", r"\bspital(?:ul)?\b", r"\burgenta\s+medicala\b", r"\boperati(?:e|a)\b",
    r"\bambulanta\b", r"\barestat(?:a)?\b", r"\b(?:am\s+fost|sunt)\s+retinut(?:a)?\b", r"\bdisperat(?:a)?\b", r"\bajuta-ma\b",
    r"\bajutati-ma\b", r"\bsunt\s+in\s+(?:mare\s+)?(?:necaz|pericol|belea|bucluc)\b", r"\bplang\b",
    r"\be\s+(?:foarte\s+)?grav\b", r"\bgrav\s+bolnav", r"\bdoar\s+tu\s+(?:ma\s+)?(?:poti|esti)\b",
    r"\bsingura\s+(?:mea\s+)?speranta\b", r"\bte\s+iubesc\b", r"\biubirea\s+mea\b",
    r"\b(?:imi|mi-e)\s+(?:e\s+)?(?:frica|teama)\b", r"\bva\s+rog\s+din\s+suflet\b", r"\bte\s+implor\b",
)

# ---------------------------------------------------------------- RF_CHANNEL_SWITCH
_APPS = r"(?:telegram|whatsapp|whats\s?app|signal|viber|messenger|instagram|skype|wechat|discord|tiktok)"
CHANNEL_SWITCH = _c(
    r"\b(?:vorbim|scrie(?:-mi|-ne|ti-mi|ti-ne)?|contacteaza(?:-ma|-ne)?|contactati(?:-ma|-ne)?|adauga(?:-ma)?|adaugati(?:-ma|-ne)?|"
    r"treci|trecem|treceti|continuam|mutam|vorbi|discutam|gasesti|gasiti|intra|intrati)\s+(?:\S+\s+){0,3}pe\s+" + _APPS,
    r"\bpe\s+" + _APPS + r"\s+(?:\S+\s+){0,2}(?:vorbim|discutam|continuam|e\s+mai\s+(?:simplu|usor|sigur))",
    r"\bt\.me/", r"\bwa\.me/", r"\bgrupul\s+(?:nostru\s+)?(?:de\s+)?" + _APPS,
)

# ---------------------------------------------------------------- org / authority claims (for IMPERSONATION)
GENERIC_CLAIMS = [
    # (regex, org_key or None). org_key matches catalog compact names.
    (r"\bbanca\s*dunarea\b|\bbancadunarea\b", "bancadunarea"),
    (r"\bcurier\s*expres+\b", "curierexpres"),
    (r"\bpiata\s*mea\b", "piatamea"),
    (r"\bmega\s*shop\b", "megashop"),
    (r"\banaf\b|\bagentia\s+nationala\s+de\s+administrare\s+fiscala\b|\bfiscul?\b", "anaf"),
    # generic claims carry a category key (starts with "_") used for the scam type
    (r"\bcasa\s+(?:nationala\s+)?de\s+pensii\b|\bcnpp\b|\bcasa\s+de\s+asigurari\b", "_pension"),
    (r"\bpolitia\b|\bpolitist(?:ul)?\b|\bagent(?:ul)?\s+de\s+politie\b|\bdiicot\b|\bparchet(?:ul)?\b|\bjandarmeri|"
     r"\bcomisar(?:ul)?\b|\bprocuror(?:ul)?\b", "_police"),
    (r"\bsuport(?:ul)?\s+tehnic\b|\bdepartamentul\s+tehnic\b|\bmicrosoft\b|\bwindows\b|\bapple\b|\bgoogle\b", "_tech"),
    (r"\b(?:de\s+la|din\s+partea|reprezentant(?:ul)?|angajat(?:ul)?)\s+(?:\w+\s+)?(?:bancii|banca|bancii\s+dvs)\b|"
     r"\bbanca\s+(?:dvs|dumneavoastra|ta)\b|\bserviciul\s+clienti\b|\bdepartamentul\s+(?:de\s+securitate|de\s+fraude|antifrauda)\b",
     "_bank"),
    (r"\bprimari(?:a|ei)\b|\bministerul\b|\bguvern(?:ul)?\b|\bghiseul(?:\.ro)?\b|\bdgaspc\b|\bcnas\b|\bmedic(?:ul)?\s+de\s+familie\b",
     "_gov"),
    (r"\bposta(?:\s+romana)?\b|\bfirma\s+de\s+curierat\b|\bfan\s*courier\b|\bsameday\b|\bdhl\b|\bcargus\b|\bgls\b|\bdpd\b|"
     r"\bvama\b|\bautoritatea\s+vamala\b", "_courier"),
    (r"\bnetflix\b|\bemag\b|\bolx\b|\brevolut\b|\bbcr\b|\bbrd\b|\bing\s+bank\b|\bbanca\s+transilvania\b|\braiffeisen\b|"
     r"\bcec\s+bank\b|\benel\b|\be-?on\b|\bdigi\b|\borange\b|\bvodafone\b", "_brand"),
]
GENERIC_CLAIMS = [(re.compile(p), k) for p, k in GENERIC_CLAIMS]
# "X:" at the very start of an SMS is a sender-style header claim, e.g. "CurierExpres: ..."
HEADER_CLAIM = re.compile(r"^\s*([a-z][a-z .]{2,30}):")


def _spans(regex, text, flag):
    return [(flag, (m.start(), m.end())) for m in regex.finditer(text)]


PAY_ON_DELIVERY = re.compile(r"\bla\s+livrare\b|\bramburs\b|\bcash\s+la\b|\bla\s+ridicare\b|\bnumerar\s+la\b|\bla\s+fata\s+locului\b")


def _is_request_list(ntext, sent, pos):
    """A bare list of data items is a request too: "Numele complet, CNP-ul si numarul cardului." /
    "Card number and CVV, please." -> the data word is near the start of the sentence or the sentence asks (?/va rog)."""
    s0 = ntext.find(sent)
    near_start = s0 >= 0 and pos - s0 <= 30
    return near_start or "?" in sent or bool(re.search(r"\b(?:va\s+rog|te\s+rog|please)\b", sent))


def _sentence_of(text, pos):
    for s, e in sentences(text):
        if s <= pos < e:
            return text[s:e]
    return text


def detect(ntext: str, known_contact: bool = False, prev_ntext: str = ""):
    """Return list of (flag, span) for one normalised message text.

    prev_ntext: the previous sender message (a code mentioned there can be requested here: "mi-l trimiti?")."""
    out = []
    if not ntext or not ntext.strip():
        return out
    negated = bool(NEG_ADVICE.search(ntext))

    # CODE_REQUEST: strong request phrasing next to a code noun; safety-advice negation vetoes weak matches.
    if CODE_NOUN.search(ntext) or CODE_NOUN.search(prev_ntext or ""):
        strong = list(CODE_REQ_STRONG.finditer(ntext))
        for m in strong:
            sent = _sentence_of(ntext, m.start())
            if NEG_ADVICE.search(sent) and not re.search(r"-mi\b|mi-l|inapoi|pe\s+care\s+mi", sent):
                continue
            out.append(("RF_CODE_REQUEST", (m.start(), m.end())))
        # "mi-l poti trimite inapoi" refers to a code mentioned in the previous sentence
    out += _spans(REMOTE, ntext, "RF_REMOTE_ACCESS")

    # DATA_REQUEST
    for m in DATA_STRONG.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if NEG_ADVICE.search(sent):
            continue
        if DATA_DESCRIPTIVE.search(sent) and not DATA_VERB.search(sent):
            continue  # "hackerii va vad parolele" describes a threat, it is not a request
        if not DATA_VERB.search(sent) and not _is_request_list(ntext, sent, m.start()):
            continue  # "...dupa 3 introduceri gresite ale PIN-ului" only mentions the PIN
        out.append(("RF_DATA_REQUEST", (m.start(), m.end())))
    for m in DATA_WEAK.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if DATA_VERB.search(sent) and not NEG_ADVICE.search(sent):
            if m.group(0).startswith("datele") and not re.search(r"\b(?:confirm|verific|valid|actualiz)", sent):
                continue
            out.append(("RF_DATA_REQUEST", (m.start(), m.end())))

    # PAYMENT_REQUEST (skip sentences that only report a past payment)
    for m in PAYMENT.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if NEG_ADVICE.search(sent) and re.search(r"\bnu\s+(?:va\s+)?(?:cer|solicit|trebuie)", sent):
            continue
        if PAYMENT_PAST.search(sent) and not re.search(r"\b(?:achitati|platiti|transferati|virati|trimiteti|depuneti)\b", sent):
            continue
        if re.search(r"\b0\s*(?:lei|ron)\b", sent) and not re.search(r"\b(?:achitati|platiti|transferati)\b", sent):
            continue
        if PAY_ON_DELIVERY.search(sent):
            continue  # "puteti plati la livrare / ramburs / cash la ridicare" is the safe way to pay
        out.append(("RF_PAYMENT_REQUEST", (m.start(), m.end())))

    if not known_contact:
        out += _spans(NEW_NUMBER, ntext, "RF_NEW_NUMBER")

    for m in SECRECY.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if re.search(r"\b(?:cod|codul|parola|pin|otp)\b", sent) and NEG_ADVICE.search(sent):
            continue  # "nu spuneti nimanui codul" = genuine safety advice
        out.append(("RF_SECRECY", (m.start(), m.end())))

    out += _spans(TOO_GOOD, ntext, "RF_TOO_GOOD")
    for m in URGENCY.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if re.search(r"\bnu\s+pierdeti\b", sent) and not re.search(r"urgent|imediat|azi|ore|expira", sent):
            continue
        out.append(("RF_URGENCY", (m.start(), m.end())))
    out += _spans(THREAT, ntext, "RF_THREAT")
    for m in EMOTIONAL.finditer(ntext):
        sent = _sentence_of(ntext, m.start())
        if re.search(r"\bsunt\s+bine\b|nu-?\s*ti\s+face\s+griji|nu\s+va\s+faceti\s+griji|\bmic\s+accident", sent):
            continue
        out.append(("RF_EMOTIONAL_PRESSURE", (m.start(), m.end())))
    out += _spans(CHANNEL_SWITCH, ntext, "RF_CHANNEL_SWITCH")
    return out


_NOT_CLAIM_BEFORE = re.compile(r"(?:\bprin|\bpe|\bvia|\bin\s+aplicatia|\bcontul\s+de|\bde\s+pe|\bla\s+ghiseul)\s+$")


def org_claims(ntext: str):
    """Return list of (org_key|None, span) for organisations/authorities the text speaks for.

    "am platit prin PiataMea" / "am vazut anuntul pe PiataMea" mention a platform, they do not claim to BE it."""
    claims = []
    for rx, key in GENERIC_CLAIMS:
        for m in rx.finditer(ntext):
            if _NOT_CLAIM_BEFORE.search(ntext[max(0, m.start() - 25):m.start()]):
                continue
            claims.append((key, (m.start(), m.end())))
    return claims
