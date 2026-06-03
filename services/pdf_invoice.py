import io
from decimal import Decimal
from pathlib import Path

from reportlab.lib import colors
from reportlab.lib.pagesizes import A4
from reportlab.lib.styles import ParagraphStyle, getSampleStyleSheet
from reportlab.lib.units import cm
from reportlab.platypus import Paragraph, SimpleDocTemplate, Spacer, Table, TableStyle

from database.models import Parametre, Produit, Vente


def _param(session, cle: str, default: str = "") -> str:
    p = session.query(Parametre).filter(Parametre.cle == cle).first()
    return p.valeur if p and p.valeur else default


def generate_invoice_pdf(session, vente: Vente) -> bytes:
    buffer = io.BytesIO()
    doc = SimpleDocTemplate(buffer, pagesize=A4, rightMargin=2 * cm, leftMargin=2 * cm)
    styles = getSampleStyleSheet()
    title_style = ParagraphStyle("Title", parent=styles["Heading1"], fontSize=16, spaceAfter=12)
    elements = []

    nom = _param(session, "societe_nom", "Quincaillerie SGIQ")
    adresse = _param(session, "societe_adresse", "")
    tel = _param(session, "societe_telephone", "")
    nif = _param(session, "societe_nif", "")
    devise = _param(session, "devise", "MAD")

    logo_path = _param(session, "societe_logo", "")
    if logo_path and Path(logo_path).exists():
        from reportlab.platypus import Image

        elements.append(Image(logo_path, width=3 * cm, height=2 * cm))
        elements.append(Spacer(1, 0.3 * cm))

    elements.append(Paragraph(f"<b>{nom}</b>", title_style))
    if adresse:
        elements.append(Paragraph(adresse, styles["Normal"]))
    if tel:
        elements.append(Paragraph(f"Tél: {tel}", styles["Normal"]))
    if nif:
        elements.append(Paragraph(f"NIF: {nif}", styles["Normal"]))
    elements.append(Spacer(1, 0.5 * cm))

    num = vente.numero_facture or f"FAC-{vente.id_vente:06d}"
    client_nom = vente.client.nom_client if vente.client else "Client comptant"
    elements.append(Paragraph(f"<b>Facture N° {num}</b>", styles["Heading2"]))
    elements.append(Paragraph(f"Date: {vente.date.strftime('%d/%m/%Y %H:%M')}", styles["Normal"]))
    elements.append(Paragraph(f"Client: {client_nom}", styles["Normal"]))
    elements.append(Spacer(1, 0.4 * cm))

    data = [["Produit", "Qté", "P.U.", "Total"]]
    for ligne in vente.lignes:
        prod = session.get(Produit, ligne.code_produit)
        desig = prod.designation if prod else ligne.code_produit
        data.append(
            [
                desig,
                str(ligne.quantite),
                f"{ligne.prix_unitaire:.2f}",
                f"{ligne.total:.2f}",
            ]
        )

    table = Table(data, colWidths=[8 * cm, 2 * cm, 3 * cm, 3 * cm])
    table.setStyle(
        TableStyle(
            [
                ("BACKGROUND", (0, 0), (-1, 0), colors.HexColor("#1f4e79")),
                ("TEXTCOLOR", (0, 0), (-1, 0), colors.whitesmoke),
                ("ALIGN", (1, 1), (-1, -1), "RIGHT"),
                ("FONTNAME", (0, 0), (-1, 0), "Helvetica-Bold"),
                ("GRID", (0, 0), (-1, -1), 0.5, colors.grey),
                ("ROWBACKGROUNDS", (0, 1), (-1, -1), [colors.white, colors.HexColor("#f0f4f8")]),
            ]
        )
    )
    elements.append(table)
    elements.append(Spacer(1, 0.5 * cm))

    ht = vente.montant_ht or Decimal("0")
    remise = vente.remise or Decimal("0")
    tva = vente.tva or Decimal("0")
    ttc = vente.montant_total or Decimal("0")

    resume = [
        ["Sous-total HT", f"{ht:.2f} {devise}"],
        ["Remise", f"{remise:.2f} {devise}"],
        ["TVA", f"{tva:.2f} {devise}"],
        ["Total TTC", f"{ttc:.2f} {devise}"],
    ]
    rt = Table(resume, colWidths=[10 * cm, 6 * cm])
    rt.setStyle(TableStyle([("ALIGN", (1, 0), (1, -1), "RIGHT"), ("FONTNAME", (0, -1), (-1, -1), "Helvetica-Bold")]))
    elements.append(rt)
    elements.append(Spacer(1, 1 * cm))
    elements.append(Paragraph("<i>Merci pour votre confiance</i>", styles["Normal"]))

    doc.build(elements)
    buffer.seek(0)
    return buffer.read()
