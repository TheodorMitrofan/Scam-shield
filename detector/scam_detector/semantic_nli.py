import os
import re
import joblib
from typing import Dict, List, Optional
from sklearn.feature_extraction.text import TfidfVectorizer
from sklearn.metrics.pairwise import cosine_similarity
from .text_utils import deobfuscate_for_detection

SEMANTIC_ANCHORS: Dict[str, List[str]] = {
    "RF_CODE_REQUEST": [
        "trimite-mi codul primit prin sms",
        "mi-l poti trimite inapoi codul",
        "cititi-mi codul de confirmare din mesaj",
        "spuneti-mi ce cifre apar in mesajul de securitate",
        "a ajuns la tine un mesaj cu sase cifre de securitate",
        "am introdus gresit numarul si a venit la tine codul",
    ],
    "RF_REMOTE_ACCESS": [
        "instalati programul de control la distanta",
        "descarcati aplicatia anydesk sau teamviewer",
        "descarcati aplicatia de partajare a ecranului sa va vad desktopul",
        "oferiti acces la distanta pe calculator",
    ],
    "RF_DATA_REQUEST": [
        "completati datele cardului bancar si cvv",
        "introduceti cnp-ul si seria de buletin ci",
        "validati cardul cu soldul disponibil pe pagina de confirmare",
        "datele de autentificare si parola contului",
        "intrati in contul de banca sa verificam tranzactiile",
    ],
    "RF_PAYMENT_REQUEST": [
        "achitati taxa de reprogramare a coletului",
        "fa-mi un transfer de bani urgent",
        "platiti suma pentru eliberarea coletului din vama",
        "mutati toate economiile intr-un cont tampon de siguranta",
        "depuneti garantia sau avansul de activare",
        "ajuta-ma cu un card preplatit paysafe sau cadou",
    ],
    "RF_NEW_NUMBER": [
        "mi s-a stricat telefonul acesta este numarul meu nou",
        "scriu de pe cartela unui coleg mi s-a inchis telefonul vechi",
        "buna mami salveaza noul numar",
    ],
    "RF_SECRECY": [
        "te rog nu-i spune lui tata",
        "pastreaza secretul sa ramana intre noi",
        "nu mai spune nimanui despre aceasta conversatie",
        "nu anuntati banca sau politia ancheta e secreta",
    ],
    "RF_TOO_GOOD": [
        "ati fost ales castigatorul unui telefon la tombola",
        "ofera sprijin financiar sau voucher garantat",
        "pensia dumneavoastra va creste cu o suma de bani",
        "profit garantat sau randament constant lunar fara risc",
        "platim zilnic pentru evaluari sau lucru de acasa",
        "formula unica naturala vindeca instant garantat",
    ],
    "RF_URGENCY": [
        "trebuie sa actionati in termen de 24 de ore",
        "platiti azi pana diseara e urgent",
        "linkul expira intr-o ora grabiti-va",
    ],
    "RF_THREAT": [
        "cardul dumneavoastra a fost blocat temporar",
        "calculatorul dumneavoastra este infectat cu virusi",
        "aveti poprire pe venituri evitati sechestrul sau dosarul penal",
        "va sista furnizarea energiei pentru debit restant",
        "s-a incercat o frauda pe cont economiile sunt in pericol",
    ],
    "RF_EMOTIONAL_PRESSURE": [
        "am facut un accident grav si sunt la spital",
        "sunt disperat te implor din suflet ajuta-ma",
        "este retinut la politie si risca inchisoarea",
        "doar tu ma poti ajuta suflet drag",
    ],
    "RF_CHANNEL_SWITCH": [
        "hai sa continuam conversatia pe telegram",
        "scrie-mi urgent pe whatsapp sau telegram",
    ],
}

# Structural safety / educational / official-notice patterns that must never be boosted into false alarms
_SAFETY_GUARD_RX = re.compile(
    r"\b(?:nu\s+(?:va|ne)\s+(?:vom|va|cerem|solicitam|solicita)\s+(?:niciodata\s+)?(?:cere|solicita|cer)|"
    r"banca\s+nu\s+(?:solicita|va\s+cere)\s+niciodata|"
    r"ai\s+grija\s+sa\s+nu\b|"
    r"sa\s+nu\s+(?:instalezi|instalati|descarci|descarcati|dai|dati|trimiti|trimiteti|comunici|comunicati)\b|"
    r"nu\s+(?:il\s+|o\s+)?(?:comunicati|comunica|trimiteti|trimite|dati|da|spuneti|spune|introduceti|divulgati)\b[^.!?]{0,45}\b(?:nimanui|niciodata|altor\s+persoane|cod|datele)|"
    r"la\s+(?:orice\s+sucursala|ghiseul|casierie|receptie)|"
    r"ramburs\s*:\s*0\s*lei|"
    r"nu\s+am\s+nevoie\s+de\s+bani|"
    r"depozitul\s+local)\b",
    re.IGNORECASE,
)


class SemanticNLIEnsemble:
    """
    SOTA Local Multi-Signal Semantic & Neural Intent Scorer (100% offline).
    Combines:
      1. De-obfuscated Character (3-5 gram) + Word TF-IDF cosine similarity vs paraphrased anchors.
      2. Trained Multi-Label Red-Flag LogisticRegression head (`flag_pipeline`).
      3. Trained Neural+Linear Malicious-Intent vs Safe-Notice gate (`risk_pipeline`).
    """

    def __init__(self, model_bundle: Optional[Dict] = None):
        self._anchor_labels: List[str] = []
        anchor_texts: List[str] = []
        for flag, phrases in SEMANTIC_ANCHORS.items():
            for p in phrases:
                self._anchor_labels.append(flag)
                anchor_texts.append(deobfuscate_for_detection(p))

        self._char_vec = TfidfVectorizer(analyzer="char_wb", ngram_range=(3, 5), sublinear_tf=True)
        self._word_vec = TfidfVectorizer(analyzer="word", ngram_range=(1, 2), sublinear_tf=True)
        self._anchor_char_mat = self._char_vec.fit_transform(anchor_texts)
        self._anchor_word_mat = self._word_vec.fit_transform(anchor_texts)

        self._ml_flag_pipeline = None
        self._ml_risk_pipeline = None
        self._ml_flag_names: List[str] = []

        loaded = model_bundle
        if loaded is None:
            model_path = os.path.join(os.path.dirname(__file__), "trained_model.joblib")
            if os.path.exists(model_path):
                try:
                    loaded = joblib.load(model_path)
                except Exception:
                    loaded = None

        if isinstance(loaded, dict) and loaded.get("version", 1) >= 2:
            self._ml_flag_pipeline = loaded.get("flag_pipeline")
            self._ml_risk_pipeline = loaded.get("risk_pipeline")
            self._ml_flag_names = loaded.get("flag_names", [])

    def is_safety_educational(self, text: str) -> bool:
        norm = deobfuscate_for_detection(text)
        return bool(_SAFETY_GUARD_RX.search(norm))

    def evaluate_semantic_resonance(self, text: str) -> Dict[str, float]:
        norm = deobfuscate_for_detection(text)
        if not norm or _SAFETY_GUARD_RX.search(norm):
            return {}

        q_char = self._char_vec.transform([norm])
        q_word = self._word_vec.transform([norm])
        sim_char = cosine_similarity(q_char, self._anchor_char_mat)[0]
        sim_word = cosine_similarity(q_word, self._anchor_word_mat)[0]
        combined = 0.55 * sim_char + 0.45 * sim_word

        scores: Dict[str, float] = {}
        for idx, flag in enumerate(self._anchor_labels):
            val = float(combined[idx])
            if val > scores.get(flag, 0.0):
                scores[flag] = val
        return scores

    def predict_ml_flag_probs(self, text: str) -> Dict[str, float]:
        norm = deobfuscate_for_detection(text)
        if not norm or self._ml_flag_pipeline is None or _SAFETY_GUARD_RX.search(norm):
            return {}
        try:
            probs = self._ml_flag_pipeline.predict_proba([norm])[0]
            return {flag: float(prob) for flag, prob in zip(self._ml_flag_names, probs)}
        except Exception:
            return {}

    def predict_risk_intent_prob(self, text: str) -> float:
        norm = deobfuscate_for_detection(text)
        if not norm or self._ml_risk_pipeline is None:
            return 0.5
        if _SAFETY_GUARD_RX.search(norm):
            return 0.0
        try:
            return float(self._ml_risk_pipeline.predict_proba([norm])[0][1])
        except Exception:
            return 0.5
