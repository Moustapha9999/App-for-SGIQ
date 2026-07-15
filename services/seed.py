# services/seed.py
# ============================================================
#  Données initiales — compatibles PostgreSQL et SQLite
# ============================================================

from decimal import Decimal
from datetime import datetime, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from config import TVA_DEFAULT
from database.models import (
    Client, Fournisseur, Parametre, Produit,
    Utilisateur, Vente, LigneVente, Achat,
    LigneAchat, MouvementStock, Credit,
)
from services.auth import hash_password


def seed_if_empty(session: Session):
    """Insère les données initiales si la base est vide."""
    if session.scalar(select(Utilisateur).limit(1)):
        return  # Déjà initialisée

    print("🌱 Initialisation des données...")

    # ── Utilisateurs ─────────────────────────────────────────────────────
    users = [
        Utilisateur(
            nom="Admin", prenom="Système", username="admin",
            email="admin@sgiq.sn",
            mot_de_passe=hash_password("admin123"),
            role="ADMIN", telephone="77 000 00 00", statut="Actif",
        ),
        Utilisateur(
            nom="Caissier", prenom="Démo", username="caissier",
            email="caissier@sgiq.sn",
            mot_de_passe=hash_password("caissier123"),
            role="CAISSIER", statut="Actif",
        ),
        Utilisateur(
            nom="Magasinier", prenom="Démo", username="magasinier",
            email="magasin@sgiq.sn",
            mot_de_passe=hash_password("magasin123"),
            role="MAGASINIER", statut="Actif",
        ),
    ]
    session.add_all(users)
    session.flush()

    # ── Paramètres ───────────────────────────────────────────────────────
    params = {
        "societe_nom":       "Quincaillerie SGIQ",
        "societe_adresse":   "Rue 10, Médina, Dakar, Sénégal",
        "societe_telephone": "+221 33 820 00 00",
        "societe_email":     "contact@sgiq.sn",
        "societe_nif":       "SN-1234567890",
        "devise":            "MRU",
        "tva":               str(TVA_DEFAULT),
        "facture_prefixe":   "FC",
    }
    for cle, valeur in params.items():
        session.add(Parametre(cle=cle, valeur=valeur))

    # ── Clients ───────────────────────────────────────────────────────────
    clients = [
        Client(nom_client="BTP Sénégal SARL",      type_client="Entreprise",
               telephone_client="77 123 45 67",    adresse="Zone Industrielle, Dakar",
               email="contact@btpsenegal.sn",      statut="Actif"),
        Client(nom_client="Ibrahima Diallo",        type_client="Particulier",
               telephone_client="70 987 65 43",    adresse="Médina, Dakar", statut="Actif"),
        Client(nom_client="Colobane Construction",  type_client="Entreprise",
               telephone_client="33 820 00 01",    adresse="Colobane, Dakar", statut="Actif"),
        Client(nom_client="Fatou Ndiaye",           type_client="Particulier",
               telephone_client="76 543 21 09",    adresse="Pikine", statut="Actif"),
        Client(nom_client="Mamadou Sow",            type_client="Particulier",
               telephone_client="77 111 22 33",    adresse="Guédiawaye", statut="Actif"),
    ]
    session.add_all(clients)
    session.flush()

    # ── Fournisseurs ──────────────────────────────────────────────────────
    fournisseurs = [
        Fournisseur(raison_sociale="SOCOCIM Industries",
                    produit_principal="Ciment",
                    telephone="33 839 00 00", mode_paiement="Bankily", statut="Actif"),
        Fournisseur(raison_sociale="Ets. Diallo Matériaux",
                    produit_principal="Fer, Acier",
                    telephone="77 456 78 90", mode_paiement="Masrvi", statut="Actif"),
        Fournisseur(raison_sociale="Peintex Dakar",
                    produit_principal="Peinture",
                    telephone="78 123 00 11", mode_paiement="Cash", statut="Actif"),
        Fournisseur(raison_sociale="Électro Distribution SN",
                    produit_principal="Câbles, Disjoncteurs",
                    telephone="76 999 88 77", mode_paiement="Sedad", statut="Actif"),
    ]
    session.add_all(fournisseurs)
    session.flush()

    # ── Produits ──────────────────────────────────────────────────────────
    produits_data = [
        ("PRD-001", "Ciment CEM II 50kg",        "Ciment",      "Sac",     4500,  5500,  0,   50, "Zone A-1"),
        ("PRD-002", "Fer HA 12mm 12m",           "Fer",         "Barre",   8200,  11000, 85,  20, "Zone B-2"),
        ("PRD-003", "Peinture Sikkens 10L",       "Peinture",    "Bidon",   18000, 24500, 42,  10, "Zone C-1"),
        ("PRD-004", "Câble 2.5mm² 100m",         "Électricité", "Rouleau", 24000, 32000, 3,   10, "Zone D-1"),
        ("PRD-005", "Robinet ball valve 1/2",     "Plomberie",   "Pièce",   1800,  2800,  8,   20, "Zone E-3"),
        ("PRD-006", "Cheville Fischer 8mm x100",  "Visserie",    "Boîte",   900,   1500,  320, 50, "Zone F-2"),
        ("PRD-007", "Disque tronçonner 230mm",    "Outillage",   "Pièce",   1200,  2000,  148, 30, "Zone G-1"),
        ("PRD-008", "Tuyau PVC 110mm 4m",         "Plomberie",   "Pièce",   3500,  5000,  60,  15, "Zone E-1"),
        ("PRD-009", "Disjoncteur 16A",            "Électricité", "Pièce",   2500,  4000,  95,  20, "Zone D-2"),
        ("PRD-010", "Sable fin (sac 50kg)",       "Ciment",      "Sac",     1200,  1800,  200, 100,"Zone A-2"),
    ]
    produits = []
    for code, desig, cat, unite, pa, pv, stock, smin, emp in produits_data:
        p = Produit(
            code_produit=code, designation=desig, categorie=cat, unite=unite,
            prix_achat=Decimal(pa), prix_vente=Decimal(pv),
            stock=stock, stock_minimum=smin,
            marge=Decimal(pv - pa), emplacement=emp, statut="Actif",
        )
        produits.append(p)
    session.add_all(produits)
    session.flush()

    # ── Achat de démonstration ────────────────────────────────────────────
    achat1 = Achat(
        date=datetime.now() - timedelta(days=3),
        id_fournisseur=fournisseurs[1].id_fournisseur,
        montant_total=Decimal("820000"),
        mode_paiement="Cash", statut="Payé",
        id_user=users[0].id_user,
    )
    session.add(achat1)
    session.flush()
    session.add(LigneAchat(
        id_achat=achat1.id_achat, code_produit="PRD-002",
        quantite=100, prix_unitaire=Decimal("8200"), total=Decimal("820000"),
    ))
    session.add(MouvementStock(
        code_produit="PRD-002", type="Entrée", quantite=100,
        reference=f"Achat-{achat1.id_achat}", id_user=users[0].id_user,
    ))

    # ── Ventes de démonstration ───────────────────────────────────────────
    vente1 = Vente(
        date=datetime.now() - timedelta(hours=5),
        id_client=clients[0].id_client,
        montant_ht=Decimal("185000"), remise=Decimal("0"),
        tva=Decimal("33300"), montant_total=Decimal("218300"),
        mode_paiement="Bankily", statut="Payée",
        id_user=users[1].id_user, numero_facture="FC-2025-0001",
    )
    session.add(vente1)
    session.flush()
    session.add_all([
        LigneVente(id_vente=vente1.id_vente, code_produit="PRD-002",
                   quantite=5, prix_unitaire=Decimal("11000"),
                   remise=Decimal("0"), total=Decimal("55000")),
        LigneVente(id_vente=vente1.id_vente, code_produit="PRD-003",
                   quantite=2, prix_unitaire=Decimal("24500"),
                   remise=Decimal("0"), total=Decimal("49000")),
    ])
    session.add(MouvementStock(
        code_produit="PRD-002", type="Sortie", quantite=5,
        reference="FC-2025-0001", id_user=users[1].id_user,
    ))

    # Vente à crédit
    vente2 = Vente(
        date=datetime.now() - timedelta(hours=2),
        id_client=clients[3].id_client,
        montant_ht=Decimal("47500"), remise=Decimal("0"),
        tva=Decimal("8550"), montant_total=Decimal("56050"),
        mode_paiement="Crédit", statut="Impayée",
        id_user=users[1].id_user, numero_facture="FC-2025-0002",
    )
    session.add(vente2)
    session.flush()
    session.add(LigneVente(
        id_vente=vente2.id_vente, code_produit="PRD-005",
        quantite=5, prix_unitaire=Decimal("2800"),
        remise=Decimal("0"), total=Decimal("14000"),
    ))
    session.add(Credit(
        id_client=clients[3].id_client, id_vente=vente2.id_vente,
        montant=Decimal("56050"), montant_restant=Decimal("56050"),
        date_echeance=(datetime.now() + timedelta(days=30)).date(),
        statut="Ouvert",
    ))

    print("✅ Base initialisée avec succès !")