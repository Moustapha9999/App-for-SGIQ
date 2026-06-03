from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.models import Client, Commande, LigneCommande, Produit, Vente
from services.logging_service import log_action
from database.models import LigneVente
from services.invoice_helpers import get_tva, next_facture_number
from services.stock_service import mouvement_stock


def page_commandes(session, user):
    st.header("📋 Gestion des Commandes")
    tab_nouvelle, tab_suivi, tab_modifier, tab_supprimer = st.tabs(
        ["Nouvelle Commande", "Suivi", "Modifier statut", "Supprimer"]
    )

    with tab_nouvelle:
        clients = session.scalars(select(Client).where(Client.statut == "Actif")).all()
        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()
        if clients and produits:
            cid = st.selectbox("Client", [c.id_client for c in clients], format_func=lambda i: next(c.nom_client for c in clients if c.id_client == i))
            mp = st.selectbox("Mode paiement", ["Espèces", "Crédit", "Virement"])
            if "lignes_cmd" not in st.session_state:
                st.session_state.lignes_cmd = []
            code = st.selectbox("Produit", [p.code_produit for p in produits])
            prod = session.get(Produit, code)
            qte = st.number_input("Quantité", min_value=1, value=1)
            pu = st.number_input("Prix", value=float(prod.prix_vente), step=0.01)
            if st.button("Ajouter ligne commande"):
                total = Decimal(str(qte)) * Decimal(str(pu))
                st.session_state.lignes_cmd.append({"code": code, "qte": int(qte), "pu": Decimal(str(pu)), "total": total})
            if st.session_state.lignes_cmd:
                st.dataframe(pd.DataFrame(st.session_state.lignes_cmd), hide_index=True)
                if st.button("Créer commande", type="primary"):
                    montant = sum(l["total"] for l in st.session_state.lignes_cmd)
                    cmd = Commande(id_client=cid, montant_total=montant, mode_paiement=mp, statut="En attente")
                    session.add(cmd)
                    session.flush()
                    for l in st.session_state.lignes_cmd:
                        session.add(
                            LigneCommande(
                                id_commande=cmd.id_commande,
                                code_produit=l["code"],
                                quantite=l["qte"],
                                prix_unitaire=l["pu"],
                                total=l["total"],
                            )
                        )
                    log_action(session, user.id_user, f"Commande #{cmd.id_commande} créée")
                    session.commit()
                    st.session_state.lignes_cmd = []
                    st.success(f"Commande #{cmd.id_commande} créée.")
                    st.rerun()

    with tab_suivi:
        cmds = session.scalars(
            select(Commande).options(joinedload(Commande.client)).order_by(Commande.date_commande.desc())
        ).unique().all()
        df = pd.DataFrame(
            [
                {
                    "ID": c.id_commande,
                    "Date": c.date_commande,
                    "Client": c.client.nom_client if c.client else "",
                    "Montant": float(c.montant_total),
                    "Statut": c.statut,
                    "Paiement": c.mode_paiement,
                }
                for c in cmds
            ]
        )
        st.dataframe(df, hide_index=True, use_container_width=True)

        st.subheader("Workflow commande")
        cmds_act = session.scalars(select(Commande).where(Commande.statut != "Annulée")).all()
        if cmds_act:
            cmd_id = st.selectbox("Commande", [c.id_commande for c in cmds_act])
            cmd = session.get(Commande, cmd_id)
            st.info(f"Statut actuel: **{cmd.statut}**")
            workflow = ["En attente", "Validée", "Livrée"]
            if cmd.statut in workflow:
                idx = workflow.index(cmd.statut)
                if idx < len(workflow) - 1:
                    next_statut = workflow[idx + 1]
                    if st.button(f"Passer à « {next_statut} »", type="primary"):
                        if next_statut == "Validée":
                            tva_rate = get_tva(session) / 100
                            ht = cmd.montant_total
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
                                session.add(
                                    LigneVente(
                                        id_vente=vente.id_vente,
                                        code_produit=l.code_produit,
                                        quantite=l.quantite,
                                        prix_unitaire=l.prix_unitaire,
                                        remise=Decimal(0),
                                        total=l.total,
                                    )
                                )
                        elif next_statut == "Livrée":
                            for l in cmd.lignes:
                                mouvement_stock(
                                    session, l.code_produit, "Sortie", l.quantite,
                                    f"Commande-{cmd.id_commande}", user.id_user,
                                )
                        cmd.statut = next_statut
                        log_action(session, user.id_user, f"Commande #{cmd_id} → {next_statut}")
                        session.commit()
                        st.success(f"Commande passée à {next_statut}.")
                        st.rerun()

    with tab_modifier:
        cmds = session.scalars(select(Commande)).all()
        if cmds:
            cmd_id = st.selectbox("Commande", [c.id_commande for c in cmds], key="mod_cmd")
            cmd = session.get(Commande, cmd_id)
            new_statut = st.selectbox("Statut", ["En attente", "Validée", "Livrée", "Annulée"])
            if st.button("Mettre à jour", type="primary"):
                cmd.statut = new_statut
                session.commit()
                st.success("Statut mis à jour.")

    with tab_supprimer:
        cmds = session.scalars(select(Commande).where(Commande.statut == "En attente")).all()
        if cmds:
            cmd_id = st.selectbox("Commande", [c.id_commande for c in cmds])
            if st.button("Supprimer", type="primary"):
                cmd = session.get(Commande, cmd_id)
                session.delete(cmd)
                session.commit()
                st.success("Commande supprimée.")
                st.rerun()
