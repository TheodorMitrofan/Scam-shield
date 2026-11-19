"""Renders the fraud report as a formal complaint ("Plângere penală", art. 289 C.proc.pen.).

Plain black-on-white, serif font, no scores or app jargon: addressee, the complainant's identity, the facts,
the evidence, date and signature. The numbered conversation goes into an annex. Empty personal fields are
printed as dotted lines so the document can also be printed and completed by hand.
"""

import re
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.schemas import RedFlag
from app.schemas.report import FraudReportDraft, PersonalData

from .indicators import defang_text
from .labels import CHANNEL_FORMAL, CHANNEL_LABEL, FLAG_REQUEST, SCAM_TYPE_PRETEXT

FONTS = Path(__file__).parent / "fonts"
DOTS = "........................"
MAX_CELL_CHARS = 1500  # a table row must fit on one page; full text stays in raport.json
LINE = 5.6
# The serif font has no emoji glyphs; keep the transcript faithful with a visible placeholder.
_EMOJI = re.compile("[\U0001F000-\U0001FAFF\u2600-\u27BF\uFE0F\u200D]+")


def _plain(text: str) -> str:
    return _EMOJI.sub("[emoji]", text)


class _Doc(FPDF):
    def __init__(self) -> None:
        super().__init__(format="A4")
        self.add_font("Serif", "", str(FONTS / "DejaVuSerif.ttf"))
        self.add_font("Serif", "B", str(FONTS / "DejaVuSerif-Bold.ttf"))
        self.set_margins(25, 22, 22)
        self.set_auto_page_break(True, margin=20)
        self.alias_nb_pages()
        self.set_text_color(0, 0, 0)
        self.set_draw_color(0, 0, 0)

    def footer(self) -> None:
        self.set_y(-14)
        self.set_font("Serif", "", 7.5)
        self.set_text_color(110, 110, 110)
        self.cell(0, 5, "Document generat cu Scam Shield (demonstrație hackathon).", align="L")
        self.cell(0, 5, f"{self.page_no()}/{{nb}}", align="R")
        self.set_text_color(0, 0, 0)

    def p(self, text: str, size: float = 11, bold: bool = False, align: str = "L", indent: bool = False) -> None:
        self.set_font("Serif", "B" if bold else "", size)
        self.multi_cell(0, LINE, ("        " if indent else "") + text, align=align, new_x="LMARGIN", new_y="NEXT")
        if indent:
            self.ln(1.2)

    def item(self, marker: str, text: str) -> None:
        """List item with a hanging indent, so wrapped lines align under the text."""
        self.set_font("Serif", "", 11)
        self.set_x(self.l_margin + 8)
        self.cell(7, LINE, marker)
        self.multi_cell(0, LINE, text, align="L", new_x="LMARGIN", new_y="NEXT")

    def section(self, text: str) -> None:
        self.ln(3)
        self.p(text, bold=True, align="L")
        self.ln(1)


def _f(v) -> str:
    return str(v).strip() if v not in (None, "") else DOTS


def _money(x: float) -> str:
    return f"{x:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".").removesuffix(",00")


def _contact_phrase(draft: FraudReportDraft) -> str:
    """'de pe numărul de telefon X' / 'de pe adresa de e-mail X' / 'de pe contul X'."""
    inc = draft.incident
    addr = (inc.sender.address or "").strip()
    if not addr:
        return "de pe un număr sau o adresă necunoscută"
    shown = defang_text(addr)
    kind = {i.value: i.kind for i in inc.indicators if i.message_n is None}.get(addr)
    if kind == "phone":
        return f"de pe numărul de telefon {shown}"
    if kind == "email":
        return f"de pe adresa de e-mail {shown}"
    return f"de la expeditorul „{shown}”"


def _requests(draft: FraudReportDraft) -> list[str]:
    """What the author concretely asked for, from the detected request flags and indicators."""
    inc = draft.incident
    flags = {f.code for f in inc.red_flags}
    amounts = [i.display for i in inc.indicators if i.kind == "amount"]
    ibans = [i.display for i in inc.indicators if i.kind == "iban"]
    out = []
    for flag, text in FLAG_REQUEST.items():
        if flag not in flags:
            continue
        if flag == RedFlag.PAYMENT_REQUEST:
            if amounts:
                text += f" în cuantum de {amounts[0]}"
            if ibans:
                text += f", în contul {ibans[0]}"
        out.append(text)
    urls = [i.display for i in inc.indicators if i.kind == "url"]
    if urls:
        out.append("accesarea adresei de internet " + ", ".join(urls))
    return out


def _signature(doc: _Doc, draft: FraudReportDraft, signer: str) -> None:
    block_h = 10 + 4 * LINE  # gap + "Semnătura," + name + blank line + dotted line
    if doc.will_page_break(block_h):
        doc.add_page()
    doc.ln(10)
    y = doc.get_y()
    box = 75
    doc.set_font("Serif", "", 11)
    doc.cell(80, LINE, f"Data: {draft.generated_at.strftime('%d.%m.%Y')}")
    x = doc.w - doc.r_margin - box
    doc.set_xy(x, y)
    doc.cell(box, LINE, "Semnătura,", align="C")
    # the name always fits on one line: shrink the font for very long names
    size = 11.0
    while size > 7 and doc.get_string_width(signer) > box:
        size -= 0.5
        doc.set_font("Serif", "", size)
    if doc.get_string_width(signer) > box:
        while signer and doc.get_string_width(signer + "…") > box:
            signer = signer[:-1]
        signer += "…"
    doc.set_xy(x, y + LINE)
    doc.cell(box, LINE, signer, align="C")
    doc.set_font("Serif", "", 11)
    doc.set_xy(x, y + 3 * LINE)
    doc.cell(box, LINE, "..............................", align="C", new_x="LMARGIN", new_y="NEXT")


def render_pdf(draft: FraudReportDraft, p: PersonalData) -> bytes:
    inc = draft.incident
    doc = _Doc()
    doc.add_page()

    # Addressee ---------------------------------------------------------------------------------
    doc.p("Către:", bold=True, align="L")
    doc.p(f"Inspectoratul de Poliție Județean {DOTS}", align="L")
    doc.p(f"Secția de Poliție nr. {DOTS}", align="L")
    doc.p("Directoratul Național de Securitate Cibernetică – DNSC", align="L")
    doc.ln(5)
    doc.p("Domnule Comandant,", align="L")
    doc.ln(3)

    # Complainant -------------------------------------------------------------------------------
    name = f"{p.last_name or ''} {p.first_name or ''}".strip() or DOTS
    series, number = DOTS, DOTS
    if p.id_series_number:
        parts = p.id_series_number.replace(",", " ").split()
        series, number = (parts[0], " ".join(parts[1:])) if len(parts) > 1 else (DOTS, parts[0])
    doc.p(
        f"Subsemnatul/a {name}, cetățean român, domiciliat/ă în {_f(p.address)}, identificat/ă cu CI seria "
        f"{series} nr. {number}, CNP {_f(p.cnp)}, telefon {_f(p.phone)}, e-mail {_f(p.email)}, "
        "în temeiul art. 289 din Codul de procedură penală, formulez prezenta",
        indent=True,
    )
    doc.ln(4)
    doc.p("PLÂNGERE PENALĂ", size=13, bold=True, align="C")
    doc.p("privind o tentativă de înșelăciune prin mijloace electronice", align="C")
    doc.ln(4)
    against = "împotriva unor persoane necunoscute (autor necunoscut – A.N.)"
    if inc.sender.name:
        against += f", care au folosit numele „{defang_text(inc.sender.name)}”"
    doc.p(f"{against}, solicitând efectuarea de cercetări pentru identificarea autorilor și tragerea "
          "acestora la răspundere penală.", indent=True)

    # I. Facts ----------------------------------------------------------------------------------
    doc.section("I. Starea de fapt")
    when = p.incident_date.strftime("%d.%m.%Y") if p.incident_date else DOTS
    at = p.incident_time.strftime("%H:%M") if p.incident_time else DOTS
    doc.p(f"În data de {when}, în jurul orei {at}, am fost contactat/ă prin intermediul "
          f"{CHANNEL_FORMAL[inc.channel]} {_contact_phrase(draft)}.", indent=True)
    pretext = SCAM_TYPE_PRETEXT.get(inc.scam_type, "")
    if pretext:
        doc.p(f"Autorul {pretext}.", indent=True)
    reqs = _requests(draft)
    if reqs:
        doc.p("Concret, autorul mi-a solicitat:", indent=True)
        for r in reqs:
            doc.item("–", f"{r};")
        doc.ln(1.2)
    if len(inc.timeline) > 1:
        doc.p(f"Conversația a cuprins {len(inc.timeline)} mesaje, redate integral în Anexa 1.", indent=True)

    if p.lost_money:
        amount = _money(p.amount_lost) if p.amount_lost is not None else DOTS
        bank = f", prin intermediul băncii {p.bank}" if p.bank else ""
        doc.p(f"Precizez că, în urma acestor demersuri, am suferit un prejudiciu în cuantum de {amount} lei{bank}, "
              "motiv pentru care înțeleg să mă constitui parte civilă în procesul penal.", indent=True)
    else:
        doc.p("Precizez că am sesizat caracterul fraudulos al demersului și nu am dat curs solicitărilor "
              "(nu am furnizat date confidențiale și nu am efectuat plăți), fapta rămânând în faza de tentativă.",
              indent=True)
    if p.additional_details:
        doc.p(_plain(p.additional_details[:4000]), indent=True)

    # II. Evidence ------------------------------------------------------------------------------
    doc.section("II. Probe și mijloace materiale de probă")
    doc.p("În susținerea celor declarate, anexez prezentei următoarele:", indent=True)
    evidence = ["Anexa 1 – transcrierea integrală a conversației, cu mesajele numerotate"]
    sender = [i.display for i in inc.indicators if i.message_n is None]
    used = [i.display for i in inc.indicators if i.message_n is not None and i.kind in ("url", "email", "phone", "iban")]
    if sender:
        evidence.append("datele de identificare ale expeditorului: " + ", ".join(sender))
    if used:
        evidence.append("adresele și numerele folosite în mesaje: " + ", ".join(used)
                        + " (redate cu „[.]” pentru a nu fi accesate din greșeală)")
    evidence.append("capturi de ecran ale mesajelor, pe care le pot pune la dispoziție la cerere")
    if p.lost_money:
        evidence.append("extras de cont și dovada tranzacției")
    for k, e in enumerate(evidence, 1):
        doc.item(f"{k}.", f"{e};")

    # Date + signature (kept together: never split across pages) -------------------------------
    _signature(doc, draft, name if name != DOTS else "")

    # Annex 1: conversation ----------------------------------------------------------------------
    doc.add_page()
    doc.p("Anexa 1", bold=True, align="R")
    doc.ln(2)
    doc.p("Transcrierea conversației", size=12, bold=True, align="C")
    doc.ln(2)
    who = defang_text(inc.sender.name or inc.sender.address or "") or "necunoscut"
    doc.p(f"Canal: {CHANNEL_LABEL[inc.channel]}. Expeditor: {who}. "
          "Mesajele sunt redate în ordinea primirii; „Eu” indică răspunsurile mele.", size=10, align="L")
    doc.ln(3)
    doc.set_font("Serif", "", 10)
    with doc.table(col_widths=(12, 28, 123), headings_style=FontFace(emphasis="BOLD"), line_height=5.2,
                   padding=1.6, text_align=("CENTER", "LEFT", "LEFT")) as t:
        r = t.row()
        for h in ("Nr.", "Autor", "Mesaj"):
            r.cell(h)
        for e in inc.timeline:
            text = e.text if len(e.text) <= MAX_CELL_CHARS else (
                e.text[:MAX_CELL_CHARS] + f"… [mesaj trunchiat: {len(e.text)} caractere]"
            )
            r = t.row()
            r.cell(str(e.n))
            r.cell("Eu" if e.author == "reader" else "Expeditorul")
            r.cell(_plain(text) or "(mesaj gol)")
    return bytes(doc.output())
