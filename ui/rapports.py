from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database.models import (
    Achat, Client, Credit, Fournisseur,
    LigneVente, Parametre, Produit, Vente,
)
from utils.ui import page_header


def _get_devise(session) -> str:
    p = session.query(Parametre).filter(Parametre.cle == "devise").first()
    return p.valeur if p and p.valeur else "MRU"


def _fmt(val, devise: str) -> str:
    return f"{float(val):,.0f} {devise}"


def page_rapports(session, user):
    page_header("Rapports & Analyses", "Ventes, achats, stock, crédits et rentabilité", "📈")
    devise = _get_devise(session)

    tab_ventes, tab_achats, tab_stock, tab_credits, tab_rentabilite = st.tabs([
        "💰 Ventes", "🛒 Achats", "📦 Stock", "💳 Crédits", "📊 Rentabilité",
    ])

    # ------------------------------------------------------------------ #
    # TAB 1 : RAPPORT VENTES
    # ------------------------------------------------------------------ #
    with tab_ventes:
        st.subheader("Rapport des Ventes")

        col_f1, col_f2, col_f3 = st.columns(3)
        date_debut = col_f1.date_input(
            "Date début", value=datetime.now().date().replace(day=1)
        )
        date_fin   = col_f2.date_input("Date fin", value=datetime.now().date())

        # Filtre client
        clients = session.scalars(select(Client).order_by(Client.nom_client)).all()
        client_choix = col_f3.selectbox(
            "Client", ["Tous"] + [c.nom_client for c in clients], key="rpt_vente_cli"
        )

        query = (
            select(Vente)
            .options(joinedload(Vente.client))
            .where(func.date(Vente.date) >= date_debut, func.date(Vente.date) <= date_fin)
            .order_by(Vente.date.desc())
        )
        if client_choix != "Tous":
            c_sel = next((c for c in clients if c.nom_client == client_choix), None)
            if c_sel:
                query = query.where(Vente.id_client == c_sel.id_client)

        ventes = session.scalars(query).unique().all()

        if ventes:
            # Métriques synthèse
            total_ttc  = sum(float(v.montant_total) for v in ventes)
            total_ht   = sum(float(v.montant_ht) for v in ventes)
            total_tva  = sum(float(v.tva) for v in ventes)
            nb_ventes  = len(ventes)
            panier_moy = total_ttc / nb_ventes if nb_ventes else 0

            m1, m2, m3, m4, m5 = st.columns(5)
            m1.metric("Nb ventes", nb_ventes)
            m2.metric("CA HT", _fmt(total_ht, devise))
            m3.metric("TVA collectée", _fmt(total_tva, devise))
            m4.metric("CA TTC", _fmt(total_ttc, devise))
            m5.metric("Panier moyen", _fmt(panier_moy, devise))

            st.divider()

            # Graphique évolution
            df_v = pd.DataFrame([
                {"date": v.date.date(), "TTC": float(v.montant_total)}
                for v in ventes
            ]).groupby("date", as_index=False)["TTC"].sum()
            fig = px.area(
                df_v, x="date", y="TTC",
                title="Évolution du CA sur la période",
                labels={"TTC": devise, "date": ""},
                color_discrete_sequence=["#4f9cf9"],
            )
            st.plotly_chart(fig, use_container_width=True)

            # Tableau détaillé
            st.subheader("Détail des ventes")
            df_table = pd.DataFrame([
                {
                    "Facture":   v.numero_facture or f"#{v.id_vente}",
                    "Date":      v.date.strftime("%d/%m/%Y %H:%M"),
                    "Client":    v.client.nom_client if v.client else "Comptant",
                    "HT":        f"{float(v.montant_ht):,.0f}",
                    "Remise":    f"{float(v.remise):,.0f}",
                    "TVA":       f"{float(v.tva):,.0f}",
                    "TTC":       f"{float(v.montant_total):,.0f}",
                    "Mode":      v.mode_paiement,
                    "Statut":    v.statut,
                }
                for v in ventes
            ])
            st.dataframe(df_table, hide_index=True, use_container_width=True)

            # Export Excel
            buf = _to_excel(df_table)
            st.download_button(
                "📥 Exporter Excel",
                data=buf,
                file_name=f"rapport_ventes_{date_debut}_{date_fin}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Aucune vente sur cette période.")

    # ------------------------------------------------------------------ #
    # TAB 2 : RAPPORT ACHATS
    # ------------------------------------------------------------------ #
    with tab_achats:
        st.subheader("Rapport des Achats")

        col_f1, col_f2, col_f3 = st.columns(3)
        date_debut_a = col_f1.date_input(
            "Date début", value=datetime.now().date().replace(day=1), key="rpt_ach_d1"
        )
        date_fin_a   = col_f2.date_input(
            "Date fin", value=datetime.now().date(), key="rpt_ach_d2"
        )
        fournisseurs = session.scalars(select(Fournisseur).order_by(Fournisseur.raison_sociale)).all()
        fourn_choix  = col_f3.selectbox(
            "Fournisseur", ["Tous"] + [f.raison_sociale for f in fournisseurs],
            key="rpt_ach_f"
        )

        query_a = (
            select(Achat)
            .options(joinedload(Achat.fournisseur))
            .where(
                func.date(Achat.date) >= date_debut_a,
                func.date(Achat.date) <= date_fin_a,
                Achat.annule == False,
            )
            .order_by(Achat.date.desc())
        )
        if fourn_choix != "Tous":
            f_sel = next((f for f in fournisseurs if f.raison_sociale == fourn_choix), None)
            if f_sel:
                query_a = query_a.where(Achat.id_fournisseur == f_sel.id_fournisseur)

        achats = session.scalars(query_a).unique().all()

        if achats:
            total_a  = sum(float(a.montant_total) for a in achats)
            nb_a     = len(achats)

            m1, m2 = st.columns(2)
            m1.metric("Nb achats", nb_a)
            m2.metric("Total achats", _fmt(total_a, devise))

            df_a = pd.DataFrame([
                {
                    "N° Achat":   a.id_achat,
                    "Date":       a.date.strftime("%d/%m/%Y"),
                    "Fournisseur": a.fournisseur.raison_sociale if a.fournisseur else "—",
                    "Montant":    f"{float(a.montant_total):,.0f}",
                    "Mode":       a.mode_paiement,
                    "Statut":     a.statut,
                }
                for a in achats
            ])
            st.dataframe(df_a, hide_index=True, use_container_width=True)

            buf = _to_excel(df_a)
            st.download_button(
                "📥 Exporter Excel", data=buf,
                file_name=f"rapport_achats_{date_debut_a}_{date_fin_a}.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Aucun achat sur cette période.")

    # ------------------------------------------------------------------ #
    # TAB 3 : RAPPORT STOCK
    # ------------------------------------------------------------------ #
    with tab_stock:
        st.subheader("Rapport de Stock")

        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()

        if produits:
            df_stock = pd.DataFrame([
                {
                    "Code":          p.code_produit,
                    "Désignation":   p.designation,
                    "Catégorie":     p.categorie,
                    "Unité":         p.unite,
                    "Stock actuel":  p.stock,
                    "Stock min":     p.stock_minimum,
                    "P. Achat":      float(p.prix_achat),
                    "P. Vente":      float(p.prix_vente),
                    "Marge":         float(p.marge),
                    "Valorisation":  float(p.stock * p.prix_achat),
                    "Statut stock":  (
                        "🔴 Rupture" if p.stock == 0
                        else ("🟡 Faible" if p.stock <= p.stock_minimum else "🟢 OK")
                    ),
                }
                for p in produits
            ])

            total_val = df_stock["Valorisation"].sum()
            nb_rupture = len([p for p in produits if p.stock == 0])
            nb_faible  = len([p for p in produits if 0 < p.stock <= p.stock_minimum])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Produits actifs", len(produits))
            m2.metric("Valorisation totale", _fmt(total_val, devise))
            m3.metric("🔴 Ruptures", nb_rupture)
            m4.metric("🟡 Stocks faibles", nb_faible)

            st.divider()

            # Filtre catégorie
            cats = ["Toutes"] + sorted(df_stock["Catégorie"].unique().tolist())
            cat_sel = st.selectbox("Filtrer par catégorie", cats, key="rpt_stock_cat")
            df_show = df_stock if cat_sel == "Toutes" else df_stock[df_stock["Catégorie"] == cat_sel]
            st.dataframe(df_show, hide_index=True, use_container_width=True)

            # Graphique valorisation par catégorie
            df_val_cat = df_stock.groupby("Catégorie")["Valorisation"].sum().reset_index()
            fig_val = px.bar(
                df_val_cat.sort_values("Valorisation", ascending=False),
                x="Catégorie", y="Valorisation",
                title="Valorisation du stock par catégorie",
                labels={"Valorisation": devise},
                color="Catégorie",
            )
            st.plotly_chart(fig_val, use_container_width=True)

            buf = _to_excel(df_show)
            st.download_button(
                "📥 Exporter Excel", data=buf,
                file_name="rapport_stock.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Aucun produit actif.")

    # ------------------------------------------------------------------ #
    # TAB 4 : RAPPORT CRÉDITS
    # ------------------------------------------------------------------ #
    with tab_credits:
        st.subheader("Rapport des Crédits Clients")

        credits = session.scalars(
            select(Credit)
            .options(joinedload(Credit.client))
            .order_by(Credit.id_credit.desc())
        ).unique().all()

        if credits:
            total_du    = sum(float(c.montant_restant) for c in credits if c.statut == "Ouvert")
            total_solde = sum(float(c.montant) for c in credits if c.statut == "Soldé")
            nb_ouverts  = len([c for c in credits if c.statut == "Ouvert"])
            nb_echus    = len([
                c for c in credits
                if c.statut == "Ouvert" and c.date_echeance
                and c.date_echeance < datetime.now().date()
            ])

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Total dû", _fmt(total_du, devise))
            m2.metric("Total soldé", _fmt(total_solde, devise))
            m3.metric("Crédits ouverts", nb_ouverts)
            m4.metric("🔴 Échus", nb_echus)

            df_cr = pd.DataFrame([
                {
                    "N° Crédit":    c.id_credit,
                    "Client":       c.client.nom_client if c.client else "—",
                    "Montant":      f"{float(c.montant):,.0f}",
                    "Restant":      f"{float(c.montant_restant):,.0f}",
                    "Échéance":     c.date_echeance.strftime("%d/%m/%Y") if c.date_echeance else "—",
                    "Statut":       "🟢 Soldé" if c.statut == "Soldé" else "🟠 Ouvert",
                }
                for c in credits
            ])
            st.dataframe(df_cr, hide_index=True, use_container_width=True)

            buf = _to_excel(df_cr)
            st.download_button(
                "📥 Exporter Excel", data=buf,
                file_name="rapport_credits.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
            )
        else:
            st.info("Aucun crédit enregistré.")

    # ------------------------------------------------------------------ #
    # TAB 5 : RENTABILITÉ
    # ------------------------------------------------------------------ #
    with tab_rentabilite:
        st.subheader("Analyse de Rentabilité")

        col_f1, col_f2 = st.columns(2)
        date_debut_r = col_f1.date_input(
            "Date début", value=(datetime.now() - timedelta(days=180)).date(),
            key="rpt_rent_d1"
        )
        date_fin_r = col_f2.date_input(
            "Date fin", value=datetime.now().date(), key="rpt_rent_d2"
        )

        ventes_r = session.scalars(
            select(Vente).where(
                func.date(Vente.date) >= date_debut_r,
                func.date(Vente.date) <= date_fin_r,
            )
        ).all()
        achats_r = session.scalars(
            select(Achat).where(
                func.date(Achat.date) >= date_debut_r,
                func.date(Achat.date) <= date_fin_r,
                Achat.annule == False,
            )
        ).all()

        if ventes_r or achats_r:
            ca    = sum(float(v.montant_total) for v in ventes_r)
            couts = sum(float(a.montant_total) for a in achats_r)
            profit = ca - couts
            marge_pct = (profit / ca * 100) if ca > 0 else 0

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("CA TTC", _fmt(ca, devise))
            m2.metric("Coûts achats", _fmt(couts, devise))
            m3.metric("Profit brut", _fmt(profit, devise))
            m4.metric("Marge brute", f"{marge_pct:.1f} %")

            st.divider()

            # Graphique mensuel CA / Achats / Profit
            if ventes_r and achats_r:
                df_vm = pd.DataFrame([
                    {"mois": v.date.strftime("%Y-%m"), "ca": float(v.montant_total)}
                    for v in ventes_r
                ]).groupby("mois")["ca"].sum()

                df_am = pd.DataFrame([
                    {"mois": a.date.strftime("%Y-%m"), "couts": float(a.montant_total)}
                    for a in achats_r
                ]).groupby("mois")["couts"].sum()

                mois_list = sorted(set(df_vm.index) | set(df_am.index))
                combo = pd.DataFrame({
                    "Mois":   mois_list,
                    "CA":     [df_vm.get(m, 0) for m in mois_list],
                    "Achats": [df_am.get(m, 0) for m in mois_list],
                })
                combo["Profit"] = combo["CA"] - combo["Achats"]

                fig_combo = px.bar(
                    combo.melt("Mois", var_name="Indicateur", value_name="Montant"),
                    x="Mois", y="Montant", color="Indicateur",
                    barmode="group",
                    title="CA · Achats · Profit par mois",
                    labels={"Montant": devise},
                    color_discrete_map={
                        "CA":     "#4f9cf9",
                        "Achats": "#EF9F27",
                        "Profit": "#1D9E75",
                    },
                )
                st.plotly_chart(fig_combo, use_container_width=True)

            # Rentabilité par produit (marge)
            st.subheader("Marge par produit (top 15)")
            lignes_all = session.scalars(
                select(LigneVente).where(
                    LigneVente.id_vente.in_([v.id_vente for v in ventes_r])
                )
            ).all()
            if lignes_all:
                prods_map = {
                    p.code_produit: {"designation": p.designation, "prix_achat": float(p.prix_achat)}
                    for p in session.scalars(select(Produit)).all()
                }
                rows = []
                for l in lignes_all:
                    info = prods_map.get(l.code_produit, {})
                    ca_ligne = float(l.total)
                    cout_ligne = info.get("prix_achat", 0) * l.quantite
                    rows.append({
                        "code": l.code_produit,
                        "designation": info.get("designation", l.code_produit),
                        "ca": ca_ligne,
                        "cout": cout_ligne,
                        "marge": ca_ligne - cout_ligne,
                    })
                df_prod_marge = (
                    pd.DataFrame(rows)
                    .groupby(["code", "designation"])[["ca", "cout", "marge"]]
                    .sum()
                    .reset_index()
                    .sort_values("marge", ascending=False)
                    .head(15)
                )
                df_prod_marge["marge_%"] = (
                    df_prod_marge["marge"] / df_prod_marge["ca"] * 100
                ).round(1)

                fig_pm = px.bar(
                    df_prod_marge, x="marge", y="designation", orientation="h",
                    title="Marge brute par produit",
                    labels={"marge": devise, "designation": ""},
                    color="marge_%",
                    color_continuous_scale="RdYlGn",
                )
                fig_pm.update_layout(yaxis={"autorange": "reversed"})
                st.plotly_chart(fig_pm, use_container_width=True)
        else:
            st.info("Aucune donnée sur cette période.")


# ── Utilitaire export Excel ──────────────────────────────────────────────
def _to_excel(df: pd.DataFrame) -> bytes:
    import io
    buf = io.BytesIO()
    with pd.ExcelWriter(buf, engine="openpyxl") as writer:
        df.to_excel(writer, index=False, sheet_name="Rapport")
    return buf.getvalue()