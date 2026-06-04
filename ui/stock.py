import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.models import MouvementStock, Produit
from services.logging_service import log_action
from services.stock_service import mouvement_stock
from utils.crud_ui import render_dataframe


def page_stock(session, user):
    st.title("📊 Gestion du Stock")

    tab_etat, tab_mouv, tab_ajust, tab_alertes = st.tabs(
        ["📦 État Stock", "🔄 Mouvements", "✏️ Ajustement", "🚨 Alertes"]
    )

    # ── État Stock ────────────────────────────────────────────────────────
    with tab_etat:
        produits = session.scalars(
            select(Produit).where(Produit.statut == "Actif").order_by(Produit.categorie)
        ).all()
        df = pd.DataFrame([{
            "Code":          p.code_produit,
            "Désignation":   p.designation,
            "Catégorie":     p.categorie,
            "Stock":         p.stock,
            "Minimum":       p.stock_minimum,
            "Emplacement":   p.emplacement or "—",
            "Valorisation":  f"{float(p.stock * p.prix_achat):,.0f}",
            "Alerte":        (
                "🔴 Rupture" if p.stock == 0
                else ("🟡 Faible" if p.stock <= p.stock_minimum else "🟢 OK")
            ),
        } for p in produits])

        total_val = sum(float(p.stock * p.prix_achat) for p in produits)
        c1, c2, c3, c4 = st.columns(4)
        c1.metric("Produits actifs",     len(produits))
        c2.metric("Valorisation totale", f"{total_val:,.0f} MRU")
        c3.metric("🔴 Ruptures",
                  len([p for p in produits if p.stock == 0]))
        c4.metric("🟡 Stocks faibles",
                  len([p for p in produits if 0 < p.stock <= p.stock_minimum]))

        st.divider()
        render_dataframe(df)

    # ── Mouvements ────────────────────────────────────────────────────────
    with tab_mouv:
        mouvs = session.scalars(
            select(MouvementStock).order_by(MouvementStock.date.desc()).limit(200)
        ).all()
        if mouvs:
            df_m = pd.DataFrame([{
                "Date":      m.date.strftime("%d/%m/%Y %H:%M") if m.date else "—",
                "Produit":   m.code_produit,
                "Type":      "📥 Entrée" if m.type == "Entrée" else "📤 Sortie",
                "Quantité":  m.quantite,
                "Référence": m.reference or "—",
            } for m in mouvs])
            st.caption(f"{len(mouvs)} derniers mouvements")
            render_dataframe(df_m)
        else:
            st.info("Aucun mouvement de stock enregistré.")

    # ── Ajustement manuel ─────────────────────────────────────────────────
    with tab_ajust:
        st.subheader("Ajustement manuel du stock")
        st.info("💡 Utilisez cet onglet pour corriger un stock après inventaire.")

        produits = session.scalars(
            select(Produit).where(Produit.statut == "Actif").order_by(Produit.designation)
        ).all()
        if not produits:
            st.warning("Aucun produit actif.")
        else:
            with st.form("ajust_stock", clear_on_submit=True):
                code = st.selectbox(
                    "Produit *",
                    [p.code_produit for p in produits],
                    format_func=lambda x: next(
                        f"{p.code_produit} — {p.designation} (stock actuel: {p.stock})"
                        for p in produits if p.code_produit == x
                    ),
                    key="ajust_prod_select",
                )
                c1, c2 = st.columns(2)
                type_mvt = c1.selectbox("Type mouvement", ["Entrée", "Sortie"])
                qte      = c2.number_input("Quantité *", min_value=1, value=1, step=1)
                motif    = st.text_input(
                    "Motif / Référence *",
                    placeholder="Inventaire juin 2025, Casse, Retour fournisseur..."
                )
                submitted = st.form_submit_button("💾 Enregistrer l'ajustement", type="primary")

            if submitted:
                if not motif.strip():
                    st.error("❌ Le motif est obligatoire pour tracer l'ajustement.")
                else:
                    try:
                        mouvement_stock(
                            session, code, type_mvt, int(qte),
                            f"Ajust-{motif[:30]}", user.id_user,
                        )
                        session.commit()
                        p_obj = session.get(Produit, code)
                        st.toast(
                            f"✅ Ajustement enregistré — "
                            f"**{p_obj.designation}** : stock now **{p_obj.stock}**",
                            icon="✅",
                        )
                        st.rerun()
                    except ValueError as e:
                        st.error(f"❌ Erreur : {e}")

    # ── Alertes ───────────────────────────────────────────────────────────
    with tab_alertes:
        faibles = session.scalars(
            select(Produit).where(
                Produit.stock <= Produit.stock_minimum, Produit.stock > 0
            ).order_by(Produit.stock)
        ).all()
        rupture = session.scalars(
            select(Produit).where(Produit.stock == 0).order_by(Produit.designation)
        ).all()

        if not faibles and not rupture:
            st.success("✅ Aucune alerte — tous les stocks sont corrects.")
        else:
            if rupture:
                st.error(f"🔴 **{len(rupture)} produit(s) en rupture totale**")
                render_dataframe(pd.DataFrame([{
                    "Code":        p.code_produit,
                    "Désignation": p.designation,
                    "Catégorie":   p.categorie,
                    "Emplacement": p.emplacement or "—",
                } for p in rupture]))

            if faibles:
                st.warning(f"🟡 **{len(faibles)} produit(s) en stock faible**")
                render_dataframe(pd.DataFrame([{
                    "Code":        p.code_produit,
                    "Désignation": p.designation,
                    "Stock":       p.stock,
                    "Minimum":     p.stock_minimum,
                    "Manquant":    p.stock_minimum - p.stock,
                } for p in faibles]))