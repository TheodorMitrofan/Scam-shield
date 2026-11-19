"""Formal Romanian wording used in the report e-mail (the UI has its own, friendlier labels)."""

from app.schemas import Channel, RedFlag, ScamType

CHANNEL_LABEL = {
    Channel.SMS: "SMS",
    Channel.WHATSAPP: "WhatsApp",
    Channel.EMAIL: "e-mail",
    Channel.CHAT: "chat (platformă online)",
    Channel.CALL_TRANSCRIPT: "apel telefonic",
}

# How the contact reached the victim, used inside sentences ("am primit ...").
CHANNEL_PHRASE = {
    Channel.SMS: "un SMS",
    Channel.WHATSAPP: "mesaje pe WhatsApp",
    Channel.EMAIL: "un e-mail",
    Channel.CHAT: "mesaje pe o platformă de chat",
    Channel.CALL_TRANSCRIPT: "un apel telefonic",
}

SCAM_TYPE_LABEL = {
    ScamType.BANK_IMPERSONATION: "Uzurparea identității unei bănci",
    ScamType.COURIER_FEE: "Taxă falsă de curierat",
    ScamType.AUTHORITY_IMPERSONATION: "Uzurparea identității unei instituții publice",
    ScamType.FAMILY_EMERGENCY: "Falsă urgență în familie",
    ScamType.TECH_SUPPORT: "Fals suport tehnic",
    ScamType.MARKETPLACE: "Înșelăciune pe platformă de vânzări",
    ScamType.ACCOUNT_TAKEOVER: "Preluarea unui cont (cerere de cod)",
    ScamType.INVESTMENT: "Investiție falsă",
    ScamType.ROMANCE: "Înșelăciune sentimentală",
    ScamType.JOB_OFFER: "Ofertă falsă de muncă",
    ScamType.PRIZE_LOTTERY: "Premiu sau loterie falsă",
    ScamType.OTHER: "Altă tentativă de înșelăciune",
    ScamType.NONE: "Fără tentativă de înșelăciune",
}

# One sentence: what the scammer tried to do.
SCAM_TYPE_STORY = {
    ScamType.BANK_IMPERSONATION: "Persoana s-a dat drept banca mea și a încercat să mă convingă să intru pe o adresă de internet falsă sau să îi dau datele cardului.",
    ScamType.COURIER_FEE: "Persoana s-a dat drept o firmă de curierat și mi-a cerut să plătesc o taxă pentru un colet.",
    ScamType.AUTHORITY_IMPERSONATION: "Persoana s-a dat drept o instituție a statului și mi-a cerut date personale sau bancare.",
    ScamType.FAMILY_EMERGENCY: "Persoana s-a dat drept un membru al familiei, de pe un număr nou, și mi-a cerut bani urgent.",
    ScamType.TECH_SUPPORT: "Persoana s-a dat drept suport tehnic și mi-a cerut să instalez un program de control de la distanță.",
    ScamType.MARKETPLACE: "Persoana s-a dat drept cumpărător și mi-a trimis o adresă falsă de plată, cerându-mi datele cardului.",
    ScamType.ACCOUNT_TAKEOVER: "Persoana mi-a cerut un cod primit prin SMS, probabil pentru a-mi prelua un cont.",
    ScamType.INVESTMENT: "Persoana mi-a promis câștiguri garantate dintr-o investiție și mi-a cerut bani.",
    ScamType.ROMANCE: "Persoana a legat o relație de prietenie online și apoi mi-a cerut bani.",
    ScamType.JOB_OFFER: "Persoana mi-a oferit un câștig ușor pentru sarcini simple și apoi mi-a cerut un depozit.",
    ScamType.PRIZE_LOTTERY: "Persoana mi-a spus că am câștigat un premiu, pentru a obține date sau bani de la mine.",
    ScamType.OTHER: "Persoana a încercat să obțină de la mine bani, date sau acces la dispozitive.",
    ScamType.NONE: "",
}

FLAG_LABEL = {
    RedFlag.CODE_REQUEST: "a cerut un cod primit prin SMS sau din aplicație",
    RedFlag.REMOTE_ACCESS: "a cerut instalarea unui program de control de la distanță",
    RedFlag.DATA_REQUEST: "a cerut date de card, parole, CNP sau acte",
    RedFlag.PAYMENT_REQUEST: "a cerut o plată, un transfer sau o taxă",
    RedFlag.SUSPICIOUS_CONTACT: "a folosit o adresă de internet, un e-mail sau un număr neoficial",
    RedFlag.NEW_NUMBER: "a scris de pe un număr nou, dându-se drept rudă sau prieten",
    RedFlag.SECRECY: "a cerut păstrarea secretului",
    RedFlag.TOO_GOOD: "a promis un premiu, o rambursare sau un câștig prea bun",
    RedFlag.IMPERSONATION: "s-a dat drept o bancă, o firmă, o instituție sau suport tehnic",
    RedFlag.URGENCY: "a impus un termen scurt sau a grăbit decizia",
    RedFlag.THREAT: "a amenințat cu blocarea contului, amenzi sau viruși",
    RedFlag.EMOTIONAL_PRESSURE: "a folosit frica, mila sau afecțiunea ca presiune",
    RedFlag.CHANNEL_SWITCH: "a cerut mutarea conversației în altă aplicație",
}
