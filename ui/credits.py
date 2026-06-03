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
    st.header("💳 Gestion des Crédits")
    tab_debiteurs, tab_encaissements, tab_hist, tab_modifier = st.tabs(
        ["Clients Débiteurs", "Encaissements", "Historique", "Modifier"]
    )

    with tab_debiteurs:
        rows = session.execute(
            select(Client.nom_client, func.sum(Credit.montant_restant).label("du"))
            .join(Credit)
            .where(Credit.statut == "Ouvert")
            .group_by(Client.id_client, Client.nom_client)
        ).all()
        df = pd.DataFrame([{"Client": r[0], "Montant dû": float(r[1])} for r in rows])
        render_dataframe(df)
        alertes = session.scalars(
            select(Credit).where(Credit.statut == "Ouvert", Credit.date_echeance < date.today())
        ).all()
        if alertes:
            st.error(f"⚠️ {len(alertes)} crédit(s) en retard d'échéance")

    with tab_encaissements:
        credits = session.scalars(
            select(Credit).options(joinedload(Credit.client)).where(Credit.statut == "Ouvert")
        ).unique().all()
        if credits:
            cid = st.selectbox(
                "Crédit",
                [c.id_credit for c in credits],
                format_func=lambda i: next(
                    f"{c.client.nom_client} — reste {c.montant_restant}" for c in credits if c.id_credit == i
                ),
            )
            cr = session.get(Credit, cid)
            montant = st.number_input("Montant encaissé", min_value=0.01, max_value=float(cr.montant_restant), step=0.01)
            if st.button("Enregistrer paiement", type="primary"):
                m = Decimal(str(montant))
                session.add(PaiementCredit(id_credit=cid, montant=m))
                cr.montant_restant -= m
                if cr.montant_restant <= 0:
                    cr.montant_restant = Decimal(0)
                    cr.statut = "Soldé"
                    if cr.vente:
                        cr.vente.statut = "Payée"
                log_action(session, user.id_user, f"Paiement crédit #{cid}: {m}")
                session.commit()
                st.success("Paiement enregistré.")
                st.rerun()

    with tab_hist:
        credits = session.scalars(select(Credit).order_by(Credit.id_credit.desc())).all()
        render_dataframe(
            pd.DataFrame(
                [
                    {
                        "ID": c.id_credit,
                        "Client": c.id_client,
                        "Montant": float(c.montant),
                        "Restant": float(c.montant_restant),
                        "Échéance": c.date_echeance,
                        "Statut": c.statut,
                    }
                    for c in credits
                ]
            )
        )

    with tab_modifier:
        credits = session.scalars(select(Credit).where(Credit.statut == "Ouvert")).all()
        if credits:
            cid = st.selectbox("Crédit", [c.id_credit for c in credits])
            cr = session.get(Credit, cid)
            new_echeance = st.date_input("Date échéance", value=cr.date_echeance or date.today())
            if st.button("Mettre à jour échéance", type="primary"):
                cr.date_echeance = new_echeance
                session.commit()
                st.success("Échéance mise à jour.")
