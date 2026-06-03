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
    st.markdown("---")
    
    tab_debiteurs, tab_encaissements, tab_hist, tab_modifier = st.tabs(
        ["👥 Clients Débiteurs", "💰 Enregistrer un Encaissement", "📜 Historique des Crédits", "✏️ Reporter l'Échéance"]
    )

    # ----------------------------------------------------
    # TAB 1 : CLIENTS DÉBITEURS
    # ----------------------------------------------------
    with tab_debiteurs:
        st.subheader("Situation globale des encours")
        
        # Alerte préventive pour les retards de paiement
        alertes = session.scalars(
            select(Credit).where(Credit.statut == "Ouvert", Credit.date_echeance < date.today())
        ).all()
        if alertes:
            st.error(f"⚠️ Alerte : {len(alertes)} dossier(s) de crédit ont dépassé leur date d'échéance sans être soldés !")

        rows = session.execute(
            select(Client.nom_client, func.sum(Credit.montant_restant).label("du"))
            .join(Credit)
            .where(Credit.statut == "Ouvert")
            .group_by(Client.id_client, Client.nom_client)
        ).all()
        
        if rows:
            df = pd.DataFrame([{"Nom du Client": r[0], "Total Restant Dû (€)": float(r[1])} for r in rows])
            render_dataframe(df)
        else:
            st.success("🎉 Parfait ! Aucun client n'a de dette ou de crédit ouvert actuellement.")

    # ----------------------------------------------------
    # TAB 2 : ENCAISSEMENTS
    # ----------------------------------------------------
    with tab_encaissements:
        credits_ouverts = session.scalars(
            select(Credit).options(joinedload(Credit.client)).where(Credit.statut == "Ouvert")
        ).unique().all()
        
        if credits_ouverts:
            st.subheader("Saisie d'un versement client")
            
            with st.container(border=True):
                cid = st.selectbox(
                    "Sélectionner le dossier de crédit",
                    [c.id_credit for c in credits_ouverts],
                    format_func=lambda i: next(
                        f"Ref #{c.id_credit} — {c.client.nom_client} (Reste : {c.montant_restant:.2f} €)"
                        for c in credits_ouverts if c.id_credit == i
                    ),
                    key="key_credits_encaissement_select_id"
                )
                cr = session.get(Credit, cid)
                
                # Input bridé dynamiquement entre 0.01 et le montant exact restant dû
                montant = st.number_input(
                    "Montant encaissé (€)", 
                    min_value=0.01, 
                    max_value=float(cr.montant_restant), 
                    step=0.01,
                    key="key_credits_encaissement_montant_input"
                )
                
                st.write("")
                btn_payer = st.button("💵 Enregistrer le versement", type="primary", use_container_width=True, key="key_credits_btn_valider_paiement")
                
            if btn_payer:
                m = Decimal(str(montant))
                session.add(PaiementCredit(id_credit=cid, montant=m))
                
                cr.montant_restant -= m
                if cr.montant_restant <= 0:
                    cr.montant_restant = Decimal(0)
                    cr.statut = "Soldé"
                    if cr.vente:
                        cr.vente.statut = "Payée"
                        
                log_action(session, user.id_user, f"Paiement crédit #{cid}: {m} €")
                session.commit()
                st.toast(f"Versement de {m:.2f} € enregistré sur le crédit #{cid}.", icon="✅")
                st.rerun()
        else:
            st.info("Aucun crédit actif trouvé. Tous les comptes sont à jour.")

    # ----------------------------------------------------
    # TAB 3 : HISTORIQUE
    # ----------------------------------------------------
    with tab_hist:
        credits_all = session.scalars(
            select(Credit).options(joinedload(Credit.client)).order_by(Credit.id_credit.desc())
        ).unique().all()
        
        if credits_all:
            st.subheader("Registre complet des encours")
            df = pd.DataFrame(
                [
                    {
                        "N° Crédit": c.id_credit,
                        "Nom du Client": c.client.nom_client if c.client else f"Client #{c.id_client}",
                        "Montant Initial (€)": float(c.montant),
                        "Reste à Payer (€)": float(c.montant_restant),
                        "Date Échéance": c.date_echeance.strftime("%d/%m/%Y") if c.date_echeance else "N/A",
                        "Statut": "🟢 Soldé" if c.statut == "Soldé" else "🟠 Ouvert",
                    }
                    for c in credits_all
                ]
            )
            render_dataframe(df)
        else:
            st.info("Aucun historique de crédit disponible.")

    # ----------------------------------------------------
    # TAB 4 : MODIFIER (REPORTER L'ÉCHÉANCE)
    # ----------------------------------------------------
    with tab_modifier:
        credits_mod = session.scalars(
            select(Credit).options(joinedload(Credit.client)).where(Credit.statut == "Ouvert")
        ).unique().all()
        
        if credits_mod:
            st.subheader("Avenant ou report de date limite")
            
            cid = st.selectbox(
                "Sélectionner le crédit à modifier", 
                [c.id_credit for c in credits_mod],
                format_func=lambda i: next(
                    f"Ref #{c.id_credit} — {c.client.nom_client}"
                    for c in credits_mod if c.id_credit == i
                ),
                key="key_credits_modifier_select_id"
            )
            cr = session.get(Credit, cid)
            
            new_echeance = st.date_input(
                "Nouvelle date d'échéance accordée", 
                value=cr.date_echeance or date.today(),
                key="key_credits_modifier_date_input"
            )
            
            if st.button("💾 Enregistrer le report d'échéance", type="primary", key="key_credits_btn_sauver_echeance"):
                cr.date_echeance = new_echeance
                log_action(session, user.id_user, f"Report échéance crédit #{cid} au {new_echeance}")
                session.commit()
                st.toast(f"La date d'échéance pour le dossier #{cid} a été repoussée.", icon="💾")
                st.rerun()
        else:
            st.info("Aucun crédit actif n'est éligible pour une modification de planning.")