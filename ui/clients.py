from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from database.models import Client, Commande, Credit, Vente
from services.logging_service import log_action
from utils.crud_ui import render_dataframe


def page_clients(session, user):
    st.header("👤 Gestion des Clients")
    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_hist = st.tabs(
        ["Liste", "Ajouter", "Modifier", "Supprimer", "Historique"]
    )

    def load_df():
        clients = session.scalars(select(Client).order_by(Client.id_client)).all()
        return pd.DataFrame(
            [
                {
                    "ID": c.id_client,
                    "Nom": c.nom_client,
                    "Type": c.type_client,
                    "Téléphone": c.telephone_client,
                    "Email": c.email,
                    "Statut": c.statut,
                }
                for c in clients
            ]
        )

    with tab_liste:
        c1, c2, c3 = st.columns(3)
        filtre_nom = c1.text_input("Filtrer par nom")
        filtre_tel = c2.text_input("Filtrer par téléphone")
        filtre_type = c3.selectbox("Type", ["Tous", "Particulier", "Entreprise"])
        df = load_df()
        if filtre_nom:
            df = df[df["Nom"].str.contains(filtre_nom, case=False, na=False)]
        if filtre_tel:
            df = df[df["Téléphone"].astype(str).str.contains(filtre_tel, na=False)]
        if filtre_type != "Tous":
            df = df[df["Type"] == filtre_type]
        render_dataframe(df)

    with tab_ajouter:
        with st.form("add_client"):
            nom = st.text_input("Nom client *")
            type_c = st.selectbox("Type", ["Particulier", "Entreprise"])
            tel = st.text_input("Téléphone")
            adresse = st.text_input("Adresse")
            email = st.text_input("Email")
            statut = st.selectbox("Statut", ["Actif", "Inactif"])
            if st.form_submit_button("Enregistrer", type="primary") and nom:
                session.add(
                    Client(
                        nom_client=nom,
                        type_client=type_c,
                        telephone_client=tel,
                        adresse=adresse,
                        email=email,
                        statut=statut,
                    )
                )
                log_action(session, user.id_user, f"Ajout client {nom}")
                session.commit()
                st.success("Client ajouté.")
                st.rerun()

    with tab_modifier:
        clients = session.scalars(select(Client)).all()
        if clients:
            cid = st.selectbox("Client", [c.id_client for c in clients], format_func=lambda i: next(c.nom_client for c in clients if c.id_client == i))
            c = session.get(Client, cid)
            with st.form("edit_client"):
                c.nom_client = st.text_input("Nom", value=c.nom_client)
                c.type_client = st.selectbox("Type", ["Particulier", "Entreprise"], index=0 if c.type_client == "Particulier" else 1)
                c.telephone_client = st.text_input("Téléphone", value=c.telephone_client or "")
                c.adresse = st.text_input("Adresse", value=c.adresse or "")
                c.email = st.text_input("Email", value=c.email or "")
                c.statut = st.selectbox("Statut", ["Actif", "Inactif"], index=0 if c.statut == "Actif" else 1)
                if st.form_submit_button("Mettre à jour", type="primary"):
                    log_action(session, user.id_user, f"Modification client {c.nom_client}")
                    session.commit()
                    st.success("Client mis à jour.")
                    st.rerun()

    with tab_supprimer:
        clients = session.scalars(select(Client)).all()
        if clients:
            cid = st.selectbox("Client à supprimer", [c.id_client for c in clients], format_func=lambda i: next(c.nom_client for c in clients if c.id_client == i))
            if st.button("Supprimer", type="primary"):
                c = session.get(Client, cid)
                log_action(session, user.id_user, f"Suppression client {c.nom_client}")
                session.delete(c)
                session.commit()
                st.success("Client supprimé.")
                st.rerun()

    with tab_hist:
        clients = session.scalars(select(Client)).all()
        if clients:
            cid = st.selectbox("Client", [c.id_client for c in clients], key="hist_client", format_func=lambda i: next(c.nom_client for c in clients if c.id_client == i))
            nb_cmd = session.scalar(select(func.count()).select_from(Commande).where(Commande.id_client == cid)) or 0
            total_achats = session.scalar(
                select(func.coalesce(func.sum(Vente.montant_total), 0)).where(Vente.id_client == cid)
            ) or Decimal(0)
            solde = session.scalar(
                select(func.coalesce(func.sum(Credit.montant_restant), 0)).where(
                    Credit.id_client == cid, Credit.statut == "Ouvert"
                )
            ) or Decimal(0)
            c1, c2, c3 = st.columns(3)
            c1.metric("Commandes", nb_cmd)
            c2.metric("Total achats", f"{total_achats:.2f}")
            c3.metric("Solde crédit", f"{solde:.2f}")
