from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.models import Achat, Fournisseur, LigneAchat, Produit
from services.logging_service import log_action
from services.stock_service import mouvement_stock
from utils.crud_ui import render_dataframe


def page_achats(session, user):
    st.header("🛒 Gestion des Achats")
    tab_nouveau, tab_hist, tab_modifier, tab_annuler = st.tabs(
        ["Nouveau Achat", "Historique", "Modifier", "Annuler"]
    )

    with tab_nouveau:
        fournisseurs = session.scalars(select(Fournisseur).where(Fournisseur.statut == "Actif")).all()
        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()
        if not fournisseurs or not produits:
            st.warning("Ajoutez des fournisseurs et produits d'abord.")
        else:
            fid = st.selectbox("Fournisseur", [f.id_fournisseur for f in fournisseurs], format_func=lambda i: next(f.raison_sociale for f in fournisseurs if f.id_fournisseur == i))
            mp = st.selectbox("Mode paiement", ["Espèces", "Virement", "Chèque"])
            statut = st.selectbox("Statut", ["Payé", "En attente"])

            if "lignes_achat" not in st.session_state:
                st.session_state.lignes_achat = []

            c1, c2, c3 = st.columns(3)
            code = c1.selectbox("Produit", [p.code_produit for p in produits], key="achat_prod")
            qte = c2.number_input("Quantité", min_value=1, value=1, key="achat_qte")
            pu = c3.number_input("Prix unitaire", min_value=0.0, step=0.01, value=float(next(p.prix_achat for p in produits if p.code_produit == code)))
            if st.button("Ajouter ligne"):
                total = Decimal(str(qte)) * Decimal(str(pu))
                st.session_state.lignes_achat.append({"code": code, "qte": int(qte), "pu": Decimal(str(pu)), "total": total})

            if st.session_state.lignes_achat:
                st.dataframe(pd.DataFrame(st.session_state.lignes_achat), hide_index=True)
                montant = sum(l["total"] for l in st.session_state.lignes_achat)
                st.write(f"**Total: {montant:.2f}**")
                if st.button("Valider l'achat", type="primary"):
                    achat = Achat(
                        id_fournisseur=fid,
                        montant_total=montant,
                        mode_paiement=mp,
                        statut=statut,
                        id_user=user.id_user,
                    )
                    session.add(achat)
                    session.flush()
                    for l in st.session_state.lignes_achat:
                        session.add(
                            LigneAchat(
                                id_achat=achat.id_achat,
                                code_produit=l["code"],
                                quantite=l["qte"],
                                prix_unitaire=l["pu"],
                                total=l["total"],
                            )
                        )
                        p = session.get(Produit, l["code"])
                        p.prix_achat = l["pu"]
                        mouvement_stock(session, l["code"], "Entrée", l["qte"], f"Achat-{achat.id_achat}", user.id_user)
                    log_action(session, user.id_user, f"Création achat #{achat.id_achat}")
                    session.commit()
                    st.session_state.lignes_achat = []
                    st.success(f"Achat #{achat.id_achat} enregistré.")
                    st.rerun()

    with tab_hist:
        achats = session.scalars(
            select(Achat).options(joinedload(Achat.fournisseur)).where(Achat.annule == False).order_by(Achat.date.desc())
        ).unique().all()
        df = pd.DataFrame(
            [
                {
                    "ID": a.id_achat,
                    "Date": a.date,
                    "Fournisseur": a.fournisseur.raison_sociale if a.fournisseur else "",
                    "Montant": float(a.montant_total),
                    "Paiement": a.mode_paiement,
                    "Statut": a.statut,
                }
                for a in achats
            ]
        )
        render_dataframe(df)

    with tab_modifier:
        achats = session.scalars(select(Achat).where(Achat.annule == False)).all()
        if achats:
            aid = st.selectbox("Achat", [a.id_achat for a in achats])
            a = session.get(Achat, aid)
            statut = st.selectbox("Nouveau statut", ["Payé", "En attente"], index=0 if a.statut == "Payé" else 1)
            mp = st.selectbox("Mode paiement", ["Espèces", "Virement", "Chèque"])
            if st.button("Mettre à jour", type="primary"):
                a.statut = statut
                a.mode_paiement = mp
                log_action(session, user.id_user, f"Modification achat #{aid}")
                session.commit()
                st.success("Achat mis à jour.")

    with tab_annuler:
        achats = session.scalars(select(Achat).where(Achat.annule == False)).all()
        if achats:
            aid = st.selectbox("Achat à annuler", [a.id_achat for a in achats])
            if st.button("Annuler l'achat", type="primary"):
                a = session.get(Achat, aid)
                for l in a.lignes:
                    try:
                        mouvement_stock(session, l.code_produit, "Sortie", l.quantite, f"Annul-Achat-{aid}", user.id_user)
                    except ValueError as e:
                        st.error(str(e))
                        session.rollback()
                        return
                a.annule = True
                log_action(session, user.id_user, f"Annulation achat #{aid}")
                session.commit()
                st.success("Achat annulé.")
                st.rerun()
