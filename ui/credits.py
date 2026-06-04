from datetime import date
from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database.models import Client, Credit, PaiementCredit
from services.logging_service import log_action
from utils.crud_ui import render_dataframe


def page_credits(session, user):
    st.title("💳 Gestion des Crédits Clients")

    tab_debiteurs, tab_encaissements, tab_hist, tab_modifier = st.tabs([
        "👥 Clients Débiteurs",
        "💰 Enregistrer un Encaissement",
        "📜 Historique",
        "✏️ Reporter l'Échéance",
    ])

    # ── Débiteurs ─────────────────────────────────────────────────────────
    with tab_debiteurs:
        alertes = session.scalars(
            select(Credit).where(Credit.statut == "Ouvert", Credit.date_echeance < date.today())
        ).all()
        if alertes:
            st.error(
                f"⚠️ **{len(alertes)} dossier(s)** ont dépassé leur date d'échéance !"
            )

        rows = session.execute(
            select(Client.nom_client, func.sum(Credit.montant_restant).label("du"))
            .join(Credit)
            .where(Credit.statut == "Ouvert")
            .group_by(Client.id_client, Client.nom_client)
        ).all()

        if rows:
            total_du = sum(float(r[1]) for r in rows)
            st.metric("Total des créances ouvertes", f"{total_du:,.0f} MRU")
            st.divider()
            df = pd.DataFrame([{
                "Client":           r[0],
                "Total restant dû": f"{float(r[1]):,.0f} MRU",
            } for r in rows])
            render_dataframe(df)
        else:
            st.success("🎉 Aucun client débiteur — tous les comptes sont à jour !")

    # ── Encaissements ─────────────────────────────────────────────────────
    with tab_encaissements:
        credits_ouverts = session.scalars(
            select(Credit)
            .options(joinedload(Credit.client))
            .where(Credit.statut == "Ouvert")
        ).unique().all()

        if not credits_ouverts:
            st.info("Aucun crédit ouvert. Tous les comptes sont soldés.")
        else:
            st.subheader("Saisie d'un versement client")
            with st.container(border=True):
                cid = st.selectbox(
                    "Sélectionner le dossier de crédit",
                    [c.id_credit for c in credits_ouverts],
                    format_func=lambda i: next(
                        f"#{c.id_credit} — {c.client.nom_client} "
                        f"(Reste : {float(c.montant_restant):,.0f} MRU)"
                        for c in credits_ouverts if c.id_credit == i
                    ),
                    key="encaiss_select",
                )
                cr = session.get(Credit, cid)
                montant = st.number_input(
                    "Montant encaissé (MRU)",
                    min_value=0.01,
                    max_value=float(cr.montant_restant),
                    step=100.0,
                    key="encaiss_montant",
                )
                st.caption(
                    f"Reste après versement : "
                    f"**{float(cr.montant_restant) - montant:,.0f} MRU**"
                )
                btn = st.button(
                    "💵 Enregistrer le versement",
                    type="primary",
                    use_container_width=True,
                    key="encaiss_btn",
                )

            if btn:
                m = Decimal(str(montant))
                session.add(PaiementCredit(id_credit=cid, montant=m))
                cr.montant_restant -= m
                if cr.montant_restant <= 0:
                    cr.montant_restant = Decimal(0)
                    cr.statut = "Soldé"
                    if cr.vente:
                        cr.vente.statut = "Payée"
                    log_action(session, user.id_user,
                               f"Crédit #{cid} soldé — {cr.client.nom_client}")
                    session.commit()
                    st.toast(
                        f"✅ Crédit **#{cid}** soldé intégralement ! "
                        f"Compte de {cr.client.nom_client} apuré.",
                        icon="✅",
                    )
                else:
                    log_action(session, user.id_user,
                               f"Paiement partiel crédit #{cid} : {float(m):,.0f} MRU")
                    session.commit()
                    st.toast(
                        f"💰 Versement de **{float(m):,.0f} MRU** enregistré. "
                        f"Reste : **{float(cr.montant_restant):,.0f} MRU**",
                        icon="💰",
                    )
                st.rerun()

    # ── Historique ────────────────────────────────────────────────────────
    with tab_hist:
        credits_all = session.scalars(
            select(Credit)
            .options(joinedload(Credit.client))
            .order_by(Credit.id_credit.desc())
        ).unique().all()

        if credits_all:
            total_du    = sum(float(c.montant_restant) for c in credits_all if c.statut == "Ouvert")
            total_solde = sum(float(c.montant)         for c in credits_all if c.statut == "Soldé")
            m1, m2, m3 = st.columns(3)
            m1.metric("Créances ouvertes", f"{total_du:,.0f} MRU")
            m2.metric("Total soldé",       f"{total_solde:,.0f} MRU")
            m3.metric("Nb crédits",        len(credits_all))
            st.divider()
            df = pd.DataFrame([{
                "N° Crédit": c.id_credit,
                "Client":    c.client.nom_client if c.client else "—",
                "Montant":   f"{float(c.montant):,.0f} MRU",
                "Restant":   f"{float(c.montant_restant):,.0f} MRU",
                "Échéance":  c.date_echeance.strftime("%d/%m/%Y") if c.date_echeance else "—",
                "Statut":    "🟢 Soldé" if c.statut == "Soldé" else "🟠 Ouvert",
            } for c in credits_all])
            render_dataframe(df)
        else:
            st.info("Aucun historique de crédit.")

    # ── Reporter l'échéance ───────────────────────────────────────────────
    with tab_modifier:
        credits_mod = session.scalars(
            select(Credit)
            .options(joinedload(Credit.client))
            .where(Credit.statut == "Ouvert")
        ).unique().all()

        if not credits_mod:
            st.info("Aucun crédit ouvert à modifier.")
        else:
            st.subheader("Report de date d'échéance")
            cid = st.selectbox(
                "Sélectionner le crédit",
                [c.id_credit for c in credits_mod],
                format_func=lambda i: next(
                    f"#{c.id_credit} — {c.client.nom_client} "
                    f"(Reste: {float(c.montant_restant):,.0f} MRU)"
                    for c in credits_mod if c.id_credit == i
                ),
                key="report_select",
            )
            cr = session.get(Credit, cid)
            st.info(
                f"Échéance actuelle : "
                f"**{cr.date_echeance.strftime('%d/%m/%Y') if cr.date_echeance else 'Non définie'}**"
            )
            new_echeance = st.date_input(
                "Nouvelle date d'échéance",
                value=cr.date_echeance or date.today(),
                key="report_date",
            )
            if st.button("💾 Enregistrer le report", type="primary", key="report_btn"):
                ancienne = cr.date_echeance
                cr.date_echeance = new_echeance
                log_action(
                    session, user.id_user,
                    f"Report échéance crédit #{cid} : {ancienne} → {new_echeance}"
                )
                session.commit()
                st.toast(
                    f"✅ Échéance du crédit **#{cid}** reportée au "
                    f"**{new_echeance.strftime('%d/%m/%Y')}**.",
                    icon="✅",
                )
                st.rerun()