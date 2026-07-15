from datetime import date, timedelta

from decimal import Decimal



import pandas as pd

import streamlit as st

from sqlalchemy import select

from sqlalchemy.orm import joinedload



from database.models import Client, Credit, LigneVente, Produit, Vente

from services.invoice_helpers import get_tva, next_facture_number

from services.logging_service import log_action

from services.pdf_invoice import generate_invoice_pdf

from services.stock_service import mouvement_stock

from utils.crud_ui import render_dataframe
from utils.dialogs import request_dialog, run_delete_dialog
from config import MODES_PAIEMENT_VENTE
from utils.ui import page_header





def page_ventes(session, user):

    page_header("Gestion des Ventes", "Caisse, factures et historique", "💰")

    tab_nouvelle, tab_hist, tab_factures, tab_modifier, tab_supprimer = st.tabs(

        ["Nouvelle Vente", "Historique", "Factures", "Modifier", "Supprimer"]

    )



    with tab_nouvelle:

        clients = session.scalars(select(Client).where(Client.statut == "Actif")).all()

        produits = session.scalars(select(Produit).where(Produit.statut == "Actif", Produit.stock > 0)).all()

        if not produits:

            st.warning("Aucun produit en stock.")

        else:

            cid = st.selectbox("Client", [None] + [c.id_client for c in clients], format_func=lambda i: "Comptant" if i is None else next(c.nom_client for c in clients if c.id_client == i))

            mp = st.selectbox("Mode paiement", MODES_PAIEMENT_VENTE)

            remise_globale = st.number_input("Remise globale", min_value=0.0, step=0.01, value=0.0)



            if "lignes_vente" not in st.session_state:

                st.session_state.lignes_vente = []



            c1, c2, c3, c4 = st.columns(4)

            code = c1.selectbox("Produit", [p.code_produit for p in produits], key="v_prod")

            prod = session.get(Produit, code)

            qte = c2.number_input("Qté", min_value=1, max_value=int(prod.stock) if prod else 1, value=1)

            pu = c3.number_input("P.U.", value=float(prod.prix_vente) if prod else 0.0, step=0.01)

            rem_ligne = c4.number_input("Remise ligne", min_value=0.0, step=0.01, value=0.0)

            if st.button("Ajouter au panier"):

                total = Decimal(str(qte)) * Decimal(str(pu)) - Decimal(str(rem_ligne))

                st.session_state.lignes_vente.append(

                    {"code": code, "qte": int(qte), "pu": Decimal(str(pu)), "remise": Decimal(str(rem_ligne)), "total": total}

                )



            if st.session_state.lignes_vente:

                st.dataframe(pd.DataFrame(st.session_state.lignes_vente), hide_index=True)

                ht = sum(l["total"] for l in st.session_state.lignes_vente)

                remise = Decimal(str(remise_globale))

                ht_net = ht - remise

                tva_rate = get_tva(session) / 100

                tva = ht_net * tva_rate

                ttc = ht_net + tva

                st.write(f"HT: {ht:.2f} | Remise: {remise:.2f} | TVA: {tva:.2f} | **TTC: {ttc:.2f}**")

                if st.button("Valider la vente", type="primary"):

                    try:

                        vente = Vente(

                            id_client=cid,

                            montant_ht=ht_net,

                            remise=remise,

                            tva=tva,

                            montant_total=ttc,

                            mode_paiement=mp,

                            statut="Impayée" if mp == "Crédit" else "Payée",

                            id_user=user.id_user,

                            numero_facture=next_facture_number(session),

                        )

                        session.add(vente)

                        session.flush()

                        for l in st.session_state.lignes_vente:

                            session.add(

                                LigneVente(

                                    id_vente=vente.id_vente,

                                    code_produit=l["code"],

                                    quantite=l["qte"],

                                    prix_unitaire=l["pu"],

                                    remise=l["remise"],

                                    total=l["total"],

                                )

                            )

                            mouvement_stock(session, l["code"], "Sortie", l["qte"], f"Vente-{vente.id_vente}", user.id_user)

                        if mp == "Crédit" and cid:

                            session.add(

                                Credit(

                                    id_client=cid,

                                    id_vente=vente.id_vente,

                                    montant=ttc,

                                    montant_restant=ttc,

                                    date_echeance=date.today() + timedelta(days=30),

                                    statut="Ouvert",

                                )

                            )

                        log_action(session, user.id_user, f"Vente #{vente.id_vente}")

                        session.commit()

                        st.session_state.lignes_vente = []

                        st.success(f"Vente #{vente.id_vente} — Facture {vente.numero_facture}")

                        st.rerun()

                    except ValueError as e:

                        st.error(str(e))

                        session.rollback()



    with tab_hist:

        ventes = session.scalars(

            select(Vente).options(joinedload(Vente.client)).order_by(Vente.date.desc())

        ).unique().all()

        df = pd.DataFrame(

            [

                {

                    "ID": v.id_vente,

                    "Facture": v.numero_facture,

                    "Date": v.date,

                    "Client": v.client.nom_client if v.client else "Comptant",

                    "TTC": float(v.montant_total),

                    "Paiement": v.mode_paiement,

                    "Statut": v.statut,

                }

                for v in ventes

            ]

        )

        render_dataframe(df)



    with tab_factures:

        ventes = session.scalars(select(Vente).order_by(Vente.date.desc())).all()

        if ventes:

            vid = st.selectbox("Vente", [v.id_vente for v in ventes], format_func=lambda i: next(f"{v.numero_facture} — {v.montant_total}" for v in ventes if v.id_vente == i))

            v = session.get(Vente, vid)

            session.refresh(v)

            for l in v.lignes:

                session.refresh(l)

            if v.client:

                session.refresh(v.client)

            pdf = generate_invoice_pdf(session, v)

            st.download_button("Télécharger PDF", pdf, file_name=f"{v.numero_facture}.pdf", mime="application/pdf")



            st.divider()

            st.subheader("Envoyer par e-mail")

            default_email = v.client.email if v.client and v.client.email else ""

            to_email = st.text_input("E-mail destinataire", value=default_email)

            if st.button("Envoyer la facture", type="primary"):

                from services.email_service import is_email_configured, send_invoice_email



                if not to_email:

                    st.error("Indiquez une adresse e-mail.")

                elif not is_email_configured(session):

                    st.error("Configurez le SMTP dans Paramètres → E-mail.")

                else:

                    try:

                        send_invoice_email(

                            session,

                            to_email,

                            subject=f"Facture {v.numero_facture}",

                            body=f"Bonjour,\n\nVeuillez trouver ci-joint la facture {v.numero_facture}.\n\nCordialement,\nSGIQ",

                            pdf_bytes=pdf,

                            filename=f"{v.numero_facture}.pdf",

                        )

                        log_action(session, user.id_user, f"Envoi facture {v.numero_facture} → {to_email}")

                        session.commit()

                        st.success(f"Facture envoyée à {to_email}")

                    except Exception as e:

                        st.error(f"Échec envoi : {e}")



    with tab_modifier:

        ventes = session.scalars(select(Vente)).all()

        if ventes:

            vid = st.selectbox("Vente", [v.id_vente for v in ventes], key="edit_v")

            v = session.get(Vente, vid)

            statut = st.selectbox("Statut", ["Payée", "Impayée"], index=0 if v.statut == "Payée" else 1)

            if st.button("Mettre à jour statut", type="primary"):

                v.statut = statut

                session.commit()

                st.success("Vente mise à jour.")



    with tab_supprimer:

        st.warning("La suppression d'une vente est irréversible et restaure le stock.")

        ventes = session.scalars(select(Vente).order_by(Vente.id_vente.desc()).limit(50)).all()

        if ventes:

            vid = st.selectbox("Vente à supprimer", [v.id_vente for v in ventes])

            if st.button("Supprimer la vente", type="primary"):
                request_dialog("_del_vente", vid)

            if "_del_vente" in st.session_state:
                pending_vid = st.session_state["_del_vente"]

                def _delete():
                    v = session.get(Vente, pending_vid)
                    for l in v.lignes:
                        mouvement_stock(session, l.code_produit, "Entrée", l.quantite, f"Suppr-Vente-{pending_vid}", user.id_user)
                    if v.credit:
                        session.delete(v.credit)
                    log_action(session, user.id_user, f"Suppression vente #{pending_vid}")
                    session.delete(v)
                    session.commit()
                    st.toast(f"Vente #{pending_vid} supprimée.", icon="🗑️")

                run_delete_dialog("_del_vente", f"vente #{pending_vid}", _delete) 

