from decimal import Decimal

from sqlalchemy import select

from database.models import Parametre, Vente


def get_tva(session) -> Decimal:
    p = session.query(Parametre).filter(Parametre.cle == "tva").first()
    return Decimal(p.valeur) if p and p.valeur else Decimal("19")


def next_facture_number(session) -> str:
    prefix = "FAC"
    p = session.query(Parametre).filter(Parametre.cle == "facture_prefixe").first()
    if p and p.valeur:
        prefix = p.valeur
    last = session.scalars(select(Vente).order_by(Vente.id_vente.desc()).limit(1)).first()
    n = (last.id_vente + 1) if last else 1
    return f"{prefix}-{n:06d}"
