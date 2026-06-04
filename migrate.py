#!/usr/bin/env python3
# migrate.py
# ============================================================
#  Script de migration SQLite → Supabase/PostgreSQL
#  Usage : python migrate.py
# ============================================================

import sys
import os
sys.path.insert(0, os.path.dirname(__file__))

from dotenv import load_dotenv
load_dotenv()

import sqlite3
from decimal import Decimal
from pathlib import Path
from datetime import datetime

from sqlalchemy import create_engine, text
from sqlalchemy.orm import sessionmaker

from database.models import Base, Utilisateur, Client, Fournisseur, Produit
from database.models import MouvementStock, Achat, LigneAchat, Vente, LigneVente
from database.models import Credit, PaiementCredit, Commande, LigneCommande
from database.models import Parametre, Log


SQLITE_PATH = Path("./data/sgiq.db")


def get_pg_url() -> str:
    url = os.getenv("DATABASE_URL", "")
    if not url or "sqlite" in url:
        print("❌ DATABASE_URL non configurée ou pointe vers SQLite.")
        print("   Ajoutez votre URL Supabase dans .env")
        sys.exit(1)
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)
    return url


def migrate():
    if not SQLITE_PATH.exists():
        print(f"❌ Base SQLite introuvable : {SQLITE_PATH}")
        sys.exit(1)

    pg_url = get_pg_url()
    print(f"🔗 Connexion à PostgreSQL/Supabase...")

    pg_engine = create_engine(pg_url, echo=False, pool_pre_ping=True)
    PgSession = sessionmaker(bind=pg_engine)

    # Crée toutes les tables sur Supabase
    print("📋 Création des tables sur Supabase...")
    Base.metadata.create_all(bind=pg_engine)

    # Connexion SQLite source
    sqlite_conn = sqlite3.connect(str(SQLITE_PATH))
    sqlite_conn.row_factory = sqlite3.Row
    cur = sqlite_conn.cursor()

    pg = PgSession()

    try:
        print("\n📦 Migration des données...")

        # ── Utilisateurs ─────────────────────────────────────────────────
        cur.execute("SELECT * FROM utilisateurs")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Utilisateur(
                id_user=r["id_user"], nom=r["nom"], prenom=r["prenom"],
                username=r["username"], email=r["email"],
                mot_de_passe=r["mot_de_passe"], role=r["role"],
                telephone=r["telephone"], statut=r["statut"],
            ))
        print(f"   ✅ Utilisateurs : {len(rows)}")

        # ── Clients ───────────────────────────────────────────────────────
        cur.execute("SELECT * FROM clients")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Client(
                id_client=r["id_client"], nom_client=r["nom_client"],
                type_client=r["type_client"],
                telephone_client=r["telephone_client"],
                adresse=r["adresse"], email=r["email"], statut=r["statut"],
            ))
        print(f"   ✅ Clients : {len(rows)}")

        # ── Fournisseurs ──────────────────────────────────────────────────
        cur.execute("SELECT * FROM fournisseurs")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Fournisseur(
                id_fournisseur=r["id_fournisseur"],
                raison_sociale=r["raison_sociale"],
                produit_principal=r["produit_principal"],
                telephone=r["telephone"], adresse=r["adresse"],
                email=r["email"], mode_paiement=r["mode_paiement"],
                statut=r["statut"],
            ))
        print(f"   ✅ Fournisseurs : {len(rows)}")

        # ── Produits ──────────────────────────────────────────────────────
        cur.execute("SELECT * FROM produits")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Produit(
                code_produit=r["code_produit"], designation=r["designation"],
                categorie=r["categorie"], unite=r["unite"],
                prix_achat=Decimal(str(r["prix_achat"])),
                prix_vente=Decimal(str(r["prix_vente"])),
                stock=r["stock"], stock_minimum=r["stock_minimum"],
                marge=Decimal(str(r["marge"])),
                emplacement=r["emplacement"], statut=r["statut"],
            ))
        print(f"   ✅ Produits : {len(rows)}")

        # ── Paramètres ────────────────────────────────────────────────────
        cur.execute("SELECT * FROM parametres")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Parametre(id=r["id"], cle=r["cle"], valeur=r["valeur"]))
        print(f"   ✅ Paramètres : {len(rows)}")

        # ── Achats ────────────────────────────────────────────────────────
        cur.execute("SELECT * FROM achats")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Achat(
                id_achat=r["id_achat"], id_fournisseur=r["id_fournisseur"],
                montant_total=Decimal(str(r["montant_total"])),
                mode_paiement=r["mode_paiement"], statut=r["statut"],
                id_user=r["id_user"], annule=bool(r["annule"]),
            ))
        print(f"   ✅ Achats : {len(rows)}")

        cur.execute("SELECT * FROM lignes_achat")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(LigneAchat(
                id_ligne=r["id_ligne"], id_achat=r["id_achat"],
                code_produit=r["code_produit"], quantite=r["quantite"],
                prix_unitaire=Decimal(str(r["prix_unitaire"])),
                total=Decimal(str(r["total"])),
            ))
        print(f"   ✅ Lignes achat : {len(rows)}")

        # ── Ventes ────────────────────────────────────────────────────────
        cur.execute("SELECT * FROM ventes")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Vente(
                id_vente=r["id_vente"], id_client=r["id_client"],
                montant_ht=Decimal(str(r["montant_ht"])),
                remise=Decimal(str(r["remise"])),
                tva=Decimal(str(r["tva"])),
                montant_total=Decimal(str(r["montant_total"])),
                mode_paiement=r["mode_paiement"], statut=r["statut"],
                id_user=r["id_user"], numero_facture=r["numero_facture"],
            ))
        print(f"   ✅ Ventes : {len(rows)}")

        cur.execute("SELECT * FROM lignes_vente")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(LigneVente(
                id_ligne=r["id_ligne"], id_vente=r["id_vente"],
                code_produit=r["code_produit"], quantite=r["quantite"],
                prix_unitaire=Decimal(str(r["prix_unitaire"])),
                remise=Decimal(str(r["remise"])),
                total=Decimal(str(r["total"])),
            ))
        print(f"   ✅ Lignes vente : {len(rows)}")

        # ── Crédits ───────────────────────────────────────────────────────
        cur.execute("SELECT * FROM credits")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Credit(
                id_credit=r["id_credit"], id_client=r["id_client"],
                id_vente=r["id_vente"],
                montant=Decimal(str(r["montant"])),
                montant_restant=Decimal(str(r["montant_restant"])),
                date_echeance=r["date_echeance"], statut=r["statut"],
            ))
        print(f"   ✅ Crédits : {len(rows)}")

        # ── Mouvements stock ──────────────────────────────────────────────
        cur.execute("SELECT * FROM mouvements_stock")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(MouvementStock(
                id_mouvement=r["id_mouvement"], code_produit=r["code_produit"],
                type=r["type"], quantite=r["quantite"],
                reference=r["reference"], id_user=r["id_user"],
            ))
        print(f"   ✅ Mouvements stock : {len(rows)}")

        # ── Logs ──────────────────────────────────────────────────────────
        cur.execute("SELECT * FROM logs")
        rows = cur.fetchall()
        for r in rows:
            pg.merge(Log(
                id_log=r["id_log"], id_user=r["id_user"],
                action=r["action"],
            ))
        print(f"   ✅ Logs : {len(rows)}")

        pg.commit()

        # Resync sequences PostgreSQL (SERIAL)
        print("\n🔄 Synchronisation des séquences PostgreSQL...")
        tables_seq = [
            ("utilisateurs", "id_user"),
            ("clients",      "id_client"),
            ("fournisseurs", "id_fournisseur"),
            ("achats",       "id_achat"),
            ("lignes_achat", "id_ligne"),
            ("ventes",       "id_vente"),
            ("lignes_vente", "id_ligne"),
            ("credits",      "id_credit"),
            ("mouvements_stock", "id_mouvement"),
            ("parametres",   "id"),
            ("logs",         "id_log"),
        ]
        with pg_engine.connect() as conn:
            for table, col in tables_seq:
                conn.execute(text(
                    f"SELECT setval(pg_get_serial_sequence('{table}', '{col}'), "
                    f"COALESCE(MAX({col}), 1)) FROM {table};"
                ))
            conn.commit()
        print("   ✅ Séquences synchronisées")

        print("\n🎉 Migration terminée avec succès !")
        print(f"   Données migrées depuis : {SQLITE_PATH}")

    except Exception as e:
        pg.rollback()
        print(f"\n❌ Erreur lors de la migration : {e}")
        raise
    finally:
        pg.close()
        sqlite_conn.close()


if __name__ == "__main__":
    migrate()