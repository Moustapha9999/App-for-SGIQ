from decimal import Decimal

import pandas as pd
import streamlit as st
from sqlalchemy import select
from sqlalchemy.orm import joinedload

from database.models import Achat, Fournisseur, LigneAchat, Produit
from config import MODES_PAIEMENT, index_mode_paiement
from services.logging_service import log_action
from services.stock_service import mouvement_stock
from utils.crud_ui import render_dataframe
from utils.dialogs import request_dialog, run_confirm_dialog
from utils.ui import page_header


def page_achats(session, user):
    page_header("Gestion des Achats", "Bons d'achat, stock et annulations", "🛒")

    tab_nouveau, tab_hist, tab_modifier, tab_annuler = st.tabs(
        ["➕ Nouveau Bon d'Achat", "📜 Historique & Suivi", "✏️ Modifier", "❌ Annuler un Achat"]
    )

    # ------------------------------------------------------------------ #
    # TAB 1 : NOUVEAU ACHAT
    # ------------------------------------------------------------------ #
    with tab_nouveau:
        fournisseurs = session.scalars(
            select(Fournisseur).where(Fournisseur.statut == "Actif")
        ).all()
        produits = session.scalars(
            select(Produit).where(Produit.statut == "Actif")
        ).all()

        if not fournisseurs or not produits:
            st.warning(
                "⚠️ Veuillez d'abord ajouter des fournisseurs et des produits actifs."
            )
        else:
            st.subheader("📋 Informations Générales")
            c_fourn, c_pay, c_stat = st.columns(3)

            fid = c_fourn.selectbox(
                "Fournisseur",
                [f.id_fournisseur for f in fournisseurs],
                format_func=lambda i: next(
                    f.raison_sociale for f in fournisseurs if f.id_fournisseur == i
                ),
                key="nouvel_achat_fourn",
            )
            mp = c_pay.selectbox(
                "Mode de paiement", MODES_PAIEMENT, key="nouvel_achat_mp"
            )
            statut = c_stat.selectbox(
                "Statut initial", ["Payé", "En attente"], key="nouvel_achat_statut"
            )

            st.markdown("---")
            st.subheader("📦 Articles à inclure")

            if "lignes_achat" not in st.session_state:
                st.session_state.lignes_achat = []

            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 1])

                # ✅ CORRIGÉ : p.designation (p.nom n'existe pas sur Produit)
                code = c1.selectbox(
                    "Désignation Produit",
                    [p.code_produit for p in produits],
                    format_func=lambda x: next(
                        f"{p.code_produit} — {p.designation}"
                        for p in produits if p.code_produit == x
                    ),
                    key="achat_prod",
                )
                qte = c2.number_input("Quantité", min_value=1, value=1, key="achat_qte")
                prix_defaut = float(
                    next(p.prix_achat for p in produits if p.code_produit == code)
                )
                pu = c3.number_input(
                    "Prix unitaire", min_value=0.0, step=0.01,
                    value=prix_defaut, key="achat_pu"
                )
                c4.write("")
                c4.write("")
                btn_ajouter = c4.button("➕ Ajouter", use_container_width=True)

            if btn_ajouter:
                total = Decimal(str(qte)) * Decimal(str(pu))
                # ✅ CORRIGÉ : designation au lieu de nom
                desig = next(p.designation for p in produits if p.code_produit == code)
                st.session_state.lignes_achat.append(
                    {
                        "Code": code,
                        "Désignation": desig,
                        "Quantité": int(qte),
                        "P.U.": float(pu),
                        "Total": float(total),
                    }
                )
                st.toast("Produit ajouté.", icon="📥")

            if st.session_state.lignes_achat:
                st.markdown("### Récapitulatif du panier")
                df_panier = pd.DataFrame(st.session_state.lignes_achat)
                st.dataframe(df_panier, hide_index=True, use_container_width=True)

                montant = sum(
                    Decimal(str(l["Total"])) for l in st.session_state.lignes_achat
                )

                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    if st.button("🗑️ Vider le panier", type="secondary"):
                        st.session_state.lignes_achat = []
                        st.rerun()
                with col_m2:
                    st.metric("Montant Total", f"{montant:,.0f} MRU")
                    if st.button(
                        "💾 Valider l'Achat", type="primary", use_container_width=True
                    ):
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
                            pu_d = Decimal(str(l["P.U."]))
                            tot_d = Decimal(str(l["Total"]))
                            session.add(
                                LigneAchat(
                                    id_achat=achat.id_achat,
                                    code_produit=l["Code"],
                                    quantite=l["Quantité"],
                                    prix_unitaire=pu_d,
                                    total=tot_d,
                                )
                            )
                            # Mise à jour prix d'achat et stock
                            p_obj = session.get(Produit, l["Code"])
                            p_obj.prix_achat = pu_d
                            mouvement_stock(
                                session, l["Code"], "Entrée",
                                l["Quantité"], f"Achat-{achat.id_achat}", user.id_user,
                            )

                        log_action(session, user.id_user, f"Création achat #{achat.id_achat}")
                        session.commit()
                        st.session_state.lignes_achat = []
                        st.toast(f"Achat #{achat.id_achat} enregistré !", icon="✅")
                        st.rerun()

    # ------------------------------------------------------------------ #
    # TAB 2 : HISTORIQUE
    # ------------------------------------------------------------------ #
    with tab_hist:
        achats = session.scalars(
            select(Achat)
            .options(joinedload(Achat.fournisseur))
            .where(Achat.annule == False)
            .order_by(Achat.date.desc())
        ).unique().all()

        if achats:
            df = pd.DataFrame(
                [
                    {
                        "N° Achat": a.id_achat,
                        "Date": a.date.strftime("%d/%m/%Y %H:%M") if a.date else "",
                        "Fournisseur": a.fournisseur.raison_sociale if a.fournisseur else "—",
                        "Montant (MRU)": f"{float(a.montant_total):,.0f}",
                        "Mode Paiement": a.mode_paiement,
                        "Statut": "🟢 Payé" if a.statut == "Payé" else "🟠 En attente",
                    }
                    for a in achats
                ]
            )
            render_dataframe(df)
        else:
            st.info("Aucun achat enregistré.")

    # ------------------------------------------------------------------ #
    # TAB 3 : MODIFIER
    # ------------------------------------------------------------------ #
    with tab_modifier:
        achats = session.scalars(
            select(Achat).where(Achat.annule == False)
        ).all()
        if achats:
            st.subheader("Mise à jour rapide des statuts")
            aid = st.selectbox(
                "Bon d'Achat", [a.id_achat for a in achats], key="mod_aid"
            )
            a = session.get(Achat, aid)

            c_mod1, c_mod2 = st.columns(2)
            statut = c_mod1.selectbox(
                "Nouveau statut", ["Payé", "En attente"],
                index=0 if a.statut == "Payé" else 1,
                key="modifier_achat_statut",
            )
            liste_mp = MODES_PAIEMENT
            mp = c_mod2.selectbox(
                "Mode paiement", liste_mp,
                index=index_mode_paiement(a.mode_paiement, liste_mp),
                key="modifier_achat_mp",
            )

            if st.button("💾 Enregistrer les modifications", type="primary"):
                a.statut = statut
                a.mode_paiement = mp
                log_action(session, user.id_user, f"Modification achat #{aid}")
                session.commit()
                st.toast(f"Achat #{aid} mis à jour.", icon="💾")
                st.rerun()
        else:
            st.info("Aucun achat modifiable.")

    # ------------------------------------------------------------------ #
    # TAB 4 : ANNULER
    # ------------------------------------------------------------------ #
    with tab_annuler:
        achats = session.scalars(
            select(Achat).where(Achat.annule == False)
        ).all()
        if achats:
            st.subheader("⚠️ Zone de Danger")
            st.warning(
                "L'annulation retire automatiquement les quantités du stock."
            )
            aid = st.selectbox(
                "Bon d'Achat à annuler", [a.id_achat for a in achats], key="annul_aid"
            )
            if st.button("❌ Confirmer l'annulation", type="primary"):
                request_dialog("_annul_achat", aid)

            if "_annul_achat" in st.session_state:
                pending_aid = st.session_state["_annul_achat"]

                def _annuler():
                    a = session.get(Achat, pending_aid)
                    for l in a.lignes:
                        try:
                            mouvement_stock(
                                session, l.code_produit, "Sortie",
                                l.quantite, f"Annul-Achat-{pending_aid}", user.id_user,
                            )
                        except ValueError as e:
                            st.error(f"Erreur Stock : {e}")
                            session.rollback()
                            return
                    a.annule = True
                    log_action(session, user.id_user, f"Annulation achat #{pending_aid}")
                    session.commit()
                    st.toast(f"Achat #{pending_aid} annulé.", icon="🗑️")

                run_confirm_dialog(
                    "_annul_achat",
                    f"Annuler l'achat #{pending_aid} ?",
                    "Les quantités seront retirées du stock automatiquement.",
                    _annuler,
                    confirm_label="Annuler l'achat",
                    icon="❌",
                )
        else:
            st.info("Aucun achat disponible pour annulation.")