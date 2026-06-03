import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.models import MouvementStock, Produit
from utils.crud_ui import render_dataframe


def page_stock(session, user):
    st.header("📊 Gestion du Stock")
    tab_etat, tab_mouv, tab_alertes = st.tabs(["État Stock", "Mouvements", "Alertes"])

    with tab_etat:
        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()
        df = pd.DataFrame(
            [
                {
                    "Code": p.code_produit,
                    "Désignation": p.designation,
                    "Catégorie": p.categorie,
                    "Stock": p.stock,
                    "Minimum": p.stock_minimum,
                    "Emplacement": p.emplacement,
                    "Valorisation": float(p.stock * p.prix_achat),
                }
                for p in produits
            ]
        )
        render_dataframe(df)
        st.metric("Valorisation totale", f"{df['Valorisation'].sum():.2f}" if not df.empty else "0")

    with tab_mouv:
        mouvs = session.scalars(select(MouvementStock).order_by(MouvementStock.date.desc()).limit(200)).all()
        df = pd.DataFrame(
            [
                {
                    "Date": m.date,
                    "Produit": m.code_produit,
                    "Type": m.type,
                    "Qté": m.quantite,
                    "Référence": m.reference,
                }
                for m in mouvs
            ]
        )
        render_dataframe(df)

    with tab_alertes:
        st.subheader("Stock faible")
        faibles = session.scalars(
            select(Produit).where(Produit.stock <= Produit.stock_minimum, Produit.stock > 0)
        ).all()
        render_dataframe(
            pd.DataFrame([{"Code": p.code_produit, "Désignation": p.designation, "Stock": p.stock, "Min": p.stock_minimum} for p in faibles])
        )
        st.subheader("Rupture de stock")
        rupture = session.scalars(select(Produit).where(Produit.stock == 0)).all()
        render_dataframe(
            pd.DataFrame([{"Code": p.code_produit, "Désignation": p.designation, "Stock": 0} for p in rupture])
        )
