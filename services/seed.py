from decimal import Decimal

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import TVA_DEFAULT
from database.models import Client, Fournisseur, Parametre, Produit, Utilisateur
from services.auth import hash_password


def seed_if_empty(session: Session):
    if session.scalar(select(Utilisateur).limit(1)):
        return

    session.add(
        Utilisateur(
            nom="Admin",
            prenom="Système",
            username="admin",
            email="admin@sgiq.local",
            mot_de_passe=hash_password("admin123"),
            role="ADMIN",
            telephone="0600000000",
            statut="Actif",
        )
    )
    session.add(
        Utilisateur(
            nom="Caissier",
            prenom="Demo",
            username="caissier",
            email="caissier@sgiq.local",
            mot_de_passe=hash_password("caissier123"),
            role="CAISSIER",
            statut="Actif",
        )
    )
    session.add(
        Utilisateur(
            nom="Magasinier",
            prenom="Demo",
            username="magasinier",
            email="magasin@sgiq.local",
            mot_de_passe=hash_password("magasin123"),
            role="MAGASINIER",
            statut="Actif",
        )
    )

    defaults = {
        "societe_nom": "Quincaillerie SGIQ",
        "societe_adresse": "123 Avenue Mohammed V, Casablanca",
        "societe_telephone": "+212 5 22 00 00 00",
        "societe_email": "contact@sgiq.ma",
        "societe_nif": "12345678",
        "devise": "MAD",
        "tva": str(TVA_DEFAULT),
        "facture_prefixe": "FAC",
    }
    for cle, valeur in defaults.items():
        session.add(Parametre(cle=cle, valeur=valeur))

    session.add(
        Client(
            nom_client="Client Démo",
            type_client="Particulier",
            telephone_client="0612345678",
            adresse="Casablanca",
        )
    )
    session.add(
        Fournisseur(
            raison_sociale="Fournisseur Ciment SA",
            produit_principal="Ciment",
            telephone="0522000000",
            mode_paiement="Virement",
        )
    )

    produits_demo = [
        ("CIM-50", "Ciment CPJ 50kg", "Ciment", "Sac", 45, 65, 100, 10),
        ("FER-12", "Fer à béton 12mm", "Fer", "Pièce", 80, 110, 50, 5),
        ("PEI-BLA", "Peinture blanche 10L", "Peinture", "Pièce", 120, 180, 30, 5),
        ("VIS-M6", "Vis M6 x 50", "Visserie", "Pièce", 2, 5, 500, 50),
    ]
    for code, desig, cat, unite, pa, pv, stock, smin in produits_demo:
        session.add(
            Produit(
                code_produit=code,
                designation=desig,
                categorie=cat,
                unite=unite,
                prix_achat=Decimal(pa),
                prix_vente=Decimal(pv),
                stock=stock,
                stock_minimum=smin,
                marge=Decimal(pv - pa),
                emplacement="A1",
            )
        )
