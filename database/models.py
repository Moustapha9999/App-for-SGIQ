# database/models.py
# ============================================================
#  Modèles SQLAlchemy — compatibles SQLite ET PostgreSQL/Supabase
# ============================================================

from datetime import date, datetime
from decimal import Decimal

from sqlalchemy import (
    Boolean, Date, DateTime, ForeignKey,
    Integer, Numeric, String, Text,
    Index, func,
)
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column, relationship


class Base(DeclarativeBase):
    pass


# ── Utilisateurs ─────────────────────────────────────────────────────────
class Utilisateur(Base):
    __tablename__ = "utilisateurs"

    id_user:      Mapped[int]           = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom:          Mapped[str]           = mapped_column(String(100), nullable=False)
    prenom:       Mapped[str]           = mapped_column(String(100), nullable=False)
    username:     Mapped[str]           = mapped_column(String(50),  unique=True, nullable=False)
    email:        Mapped[str | None]    = mapped_column(String(120))
    mot_de_passe: Mapped[str]           = mapped_column(String(255), nullable=False)
    role:         Mapped[str]           = mapped_column(String(20),  nullable=False)
    telephone:    Mapped[str | None]    = mapped_column(String(30))
    statut:       Mapped[str]           = mapped_column(String(20),  default="Actif")
    date_creation: Mapped[datetime]     = mapped_column(DateTime,    server_default=func.now())

    logs: Mapped[list["Log"]] = relationship(back_populates="utilisateur")

    __table_args__ = (
        Index("ix_utilisateurs_username", "username"),
    )


# ── Clients ───────────────────────────────────────────────────────────────
class Client(Base):
    __tablename__ = "clients"

    id_client:        Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    nom_client:       Mapped[str]        = mapped_column(String(150), nullable=False)
    type_client:      Mapped[str]        = mapped_column(String(30),  default="Particulier")
    telephone_client: Mapped[str | None] = mapped_column(String(30))
    adresse:          Mapped[str | None] = mapped_column(String(255))
    email:            Mapped[str | None] = mapped_column(String(120))
    statut:           Mapped[str]        = mapped_column(String(20),  default="Actif")
    date_creation:    Mapped[datetime]   = mapped_column(DateTime,    server_default=func.now())

    ventes:   Mapped[list["Vente"]]    = relationship(back_populates="client")
    commandes: Mapped[list["Commande"]] = relationship(back_populates="client")
    credits:  Mapped[list["Credit"]]   = relationship(back_populates="client")

    __table_args__ = (
        Index("ix_clients_nom", "nom_client"),
        Index("ix_clients_statut", "statut"),
    )


# ── Fournisseurs ──────────────────────────────────────────────────────────
class Fournisseur(Base):
    __tablename__ = "fournisseurs"

    id_fournisseur:   Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    raison_sociale:   Mapped[str]        = mapped_column(String(150), nullable=False)
    produit_principal: Mapped[str | None]= mapped_column(String(100))
    telephone:        Mapped[str | None] = mapped_column(String(30))
    adresse:          Mapped[str | None] = mapped_column(String(255))
    email:            Mapped[str | None] = mapped_column(String(120))
    mode_paiement:    Mapped[str]        = mapped_column(String(30),  default="Espèces")
    statut:           Mapped[str]        = mapped_column(String(20),  default="Actif")

    achats: Mapped[list["Achat"]] = relationship(back_populates="fournisseur")

    __table_args__ = (
        Index("ix_fournisseurs_statut", "statut"),
    )


# ── Produits ──────────────────────────────────────────────────────────────
class Produit(Base):
    __tablename__ = "produits"

    code_produit:  Mapped[str]     = mapped_column(String(50),    primary_key=True)
    designation:   Mapped[str]     = mapped_column(String(200),   nullable=False)
    categorie:     Mapped[str]     = mapped_column(String(80),    nullable=False)
    unite:         Mapped[str]     = mapped_column(String(30),    default="Pièce")
    prix_achat:    Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    prix_vente:    Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    stock:         Mapped[int]     = mapped_column(Integer,        default=0)
    stock_minimum: Mapped[int]     = mapped_column(Integer,        default=5)
    marge:         Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    emplacement:   Mapped[str | None] = mapped_column(String(80))
    statut:        Mapped[str]     = mapped_column(String(20),    default="Actif")

    mouvements:   Mapped[list["MouvementStock"]] = relationship(back_populates="produit")
    lignes_vente: Mapped[list["LigneVente"]]     = relationship(back_populates="produit")
    lignes_achat: Mapped[list["LigneAchat"]]     = relationship(back_populates="produit")

    __table_args__ = (
        Index("ix_produits_categorie", "categorie"),
        Index("ix_produits_statut",    "statut"),
        Index("ix_produits_stock",     "stock"),
    )


# ── Mouvements de stock ───────────────────────────────────────────────────
class MouvementStock(Base):
    __tablename__ = "mouvements_stock"

    id_mouvement: Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    date:         Mapped[datetime]   = mapped_column(DateTime, server_default=func.now())
    code_produit: Mapped[str]        = mapped_column(ForeignKey("produits.code_produit"))
    type:         Mapped[str]        = mapped_column(String(20))
    quantite:     Mapped[int]        = mapped_column(Integer)
    reference:    Mapped[str | None] = mapped_column(String(80))
    id_user:      Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id_user"))

    produit:      Mapped["Produit"]           = relationship(back_populates="mouvements")
    utilisateur:  Mapped["Utilisateur | None"] = relationship()

    __table_args__ = (
        Index("ix_mvt_produit", "code_produit"),
        Index("ix_mvt_date",    "date"),
    )


# ── Achats ────────────────────────────────────────────────────────────────
class Achat(Base):
    __tablename__ = "achats"

    id_achat:       Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    date:           Mapped[datetime]= mapped_column(DateTime, server_default=func.now())
    id_fournisseur: Mapped[int]     = mapped_column(ForeignKey("fournisseurs.id_fournisseur"))
    montant_total:  Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    mode_paiement:  Mapped[str]     = mapped_column(String(30), default="Espèces")
    statut:         Mapped[str]     = mapped_column(String(30), default="Payé")
    id_user:        Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id_user"))
    annule:         Mapped[bool]    = mapped_column(Boolean, default=False)

    fournisseur: Mapped["Fournisseur"]   = relationship(back_populates="achats")
    lignes:      Mapped[list["LigneAchat"]] = relationship(
        back_populates="achat", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_achats_date",    "date"),
        Index("ix_achats_annule",  "annule"),
    )


class LigneAchat(Base):
    __tablename__ = "lignes_achat"

    id_ligne:      Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_achat:      Mapped[int]     = mapped_column(ForeignKey("achats.id_achat"))
    code_produit:  Mapped[str]     = mapped_column(ForeignKey("produits.code_produit"))
    quantite:      Mapped[int]     = mapped_column(Integer)
    prix_unitaire: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total:         Mapped[Decimal] = mapped_column(Numeric(12, 2))

    achat:   Mapped["Achat"]   = relationship(back_populates="lignes")
    produit: Mapped["Produit"] = relationship(back_populates="lignes_achat")


# ── Ventes ────────────────────────────────────────────────────────────────
class Vente(Base):
    __tablename__ = "ventes"

    id_vente:       Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    date:           Mapped[datetime]   = mapped_column(DateTime, server_default=func.now())
    id_client:      Mapped[int | None] = mapped_column(ForeignKey("clients.id_client"))
    montant_ht:     Mapped[Decimal]    = mapped_column(Numeric(14, 2), default=0)
    remise:         Mapped[Decimal]    = mapped_column(Numeric(12, 2), default=0)
    tva:            Mapped[Decimal]    = mapped_column(Numeric(12, 2), default=0)
    montant_total:  Mapped[Decimal]    = mapped_column(Numeric(14, 2), default=0)
    mode_paiement:  Mapped[str]        = mapped_column(String(30), default="Espèces")
    statut:         Mapped[str]        = mapped_column(String(30), default="Payée")
    id_user:        Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id_user"))
    numero_facture: Mapped[str | None] = mapped_column(String(40), unique=True)

    client:  Mapped["Client | None"]   = relationship(back_populates="ventes")
    lignes:  Mapped[list["LigneVente"]]= relationship(
        back_populates="vente", cascade="all, delete-orphan"
    )
    credit:  Mapped["Credit | None"]   = relationship(back_populates="vente", uselist=False)

    __table_args__ = (
        Index("ix_ventes_date",    "date"),
        Index("ix_ventes_client",  "id_client"),
        Index("ix_ventes_statut",  "statut"),
    )


class LigneVente(Base):
    __tablename__ = "lignes_vente"

    id_ligne:      Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_vente:      Mapped[int]     = mapped_column(ForeignKey("ventes.id_vente"))
    code_produit:  Mapped[str]     = mapped_column(ForeignKey("produits.code_produit"))
    quantite:      Mapped[int]     = mapped_column(Integer)
    prix_unitaire: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    remise:        Mapped[Decimal] = mapped_column(Numeric(12, 2), default=0)
    total:         Mapped[Decimal] = mapped_column(Numeric(12, 2))

    vente:   Mapped["Vente"]   = relationship(back_populates="lignes")
    produit: Mapped["Produit"] = relationship(back_populates="lignes_vente")


# ── Crédits ───────────────────────────────────────────────────────────────
class Credit(Base):
    __tablename__ = "credits"

    id_credit:       Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_client:       Mapped[int]        = mapped_column(ForeignKey("clients.id_client"))
    id_vente:        Mapped[int]        = mapped_column(ForeignKey("ventes.id_vente"))
    montant:         Mapped[Decimal]    = mapped_column(Numeric(14, 2))
    montant_restant: Mapped[Decimal]    = mapped_column(Numeric(14, 2))
    date_echeance:   Mapped[date | None]= mapped_column(Date)
    statut:          Mapped[str]        = mapped_column(String(20), default="Ouvert")

    client:    Mapped["Client"]              = relationship(back_populates="credits")
    vente:     Mapped["Vente"]               = relationship(back_populates="credit")
    paiements: Mapped[list["PaiementCredit"]]= relationship(
        back_populates="credit", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_credits_statut", "statut"),
        Index("ix_credits_client", "id_client"),
    )


class PaiementCredit(Base):
    __tablename__ = "paiements_credit"

    id_paiement:   Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_credit:     Mapped[int]     = mapped_column(ForeignKey("credits.id_credit"))
    montant:       Mapped[Decimal] = mapped_column(Numeric(14, 2))
    date_paiement: Mapped[datetime]= mapped_column(DateTime, server_default=func.now())

    credit: Mapped["Credit"] = relationship(back_populates="paiements")


# ── Commandes ─────────────────────────────────────────────────────────────
class Commande(Base):
    __tablename__ = "commandes"

    id_commande:   Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    date_commande: Mapped[datetime]= mapped_column(DateTime, server_default=func.now())
    id_client:     Mapped[int]     = mapped_column(ForeignKey("clients.id_client"))
    montant_total: Mapped[Decimal] = mapped_column(Numeric(14, 2), default=0)
    statut:        Mapped[str]     = mapped_column(String(30), default="En attente")
    mode_paiement: Mapped[str]     = mapped_column(String(30), default="Espèces")
    id_vente:      Mapped[int | None] = mapped_column(ForeignKey("ventes.id_vente"))

    client: Mapped["Client"]              = relationship(back_populates="commandes")
    lignes: Mapped[list["LigneCommande"]] = relationship(
        back_populates="commande", cascade="all, delete-orphan"
    )

    __table_args__ = (
        Index("ix_commandes_statut", "statut"),
        Index("ix_commandes_client", "id_client"),
    )


class LigneCommande(Base):
    __tablename__ = "lignes_commande"

    id_ligne:      Mapped[int]     = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_commande:   Mapped[int]     = mapped_column(ForeignKey("commandes.id_commande"))
    code_produit:  Mapped[str]     = mapped_column(ForeignKey("produits.code_produit"))
    quantite:      Mapped[int]     = mapped_column(Integer)
    prix_unitaire: Mapped[Decimal] = mapped_column(Numeric(12, 2))
    total:         Mapped[Decimal] = mapped_column(Numeric(12, 2))

    commande: Mapped["Commande"] = relationship(back_populates="lignes")


# ── Paramètres ────────────────────────────────────────────────────────────
class Parametre(Base):
    __tablename__ = "parametres"

    id:     Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    cle:    Mapped[str]        = mapped_column(String(80), unique=True)
    valeur: Mapped[str | None] = mapped_column(Text)

    __table_args__ = (
        Index("ix_parametres_cle", "cle"),
    )


# ── Logs ──────────────────────────────────────────────────────────────────
class Log(Base):
    __tablename__ = "logs"

    id_log:      Mapped[int]        = mapped_column(Integer, primary_key=True, autoincrement=True)
    id_user:     Mapped[int | None] = mapped_column(ForeignKey("utilisateurs.id_user"))
    action:      Mapped[str]        = mapped_column(String(255))
    date_action: Mapped[datetime]   = mapped_column(DateTime, server_default=func.now())

    utilisateur: Mapped["Utilisateur | None"] = relationship(back_populates="logs")

    __table_args__ = (
        Index("ix_logs_date",   "date_action"),
        Index("ix_logs_user",   "id_user"),
    )