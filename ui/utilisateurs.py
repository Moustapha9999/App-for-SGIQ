import streamlit as st
import pandas as pd
from sqlalchemy import select

from config import ROLES
from database.models import Utilisateur
from services.auth import hash_password
from services.logging_service import log_action
from utils.crud_ui import render_dataframe


def page_utilisateurs(session, user):
    st.header("👥 Gestion des Utilisateurs")
    tab_liste, tab_ajouter, tab_modifier, tab_supprimer = st.tabs(
        ["Liste", "Ajouter", "Modifier", "Supprimer"]
    )

    with tab_liste:
        users = session.scalars(select(Utilisateur).order_by(Utilisateur.id_user)).all()
        df = pd.DataFrame(
            [
                {
                    "ID": u.id_user,
                    "Nom": f"{u.nom} {u.prenom}",
                    "Username": u.username,
                    "Email": u.email,
                    "Rôle": u.role,
                    "Téléphone": u.telephone,
                    "Statut": u.statut,
                }
                for u in users
            ]
        )
        render_dataframe(df)

    with tab_ajouter:
        with st.form("add_user"):
            c1, c2 = st.columns(2)
            nom = c1.text_input("Nom *")
            prenom = c2.text_input("Prénom *")
            username = c1.text_input("Username *")
            email = c2.text_input("Email")
            password = c1.text_input("Mot de passe *", type="password")
            role = c2.selectbox("Rôle", ROLES)
            telephone = c1.text_input("Téléphone")
            statut = c2.selectbox("Statut", ["Actif", "Inactif"])
            if st.form_submit_button("Enregistrer", type="primary"):
                if not all([nom, prenom, username, password]):
                    st.error("Champs obligatoires manquants.")
                elif session.scalar(select(Utilisateur).where(Utilisateur.username == username)):
                    st.error("Username déjà utilisé.")
                else:
                    session.add(
                        Utilisateur(
                            nom=nom,
                            prenom=prenom,
                            username=username,
                            email=email,
                            mot_de_passe=hash_password(password),
                            role=role,
                            telephone=telephone,
                            statut=statut,
                        )
                    )
                    log_action(session, user.id_user, f"Ajout utilisateur {username}")
                    session.commit()
                    st.success("Utilisateur créé.")
                    st.rerun()

    with tab_modifier:
        users = session.scalars(select(Utilisateur)).all()
        if not users:
            st.info("Aucun utilisateur.")
        else:
            uid = st.selectbox(
                "Utilisateur",
                [u.id_user for u in users],
                format_func=lambda i: next(f"{u.username} — {u.nom}" for u in users if u.id_user == i),
            )
            u = session.get(Utilisateur, uid)
            with st.form("edit_user"):
                c1, c2 = st.columns(2)
                u.nom = c1.text_input("Nom", value=u.nom)
                u.prenom = c2.text_input("Prénom", value=u.prenom)
                u.email = c2.text_input("Email", value=u.email or "")
                u.role = c2.selectbox("Rôle", ROLES, index=ROLES.index(u.role) if u.role in ROLES else 0)
                u.telephone = c1.text_input("Téléphone", value=u.telephone or "")
                u.statut = c2.selectbox("Statut", ["Actif", "Inactif"], index=0 if u.statut == "Actif" else 1)
                new_pwd = c1.text_input("Nouveau mot de passe (vide = inchangé)", type="password")
                if st.form_submit_button("Mettre à jour", type="primary"):
                    if new_pwd:
                        u.mot_de_passe = hash_password(new_pwd)
                    log_action(session, user.id_user, f"Modification utilisateur {u.username}")
                    session.commit()
                    st.success("Utilisateur mis à jour.")
                    st.rerun()

    with tab_supprimer:
        users = session.scalars(select(Utilisateur).where(Utilisateur.id_user != user.id_user)).all()
        if not users:
            st.info("Aucun autre utilisateur à supprimer.")
        else:
            uid = st.selectbox(
                "Utilisateur à supprimer",
                [u.id_user for u in users],
                format_func=lambda i: next(u.username for u in users if u.id_user == i),
            )
            if st.button("Supprimer définitivement", type="primary"):
                u = session.get(Utilisateur, uid)
                log_action(session, user.id_user, f"Suppression utilisateur {u.username}")
                session.delete(u)
                session.commit()
                st.success("Utilisateur supprimé.")
                st.rerun()
