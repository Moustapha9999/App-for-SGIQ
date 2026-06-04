import pandas as pd
import streamlit as st
from sqlalchemy import select

from config import ROLES
from database.models import Utilisateur
from services.auth import hash_password
from services.logging_service import log_action
from utils.crud_ui import render_dataframe

ROLE_BADGES = {
    "ADMIN":       "🔴 Admin",
    "CAISSIER":    "🟡 Caissier",
    "MAGASINIER":  "🟢 Magasinier",
}


def page_utilisateurs(session, user):
    st.title("👥 Gestion des Utilisateurs")

    tab_liste, tab_ajouter, tab_modifier, tab_supprimer = st.tabs(
        ["📋 Liste", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer"]
    )

    # ── Liste ─────────────────────────────────────────────────────────────
    with tab_liste:
        users = session.scalars(select(Utilisateur).order_by(Utilisateur.id_user)).all()
        df = pd.DataFrame([{
            "ID":        u.id_user,
            "Nom":       f"{u.nom} {u.prenom}",
            "Username":  u.username,
            "Email":     u.email or "—",
            "Rôle":      ROLE_BADGES.get(u.role, u.role),
            "Téléphone": u.telephone or "—",
            "Statut":    u.statut,
        } for u in users])
        st.caption(f"{len(users)} utilisateur(s)")
        render_dataframe(df)

    # ── Ajouter ───────────────────────────────────────────────────────────
    with tab_ajouter:
        st.subheader("Nouvel utilisateur")
        with st.form("add_user", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom      = c1.text_input("Nom *",       placeholder="Diallo")
            prenom   = c2.text_input("Prénom *",    placeholder="Ibrahima")
            username = c1.text_input("Username *",  placeholder="ibrdiallo")
            email    = c2.text_input("Email",       placeholder="user@sgiq.sn")
            password = c1.text_input("Mot de passe *", type="password")
            role     = c2.selectbox("Rôle", ROLES)
            telephone = c1.text_input("Téléphone",  placeholder="77 000 00 00")
            statut   = c2.selectbox("Statut", ["Actif", "Inactif"])
            submitted = st.form_submit_button("💾 Créer l'utilisateur", type="primary")

        if submitted:
            if not all([nom, prenom, username, password]):
                st.error("❌ Les champs Nom, Prénom, Username et Mot de passe sont obligatoires.")
            elif session.scalar(select(Utilisateur).where(Utilisateur.username == username)):
                st.error(f"❌ Le username **{username}** est déjà utilisé.")
            else:
                session.add(Utilisateur(
                    nom=nom, prenom=prenom, username=username,
                    email=email or None,
                    mot_de_passe=hash_password(password),
                    role=role, telephone=telephone or None, statut=statut,
                ))
                log_action(session, user.id_user, f"Création utilisateur {username}")
                session.commit()
                st.toast(f"✅ Utilisateur **{username}** créé avec succès !", icon="✅")
                st.rerun()

    # ── Modifier ──────────────────────────────────────────────────────────
    with tab_modifier:
        users = session.scalars(select(Utilisateur).order_by(Utilisateur.username)).all()
        if not users:
            st.info("Aucun utilisateur à modifier.")
        else:
            uid = st.selectbox(
                "Sélectionner l'utilisateur",
                [u.id_user for u in users],
                format_func=lambda i: next(
                    f"{u.username} — {u.nom} {u.prenom} [{u.role}]"
                    for u in users if u.id_user == i
                ),
                key="mod_user_select",
            )
            u_obj = session.get(Utilisateur, uid)
            with st.form("edit_user"):
                c1, c2 = st.columns(2)
                nom_e   = c1.text_input("Nom",    value=u_obj.nom)
                prenom_e = c2.text_input("Prénom", value=u_obj.prenom)
                email_e  = c1.text_input("Email",  value=u_obj.email or "")
                role_e   = c2.selectbox("Rôle", list(ROLES),
                              index=list(ROLES).index(u_obj.role)
                              if u_obj.role in ROLES else 0)
                tel_e    = c1.text_input("Téléphone", value=u_obj.telephone or "")
                statut_e = c2.selectbox("Statut", ["Actif", "Inactif"],
                              index=0 if u_obj.statut == "Actif" else 1)
                new_pwd  = st.text_input(
                    "Nouveau mot de passe (laisser vide = inchangé)",
                    type="password",
                )
                update = st.form_submit_button("💾 Mettre à jour", type="primary")

            if update:
                u_obj.nom       = nom_e
                u_obj.prenom    = prenom_e
                u_obj.email     = email_e or None
                u_obj.role      = role_e
                u_obj.telephone = tel_e or None
                u_obj.statut    = statut_e
                if new_pwd:
                    u_obj.mot_de_passe = hash_password(new_pwd)
                    st.toast("🔑 Mot de passe mis à jour.", icon="🔑")
                log_action(session, user.id_user, f"Modification utilisateur {u_obj.username}")
                session.commit()
                st.toast(f"✅ Utilisateur **{u_obj.username}** mis à jour !", icon="✅")
                st.rerun()

    # ── Supprimer ─────────────────────────────────────────────────────────
    with tab_supprimer:
        # Ne peut pas se supprimer soi-même
        users = session.scalars(
            select(Utilisateur)
            .where(Utilisateur.id_user != user.id_user)
            .order_by(Utilisateur.username)
        ).all()
        if not users:
            st.info("Aucun autre utilisateur à supprimer.")
        else:
            uid = st.selectbox(
                "Sélectionner l'utilisateur à supprimer",
                [u.id_user for u in users],
                format_func=lambda i: next(
                    f"{u.username} — {u.nom} {u.prenom}"
                    for u in users if u.id_user == i
                ),
                key="del_user_select",
            )
            u_obj = session.get(Utilisateur, uid)
            st.warning(
                f"⚠️ Vous allez supprimer **{u_obj.username}** "
                f"({u_obj.nom} {u_obj.prenom}). Action irréversible."
            )
            confirmer = st.checkbox("Je confirme la suppression", key="del_user_confirm")
            if st.button("🗑️ Supprimer définitivement", type="primary",
                         disabled=not confirmer, key="del_user_btn"):
                username_supp = u_obj.username
                log_action(session, user.id_user, f"Suppression utilisateur {username_supp}")
                session.delete(u_obj)
                session.commit()
                st.toast(f"🗑️ Utilisateur **{username_supp}** supprimé.", icon="🗑️")
                st.rerun()