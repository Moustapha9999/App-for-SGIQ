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
UNITES = ["Pièce", "Sac", "Mètre", "Rouleau", "Bidon", "Barre", "Boîte", "Kg"]


def page_produits(session, user):
    st.title("📦 Gestion des Produits")

    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_cat = st.tabs(
        ["📋 Liste", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "📊 Catégories"]
    )

    # ── Liste ─────────────────────────────────────────────────────────────
    with tab_liste:
        c1, c2 = st.columns(2)
        filtre_code = c1.text_input("🔍 Code / Désignation", placeholder="PRD-001 ou Ciment...")
        filtre_cat  = c2.selectbox("Catégorie", ["Toutes"] + CATEGORIES, key="liste_prod_cat")

        produits = session.scalars(select(Produit).order_by(Produit.code_produit)).all()
        df = pd.DataFrame([{
            "Code":        p.code_produit,
            "Désignation": p.designation,
            "Catégorie":   p.categorie,
            "P.Achat":     f"{float(p.prix_achat):,.0f}",
            "P.Vente":     f"{float(p.prix_vente):,.0f}",
            "Marge":       f"{float(p.marge):,.0f}",
            "Stock":       p.stock,
            "Min":         p.stock_minimum,
            "Alerte":      (
                "🔴 Rupture" if p.stock == 0
                else ("🟡 Faible" if p.stock <= p.stock_minimum else "🟢 OK")
            ),
            "Statut":      p.statut,
        } for p in produits])

        if filtre_code:
            df = df[
                df["Code"].str.contains(filtre_code, case=False, na=False) |
                df["Désignation"].str.contains(filtre_code, case=False, na=False)
            ]
        if filtre_cat != "Toutes":
            df = df[df["Catégorie"] == filtre_cat]

        st.caption(f"{len(df)} produit(s) trouvé(s)")
        render_dataframe(df)

    # ── Ajouter ───────────────────────────────────────────────────────────
    with tab_ajouter:
        st.subheader("Nouveau produit")
        with st.form("add_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            code  = c1.text_input("Code produit *", placeholder="PRD-008")
            desig = c2.text_input("Désignation *",  placeholder="Ciment CEM II 50kg")
            cat   = c1.selectbox("Catégorie *", CATEGORIES)
            unite = c2.selectbox("Unité", UNITES)
            pa    = c1.number_input("Prix achat (MRU)",  min_value=0.0, step=1.0)
            pv    = c2.number_input("Prix vente (MRU)",  min_value=0.0, step=1.0)
            stock = c1.number_input("Stock initial", min_value=0, step=1, value=0)
            smin  = c2.number_input("Stock minimum", min_value=0, step=1, value=5)
            emp   = c1.text_input("Emplacement", placeholder="Zone A-1")
            statut = c2.selectbox("Statut", ["Actif", "Inactif"])

            marge = calculer_marge(Decimal(str(pa)), Decimal(str(pv)))
            marge_pct = (float(marge) / pa * 100) if pa > 0 else 0
            st.info(f"💡 Marge calculée : **{float(marge):,.0f} MRU** ({marge_pct:.1f} %)")

            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            if not code.strip() or not desig.strip():
                st.error("❌ Le code et la désignation sont obligatoires.")
            elif session.get(Produit, code.upper()):
                st.error(f"❌ Le code **{code.upper()}** existe déjà.")
            else:
                session.add(Produit(
                    code_produit=code.upper().strip(),
                    designation=desig.strip(),
                    categorie=cat, unite=unite,
                    prix_achat=Decimal(str(pa)),
                    prix_vente=Decimal(str(pv)),
                    stock=int(stock), stock_minimum=int(smin),
                    marge=marge, emplacement=emp or None, statut=statut,
                ))
                log_action(session, user.id_user, f"Ajout produit {code.upper()}")
                session.commit()
                st.toast(f"✅ Produit **{desig}** ajouté !", icon="✅")
                st.rerun()

    # ── Modifier ──────────────────────────────────────────────────────────
    with tab_modifier:
        produits = session.scalars(select(Produit).order_by(Produit.code_produit)).all()
        if not produits:
            st.info("Aucun produit à modifier.")
        else:
            code = st.selectbox(
                "Sélectionner le produit",
                [p.code_produit for p in produits],
                format_func=lambda x: next(
                    f"{p.code_produit} — {p.designation}"
                    for p in produits if p.code_produit == x
                ),
                key="mod_prod_select",
            )
            p = session.get(Produit, code)
            with st.form("edit_prod"):
                c1, c2 = st.columns(2)
                desig_e = c1.text_input("Désignation", value=p.designation)
                cat_e   = c2.selectbox("Catégorie", CATEGORIES,
                            index=CATEGORIES.index(p.categorie)
                            if p.categorie in CATEGORIES else len(CATEGORIES)-1)
                unite_e = c1.selectbox("Unité", UNITES,
                            index=UNITES.index(p.unite) if p.unite in UNITES else 0)
                pa_e    = c2.number_input("Prix achat", value=float(p.prix_achat), step=1.0)
                pv_e    = c1.number_input("Prix vente", value=float(p.prix_vente), step=1.0)
                smin_e  = c2.number_input("Stock minimum", value=int(p.stock_minimum), step=1)
                emp_e   = c1.text_input("Emplacement", value=p.emplacement or "")
                st_e    = c2.selectbox("Statut", ["Actif", "Inactif"],
                            index=0 if p.statut == "Actif" else 1)
                update  = st.form_submit_button("💾 Mettre à jour", type="primary")

            if update:
                p.designation   = desig_e
                p.categorie     = cat_e
                p.unite         = unite_e
                p.prix_achat    = Decimal(str(pa_e))
                p.prix_vente    = Decimal(str(pv_e))
                p.marge         = calculer_marge(p.prix_achat, p.prix_vente)
                p.stock_minimum = smin_e
                p.emplacement   = emp_e or None
                p.statut        = st_e
                log_action(session, user.id_user, f"Modification produit {code}")
                session.commit()
                st.toast(f"✅ Produit **{desig_e}** mis à jour !", icon="✅")
                st.rerun()

    # ── Supprimer ─────────────────────────────────────────────────────────
    with tab_supprimer:
        produits = session.scalars(select(Produit).order_by(Produit.code_produit)).all()
        if not produits:
            st.info("Aucun produit à supprimer.")
        else:
            code = st.selectbox(
                "Sélectionner le produit à supprimer",
                [p.code_produit for p in produits],
                format_func=lambda x: next(
                    f"{p.code_produit} — {p.designation}"
                    for p in produits if p.code_produit == x
                ),
                key="del_prod_select",
            )
            p = session.get(Produit, code)
            st.warning(
                f"⚠️ Vous allez supprimer **{p.designation}** ({p.code_produit}). "
                "Tous les mouvements de stock liés seront aussi supprimés."
            )
            confirmer = st.checkbox("Je confirme la suppression", key="del_prod_confirm")
            if st.button("🗑️ Supprimer définitivement", type="primary",
                         disabled=not confirmer, key="del_prod_btn"):
                nom_supp = p.designation
                log_action(session, user.id_user, f"Suppression produit {code}")
                session.delete(p)
                session.commit()
                st.toast(f"🗑️ Produit **{nom_supp}** supprimé.", icon="🗑️")
                st.rerun()

    # ── Catégories ────────────────────────────────────────────────────────
    with tab_cat:
        produits = session.scalars(select(Produit)).all()
        if produits:
            df_cat = pd.DataFrame([{
                "Catégorie": p.categorie, "Stock": p.stock,
                "Valeur": float(p.stock * p.prix_achat),
            } for p in produits])
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Nombre de produits par catégorie**")
                counts = df_cat["Catégorie"].value_counts()
                st.bar_chart(counts)
            with col2:
                st.markdown("**Stock total par catégorie**")
                stock_cat = df_cat.groupby("Catégorie")["Stock"].sum()
                st.bar_chart(stock_cat)
        else:
            st.info("Aucun produit enregistré.")