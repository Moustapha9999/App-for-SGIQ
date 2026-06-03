import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from database.models import Achat, Fournisseur
from services.logging_service import log_action
from utils.crud_ui import render_dataframe


def page_fournisseurs(session, user):
    st.header("🏭 Gestion des Fournisseurs")
    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_hist = st.tabs(
        ["Liste", "Ajouter", "Modifier", "Supprimer", "Historique"]
    )

    with tab_liste:
        fournisseurs = session.scalars(select(Fournisseur).order_by(Fournisseur.id_fournisseur)).all()
        df = pd.DataFrame(
            [
                {
                    "ID": f.id_fournisseur,
                    "Raison sociale": f.raison_sociale,
                    "Produit principal": f.produit_principal,
                    "Téléphone": f.telephone,
                    "Paiement": f.mode_paiement,
                    "Statut": f.statut,
                }
                for f in fournisseurs
            ]
        )
        render_dataframe(df)

    with tab_ajouter:
        with st.form("add_fourn"):
            rs = st.text_input("Raison sociale *")
            pp = st.text_input("Produit principal")
            tel = st.text_input("Téléphone")
            adr = st.text_input("Adresse")
            email = st.text_input("Email")
            mp = st.selectbox("Mode paiement", ["Espèces", "Virement", "Chèque"])
            statut = st.selectbox("Statut", ["Actif", "Inactif"])
            if st.form_submit_button("Enregistrer", type="primary") and rs:
                session.add(
                    Fournisseur(
                        raison_sociale=rs,
                        produit_principal=pp,
                        telephone=tel,
                        adresse=adr,
                        email=email,
                        mode_paiement=mp,
                        statut=statut,
                    )
                )
                log_action(session, user.id_user, f"Ajout fournisseur {rs}")
                session.commit()
                st.success("Fournisseur ajouté.")
                st.rerun()

    with tab_modifier:
        fournisseurs = session.scalars(select(Fournisseur)).all()
        if fournisseurs:
            fid = st.selectbox("Fournisseur", [f.id_fournisseur for f in fournisseurs], format_func=lambda i: next(f.raison_sociale for f in fournisseurs if f.id_fournisseur == i))
            f = session.get(Fournisseur, fid)
            with st.form("edit_fourn"):
                f.raison_sociale = st.text_input("Raison sociale", value=f.raison_sociale)
                f.produit_principal = st.text_input("Produit principal", value=f.produit_principal or "")
                f.telephone = st.text_input("Téléphone", value=f.telephone or "")
                f.adresse = st.text_input("Adresse", value=f.adresse or "")
                f.email = st.text_input("Email", value=f.email or "")
                f.mode_paiement = st.selectbox("Mode paiement", ["Espèces", "Virement", "Chèque"], index=["Espèces", "Virement", "Chèque"].index(f.mode_paiement) if f.mode_paiement in ["Espèces", "Virement", "Chèque"] else 0)
                f.statut = st.selectbox("Statut", ["Actif", "Inactif"], index=0 if f.statut == "Actif" else 1)
                if st.form_submit_button("Mettre à jour", type="primary"):
                    log_action(session, user.id_user, f"Modification fournisseur {f.raison_sociale}")
                    session.commit()
                    st.success("Fournisseur mis à jour.")
                    st.rerun()

    with tab_supprimer:
        fournisseurs = session.scalars(select(Fournisseur)).all()
        if fournisseurs:
            fid = st.selectbox("À supprimer", [f.id_fournisseur for f in fournisseurs], format_func=lambda i: next(f.raison_sociale for f in fournisseurs if f.id_fournisseur == i))
            if st.button("Supprimer", type="primary"):
                f = session.get(Fournisseur, fid)
                log_action(session, user.id_user, f"Suppression fournisseur {f.raison_sociale}")
                session.delete(f)
                session.commit()
                st.success("Fournisseur supprimé.")
                st.rerun()

    with tab_hist:
        fournisseurs = session.scalars(select(Fournisseur)).all()
        if fournisseurs:
            fid = st.selectbox("Fournisseur", [f.id_fournisseur for f in fournisseurs], key="hist_f", format_func=lambda i: next(f.raison_sociale for f in fournisseurs if f.id_fournisseur == i))
            total = session.scalar(
                select(func.coalesce(func.sum(Achat.montant_total), 0)).where(
                    Achat.id_fournisseur == fid, Achat.annule == False
                )
            )
            nb = session.scalar(select(func.count()).select_from(Achat).where(Achat.id_fournisseur == fid, Achat.annule == False)) or 0
            st.metric("Total commandes (achats)", f"{total:.2f}")
            st.metric("Nombre d'achats", nb)
