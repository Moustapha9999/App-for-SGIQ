from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.models import Produit
from services.logging_service import log_action
from services.stock_service import calculer_marge
from utils.crud_ui import render_dataframe

CATEGORIES = [
    "Ciment", "Fer", "Peinture", "Électricité", "Plomberie",
    "Outillage", "Visserie", "Serrurerie", "Autre",
]
UNITES = ["Pièce", "Sac", "Mètre"]


def page_produits(session, user):
    st.header("📦 Gestion des Produits")
    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_cat = st.tabs(
        ["Liste", "Ajouter", "Modifier", "Supprimer", "Catégories"]
    )

    with tab_liste:
        produits = session.scalars(select(Produit).order_by(Produit.code_produit)).all()
        df = pd.DataFrame(
            [
                {
                    "Code": p.code_produit,
                    "Désignation": p.designation,
                    "Catégorie": p.categorie,
                    "P.Achat": float(p.prix_achat),
                    "P.Vente": float(p.prix_vente),
                    "Stock": p.stock,
                    "Min": p.stock_minimum,
                    "Marge": float(p.marge),
                    "Statut": p.statut,
                }
                for p in produits
            ]
        )
        render_dataframe(df)

    with tab_ajouter:
        with st.form("add_prod"):
            code = st.text_input("Code produit *")
            desig = st.text_input("Désignation *")
            cat = st.selectbox("Catégorie", CATEGORIES)
            unite = st.selectbox("Unité", UNITES)
            pa = st.number_input("Prix achat", min_value=0.0, step=0.01)
            pv = st.number_input("Prix vente", min_value=0.0, step=0.01)
            stock = st.number_input("Stock initial", min_value=0, step=1, value=0)
            smin = st.number_input("Stock minimum", min_value=0, step=1, value=5)
            emp = st.text_input("Emplacement")
            statut = st.selectbox("Statut", ["Actif", "Inactif"])
            marge = calculer_marge(Decimal(str(pa)), Decimal(str(pv)))
            marge_pct = (float(marge) / pa * 100) if pa > 0 else 0
            st.caption(f"Marge: {marge:.2f} ({marge_pct:.1f}%)")
            if st.form_submit_button("Enregistrer", type="primary") and code and desig:
                if session.get(Produit, code):
                    st.error("Code produit déjà existant.")
                else:
                    session.add(
                        Produit(
                            code_produit=code.upper(),
                            designation=desig,
                            categorie=cat,
                            unite=unite,
                            prix_achat=Decimal(str(pa)),
                            prix_vente=Decimal(str(pv)),
                            stock=int(stock),
                            stock_minimum=int(smin),
                            marge=marge,
                            emplacement=emp,
                            statut=statut,
                        )
                    )
                    log_action(session, user.id_user, f"Ajout produit {code}")
                    session.commit()
                    st.success("Produit ajouté.")
                    st.rerun()

    with tab_modifier:
        produits = session.scalars(select(Produit)).all()
        if produits:
            code = st.selectbox("Produit", [p.code_produit for p in produits])
            p = session.get(Produit, code)
            with st.form("edit_prod"):
                p.designation = st.text_input("Désignation", value=p.designation)
                p.categorie = st.selectbox("Catégorie", CATEGORIES, index=CATEGORIES.index(p.categorie) if p.categorie in CATEGORIES else len(CATEGORIES) - 1)
                p.unite = st.selectbox("Unité", UNITES, index=UNITES.index(p.unite) if p.unite in UNITES else 0)
                pa = st.number_input("Prix achat", value=float(p.prix_achat), step=0.01)
                pv = st.number_input("Prix vente", value=float(p.prix_vente), step=0.01)
                p.stock_minimum = st.number_input("Stock minimum", value=int(p.stock_minimum), step=1)
                p.emplacement = st.text_input("Emplacement", value=p.emplacement or "")
                p.statut = st.selectbox("Statut", ["Actif", "Inactif"], index=0 if p.statut == "Actif" else 1)
                if st.form_submit_button("Mettre à jour", type="primary"):
                    p.prix_achat = Decimal(str(pa))
                    p.prix_vente = Decimal(str(pv))
                    p.marge = calculer_marge(p.prix_achat, p.prix_vente)
                    log_action(session, user.id_user, f"Modification produit {code}")
                    session.commit()
                    st.success("Produit mis à jour.")
                    st.rerun()

    with tab_supprimer:
        produits = session.scalars(select(Produit)).all()
        if produits:
            code = st.selectbox("Produit à supprimer", [p.code_produit for p in produits])
            if st.button("Supprimer", type="primary"):
                p = session.get(Produit, code)
                log_action(session, user.id_user, f"Suppression produit {code}")
                session.delete(p)
                session.commit()
                st.success("Produit supprimé.")
                st.rerun()

    with tab_cat:
        produits = session.scalars(select(Produit)).all()
        if produits:
            counts = pd.Series([p.categorie for p in produits]).value_counts()
            st.bar_chart(counts)
