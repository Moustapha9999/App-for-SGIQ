from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from config import MODES_PAIEMENT_VENTE
from database.models import Client, Commande, LigneCommande, Produit, Vente, LigneVente
from services.invoice_helpers import get_tva, next_facture_number
from services.logging_service import log_action
from services.stock_service import mouvement_stock
from utils.dialogs import request_dialog, run_delete_dialog
from utils.ui import page_header


def page_commandes(session, user):
    page_header("Gestion des Commandes", "Commandes clients et suivi des statuts", "📋")
    tab_nouvelle, tab_suivi, tab_modifier, tab_supprimer = st.tabs(
        ["Nouvelle Commande", "Suivi", "Modifier statut", "Supprimer"]
    )

    with tab_nouvelle:
        clients = session.scalars(select(Client).where(Client.statut == "Actif")).all()
        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()
        if clients and produits:
            cid = st.selectbox(
                "Client",
                [c.id_client for c in clients],
                format_func=lambda i: next(c.nom_client for c in clients if c.id_client == i),
                key="cmd_nouvelle_client",
            )
            mp = st.selectbox(
                "Mode paiement", MODES_PAIEMENT_VENTE,
                key="cmd_nouvelle_mp",
            )
            if "lignes_cmd" not in st.session_state:
                st.session_state.lignes_cmd = []

            code = st.selectbox(
                "Produit",
                [p.code_produit for p in produits],
                format_func=lambda x: next(
                    f"{p.code_produit} — {p.designation}"
                    for p in produits if p.code_produit == x
                ),
                key="cmd_nouvelle_produit",
            )
            prod = session.get(Produit, code)
            qte = st.number_input("Quantité", min_value=1, value=1, key="cmd_nouvelle_qte")
            pu  = st.number_input(
                "Prix", value=float(prod.prix_vente) if prod else 0.0,
                step=0.01, key="cmd_nouvelle_pu",
            )
            if st.button("Ajouter ligne commande", key="cmd_btn_ajouter"):
                total = Decimal(str(qte)) * Decimal(str(pu))
                st.session_state.lignes_cmd.append({
                    "code": code, "qte": int(qte),
                    "pu": Decimal(str(pu)), "total": total,
                })

            if st.session_state.lignes_cmd:
                st.dataframe(pd.DataFrame(st.session_state.lignes_cmd), hide_index=True)
                if st.button("Créer commande", type="primary", key="cmd_btn_creer"):
                    montant = sum(l["total"] for l in st.session_state.lignes_cmd)
                    cmd = Commande(
                        id_client=cid, montant_total=montant,
                        mode_paiement=mp, statut="En attente",
                    )
                    session.add(cmd)
                    session.flush()
                    for l in st.session_state.lignes_cmd:
                        session.add(LigneCommande(
                            id_commande=cmd.id_commande,
                            code_produit=l["code"],
                            quantite=l["qte"],
                            prix_unitaire=l["pu"],
                            total=l["total"],
                        ))
                    log_action(session, user.id_user, f"Commande #{cmd.id_commande} créée")
                    session.commit()
                    st.session_state.lignes_cmd = []
                    st.success(f"Commande #{cmd.id_commande} créée.")
                    st.rerun()
        else:
            st.warning("Ajoutez d'abord des clients et des produits actifs.")

    with tab_suivi:
        cmds = session.scalars(
            select(Commande)
            .options(joinedload(Commande.client))
            .order_by(Commande.date_commande.desc())
        ).unique().all()

        df = pd.DataFrame([
            {
                "ID":       c.id_commande,
                "Date":     c.date_commande.strftime("%d/%m/%Y %H:%M") if c.date_commande else "",
                "Client":   c.client.nom_client if c.client else "—",
                "Montant":  f"{float(c.montant_total):,.0f}",
                "Statut":   c.statut,
                "Paiement": c.mode_paiement,
            }
            for c in cmds
        ])
        st.dataframe(df, hide_index=True, use_container_width=True)

        st.subheader("Workflow commande")
        cmds_act = session.scalars(
            select(Commande).where(Commande.statut != "Annulée")
        ).all()
        if cmds_act:
            # ✅ key unique pour ce selectbox
            cmd_id = st.selectbox(
                "Commande",
                [c.id_commande for c in cmds_act],
                format_func=lambda i: next(
                    f"#{c.id_commande} — {c.client.nom_client if c.client else '?'} [{c.statut}]"
                    for c in cmds_act if c.id_commande == i
                ),
                key="cmd_suivi_workflow",
            )
            cmd = session.get(Commande, cmd_id)
            st.info(f"Statut actuel : **{cmd.statut}**")

            workflow = ["En attente", "Validée", "Livrée"]
            if cmd.statut in workflow:
                idx = workflow.index(cmd.statut)
                if idx < len(workflow) - 1:
                    next_statut = workflow[idx + 1]
                    if st.button(
                        f"➡️ Passer à « {next_statut} »",
                        type="primary",
                        key="cmd_btn_workflow",
                    ):
                        if next_statut == "Validée":
                            tva_rate = get_tva(session) / 100
                            ht  = cmd.montant_total
                            tva = ht * tva_rate
                            ttc = ht + tva
                            vente = Vente(
                                id_client=cmd.id_client,
                                montant_ht=ht,
                                remise=Decimal(0),
                                tva=tva,
                                montant_total=ttc,
                                mode_paiement=cmd.mode_paiement,
                                statut="Payée" if cmd.mode_paiement != "Crédit" else "Impayée",
                                id_user=user.id_user,
                                numero_facture=next_facture_number(session),
                            )
                            session.add(vente)
                            session.flush()
                            cmd.id_vente = vente.id_vente
                            for l in cmd.lignes:
                                session.add(LigneVente(
                                    id_vente=vente.id_vente,
                                    code_produit=l.code_produit,
                                    quantite=l.quantite,
                                    prix_unitaire=l.prix_unitaire,
                                    remise=Decimal(0),
                                    total=l.total,
                                ))
                        elif next_statut == "Livrée":
                            for l in cmd.lignes:
                                mouvement_stock(
                                    session, l.code_produit, "Sortie",
                                    l.quantite, f"Commande-{cmd.id_commande}",
                                    user.id_user,
                                )
                        cmd.statut = next_statut
                        log_action(session, user.id_user, f"Commande #{cmd_id} → {next_statut}")
                        session.commit()
                        st.success(f"Commande passée à {next_statut}.")
                        st.rerun()
        else:
            st.info("Aucune commande active.")

    with tab_modifier:
        cmds = session.scalars(select(Commande)).all()
        if cmds:
            # ✅ key unique pour ce selectbox
            cmd_id = st.selectbox(
                "Commande",
                [c.id_commande for c in cmds],
                format_func=lambda i: next(
                    f"#{c.id_commande} [{c.statut}]"
                    for c in cmds if c.id_commande == i
                ),
                key="cmd_modifier_select",
            )
            cmd = session.get(Commande, cmd_id)
            new_statut = st.selectbox(
                "Nouveau statut",
                ["En attente", "Validée", "Livrée", "Annulée"],
                key="cmd_modifier_statut",
            )
            if st.button("Mettre à jour", type="primary", key="cmd_btn_modifier"):
                cmd.statut = new_statut
                log_action(session, user.id_user, f"Modif commande #{cmd_id} → {new_statut}")
                session.commit()
                st.success("Statut mis à jour.")
                st.rerun()
        else:
            st.info("Aucune commande.")

    with tab_supprimer:
        cmds = session.scalars(
            select(Commande).where(Commande.statut == "En attente")
        ).all()
        if cmds:
            # ✅ key unique pour ce selectbox
            cmd_id = st.selectbox(
                "Commande à supprimer",
                [c.id_commande for c in cmds],
                format_func=lambda i: next(
                    f"#{c.id_commande} — {c.client.nom_client if c.client else '?'}"
                    for c in cmds if c.id_commande == i
                ),
                key="cmd_supprimer_select",
            )
            if st.button("🗑️ Supprimer", type="primary", key="cmd_btn_supprimer"):
                request_dialog("_del_cmd", cmd_id)

            if "_del_cmd" in st.session_state:
                pending_id = st.session_state["_del_cmd"]

                def _delete():
                    cmd = session.get(Commande, pending_id)
                    session.delete(cmd)
                    log_action(session, user.id_user, f"Suppression commande #{pending_id}")
                    session.commit()
                    st.toast(f"Commande #{pending_id} supprimée.", icon="🗑️")

                run_delete_dialog("_del_cmd", f"commande #{pending_id}", _delete)
        else:
            st.info("Aucune commande en attente à supprimer.")