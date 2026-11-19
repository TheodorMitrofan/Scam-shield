"""Renders the fraud report as a formal "Sesizare" PDF (fpdf2 + bundled DejaVu font for ș/ț/ă/î/â).

Empty personal fields are printed as dotted lines so the document can also be printed and filled by hand.
"""

from datetime import UTC, datetime
from pathlib import Path

from fpdf import FPDF
from fpdf.fonts import FontFace

from app.schemas.report import FraudReportDraft, PersonalData

from .indicators import defang_text

FONTS = Path(__file__).parent / "fonts"
BLANK = "................................"
MAX_CELL_CHARS = 1500  # a table row must fit on one page; full text stays in raport.json
_KIND = {"url": "Adresă de internet", "email": "Adresă de e-mail", "phone": "Număr de telefon",
         "iban": "Cont bancar (IBAN)", "amount": "Sumă menționată"}

INK = (25, 30, 40)
MUTED = (95, 105, 120)
RED = (183, 28, 28)
RED_BG = (253, 236, 234)
GREY_BG = (242, 244, 247)


class _Doc(FPDF):
    def __init__(self, report_id: str):
        super().__init__(format="A4")
        self.report_id = report_id
        self.add_font("DejaVu", "", str(FONTS / "DejaVuSans.ttf"))
        self.add_font("DejaVu", "B", str(FONTS / "DejaVuSans-Bold.ttf"))
        self.set_margins(18, 16, 18)
        self.set_auto_page_break(True, margin=18)
        self.alias_nb_pages()

    def header(self):
        self.set_fill_color(*RED_BG)
        self.set_text_color(*RED)
        self.set_font("DejaVu", "B", 8)
        self.cell(0, 6, "DOCUMENT DEMO — generat de Scam Shield (hackathon). NU a fost transmis autorităților.",
                  align="C", fill=True, new_x="LMARGIN", new_y="NEXT")
        self.ln(3)
        self.set_text_color(*INK)

    def footer(self):
        self.set_y(-12)
        self.set_font("DejaVu", "", 7.5)
        self.set_text_color(*MUTED)
        self.cell(0, 5, f"Raport nr. {self.report_id}", align="L")
        self.cell(0, 5, f"Pagina {self.page_no()}/{{nb}}", align="R")

    # helpers -----------------------------------------------------------------------------------
    def h2(self, text: str):
        self.ln(3)
        self.set_font("DejaVu", "B", 11)
        self.set_text_color(*INK)
        self.cell(0, 7, text.upper(), new_x="LMARGIN", new_y="NEXT")
        self.set_draw_color(*RED)
        self.set_line_width(0.5)
        self.line(self.l_margin, self.get_y(), self.l_margin + 28, self.get_y())
        self.ln(2.5)
        # reset so tables / paragraphs after a heading start regular, with neutral borders
        self.set_draw_color(205, 210, 218)
        self.set_line_width(0.2)
        self.set_font("DejaVu", "", 10)

    def para(self, text: str, size: float = 10, color=INK, bold: bool = False):
        self.set_font("DejaVu", "B" if bold else "", size)
        self.set_text_color(*color)
        self.multi_cell(0, 5.4, text, new_x="LMARGIN", new_y="NEXT")


def _f(v) -> str:
    return str(v).strip() if v not in (None, "") else BLANK


def render_pdf(draft: FraudReportDraft, p: PersonalData) -> bytes:
    inc = draft.incident
    doc = _Doc(str(draft.report_id))
    doc.add_page()

    # Addressee + title ---------------------------------------------------------------------------
    doc.set_font("DejaVu", "", 9.5)
    doc.set_text_color(*MUTED)
    doc.multi_cell(0, 5, "Către: Poliția Română — structura de combatere a criminalității informatice\n"
                         "În atenția: Directoratul Național de Securitate Cibernetică (DNSC)",
                   new_x="LMARGIN", new_y="NEXT")
    doc.ln(4)
    doc.set_font("DejaVu", "B", 17)
    doc.set_text_color(*INK)
    doc.cell(0, 9, "SESIZARE", align="C", new_x="LMARGIN", new_y="NEXT")
    doc.set_font("DejaVu", "", 10.5)
    doc.cell(0, 6, "privind o tentativă de înșelăciune prin mijloace electronice", align="C",
             new_x="LMARGIN", new_y="NEXT")
    doc.ln(5)

    # Identity paragraph --------------------------------------------------------------------------
    name = f"{p.last_name or ''} {p.first_name or ''}".strip() or BLANK
    doc.para(
        f"Subsemnatul/Subsemnata {name}, CNP {_f(p.cnp)}, posesor/posesoare al/a actului de identitate "
        f"{_f(p.id_series_number)}, domiciliat(ă) în {_f(p.address)}, telefon {_f(p.phone)}, "
        f"e-mail {_f(p.email)}, formulez prezenta sesizare cu privire la următoarea situație:"
    )

    # Facts ---------------------------------------------------------------------------------------
    doc.h2("1. Descrierea faptei")
    when = p.incident_date.strftime("%d.%m.%Y") if p.incident_date else BLANK
    with doc.table(col_widths=(58, 116), first_row_as_headings=False, line_height=6, padding=(0.6, 0),
                   borders_layout="NONE", text_align="LEFT") as t:
        for k, v in (("Data incidentului", when), ("Canal de comunicare", inc.channel_label),
                     ("Tipul tentativei", inc.scam_type_label),
                     ("Nivel de risc (Scam Shield)", f"{inc.risk_score}/100 — {inc.verdict.value}")):
            row = t.row()
            row.cell(k, style=FontFace(color=MUTED))
            row.cell(v, style=FontFace(emphasis="BOLD"))
    doc.ln(2)
    doc.para(inc.summary_ro)

    # Suspect -------------------------------------------------------------------------------------
    doc.h2("2. Date despre expeditorul suspect")
    with doc.table(col_widths=(58, 116), first_row_as_headings=False, line_height=6, padding=(0.6, 0),
                   borders_layout="NONE", text_align="LEFT") as t:
        for k, v in (("Nume afișat", defang_text(inc.sender.name or "") or "—"),
                     ("Număr / adresă", defang_text(inc.sender.address or "") or "—"),
                     ("Salvat în agendă", "da" if inc.sender.known_contact else "nu")):
            row = t.row()
            row.cell(k, style=FontFace(color=MUTED))
            row.cell(v)

    # Conversation --------------------------------------------------------------------------------
    doc.h2("3. Conversația (mesajele numerotate)")
    head = FontFace(emphasis="BOLD", fill_color=GREY_BG)
    with doc.table(col_widths=(11, 27, 136), headings_style=head, line_height=5.2, padding=1.6,
                   text_align=("CENTER", "LEFT", "LEFT")) as t:
        r = t.row()
        for h in ("Nr.", "Autor", "Mesaj"):
            r.cell(h)
        for e in inc.timeline:
            style = FontFace(fill_color=RED_BG, color=RED, emphasis="BOLD") if e.is_first_alert else None
            r = t.row(style=style)
            r.cell(str(e.n))
            r.cell(e.author_label)
            text = e.text if len(e.text) <= MAX_CELL_CHARS else (
                e.text[:MAX_CELL_CHARS] + f"… [mesaj trunchiat: {len(e.text)} caractere, textul complet în raport.json]"
            )
            r.cell((text or "(mesaj gol)") + ("\n▲ Aici a început tentativa de înșelăciune." if e.is_first_alert else ""))

    # Indicators ----------------------------------------------------------------------------------
    doc.h2("4. Elemente de identificare folosite")
    if inc.indicators:
        doc.para("Adresele sunt scrise intenționat „dezactivat” ([.] în loc de punct) ca să nu fie accesate.",
                 size=8.5, color=MUTED)
        doc.ln(1)
        doc.set_font("DejaVu", "", 10)
        doc.set_text_color(*INK)
        with doc.table(col_widths=(44, 106, 24), headings_style=head, line_height=5.2, padding=1.6,
                       text_align=("LEFT", "LEFT", "CENTER")) as t:
            r = t.row()
            for h in ("Tip", "Valoare", "Mesajul"):
                r.cell(h)
            for i in inc.indicators:
                r = t.row()
                r.cell(_KIND[i.kind])
                r.cell(i.display)
                r.cell(str(i.message_n) if i.message_n else "expeditor")
    else:
        doc.para("—")

    # Red flags -----------------------------------------------------------------------------------
    doc.h2("5. Semnale de înșelăciune identificate")
    for f in inc.red_flags:
        doc.set_font("DejaVu", "", 10)
        doc.set_text_color(*INK)
        doc.multi_cell(0, 5.4, f"•  Persoana {f.label}.", new_x="LMARGIN", new_y="NEXT")

    # Damage --------------------------------------------------------------------------------------
    doc.h2("6. Prejudiciu")
    lost = "Da" if p.lost_money else "Nu"
    amount = f"{p.amount_lost:,.2f}".replace(",", " ").replace(".", ",").replace(" ", ".").removesuffix(",00") + " lei" if p.amount_lost is not None else ("—" if not p.lost_money else BLANK)
    doc.para(f"Am pierdut bani: {lost}.   Suma: {amount}.   Banca: {p.bank or ('—' if not p.lost_money else BLANK)}.")

    if p.additional_details:
        doc.h2("7. Alte detalii")
        doc.para(p.additional_details[:4000])

    # Request + signature -------------------------------------------------------------------------
    doc.ln(4)
    doc.para("Solicit verificarea celor sesizate și luarea măsurilor legale care se impun. "
             "Anexez conversația și elementele de identificare de mai sus.")
    doc.ln(10)
    y = doc.get_y()
    doc.set_font("DejaVu", "", 10)
    doc.cell(85, 6, f"Data: {datetime.now(UTC).strftime('%d.%m.%Y')}")
    doc.cell(0, 6, "Semnătura: ..................................", align="R", new_x="LMARGIN", new_y="NEXT")
    doc.set_y(y + 12)
    doc.para("Raport generat automat de aplicația Scam Shield pe baza conversației furnizate de petent. "
             "Analiza este orientativă; datele personale nu au fost stocate de aplicație.", size=7.5, color=MUTED)
    return bytes(doc.output())
