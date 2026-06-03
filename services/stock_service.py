from decimal import Decimal

from sqlalchemy.orm import Session

from database.models import MouvementStock, Produit
from services.logging_service import log_action


def calculer_marge(prix_achat: Decimal, prix_vente: Decimal) -> Decimal:
    return prix_vente - prix_achat


def mouvement_stock(
    session: Session,
    code_produit: str,
    type_mouv: str,
    quantite: int,
    reference: str,
    id_user: int | None,
):
    produit = session.get(Produit, code_produit)
    if not produit:
        raise ValueError(f"Produit {code_produit} introuvable")

    if type_mouv == "Sortie" and produit.stock < quantite:
        raise ValueError(f"Stock insuffisant pour {code_produit}")

    if type_mouv == "Entrée":
        produit.stock += quantite
    else:
        produit.stock -= quantite

    session.add(
        MouvementStock(
            code_produit=code_produit,
            type=type_mouv,
            quantite=quantite,
            reference=reference,
            id_user=id_user,
        )
    )
    log_action(session, id_user, f"Stock {type_mouv}: {code_produit} x{quantite} ({reference})")
