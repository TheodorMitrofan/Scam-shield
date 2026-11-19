from typing import Dict
from .text_utils import normalize_text


class WarningGenerator:
    """
    Generates calm, respectful warnings in Romanian (max 3 short sentences, zero jargon),
    plus optional English translations for UI bilingual toggle.
    """

    def generate_warning(self, analysis_result: Dict, scenario_text: str = "") -> str:
        return self.generate_bilingual_warning(analysis_result, scenario_text=scenario_text)["ro"]

    def generate_bilingual_warning(self, analysis_result: Dict, scenario_text: str = "") -> Dict[str, str]:
        verdict = analysis_result.get("verdict", "SAFE")
        scam_type = analysis_result.get("scam_type", "NONE")
        red_flags = set(analysis_result.get("red_flags", []))
        norm_ctx = normalize_text(scenario_text)
        if not norm_ctx and analysis_result.get("messages_analysis"):
            norm_ctx = normalize_text(" ".join(
                str(m.get("text") or "") for m in analysis_result["messages_analysis"] if isinstance(m, dict)
            ))

        if verdict == "SAFE":
            return {
                "ro": (
                    "Mesajul pare în regulă. "
                    "Nu vi se cer date personale, bani sau coduri secrete. "
                    "Puteți continua liniștit, dar păstrați întotdeauna codurile doar pentru dumneavoastră."
                ),
                "en": (
                    "This message looks safe. "
                    "It does not ask for personal details, money, or secret codes. "
                    "You may proceed safely, while always keeping your codes private."
                ),
            }

        if verdict == "SUSPICIOUS":
            if scam_type == "PRIZE_LOTTERY":
                ro_action = (
                    "Nu trimiteți date personale și verificați oferta direct pe megashop.ro sau la 0800 500 600."
                    if "megashop" in norm_ctx
                    else "Nu trimiteți date personale și verificați oferta direct pe site-ul oficial al magazinului."
                )
                return {
                    "ro": (
                        "Atenție, verificați înainte să răspundeți! "
                        "Ați primit un mesaj despre un premiu sau o promoție neașteptată. "
                        + ro_action
                    ),
                    "en": (
                        "Caution, verify before replying! "
                        "You received an unexpected prize or promotion message. "
                        "Do not share personal details and check the offer directly on the store's official website."
                    ),
                }
            if scam_type == "JOB_OFFER":
                return {
                    "ro": (
                        "Atenție, verificați înainte să răspundeți! "
                        "Ofertele care promit câștiguri foarte mari și ușoare pe zi pot fi capcane. "
                        "Nu plătiți nicio taxă și nu mutați discuția pe alte aplicații cu persoane necunoscute."
                    ),
                    "en": (
                        "Caution, verify before replying! "
                        "Offers promising unusually easy daily earnings may be traps. "
                        "Never pay upfront fees or move the chat to another app with strangers."
                    ),
                }
            if scam_type == "ROMANCE":
                return {
                    "ro": (
                        "Atenție, fiți precaut! "
                        "O persoană cunoscută doar pe internet vă cere bani sau ajutor financiar. "
                        "Nu trimiteți bani și cereți sfatul unei persoane apropiate din familie."
                    ),
                    "en": (
                        "Caution, please be careful! "
                        "Someone you only met online is asking for money or financial help. "
                        "Do not send money and ask a trusted family member for advice."
                    ),
                }
            return {
                "ro": (
                    "Atenție, verificați înainte să răspundeți! "
                    "Acest mesaj conține detalii neobișnuite sau vă cere date sensibile. "
                    "Nu accesați adrese de internet din mesaj și contactați instituția doar pe canalul oficial."
                ),
                "en": (
                    "Caution, verify before replying! "
                    "This message contains unusual details or requests sensitive information. "
                    "Do not open links from the message and contact the organization through official channels."
                ),
            }

        # SCAM verdict warnings (<= 3 short sentences, zero jargon, official action only)
        if scam_type == "BANK_IMPERSONATION":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Mesajul se dă drept banca dumneavoastră pentru a vă speria sau a vă cere datele ori mutarea banilor. "
                    "Nu apăsați pe adresa trimisă; sunați direct la numărul de pe spatele cardului sau la Banca Dunărea: 0800 100 200."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "The message pretends to be your bank to frighten you or ask for card details or money transfers. "
                    "Do not open any link sent; call the number on the back of your card directly."
                ),
            }

        if scam_type == "COURIER_FEE":
            ro_action = (
                "Nu plătiți și nu introduceți cardul; verificați coletul direct pe curierexpres.ro sau la 0800 300 400."
                if "curierexpres" in norm_ctx
                else "Nu plătiți și nu introduceți cardul; verificați coletul direct pe site-ul oficial al curierului."
            )
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Cineva pretinde că este o firmă de curierat și vă cere o taxă pe o adresă de internet falsă. "
                    + ro_action
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Someone pretends to be a courier company asking for a fee on a fake web address. "
                    "Do not pay or enter card details; check your parcel directly on the official courier website."
                ),
            }

        if scam_type == "FAMILY_EMERGENCY":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Cineva pretinde că o rudă are o urgență și vă cere bani imediat, cerându-vă să păstrați secretul. "
                    "Nu trimiteți niciun ban; sunați-vă ruda direct la numărul ei vechi pe care îl știți."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Someone claims a relative has an emergency and asks for money urgently in secret. "
                    "Do not send money; call your relative directly at their usual known phone number."
                ),
            }

        if scam_type == "TECH_SUPPORT":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Nimeni de la suportul tehnic nu vă sună să vă spună că aveți viruși sau să instalați programe de control. "
                    "Nu instalați nicio aplicație și închideți imediat apelul."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Legitimate tech support never calls asking you to install remote-control apps for viruses. "
                    "Do not install any software and hang up immediately."
                ),
            }

        if scam_type == "AUTHORITY_IMPERSONATION":
            ro_action = (
                "Nu comunicați date personale și verificați direct pe anaf.ro sau la 031 403 91 60."
                if "anaf" in norm_ctx
                else "Nu comunicați date personale și verificați direct la instituția oficială sau cu un membru al familiei."
            )
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Instituțiile statului nu cer niciodată datele cardului, coduri din mesaje sau retragerea banilor prin telefon. "
                    + ro_action
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Government authorities never ask for card details, message codes, or cash withdrawals by phone. "
                    "Do not share personal data and verify directly through official government channels."
                ),
            }

        if scam_type == "MARKETPLACE":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Ca să primiți bani pe un produs vândut, nu trebuie niciodată să introduceți datele cardului sau să plătiți o garanție. "
                    "Nu accesați adresa de internet trimisă de cumpărător și discutați doar în aplicația oficială."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "To receive money for an item you sell, you never need to enter card details or pay courier insurance. "
                    "Do not open links sent by the buyer and communicate only inside the official marketplace app."
                ),
            }

        if scam_type == "ACCOUNT_TAKEOVER":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Codul primit prin mesaj aparține contului dumneavoastră și poate fi folosit ca să vă fure accesul, chiar dacă cere o cunoștință. "
                    "Nu trimiteți codul nimănui; sunați persoana la telefon pentru a verifica dacă i-a fost spart contul."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "The code sent to your phone protects your account, even when requested by a known contact. "
                    "Never share codes with anyone; call the person directly to warn them their account may be hacked."
                ),
            }

        if scam_type == "INVESTMENT":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Promisiunile de profituri mari și garantate ori taxele de deblocare a câștigurilor sunt capcane financiare. "
                    "Nu transferați bani și cereți părerea familiei sau a băncii dumneavoastră."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Promises of guaranteed high returns or fees to unlock profits are financial traps. "
                    "Do not transfer money and consult your family or your bank."
                ),
            }

        if scam_type == "ROMANCE":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Escrocii folosesc povești de dragoste sau misiuni în străinătate ca să vă ceară bani, cadouri sau taxe vamale în secret. "
                    "Nu trimiteți bani sau carduri cadou și vorbiți cu o persoană de încredere."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "Scammers use romance or overseas deployment stories to ask for money, gift cards, or customs fees in secret. "
                    "Never send money or gift cards and speak with someone you trust."
                ),
            }

        if scam_type == "JOB_OFFER":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Un loc de muncă real nu vă cere să depuneți bani sau garanții pentru sarcini online cu câștiguri zilnice uriașe. "
                    "Nu trimiteți bani și opriți conversația."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "A real employer never asks you to deposit money or pay a guarantee for simple online tasks. "
                    "Do not send any money and stop responding."
                ),
            }

        if scam_type == "PRIZE_LOTTERY":
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Un premiu adevărat nu vă cere să plătiți o taxă și nu vă solicită datele cardului pe adrese necunoscute. "
                    "Nu introduceți datele cardului și verificați doar pe site-ul oficial al magazinului."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "A genuine prize never asks you to pay a fee or enter card details on unknown websites. "
                    "Do not enter card details and verify only on the store's official website."
                ),
            }

        if "RF_TOO_GOOD" in red_flags or "RF_THREAT" in red_flags:
            return {
                "ro": (
                    "Atenție, pare o țeapă! "
                    "Mesajul încearcă să vă sperie sau să vă convingă să cumpărați ori să plătiți ceva urgent fără verificare. "
                    "Nu comandați, nu plătiți și întrebați mai întâi medicul de familie sau o persoană apropiată."
                ),
                "en": (
                    "Warning, this looks like a scam! "
                    "The message uses fear or miracle promises to rush you into paying or ordering something unverified. "
                    "Do not pay or order and consult your doctor or a trusted family member first."
                ),
            }

        return {
            "ro": (
                "Atenție, pare o țeapă! "
                "Mesajul încearcă să vă convingă să trimiteți date personale, bani sau coduri secrete. "
                "Nu răspundeți, nu accesați adrese de internet din mesaj și cereți sfatul unei persoane de încredere."
            ),
            "en": (
                "Warning, this looks like a scam! "
                "This message tries to pressure you into sharing personal data, money, or secret codes. "
                "Do not reply, avoid links in the message, and ask a trusted person for advice."
            ),
        }
