import os
import random
import joblib
import numpy as np
from typing import List, Tuple
from sklearn.decomposition import TruncatedSVD
from sklearn.ensemble import VotingClassifier
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.linear_model import LogisticRegression
from sklearn.metrics import classification_report
from sklearn.model_selection import StratifiedKFold, cross_val_score
from sklearn.multiclass import OneVsRestClassifier
from sklearn.naive_bayes import ComplementNB
from sklearn.neural_network import MLPClassifier
from sklearn.pipeline import FeatureUnion, Pipeline
from sklearn.preprocessing import Normalizer
from scam_detector.text_utils import deobfuscate_for_detection

# Zero-leakage training corpus (no V01-V11 verbatim examples, no ADVERSARIAL_SCENARIOS verbatim copies).
# Covers all 13 scam categories + paraphrased intents + near-miss safe hard negatives.
TRAINING_CORPUS: List[Tuple[str, str, List[str]]] = [
    # --- BANK_IMPERSONATION (12) ---
    ("Alerta securitate BCR: cardul dumneavoastra a fost restrictionat temporar. Deblocati accesand bcr-verificare.net in 24 ore", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_URGENCY"]),
    ("ING HomeBank: s-a incercat conectarea de pe un dispozitiv necunoscut. Introduceti userul si parola pe ing-securitate.com", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_DATA_REQUEST"]),
    ("Banca Transilvania: confirmati sau anulati transferul de 2.100 lei introducand datele cardului pe bt-anulare.info", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_DATA_REQUEST"]),
    ("Va sun de la departamentul antifrauda bancara. Contul dvs a fost compromis, trebuie sa mutati urgent banii intr-un cont de siguranta", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Raiffeisen Notificare: contul dvs va fi suspendat astazi daca nu actualizati codul PIN si CVV pe linkul urmator", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_DATA_REQUEST", "RF_URGENCY"]),
    ("Buna ziua, suntem de la securitatea bancii. Va rog sa ne cititi numarul complet al cardului si codul de pe spate pentru blocare", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_DATA_REQUEST"]),
    ("BRD: O tranzactie suspecta de 4.200 lei este in curs. Sunati imediat la numarul nostru de urgenta 0371 888 999", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_URGENCY"]),
    ("Revolut Security: your account is locked due to unusual activity. Verify card details within 12 hours", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_DATA_REQUEST", "RF_URGENCY"]),
    ("Serviciul antifrauda: transferati fondurile in contul protejat al bancii ca sa nu vi se goleasca contul, pastrati secretul", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Unicredit: cardul a fost blocat preventiv. Reactivarea se face prin introducerea codului SMS primit pe telefon", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_CODE_REQUEST"]),
    ("Banca va atentioneaza ca economiile sunt in pericol: transferati banii in depozitul de rezerva indicat de consilier", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST"]),
    ("Departamentul siguranta financiara bancara: aveti un debit neautorizat, confirmati cardul pe portalul de blocare", "BANK_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_DATA_REQUEST"]),

    # --- COURIER_FEE (11) ---
    ("FanCourier: pachetul dvs nu a putut fi predat din cauza adresei incomplete. Achitati taxa de relivrare de 3,50 lei", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST"]),
    ("DPD Romania: coletul este blocat in vama si necesita plata unei taxe vamale de 9 lei pe dpd-taxa.online", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST"]),
    ("Sameday Easybox: coletul dvs asteapta achitarea taxei de depozitare de 4,99 lei astazi altfel se intoarce la expeditor", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Posta Romana: aviz colet extern. Pentru livrare rapida achitati comisionul postal de 2 euro cu cardul", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST", "RF_DATA_REQUEST"]),
    ("DHL Express: Your parcel is held at customs. Please pay the 2.50 EUR delivery fee to schedule shipping", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST"]),
    ("FedEx Notification: package delivery suspended until you pay the customs clearance charge online", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST"]),
    ("Cargus: livrarea a esuat. Reprogramati curierul achitand suma de 5 lei si completand datele cardului", "COURIER_FEE", ["RF_IMPERSONATION", "RF_PAYMENT_REQUEST", "RF_DATA_REQUEST"]),
    ("Aveti un colet cu numar AWB retinut in terminal. Platiti taxa de procesare de 1,99 EUR in 24 de ore", "COURIER_FEE", ["RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Curierul nu a gasit destinatarul la adresa pentru coletul dvs. Confirmati adresa si platiti taxa de transport de 6 lei", "COURIER_FEE", ["RF_PAYMENT_REQUEST"]),
    ("Livrare colet blocata: pentru a primi pachetul prin curier achitati taxa de vama si reprogramare online", "COURIER_FEE", ["RF_PAYMENT_REQUEST"]),
    ("Colet retinut la sortare! Validati livrarea si platiti tariful de reexpediere accesand scurtatura web", "COURIER_FEE", ["RF_PAYMENT_REQUEST"]),

    # --- AUTHORITY_IMPERSONATION (12) ---
    ("ANAF: aveti o restituire de taxe de 950 lei. Completati formularul cu IBAN si card pe anaf-portal.com", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Ghiseul.ro: figurati cu o amenda rutiera neplatita de 450 lei. Evitati executarea silita platind acum", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Politia Romana: s-a deschis un dosar penal pe numele dumneavoastra. Contactati inspectoratul si achitati amenda astazi", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Sunt comisarul Popescu de la politia economica. O retea de hoti vrea sa va fure banii din cont, retrageti banii si dati-i colegului nostru, ancheta e secreta", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Casa Nationala de Pensii: pensia va creste automat cu 420 lei. Confirmati datele personale, CNP si cardul pentru virament", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Ministerul Finantelor: declaratia fiscala are erori. Riscati poprire pe cont daca nu validati datele bancare pana maine", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_DATA_REQUEST", "RF_URGENCY"]),
    ("Sunt procuror DIICOT: contul dumneavoastra este implicat intr-o investigatie. Nu vorbiti cu nimeni de la banca", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_SECRECY"]),
    ("Directia Taxe si Impozite: beneficiati de o rambursare de 1.100 lei. Introduceti cardul pentru incasare", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Citatie oficiala de la Inspectoratul de Politie: aveti mandat de aducere pentru frauda informatica, achitati amenda in 24 ore", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Guvernul Romaniei si Casa de Pensii acorda compensatie la factura. Completati seria de buletin si datele cardului", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Biroul executor judecatoresc: somat pentru datorie fiscala! Evitati sechestrul pe bunuri achitand obligatia de plata azi", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Ajutor guvernamental de la minister pentru plata facturilor: introduceti datele de pe buletin si contul bancar", "AUTHORITY_IMPERSONATION", ["RF_IMPERSONATION", "RF_TOO_GOOD", "RF_DATA_REQUEST"]),

    # --- FAMILY_EMERGENCY (12) ---
    ("Buna mama, mi-am pierdut telefonul si scriu de pe un numar nou. Salveaza contactul asta te rog", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER"]),
    ("Tati, sunt eu, fiul tau! Am avut un accident cu masina, am nevoie urgent de 2.500 lei, nu-i spune mamei ca face criza", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_URGENCY", "RF_SECRECY"]),
    ("Buni, sunt la spital si trebuie platita operatia astazi. Poti sa-mi trimiti 3.000 lei pe contul unui prieten?", "FAMILY_EMERGENCY", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Sunt avocatul nepotului dumneavoastra. A lovit pe cineva si e retinut la politie, trebuie dati bani de cautiune acum, nu sunati pe nimeni", "FAMILY_EMERGENCY", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY", "RF_SECRECY", "RF_EMOTIONAL_PRESSURE"]),
    ("Mamico, mi s-a spart ecranul la mobil si scriu de pe telefonul unei colege. Am o factura urgenta de 1.200 lei de achitat azi", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Fiica ta sunt! Mi s-a blocat cardul in strainatate, te implor fa-mi un transfer de 600 euro pana diseara", "FAMILY_EMERGENCY", ["RF_PAYMENT_REQUEST", "RF_EMOTIONAL_PRESSURE", "RF_URGENCY"]),
    ("Buna tata, acesta este noul meu numar de WhatsApp. Am nevoie de bani imprumut pentru chirie astazi", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Bunico, nepotul tau a fost implicat intr-un incident rutier. Trimitem un coleg acasa sa ridice banii, sa ramana intre noi", "FAMILY_EMERGENCY", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Mami, mi s-a furat portofelul cu telefonul, acesta e nr meu nou. Imi poti transfera 700 lei rapid ca sa ma intorc acasa?", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Buni, sunt intr-o situatie grava, am lovit o masina. Te implor ajuta-ma cu bani azi si nu vorbi cu tata", "FAMILY_EMERGENCY", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_URGENCY", "RF_SECRECY"]),
    ("Buna taticule, am ramas fara baterie la telefonul personal si folosesc alta cartela. Imi pui 900 lei acum?", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Sunt fiica dumneavoastra de pe alt telefon. Am o urgenta medicala si am nevoie de bani imprumut imediat", "FAMILY_EMERGENCY", ["RF_NEW_NUMBER", "RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),

    # --- TECH_SUPPORT (11) ---
    ("Buna ziua, va contactam de la suportul tehnic Microsoft. Calculatorul dumneavoastra este infectat si trimite virusi", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_THREAT"]),
    ("Va rog sa instalati aplicatia AnyDesk sau TeamViewer ca tehnicianul nostru sa va poata remedia problema de la distanta", "TECH_SUPPORT", ["RF_REMOTE_ACCESS"]),
    ("Alerta Windows Defender: sistemul are un troian bancar! Sunati la tehnician si descarcati QuickSupport", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_THREAT", "RF_REMOTE_ACCESS"]),
    ("Sunt de la asistenta tehnica Digi internet. Descarcati UltraViewer pentru configurare router si intrati in aplicatia bancara", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST"]),
    ("Atac cibernetic detectat pe dispozitiv! Oferiti acces remote prin RustDesk pentru a va proteja economiile", "TECH_SUPPORT", ["RF_THREAT", "RF_REMOTE_ACCESS"]),
    ("Instalati programul de partajare a ecranului ca sa verificam impreuna tranzactiile din homebank", "TECH_SUPPORT", ["RF_REMOTE_ACCESS", "RF_DATA_REQUEST"]),
    ("Calculatorul dvs este virusat si hackerii va fura datele. Instalati aplicatia de asistenta la distanta acum", "TECH_SUPPORT", ["RF_THREAT", "RF_REMOTE_ACCESS", "RF_URGENCY"]),
    ("Suport tehnic Apple / Windows: abonamentul de securitate a expirat, descarcati programul de control la distanta", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_REMOTE_ACCESS"]),
    ("Va ajutam de la departamentul IT cu devirusarea laptopului, spuneti-mi ID-ul din AnyDesk ca sa ma conectez", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_REMOTE_ACCESS"]),
    ("Eroare critica de sistem: nu inchideti calculatorul, instalati TeamViewer si logati-va in contul bancar", "TECH_SUPPORT", ["RF_THREAT", "RF_REMOTE_ACCESS", "RF_DATA_REQUEST"]),
    ("Tehnicianul are nevoie sa va vada desktopul de la distanta pentru a curata fisierele infectate", "TECH_SUPPORT", ["RF_IMPERSONATION", "RF_THREAT", "RF_REMOTE_ACCESS"]),

    # --- MARKETPLACE (11) ---
    ("Buna, mai e valabil anuntul cu laptopul? Il cumpar eu, am platit prin Livrare Sigura OLX. Bagati cardul pe link sa incasati", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Sunt din alt oras si trimit curierul sa ridice canapeaua. Am achitat deja pe PiataMea, introduceti CVV-ul pentru transfer", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Cumparator interesat: curierul cere o garantie de 50 lei pe care o platiti dvs acum si o primiti inapoi odata cu pretul", "MARKETPLACE", ["RF_PAYMENT_REQUEST"]),
    ("Buna ziua! Am vazut anuntul dvs cu telefonul. Scrieti-mi urgent pe WhatsApp, plata o facem prin link securizat", "MARKETPLACE", ["RF_CHANNEL_SWITCH", "RF_URGENCY"]),
    ("Produsul dumneavoastra a fost achitat. Linkul de incasare a banilor expira intr-o ora, confirmati datele cardului aici", "MARKETPLACE", ["RF_DATA_REQUEST", "RF_URGENCY"]),
    ("Trimit curierul cu plata online pentru anuntul de pe OLX. Accesati formularul de primire bani pe card", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Vreau sa cumpar masina de cusut de pe PiataMea. Am facut transferul, completati numarul cardului si data expirarii sa primiti suma", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Super, iau obiectul din anunt! Curierul va cere doar asigurarea de livrare de 45 lei pe site-ul de incasare", "MARKETPLACE", ["RF_PAYMENT_REQUEST"]),
    ("Am rezervat produsul din anuntul tau. Intra pe linkul de Livrare Sigura sa confirmi incasarea banilor pe card", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Cumparator PiataMea: ati primit plata pentru produs. Introduceti soldul curent si codul cardului pentru deblocare incasare", "MARKETPLACE", ["RF_DATA_REQUEST"]),
    ("Pentru a incasa banii pe produsul vandut trebuie sa validati cardul cu soldul disponibil pe pagina curierului", "MARKETPLACE", ["RF_DATA_REQUEST"]),

    # --- ACCOUNT_TAKEOVER (12) ---
    ("Scuze, ti-am trimis din greseala un cod de 6 cifre pe SMS. Mi-l poti da inapoi urgent te rog?", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST", "RF_URGENCY"]),
    ("Hei, am incercat sa-mi recuperez contul de Facebook si ti-am pus numarul tau. Spune-mi codul venit pe telefon", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("Salut! Ti-a ajuns un cod de verificare WhatsApp? Trimite-mi-l rapid ca am blocat aplicatia", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST", "RF_URGENCY"]),
    ("Buna vecina, mi-ai primit din eroare codul OTP pentru parola unica? Da-mi-l si mie te rog!", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("Draga, vreau sa-ti trimit o surpriza de ziua ta pe card, imi dai numarul cardului si codul de verificare?", "ACCOUNT_TAKEOVER", ["RF_DATA_REQUEST", "RF_CODE_REQUEST"]),
    ("Sunt Elena de la birou, am introdus gresit numarul meu la logare si ti-a venit tie codul. Zi-mi cifrele te rog", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("Te rog mult, imi trimiti inapoi codul acela din SMS? E pentru recuperarea contului meu de Instagram", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("Prietena ta aici: am o problema cu telefonul si codul de conectare a ajuns la tine din greseala. Da-mi-l urgent", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST", "RF_URGENCY"]),
    ("Ti-am trimis din greseala un link si un cod de activare pe SMS, nu-l folosi, doar copiaza-l si trimite-mi-l aici", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("Buna! Am nevoie sa imi confirmi codul de autentificare primit de tine acum cateva secunde ca sa intru in cont", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),
    ("A ajuns la telefonul tau un mesaj cu sase cifre de securitate, spune-mi ce cifre sunt repede te rog", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST", "RF_URGENCY"]),
    ("Poti sa-mi dictezi cele sase cifre primite acum? Mi s-a blocat accesul la aplicatia de mesagerie", "ACCOUNT_TAKEOVER", ["RF_CODE_REQUEST"]),

    # --- INVESTMENT (10) ---
    ("Investiti 250 EUR in actiuni si criptomonede cu profit garantat de 25% pe saptamana, recomandat de experti financiari", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Am investit in platforma asta automata si am castigat 8.000 lei intr-o luna! Depui doar 500 lei sa incepi", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Felicitari, contul dvs de trading a ajuns la 14.000 euro profit! Achitati taxa de retragere si deblocare de 500 euro astazi", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Oportunitate crypto pe Telegram: dublam banii in 48 de ore fara niciun risc! Oferta valabila doar azi", "INVESTMENT", ["RF_TOO_GOOD", "RF_CHANNEL_SWITCH", "RF_URGENCY"]),
    ("Randament zilnic garantat prin bursa internationala si actiuni energetice. Va deschidem cont cu depunere minima", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Lucrez in domeniul financiar in Dubai si va pot ajuta sa faceti venit pasiv urias din crypto, vorbim pe Telegram", "INVESTMENT", ["RF_CHANNEL_SWITCH", "RF_TOO_GOOD"]),
    ("Cumparati actiuni Hidroelectrica si Bitcoin cu profit lunar sigur de 30%! Inregistrati-va si depuneti azi", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Expertul nostru in investitii va garanteaza dublarea economiilor in 2 saptamani. Deschideti contul de trading cu 1.000 lei", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Ati acumulat 12.000 EUR profit pe platforma de criptomonede! Pentru transfer platiti comisionul de deblocare", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Platforma de investitii recomandata de specialisti: randamente de 20% pe luna fara risc, depuneti suma initiala", "INVESTMENT", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),

    # --- ROMANCE (11) ---
    ("Buna frumoaso, sunt capitan pe vapor si simt ca esti sufletul meu pereche. Am nevoie de 1.000 euro sa vin in Romania", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Iubirea mea, ti-am trimis un pachet cu cadouri din Londra dar vama l-a oprit si cere taxa de 1.500 lei. Poti plati tu?", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Sunt medic militar in misiune si mi-au blocat salariul. Cumpara-mi niste carduri cadou te implor, doar tu ma poti ajuta", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Draga mea, te iubesc mult! Armata nu imi da drumul in permisie fara taxa de transfer prin Western Union. Pastreaza secretul", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Sufletul meu, ne vom casatori curand! Trimite-mi doar 400 euro pentru biletul de avion, nu spune nimanui", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Sunt inginer pe o platforma petroliera si nu am acces la contul bancar. Dragostea mea, ma ajuti cu un voucher cadou?", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Hello dear, te iubesc si vreau sa ne vedem in Romania! Poti sa achiti taxa vamala pentru valiza mea cu bijuterii?", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Draga mea, sunt blocat in strainatate si mi-au retinut actele. Doar tu esti familia mea, trimite-mi bani prin MoneyGram", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Iubitule, abia astept sa fim impreuna! Am o urgenta cu biletul de zbor si armata cere plata taxei de eliberare", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST"]),
    ("Esti sufletul meu pereche, iubirea mea! Te implor nu povesti nimanui de banii pe care mi-i trimiti pentru calatorie", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Sunt in baza militara si contul e blocat. Cumpara-mi un card preplatit Paysafe de 500 lei ca sa ne revedem, pastreaza secretul", "ROMANCE", ["RF_EMOTIONAL_PRESSURE", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),

    # --- JOB_OFFER (11) ---
    ("Angajam persoane pentru lucru de acasa, 10 minute pe zi: dati like la videoclipuri YouTube si castigati 300 lei zilnic", "JOB_OFFER", ["RF_TOO_GOOD"]),
    ("Job online flexibil: 250 lei pe zi garantat! Scrieti-ne pe WhatsApp sau Telegram pentru instruire", "JOB_OFFER", ["RF_TOO_GOOD", "RF_CHANNEL_SWITCH"]),
    ("Cautam operatori recrutare si recenzii produse. Pentru sarcinile VIP depuneti o garantie de 300 lei, ii primiti dublu", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Oferta de munca part-time de pe telefon: plata in aceeasi zi, bani usor! Achitati taxa de activare cont de lucru", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Agentie de marketing cauta colaboratori pentru abonari canale. Continuam pe Telegram si activam pachetul cu depozit", "JOB_OFFER", ["RF_CHANNEL_SWITCH", "RF_PAYMENT_REQUEST"]),
    ("Recrutam persoane pentru job remote usor: abonati-va la canale si primiti 25 lei pe sarcina. Pentru nivel VIP depuneti 400 lei", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Castigati 500 lei pe zi scriind recenzii de produse de acasa! Trecem pe Telegram sa primiti sarcinile", "JOB_OFFER", ["RF_TOO_GOOD", "RF_CHANNEL_SWITCH"]),
    ("Oportunitate de angajare online fara experienta: 4.000 lei pe saptamana. Platiti taxa de inregistrare a dosarului", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Firma de publicitate ofera salariu zilnic pentru like-uri pe TikTok si Instagram. Activati contul platind garantia", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Lucreaza de acasa 1 ora pe zi cu castiguri garantate! Scrie-ne urgent pe WhatsApp pentru activarea contului", "JOB_OFFER", ["RF_TOO_GOOD", "RF_CHANNEL_SWITCH", "RF_URGENCY"]),
    ("Colaboratori pentru evaluari hotele si restaurante, platim 350 RON pe zi. Trimiteti avansul de activare pe Telegram", "JOB_OFFER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST", "RF_CHANNEL_SWITCH"]),

    # --- PRIZE_LOTTERY (10) ---
    ("Felicitari! Numarul dvs a fost extras castigatorul unui smartphone la tombola aniversara! Raspundeti acum sa revendicati", "PRIZE_LOTTERY", ["RF_TOO_GOOD"]),
    ("Ati fost selectat pentru un sondaj cu premiu garantat: primiti un voucher de 500 lei daca completati azi", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_URGENCY"]),
    ("Marea extragere MegaShop: ati castigat marele premiu in valoare de 5.000 euro! Platiti doar taxa de livrare a premiului", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_IMPERSONATION", "RF_PAYMENT_REQUEST"]),
    ("Loteria internationala va anunta ca sunteti marele castigator! Trimiteti datele personale si copie buletin", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Tombola MegaShop: ati castigat un televizor nou si un cupon de cumparaturi! Sunati sau accesati linkul pentru premiu", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_IMPERSONATION"]),
    ("Extragere speciala de sarbatori: ati fost desemnat castigatorul sumei de 2.000 euro. Confirmati datele cardului", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_DATA_REQUEST"]),
    ("Sondaj de satisfactie client cu castig garantat: completati chestionarul si primiti voucher cadou de 300 lei", "PRIZE_LOTTERY", ["RF_TOO_GOOD"]),
    ("Ati castigat o mostenire si un premiu promotional in numerar! Achitati taxa de procesare pentru ridicare", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),
    ("Felicitari client fidel! Ati fost extras castigator la loteria telefonica. Raspundeti cu DA in 2 ore", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_URGENCY"]),
    ("Promotie incredibila: telefon nou gratuit la extragerea lunii! Platiti doar 10 lei expedierea pe site", "PRIZE_LOTTERY", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST"]),

    # --- OTHER (11) ---
    ("Vasele dumneavoastra de sange sunt infundate si riscati infarct! Comandati tratamentul miraculos natural la pret redus azi", "OTHER", ["RF_THREAT", "RF_TOO_GOOD", "RF_URGENCY"]),
    ("Doctorii va ascund adevarul despre articulatii! Formula unica nanotehnologica vindeca garantat in 5 zile", "OTHER", ["RF_TOO_GOOD", "RF_SECRECY"]),
    ("Campanie medicala subventionata: pastile naturale care topesc instant colesterolul! Luati doua pachete acum cu 1.400 lei", "OTHER", ["RF_TOO_GOOD", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Electrica Furnizare: factura restanta! Daca nu achitati pana la ora 18:00 va deconectam curentul electric", "OTHER", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Am inregistrari video compromitatoare cu dumneavoastra. Transferati 800 euro in bitcoin sau le trimit tuturor contactelor", "OTHER", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_SECRECY"]),
    ("Furnizorul de gaze va avertizeaza: aveti o datorie neachitata, platiti urgent pe link sau oprim alimentarea", "OTHER", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Supliment revolutionar pentru tensiune si inima: vindecare 100% naturala, profitati de oferta doar astazi", "OTHER", ["RF_TOO_GOOD", "RF_URGENCY"]),
    ("Sunt consultant medical: daca nu comandati acum cura de curatare a vaselor riscati paralizie sau atac cerebral", "OTHER", ["RF_THREAT", "RF_URGENCY"]),
    ("Contul dvs de email a fost spart si am toate parolele. Platiti rascumpararea in criptomonede in 24 de ore", "OTHER", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),
    ("Abonamentul de cablu va fi suspendat imediat pentru neplata! Introduceti cardul aici ca sa nu ramaneti fara servicii", "OTHER", ["RF_THREAT", "RF_DATA_REQUEST", "RF_URGENCY"]),
    ("Compania de energie va sista furnizarea azi pentru debit restant daca nu achitati factura online pe linkul de plata", "OTHER", ["RF_THREAT", "RF_PAYMENT_REQUEST", "RF_URGENCY"]),

    # --- NONE (22 HARD-NEGATIVE SAFE MESSAGES WITH DANGER WORDS USED SAFELY!) ---
    ("Banca Dunarea: codul dvs de autorizare este 739104. Nu comunicati niciodata acest cod niciunei persoane, nici angajatilor bancii", "NONE", []),
    ("Banca Dunarea: a fost inregistrata o plata cu cardul de 210 lei la MegaShop. Daca nu ati fost dvs, sunati la 0800 100 200", "NONE", []),
    ("Banca Dunarea: a fost detectata o incercare de plata. Raspundeti cu DA daca ati fost dvs sau NU pentru blocarea cardului. Nu va cerem PIN", "NONE", []),
    ("CurierExpres: coletul AWB 991204 a ajuns in depozitul local si se livreaza maine. Urmarire pe curierexpres.ro/awb", "NONE", []),
    ("CurierExpres: curierul este pe drum. Ramburs: 0 lei. Pentru detalii intrati pe curierexpres.ro", "NONE", []),
    ("MegaShop: comanda dvs a fost expediata si va ajunge in 2 zile lucratoare. Multumim ca ati ales megashop.ro", "NONE", []),
    ("MegaShop: un voucher de fidelitate a fost adaugat automat in contul dvs de pe megashop.ro, nu trebuie sa faceti nimic", "NONE", []),
    ("Clinica stomatologica Dental: va reamintim programarea de maine la ora 10:30. Daca doriti reprogramare, sunati la receptie", "NONE", []),
    ("Administratia blocului: plata intretinerii pe luna noiembrie este 280 lei si se face la casierie miercuri intre 17:00 si 19:00", "NONE", []),
    ("Banca Transilvania: va invitam sa treceti pe la orice sucursala cu buletinul pentru actualizarea datelor personale conform legii", "NONE", []),
    ("Buna puiule, ai ajuns acasa? Ne vedem duminica la masa, fac sarmale", "NONE", []),
    ("Salut! Poti sa-mi aduci cartea maine la facultate? Mergem apoi la o cafea", "NONE", []),
    ("Buna ziua, am vazut anuntul dvs pentru bicicleta. Se poate vedea in weekend in centru? Multumesc", "NONE", []),
    ("Buna ziua, am selectat CV-ul dvs pentru interviul de angajare. Va asteptam joi la sediul firmei, fara nicio taxa", "NONE", []),
    ("Abonamentul dvs lunar de telefonie a fost emis. Factura o puteti vedea in aplicatia oficiala sau plati la ghiseu", "NONE", []),
    ("Mami, sunt Andrei. Am facut o prajitura dupa reteta ta si a iesit super! Te sun diseara pe video", "NONE", []),
    ("CurierExpres: nu va vom cere niciodata datele cardului prin SMS pentru plata unui colet", "NONE", []),
    ("Ai grija mama cu escrocheriile de la televizor! Sa nu instalezi programe de control si sa nu dai codul din SMS nimanui", "NONE", []),
    ("Buletin informativ de securitate: banca nu solicita niciodata transferuri in conturi protejate sau datele de pe card prin email", "NONE", []),
    ("Codul unic de autentificare expira in 5 minute. Pastrati acest cod strict confidential si nu il trimiteti altor persoane", "NONE", []),
    ("Clinica medicala va anunta ca buletinul de analize pentru tensiune si lipide este disponibil la receptie de maine", "NONE", []),
    ("Notificare cont curent: ati incasat suma de 2.400 lei reprezentand drepturi banesti. Sold disponibil in aplicatia oficiala", "NONE", []),
]

FLAG_NAMES = [
    "RF_CODE_REQUEST",
    "RF_REMOTE_ACCESS",
    "RF_DATA_REQUEST",
    "RF_PAYMENT_REQUEST",
    "RF_NEW_NUMBER",
    "RF_SECRECY",
    "RF_TOO_GOOD",
    "RF_IMPERSONATION",
    "RF_URGENCY",
    "RF_THREAT",
    "RF_EMOTIONAL_PRESSURE",
    "RF_CHANNEL_SWITCH",
]


def _augment_typo_noise(text: str, rng: random.Random) -> str:
    """Generates realistic SMS typo / vowel-drop / character-swap perturbations."""
    words = text.split(" ")
    out = []
    for w in words:
        if len(w) >= 5 and w.isalpha() and rng.random() < 0.35:
            # Drop one internal vowel or swap two adjacent letters
            if rng.random() < 0.55:
                v_idxs = [i for i in range(1, len(w) - 1) if w[i] in "aeiou"]
                if v_idxs:
                    idx = rng.choice(v_idxs)
                    w = w[:idx] + w[idx + 1:]
            else:
                i = rng.randint(1, len(w) - 3)
                w = w[:i] + w[i + 1] + w[i] + w[i + 2:]
        out.append(w)
    return " ".join(out)


def _make_sparse_features() -> FeatureUnion:
    """Word (1-2 n-gram) + Character Boundary (3-5 n-gram) TF-IDF in float32."""
    return FeatureUnion([
        ("word", TfidfVectorizer(ngram_range=(1, 2), analyzer="word", sublinear_tf=True, min_df=1, max_features=6000, dtype=np.float32)),
        ("char", TfidfVectorizer(ngram_range=(3, 5), analyzer="char_wb", sublinear_tf=True, min_df=2, max_features=9000, dtype=np.float32)),
    ])


def _make_dense_mlp(hidden=(96, 48), n_components: int = 80) -> Pipeline:
    """Compact Neural MLP head operating on L2-normalized dense SVD semantic embeddings."""
    return Pipeline([
        ("tfidf_sem", TfidfVectorizer(ngram_range=(3, 5), analyzer="char_wb", sublinear_tf=True, min_df=2, max_features=6000, dtype=np.float32)),
        ("svd", TruncatedSVD(n_components=n_components, random_state=42)),
        ("norm", Normalizer(copy=False)),
        ("mlp", MLPClassifier(hidden_layer_sizes=hidden, alpha=0.05, max_iter=500, early_stopping=True, random_state=42)),
    ])


def train_and_save_model():
    print(f"Preparing SOTA v3 Tier-6 Hybrid Neural-SVD + Linear Ensemble ({len(TRAINING_CORPUS)} clean base samples)...")
    clean_texts = [deobfuscate_for_detection(item[0]) for item in TRAINING_CORPUS]
    clean_labels = [item[1] for item in TRAINING_CORPUS]

    # 1. Evaluate 13-class Scam Type Ensemble with 5-Fold Stratified CV strictly on CLEAN corpus
    def build_type_pipeline() -> VotingClassifier:
        lr_branch = Pipeline([
            ("sparse", _make_sparse_features()),
            ("lr", LogisticRegression(C=8.0, max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        mlp_branch = _make_dense_mlp(hidden=(96, 48), n_components=80)
        return VotingClassifier(
            estimators=[("lr", lr_branch), ("mlp_svd", mlp_branch)],
            voting="soft",
            weights=[2.5, 1.0],
        )

    skf = StratifiedKFold(n_splits=5, shuffle=True, random_state=42)
    cv_scores = cross_val_score(build_type_pipeline(), clean_texts, clean_labels, cv=skf, scoring="accuracy")
    print(f"5-Fold Stratified CV Accuracy (13-class Neural-SVD + Linear Ensemble): {cv_scores.mean() * 100:.2f}% (+/- {cv_scores.std() * 100:.2f}%)")

    # 2. Data Augmentation (Typos + Hard Negatives) ONLY for final model fitting (never leaked into CV!)
    rng = random.Random(42)
    aug_texts = list(clean_texts)
    aug_labels = list(clean_labels)
    aug_flags_list = [item[2] for item in TRAINING_CORPUS]

    for txt, lbl, flgs in zip(clean_texts, clean_labels, [item[2] for item in TRAINING_CORPUS]):
        aug_texts.append(_augment_typo_noise(txt, rng))
        aug_labels.append(lbl)
        aug_flags_list.append(flgs)

    type_pipeline = build_type_pipeline()
    type_pipeline.fit(aug_texts, aug_labels)
    print(f"Type Ensemble Clean-Corpus Fit Accuracy: {type_pipeline.score(clean_texts, clean_labels) * 100:.2f}%")

    # 3. Multi-Label Red-Flag SOTA Head (trained on clean + typo-augmented + hard negatives)
    Y_flags = np.zeros((len(aug_texts), len(FLAG_NAMES)), dtype=int)
    flag_idx = {name: i for i, name in enumerate(FLAG_NAMES)}
    for row_i, row_flags in enumerate(aug_flags_list):
        for f in row_flags:
            if f in flag_idx:
                Y_flags[row_i, flag_idx[f]] = 1

    flag_pipeline = Pipeline([
        ("features", _make_sparse_features()),
        ("clf", OneVsRestClassifier(LogisticRegression(C=5.0, max_iter=1000, class_weight="balanced", random_state=42))),
    ])
    flag_pipeline.fit(aug_texts, Y_flags)

    # 4. Binary Malicious Intent vs Safe/Hard-Negative Calibrator (`risk_pipeline`)
    y_risk_clean = [0 if lbl == "NONE" else 1 for lbl in clean_labels]
    y_risk_aug = [0 if lbl == "NONE" else 1 for lbl in aug_labels]
    def build_risk_pipeline() -> VotingClassifier:
        lr_risk = Pipeline([
            ("sparse", _make_sparse_features()),
            ("lr", LogisticRegression(C=6.0, max_iter=1000, class_weight="balanced", random_state=42)),
        ])
        mlp_risk = _make_dense_mlp(hidden=(64, 32), n_components=64)
        return VotingClassifier(
            estimators=[("lr", lr_risk), ("mlp_svd", mlp_risk)],
            voting="soft",
            weights=[1.5, 1.0],
        )

    risk_cv = cross_val_score(build_risk_pipeline(), clean_texts, y_risk_clean, cv=skf, scoring="roc_auc")
    print(f"5-Fold Stratified CV ROC-AUC (Malicious vs Hard-Negative Safe Intent): {risk_cv.mean():.4f}")
    risk_pipeline = build_risk_pipeline()
    risk_pipeline.fit(aug_texts, y_risk_aug)

    bundle = {
        "version": 3,
        "type_pipeline": type_pipeline,
        "flag_pipeline": flag_pipeline,
        "risk_pipeline": risk_pipeline,
        "flag_names": FLAG_NAMES,
        "cv_type_accuracy": float(cv_scores.mean()),
        "cv_risk_roc_auc": float(risk_cv.mean()),
    }

    save_path = os.path.join(os.path.dirname(__file__), "trained_model.joblib")
    joblib.dump(bundle, save_path, compress=3)
    size_kb = os.path.getsize(save_path) / 1024
    print(f"SOTA Tier-6 v3 bundle saved to: {save_path} ({size_kb:.1f} KB)")
    return bundle


if __name__ == "__main__":
    train_and_save_model()
