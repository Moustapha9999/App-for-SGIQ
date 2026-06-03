from datetime import datetime, timedelta
from decimal import Decimal

import altair as alt
import pandas as pd
import plotly.express as px
import streamlit as st
from sqlalchemy import func, select

from database.models import Achat, Client, Fournisseur, LigneAchat, LigneVente, Produit, Vente


def page_dashboard(session, user):
    st.header("🏠 Tableau de bord — SGIQ")
    today = datetime.now().date()
    month_start = today.replace(day=1)

    ventes_jour = session.scalar(
        select(func.coalesce(func.sum(Vente.montant_total), 0)).where(func.date(Vente.date) == today)
    ) or Decimal(0)
    achats_jour = session.scalar(
        select(func.coalesce(func.sum(Achat.montant_total), 0)).where(
            func.date(Achat.date) == today, Achat.annule == False
        )
    ) or Decimal(0)
    ventes_mois = session.scalar(
        select(func.coalesce(func.sum(Vente.montant_total), 0)).where(Vente.date >= month_start)
    ) or Decimal(0)
    achats_mois = session.scalar(
        select(func.coalesce(func.sum(Achat.montant_total), 0)).where(
            Achat.date >= month_start, Achat.annule == False
        )
    ) or Decimal(0)

    nb_clients = session.scalar(select(func.count()).select_from(Client)) or 0
    nb_fourn = session.scalar(select(func.count()).select_from(Fournisseur)) or 0
    nb_prod = session.scalar(select(func.count()).select_from(Produit)) or 0
    stock_total = session.scalar(select(func.coalesce(func.sum(Produit.stock), 0))) or 0

    st.subheader("Aujourd'hui")
    c1, c2, c3 = st.columns(3)
    c1.metric("Ventes du jour", f"{ventes_jour:.2f}")
    c2.metric("Achats du jour", f"{achats_jour:.2f}")
    c3.metric("Bénéfice du jour", f"{(ventes_jour - achats_jour):.2f}")

    st.subheader("Ce mois")
    c4, c5, c6 = st.columns(3)
    c4.metric("Chiffre d'affaires", f"{ventes_mois:.2f}")
    c5.metric("Achats", f"{achats_mois:.2f}")
    c6.metric("Bénéfice", f"{(ventes_mois - achats_mois):.2f}")

    st.subheader("Général")
    c7, c8, c9, c10 = st.columns(4)
    c7.metric("Clients", nb_clients)
    c8.metric("Fournisseurs", nb_fourn)
    c9.metric("Produits", nb_prod)
    c10.metric("Stock total (unités)", stock_total)

    # Alertes
    faibles = session.scalars(select(Produit).where(Produit.stock <= Produit.stock_minimum, Produit.stock > 0)).all()
    rupture = session.scalars(select(Produit).where(Produit.stock == 0)).all()
    if faibles or rupture:
        st.warning(f"Alertes: {len(faibles)} stock faible, {len(rupture)} rupture")

    periode = st.selectbox("Période graphiques ventes/achats", ["Jour", "Semaine", "Mois", "Année"], key="per_dashboard")
    days_map = {"Jour": 30, "Semaine": 90, "Mois": 365, "Année": 730}
    since = datetime.now() - timedelta(days=days_map[periode])

    ventes = session.scalars(select(Vente).where(Vente.date >= since)).all()
    if ventes:
        df_v = pd.DataFrame([{"date": v.date.date(), "montant": float(v.montant_total)} for v in ventes])
        df_v = df_v.groupby("date", as_index=False)["montant"].sum()
        fig = px.line(df_v, x="date", y="montant", title="Évolution des ventes")
        st.plotly_chart(fig, use_container_width=True)

        df_pay = pd.DataFrame([{"mode": v.mode_paiement, "m": float(v.montant_total)} for v in ventes])
        if not df_pay.empty:
            pie = px.pie(df_pay.groupby("mode")["m"].sum().reset_index(), values="m", names="mode", title="Répartition paiements")
            st.plotly_chart(pie, use_container_width=True)

    # Top produits
    lignes = session.scalars(select(LigneVente)).all()
    if lignes:
        df_top = pd.DataFrame([{"code": l.code_produit, "qte": l.quantite} for l in lignes])
        top = df_top.groupby("code")["qte"].sum().nlargest(10).reset_index()
        st.plotly_chart(px.bar(top, x="code", y="qte", title="Top 10 produits vendus"), use_container_width=True)

    # Top clients
    ventes_c = session.scalars(select(Vente).where(Vente.id_client.isnot(None))).all()
    if ventes_c:
        df_c = pd.DataFrame([{"client": v.id_client, "ca": float(v.montant_total)} for v in ventes_c])
        top_c = df_c.groupby("client")["ca"].sum().nlargest(10).reset_index()
        clients = {c.id_client: c.nom_client for c in session.scalars(select(Client)).all()}
        top_c["nom"] = top_c["client"].map(clients)
        st.plotly_chart(px.bar(top_c, x="nom", y="ca", title="Top clients (CA)"), use_container_width=True)

    # Stock par catégorie treemap
    produits = session.scalars(select(Produit)).all()
    if produits:
        df_st = pd.DataFrame([{"cat": p.categorie, "stock": p.stock} for p in produits])
        df_st = df_st.groupby("cat")["stock"].sum().reset_index()
        st.plotly_chart(px.treemap(df_st, path=["cat"], values="stock", title="Stock par catégorie"), use_container_width=True)

        df_marge = pd.DataFrame([{"produit": p.code_produit, "marge": float(p.marge)} for p in produits])
        st.plotly_chart(px.histogram(df_marge, x="marge", title="Marge par produit"), use_container_width=True)

    # Bénéfice mensuel combiné
    achats = session.scalars(select(Achat).where(Achat.date >= since, Achat.annule == False)).all()
    if ventes and achats:
        df_vm = pd.DataFrame([{"mois": v.date.strftime("%Y-%m"), "ca": float(v.montant_total), "type": "Ventes"} for v in ventes])
        df_am = pd.DataFrame([{"mois": a.date.strftime("%Y-%m"), "montant": float(a.montant_total)} for a in achats])
        ca_m = df_vm.groupby("mois")["ca"].sum()
        ach_m = df_am.groupby("mois")["montant"].sum()
        mois = sorted(set(ca_m.index) | set(ach_m.index))
        combo = pd.DataFrame({
            "mois": mois,
            "CA": [ca_m.get(m, 0) for m in mois],
            "Achats": [ach_m.get(m, 0) for m in mois],
        })
        combo["Profit"] = combo["CA"] - combo["Achats"]
        st.altair_chart(
            alt.Chart(combo.melt("mois", var_name="indicateur", value_name="montant"))
            .mark_bar()
            .encode(x="mois:N", y="montant:Q", color="indicateur:N", column="indicateur:N"),
            use_container_width=True,
        )

    col1, col2 = st.columns(2)
    with col1:
        st.subheader("Produits stock faible")
        st.dataframe(
            pd.DataFrame([{"Code": p.code_produit, "Stock": p.stock, "Min": p.stock_minimum} for p in faibles]),
            hide_index=True,
        )
    with col2:
        st.subheader("Rupture")
        st.dataframe(
            pd.DataFrame([{"Code": p.code_produit, "Désignation": p.designation} for p in rupture]),
            hide_index=True,
        )
