from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError

from database.models import Client, Commande, Credit, Vente
from services.logging_service import log_action
from utils.crud_ui import render_dataframe
from utils.dialogs import request_dialog, run_confirm_dialog, run_delete_dialog
from utils.ui import page_header


def _client_a_historique(session, cid: int) -> dict[str, int]:
    return {
        "ventes": session.scalar(
            select(func.count()).select_from(Vente).where(Vente.id_client == cid)
        ) or 0,
        "commandes": session.scalar(
            select(func.count()).select_from(Commande).where(Commande.id_client == cid)
        ) or 0,
        "credits": session.scalar(
            select(func.count()).select_from(Credit).where(Credit.id_client == cid)
        ) or 0,
    }


def page_clients(session, user):
    page_header("Gestion des Clients", "Liste, ajout, modification et historique", "👤")

    tab_liste, tab_ajouter, tab_modifier, tab_supprimer, tab_hist = st.tabs(
        ["📋 Liste", "➕ Ajouter", "✏️ Modifier", "🗑️ Supprimer", "📜 Historique"]
    )

    def load_df():
        clients = session.scalars(select(Client).order_by(Client.id_client)).all()
        return pd.DataFrame([
            {
                "ID":        c.id_client,
                "Nom":       c.nom_client,
                "Type":      c.type_client,
                "Téléphone": c.telephone_client,
                "Email":     c.email,
                "Statut":    c.statut,
            }
            for c in clients
        ])

    # ── Liste ────────────────────────────────────────────────────────────
    with tab_liste:
        c1, c2, c3 = st.columns(3)
        filtre_nom  = c1.text_input("🔍 Filtrer par nom",       placeholder="Ibrahima...")
        filtre_tel  = c2.text_input("🔍 Filtrer par téléphone", placeholder="77...")
        filtre_type = c3.selectbox("Type", ["Tous", "Particulier", "Entreprise"])

        df = load_df()
        if filtre_nom:
            df = df[df["Nom"].str.contains(filtre_nom, case=False, na=False)]
        if filtre_tel:
            df = df[df["Téléphone"].astype(str).str.contains(filtre_tel, na=False)]
        if filtre_type != "Tous":
            df = df[df["Type"] == filtre_type]

        st.caption(f"{len(df)} client(s) trouvé(s)")
        render_dataframe(df)

    # ── Ajouter ──────────────────────────────────────────────────────────
    with tab_ajouter:
        st.subheader("Nouveau client")
        with st.form("add_client", clear_on_submit=True):
            c1, c2 = st.columns(2)
            nom    = c1.text_input("Nom client *", placeholder="Ibrahima Diallo")
            type_c = c2.selectbox("Type *", ["Particulier", "Entreprise"])
            tel    = c1.text_input("Téléphone", placeholder="77 000 00 00")
            email  = c2.text_input("Email",     placeholder="client@email.sn")
            adresse = st.text_input("Adresse",  placeholder="Médina, Dakar")
            statut = st.selectbox("Statut", ["Actif", "Inactif"])
            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            if not nom.strip():
                st.error("❌ Le nom du client est obligatoire.")
            else:
                session.add(Client(
                    nom_client=nom.strip(), type_client=type_c,
                    telephone_client=tel or None,
                    email=email or None,
                    adresse=adresse or None,
                    statut=statut,
                ))
                log_action(session, user.id_user, f"Ajout client {nom}")
                session.commit()
                st.toast(f"✅ Client **{nom}** ajouté avec succès !", icon="✅")
                st.rerun()

    # ── Modifier ─────────────────────────────────────────────────────────
    with tab_modifier:
        clients = session.scalars(select(Client).order_by(Client.nom_client)).all()
        if not clients:
            st.info("Aucun client à modifier.")
        else:
            cid = st.selectbox(
                "Sélectionner le client à modifier",
                [c.id_client for c in clients],
                format_func=lambda i: next(
                    f"{c.nom_client} ({c.type_client})"
                    for c in clients if c.id_client == i
                ),
                key="mod_client_select",
            )
            c = session.get(Client, cid)
            with st.form("edit_client"):
                co1, co2 = st.columns(2)
                nom_edit    = co1.text_input("Nom",       value=c.nom_client)
                type_edit   = co2.selectbox("Type", ["Particulier", "Entreprise"],
                                index=0 if c.type_client == "Particulier" else 1)
                tel_edit    = co1.text_input("Téléphone", value=c.telephone_client or "")
                email_edit  = co2.text_input("Email",     value=c.email or "")
                adr_edit    = st.text_input("Adresse",    value=c.adresse or "")
                statut_edit = st.selectbox("Statut", ["Actif", "Inactif"],
                                index=0 if c.statut == "Actif" else 1)
                update = st.form_submit_button("💾 Mettre à jour", type="primary")

            if update:
                ancien_nom = c.nom_client
                c.nom_client      = nom_edit
                c.type_client     = type_edit
                c.telephone_client = tel_edit or None
                c.email           = email_edit or None
                c.adresse         = adr_edit or None
                c.statut          = statut_edit
                log_action(session, user.id_user, f"Modification client {ancien_nom}")
                session.commit()
                st.toast(f"✅ Client **{nom_edit}** mis à jour !", icon="✅")
                st.rerun()

    # ── Supprimer ─────────────────────────────────────────────────────────
    with tab_supprimer:
        clients = session.scalars(select(Client).order_by(Client.nom_client)).all()
        if not clients:
            st.info("Aucun client à supprimer.")
        else:
            cid = st.selectbox(
                "Sélectionner le client à supprimer",
                [c.id_client for c in clients],
                format_func=lambda i: next(
                    c.nom_client for c in clients if c.id_client == i
                ),
                key="del_client_select",
            )
            c = session.get(Client, cid)
            hist = _client_a_historique(session, cid)
            total_refs = sum(hist.values())

            if total_refs > 0:
                st.warning(
                    f"**{c.nom_client}** a déjà un historique "
                    f"({hist['ventes']} vente(s), {hist['commandes']} commande(s), "
                    f"{hist['credits']} crédit(s)).\n\n"
                    "Il ne peut pas être effacé définitivement — "
                    "il sera **désactivé** (statut Inactif)."
                )
                btn_label = "🚫 Désactiver le client"
                dlg_key = "_desact_client"
            else:
                st.warning(
                    f"⚠️ Vous allez supprimer définitivement **{c.nom_client}**. "
                    "Aucun historique lié."
                )
                btn_label = "🗑️ Supprimer définitivement"
                dlg_key = "_del_client"

            if st.button(btn_label, type="primary", key="del_client_btn"):
                request_dialog(dlg_key, cid)

            if "_desact_client" in st.session_state:
                pending = session.get(Client, st.session_state["_desact_client"])
                if pending:
                    def _desactiver():
                        pending.statut = "Inactif"
                        log_action(
                            session, user.id_user,
                            f"Désactivation client {pending.nom_client} (historique existant)",
                        )
                        session.commit()
                        st.toast(
                            f"🚫 **{pending.nom_client}** désactivé (conservé pour l'historique).",
                            icon="🚫",
                        )

                    run_confirm_dialog(
                        "_desact_client",
                        f"Désactiver {pending.nom_client} ?",
                        "Le client restera dans l'historique, "
                        "mais ne pourra plus être sélectionné pour de nouvelles ventes.",
                        _desactiver,
                        confirm_label="Désactiver",
                        icon="🚫",
                    )

            if "_del_client" in st.session_state:
                pending_id = st.session_state["_del_client"]
                pending = session.get(Client, pending_id)
                if pending:
                    def _delete():
                        nom_supp = pending.nom_client
                        if sum(_client_a_historique(session, pending_id).values()) > 0:
                            pending.statut = "Inactif"
                            log_action(
                                session, user.id_user,
                                f"Désactivation client {nom_supp} (refs détectées)",
                            )
                            session.commit()
                            st.toast(
                                f"🚫 **{nom_supp}** désactivé (historique trouvé).",
                                icon="🚫",
                            )
                            return
                        try:
                            log_action(session, user.id_user, f"Suppression client {nom_supp}")
                            session.delete(pending)
                            session.commit()
                            st.toast(f"🗑️ Client **{nom_supp}** supprimé.", icon="🗑️")
                        except IntegrityError:
                            session.rollback()
                            pending2 = session.get(Client, pending_id)
                            if pending2:
                                pending2.statut = "Inactif"
                                log_action(
                                    session, user.id_user,
                                    f"Désactivation client {nom_supp} (contrainte FK)",
                                )
                                session.commit()
                                st.toast(
                                    f"🚫 **{nom_supp}** désactivé (lié à des documents).",
                                    icon="🚫",
                                )

                    run_delete_dialog("_del_client", pending.nom_client, _delete)

    # ── Historique ────────────────────────────────────────────────────────
    with tab_hist:
        clients = session.scalars(select(Client).order_by(Client.nom_client)).all()
        if not clients:
            st.info("Aucun client enregistré.")
        else:
            cid = st.selectbox(
                "Sélectionner un client",
                [c.id_client for c in clients],
                format_func=lambda i: next(
                    c.nom_client for c in clients if c.id_client == i
                ),
                key="hist_client_select",
            )
            nb_cmd = session.scalar(
                select(func.count()).select_from(Commande).where(Commande.id_client == cid)
            ) or 0
            total_achats = session.scalar(
                select(func.coalesce(func.sum(Vente.montant_total), 0))
                .where(Vente.id_client == cid)
            ) or Decimal(0)
            solde = session.scalar(
                select(func.coalesce(func.sum(Credit.montant_restant), 0))
                .where(Credit.id_client == cid, Credit.statut == "Ouvert")
            ) or Decimal(0)

            m1, m2, m3 = st.columns(3)
            m1.metric("Commandes",   nb_cmd)
            m2.metric("Total achats", f"{float(total_achats):,.0f} MRU")
            m3.metric("Solde crédit", f"{float(solde):,.0f} MRU")

            ventes = session.scalars(
                select(Vente).where(Vente.id_client == cid).order_by(Vente.date.desc())
            ).all()
            if ventes:
                st.markdown("**Historique des ventes**")
                render_dataframe(pd.DataFrame([{
                    "Facture": v.numero_facture or f"#{v.id_vente}",
                    "Date":    v.date.strftime("%d/%m/%Y"),
                    "TTC":     f"{float(v.montant_total):,.0f} MRU",
                    "Mode":    v.mode_paiement,
                    "Statut":  v.statut,
                } for v in ventes]))
            else:
                st.info("Aucune vente pour ce client.")