from datetime import datetime, timedelta
from decimal import Decimal

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select

from database.models import (
    Achat, Client, Fournisseur, LigneVente,
    Parametre, Produit, Vente,
)


def _get_devise(session) -> str:
    """Lit la devise depuis les paramètres (défaut MRU)."""
    p = session.query(Parametre).filter(Parametre.cle == "devise").first()
    return p.valeur if p and p.valeur else "MRU"


def _fmt(val, devise: str) -> str:
    return f"{float(val):,.0f} {devise}"


def page_dashboard(session, user):
    st.title("🏠 Tableau de bord — SGIQ")
    devise = _get_devise(session)

    today = datetime.now().date()
    month_start = today.replace(day=1)

    # ── Requêtes KPI ────────────────────────────────────────────────────
    ventes_jour = session.scalar(
        select(func.coalesce(func.sum(Vente.montant_total), 0))
        .where(func.date(Vente.date) == today)
    ) or Decimal(0)

    achats_jour = session.scalar(
        select(func.coalesce(func.sum(Achat.montant_total), 0))
        .where(func.date(Achat.date) == today, Achat.annule == False)
    ) or Decimal(0)

    ventes_mois = session.scalar(
        select(func.coalesce(func.sum(Vente.montant_total), 0))
        .where(Vente.date >= month_start)
    ) or Decimal(0)

    achats_mois = session.scalar(
        select(func.coalesce(func.sum(Achat.montant_total), 0))
        .where(Achat.date >= month_start, Achat.annule == False)
    ) or Decimal(0)

    nb_clients   = session.scalar(select(func.count()).select_from(Client)) or 0
    nb_fourn     = session.scalar(select(func.count()).select_from(Fournisseur)) or 0
    nb_prod      = session.scalar(select(func.count()).select_from(Produit)) or 0
    stock_total  = session.scalar(
        select(func.coalesce(func.sum(Produit.stock), 0))
    ) or 0

    faibles = session.scalars(
        select(Produit).where(Produit.stock <= Produit.stock_minimum, Produit.stock > 0)
    ).all()
    rupture = session.scalars(select(Produit).where(Produit.stock == 0)).all()

    # ── KPIs Aujourd'hui ─────────────────────────────────────────────────
    st.subheader("📅 Aujourd'hui")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("💰 Ventes", _fmt(ventes_jour, devise))
    c2.metric("🛒 Achats", _fmt(achats_jour, devise))
    c3.metric("📈 Bénéfice", _fmt(ventes_jour - achats_jour, devise))
    c4.metric(
        "🚨 Alertes stock",
        f"{len(rupture)} rupture · {len(faibles)} faible",
        delta=None,
    )

    st.divider()

    # ── KPIs Ce mois ─────────────────────────────────────────────────────
    st.subheader(f"🗓️ Ce mois — {today.strftime('%B %Y')}")
    c5, c6, c7, c8, c9, c10 = st.columns(6)
    c5.metric("CA", _fmt(ventes_mois, devise))
    c6.metric("Achats", _fmt(achats_mois, devise))
    c7.metric("Bénéfice", _fmt(ventes_mois - achats_mois, devise))
    c8.metric("👤 Clients", nb_clients)
    c9.metric("🏭 Fournisseurs", nb_fourn)
    c10.metric("📦 Produits", nb_prod)

    st.divider()

    # ── Période graphiques ───────────────────────────────────────────────
    periode = st.selectbox(
        "Période", ["30 jours", "90 jours", "6 mois", "1 an"],
        key="per_dashboard",
    )
    days_map = {"30 jours": 30, "90 jours": 90, "6 mois": 180, "1 an": 365}
    since = datetime.now() - timedelta(days=days_map[periode])

    ventes = session.scalars(select(Vente).where(Vente.date >= since)).all()
    achats_list = session.scalars(
        select(Achat).where(Achat.date >= since, Achat.annule == False)
    ).all()

    col_g, col_d = st.columns([2, 1])

    with col_g:
        if ventes:
            df_v = pd.DataFrame(
                [{"date": v.date.date(), "montant": float(v.montant_total)} for v in ventes]
            )
            df_v = df_v.groupby("date", as_index=False)["montant"].sum()
            fig = px.line(
                df_v, x="date", y="montant",
                title="📊 Évolution des ventes",
                labels={"montant": devise, "date": "Date"},
                color_discrete_sequence=["#4f9cf9"],
            )
            fig.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig, use_container_width=True)
        else:
            st.info("Aucune vente sur cette période.")

    with col_d:
        if ventes:
            df_pay = pd.DataFrame(
                [{"mode": v.mode_paiement, "m": float(v.montant_total)} for v in ventes]
            )
            pie = px.pie(
                df_pay.groupby("mode")["m"].sum().reset_index(),
                values="m", names="mode",
                title="💳 Répartition paiements",
                color_discrete_sequence=["#4f9cf9", "#EF9F27", "#1D9E75"],
            )
            pie.update_layout(margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(pie, use_container_width=True)

    st.divider()

    # ── Top produits + Top clients ────────────────────────────────────────
    col_tp, col_tc = st.columns(2)

    with col_tp:
        lignes = session.scalars(select(LigneVente)).all()
        if lignes:
            df_top = pd.DataFrame(
                [{"code": l.code_produit, "qte": l.quantite} for l in lignes]
            )
            top = df_top.groupby("code")["qte"].sum().nlargest(10).reset_index()
            # Joindre les désignations
            prods = {p.code_produit: p.designation for p in session.scalars(select(Produit)).all()}
            top["designation"] = top["code"].map(prods).fillna(top["code"])
            fig_tp = px.bar(
                top, x="qte", y="designation", orientation="h",
                title="🏆 Top 10 produits vendus",
                labels={"qte": "Quantité", "designation": "Produit"},
                color_discrete_sequence=["#4f9cf9"],
            )
            fig_tp.update_layout(yaxis={"autorange": "reversed"},
                                 margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_tp, use_container_width=True)

    with col_tc:
        ventes_c = session.scalars(
            select(Vente).where(Vente.id_client.isnot(None))
        ).all()
        if ventes_c:
            df_c = pd.DataFrame(
                [{"client": v.id_client, "ca": float(v.montant_total)} for v in ventes_c]
            )
            top_c = df_c.groupby("client")["ca"].sum().nlargest(10).reset_index()
            clients_map = {
                c.id_client: c.nom_client
                for c in session.scalars(select(Client)).all()
            }
            top_c["nom"] = top_c["client"].map(clients_map).fillna("Inconnu")
            fig_tc = px.bar(
                top_c, x="ca", y="nom", orientation="h",
                title="👥 Top clients (CA)",
                labels={"ca": devise, "nom": "Client"},
                color_discrete_sequence=["#1D9E75"],
            )
            fig_tc.update_layout(yaxis={"autorange": "reversed"},
                                 margin=dict(l=0, r=0, t=40, b=0))
            st.plotly_chart(fig_tc, use_container_width=True)

    st.divider()

    # ── Stock par catégorie + Marge ───────────────────────────────────────
    produits = session.scalars(select(Produit)).all()
    col_s, col_m = st.columns(2)

    with col_s:
        if produits:
            df_st = pd.DataFrame(
                [{"cat": p.categorie, "stock": p.stock} for p in produits]
            ).groupby("cat")["stock"].sum().reset_index()
            fig_tree = px.treemap(
                df_st, path=["cat"], values="stock",
                title="📦 Stock par catégorie",
                color_discrete_sequence=px.colors.qualitative.Pastel,
            )
            st.plotly_chart(fig_tree, use_container_width=True)

    with col_m:
        if produits:
            df_marge = pd.DataFrame(
                [{"produit": p.code_produit, "marge": float(p.marge)} for p in produits
                 if float(p.marge) != 0]
            )
            if not df_marge.empty:
                fig_marge = px.histogram(
                    df_marge, x="marge",
                    title="📊 Distribution des marges",
                    labels={"marge": devise},
                    color_discrete_sequence=["#EF9F27"],
                )
                st.plotly_chart(fig_marge, use_container_width=True)

    # ── Bénéfice mensuel combiné ──────────────────────────────────────────
    if ventes and achats_list:
        st.divider()
        st.subheader("📈 Bénéfice mensuel combiné")

        df_vm = pd.DataFrame(
            [{"mois": v.date.strftime("%Y-%m"), "ca": float(v.montant_total)} for v in ventes]
        )
        df_am = pd.DataFrame(
            [{"mois": a.date.strftime("%Y-%m"), "montant": float(a.montant_total)}
             for a in achats_list]
        )
        ca_m  = df_vm.groupby("mois")["ca"].sum()
        ach_m = df_am.groupby("mois")["montant"].sum()
        mois  = sorted(set(ca_m.index) | set(ach_m.index))

        combo = pd.DataFrame({
            "mois":   mois,
            "CA":     [ca_m.get(m, 0) for m in mois],
            "Achats": [ach_m.get(m, 0) for m in mois],
        })
        combo["Profit"] = combo["CA"] - combo["Achats"]

        chart = (
            alt.Chart(combo.melt("mois", var_name="indicateur", value_name="montant"))
            .mark_bar(cornerRadiusTopLeft=3, cornerRadiusTopRight=3)
            .encode(
                x=alt.X("mois:N", title="Mois"),
                y=alt.Y("montant:Q", title=devise),
                color=alt.Color(
                    "indicateur:N",
                    scale=alt.Scale(
                        domain=["CA", "Achats", "Profit"],
                        range=["#4f9cf9", "#EF9F27", "#1D9E75"],
                    ),
                ),
                xOffset="indicateur:N",
                tooltip=["mois", "indicateur", "montant"],
            )
            .properties(height=300)
        )
        st.altair_chart(chart, use_container_width=True)

    # ── Alertes stock ─────────────────────────────────────────────────────
    st.divider()
    col_f, col_r = st.columns(2)

    with col_f:
        st.subheader("🟡 Stock faible")
        if faibles:
            st.dataframe(
                pd.DataFrame([{
                    "Code": p.code_produit,
                    "Désignation": p.designation,
                    "Stock": p.stock,
                    "Min": p.stock_minimum,
                } for p in faibles]),
                hide_index=True, use_container_width=True,
            )
        else:
            st.success("Aucun produit en stock faible.")

    with col_r:
        st.subheader("🔴 Rupture de stock")
        if rupture:
            st.dataframe(
                pd.DataFrame([{
                    "Code": p.code_produit,
                    "Désignation": p.designation,
                } for p in rupture]),
                hide_index=True, use_container_width=True,
            )
        else:
            st.success("Aucune rupture de stock.")