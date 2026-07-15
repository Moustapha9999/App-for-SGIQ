import pandas as pd
import streamlit as st
from sqlalchemy import func, select

from config import MODES_PAIEMENT, index_mode_paiement
from database.models import Achat, Fournisseur
from services.logging_service import log_action
from utils.crud_ui import render_dataframe
from utils.dialogs import request_dialog, run_delete_dialog
from utils.ui import page_header


def page_fournisseurs(session, user):
    page_header("Gestion des Fournisseurs", "Fournisseurs, contacts et historique d'achats", "🏭")

    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_hist = st.tabs(
        ["📋 Liste", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "📜 Historique"]
    )

    # ── Liste ─────────────────────────────────────────────────────────────
    with tab_liste:
        fournisseurs = session.scalars(
            select(Fournisseur).order_by(Fournisseur.raison_sociale)
        ).all()
        df = pd.DataFrame([{
            "ID":              f.id_fournisseur,
            "Raison sociale":  f.raison_sociale,
            "Produit principal": f.produit_principal or "—",
            "Téléphone":       f.telephone or "—",
            "Mode paiement":   f.mode_paiement,
            "Statut":          f.statut,
        } for f in fournisseurs])
        st.caption(f"{len(fournisseurs)} fournisseur(s)")
        render_dataframe(df)

    # ── Ajouter ───────────────────────────────────────────────────────────
    with tab_ajouter:
        st.subheader("Nouveau fournisseur")
        with st.form("add_fourn", clear_on_submit=True):
            c1, c2 = st.columns(2)
            rs     = c1.text_input("Raison sociale *", placeholder="SOCOCIM Industries")
            pp     = c2.text_input("Produit principal", placeholder="Ciment")
            tel    = c1.text_input("Téléphone",  placeholder="33 000 00 00")
            email  = c2.text_input("Email",      placeholder="contact@fourn.sn")
            adr    = st.text_input("Adresse",    placeholder="Zone Industrielle, Dakar")
            mp     = st.selectbox("Mode paiement", MODES_PAIEMENT)
            statut = st.selectbox("Statut", ["Actif", "Inactif"])
            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            if not rs.strip():
                st.error("❌ La raison sociale est obligatoire.")
            else:
                session.add(Fournisseur(
                    raison_sociale=rs.strip(), produit_principal=pp or None,
                    telephone=tel or None, email=email or None,
                    adresse=adr or None, mode_paiement=mp, statut=statut,
                ))
                log_action(session, user.id_user, f"Ajout fournisseur {rs}")
                session.commit()
                st.toast(f"✅ Fournisseur **{rs}** ajouté !", icon="✅")
                st.rerun()

    # ── Modifier ──────────────────────────────────────────────────────────
    with tab_modifier:
        fournisseurs = session.scalars(
            select(Fournisseur).order_by(Fournisseur.raison_sociale)
        ).all()
        if not fournisseurs:
            st.info("Aucun fournisseur à modifier.")
        else:
            fid = st.selectbox(
                "Sélectionner le fournisseur",
                [f.id_fournisseur for f in fournisseurs],
                format_func=lambda i: next(
                    f.raison_sociale for f in fournisseurs if f.id_fournisseur == i
                ),
                key="mod_fourn_select",
            )
            f = session.get(Fournisseur, fid)
            with st.form("edit_fourn"):
                c1, c2 = st.columns(2)
                rs_e   = c1.text_input("Raison sociale", value=f.raison_sociale)
                pp_e   = c2.text_input("Produit principal", value=f.produit_principal or "")
                tel_e  = c1.text_input("Téléphone", value=f.telephone or "")
                email_e= c2.text_input("Email",     value=f.email or "")
                adr_e  = st.text_input("Adresse",   value=f.adresse or "")
                mp_e   = st.selectbox("Mode paiement", MODES_PAIEMENT,
                            index=index_mode_paiement(f.mode_paiement, MODES_PAIEMENT))
                st_e   = st.selectbox("Statut", ["Actif", "Inactif"],
                            index=0 if f.statut == "Actif" else 1)
                update = st.form_submit_button("💾 Mettre à jour", type="primary")

            if update:
                ancien = f.raison_sociale
                f.raison_sociale   = rs_e
                f.produit_principal = pp_e or None
                f.telephone        = tel_e or None
                f.email            = email_e or None
                f.adresse          = adr_e or None
                f.mode_paiement    = mp_e
                f.statut           = st_e
                log_action(session, user.id_user, f"Modification fournisseur {ancien}")
                session.commit()
                st.toast(f"✅ Fournisseur **{rs_e}** mis à jour !", icon="✅")
                st.rerun()

    # ── Supprimer ─────────────────────────────────────────────────────────
    with tab_supprimer:
        fournisseurs = session.scalars(
            select(Fournisseur).order_by(Fournisseur.raison_sociale)
        ).all()
        if not fournisseurs:
            st.info("Aucun fournisseur à supprimer.")
        else:
            fid = st.selectbox(
                "Sélectionner le fournisseur à supprimer",
                [f.id_fournisseur for f in fournisseurs],
                format_func=lambda i: next(
                    f.raison_sociale for f in fournisseurs if f.id_fournisseur == i
                ),
                key="del_fourn_select",
            )
            f = session.get(Fournisseur, fid)
            st.warning(
                f"⚠️ Vous allez supprimer **{f.raison_sociale}**. "
                "Cette action est irréversible."
            )
            if st.button("🗑️ Supprimer définitivement", type="primary",
                         key="del_fourn_btn"):
                request_dialog("_del_fourn", fid)

            if "_del_fourn" in st.session_state:
                pending = session.get(Fournisseur, st.session_state["_del_fourn"])
                if pending:
                    def _delete():
                        nom_supp = pending.raison_sociale
                        log_action(session, user.id_user, f"Suppression fournisseur {nom_supp}")
                        session.delete(pending)
                        session.commit()
                        st.toast(f"🗑️ Fournisseur **{nom_supp}** supprimé.", icon="🗑️")

                    run_delete_dialog("_del_fourn", pending.raison_sociale, _delete)

    # ── Historique ────────────────────────────────────────────────────────
    with tab_hist:
        fournisseurs = session.scalars(
            select(Fournisseur).order_by(Fournisseur.raison_sociale)
        ).all()
        if not fournisseurs:
            st.info("Aucun fournisseur enregistré.")
        else:
            fid = st.selectbox(
                "Sélectionner un fournisseur",
                [f.id_fournisseur for f in fournisseurs],
                format_func=lambda i: next(
                    f.raison_sociale for f in fournisseurs if f.id_fournisseur == i
                ),
                key="hist_fourn_select",
            )
            total = session.scalar(
                select(func.coalesce(func.sum(Achat.montant_total), 0))
                .where(Achat.id_fournisseur == fid, Achat.annule == False)
            ) or 0
            nb = session.scalar(
                select(func.count()).select_from(Achat)
                .where(Achat.id_fournisseur == fid, Achat.annule == False)
            ) or 0
            m1, m2 = st.columns(2)
            m1.metric("Nombre d'achats",  nb)
            m2.metric("Total commandes", f"{float(total):,.0f} MRU")

            achats = session.scalars(
                select(Achat)
                .where(Achat.id_fournisseur == fid, Achat.annule == False)
                .order_by(Achat.date.desc())
            ).all()
            if achats:
                render_dataframe(pd.DataFrame([{
                    "N° Achat": a.id_achat,
                    "Date":     a.date.strftime("%d/%m/%Y") if a.date else "—",
                    "Montant":  f"{float(a.montant_total):,.0f} MRU",
                    "Mode":     a.mode_paiement,
                    "Statut":   a.statut,
                } for a in achats]))
            else:
                st.info("Aucun achat pour ce fournisseur.")