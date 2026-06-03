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
    st.title("🛒 Gestion des Achats")
    st.markdown("---")

    tab_nouveau, tab_hist, tab_modifier, tab_annuler = st.tabs(
        ["➕ Nouveau Bon d'Achat", "📜 Historique & Suivi", "✏️ Modifier", "❌ Annuler un Achat"]
    )

    # ----------------------------------------------------
    # TAB 1 : NOUVEAU ACHAT
    # ----------------------------------------------------
    with tab_nouveau:
        fournisseurs = session.scalars(select(Fournisseur).where(Fournisseur.statut == "Actif")).all()
        produits = session.scalars(select(Produit).where(Produit.statut == "Actif")).all()
        
        if not fournisseurs or not produits:
            st.warning("⚠️ Action requise : Veuillez d'abord ajouter des fournisseurs et des produits actifs dans le système.")
        else:
            # Section Métadonnées de l'Achat
            st.subheader("📋 Informations Générales")
            c_fourn, c_pay, c_stat = st.columns(3)
            
            with c_fourn:
                fid = st.selectbox(
                    "Fournisseur", 
                    [f.id_fournisseur for f in fournisseurs], 
                    format_func=lambda i: next(f.raison_sociale for f in fournisseurs if f.id_fournisseur == i),
                    key="nouvel_achat_fourn"
                )
            with c_pay:
                mp = st.selectbox("Mode de paiement", ["Espèces", "Virement", "Chèque"], key="nouvel_achat_mp")
                
            with c_stat:
                statut = st.selectbox("Statut initial", ["Payé", "En attente"], key="nouvel_achat_statut")

            st.markdown("---")
            
            # Section Ajout des Articles
            st.subheader("📦 Articles à inclure")
            if "lignes_achat" not in st.session_state:
                st.session_state.lignes_achat = []

            # Ajout d'une bordure visuelle pour le formulaire de ligne
            with st.container(border=True):
                c1, c2, c3, c4 = st.columns([3, 1, 1.5, 1])
                with c1:
                    code = st.selectbox(
                        "Désignation Produit", 
                        [p.code_produit for p in produits], 
                        format_func=lambda x: f"{x} - {next(p.nom for p in produits if p.code_produit == x)}",
                        key="achat_prod"
                    )
                with c2:
                    qte = st.number_input("Quantité", min_value=1, value=1, key="achat_qte")
                with c3:
                    prix_defaut = float(next(p.prix_achat for p in produits if p.code_produit == code))
                    pu = st.number_input("Prix unitaire (€)", min_value=0.0, step=0.01, value=prix_defaut, key="achat_pu")
                with c4:
                    st.write("") # Espacement alignement vertical
                    st.write("")
                    btn_ajouter = st.button("➕ Ajouter", use_container_width=True)

                if btn_ajouter:
                    total = Decimal(str(qte)) * Decimal(str(pu))
                    st.session_state.lignes_achat.append({
                        "Code": code, 
                        "Désignation": next(p.nom for p in produits if p.code_produit == code),
                        "Quantité": int(qte), 
                        "P.U. (€)": float(pu), 
                        "Total (€)": float(total)
                    })
                    st.toast("Produit ajouté à la liste temporaire.", icon="📥")

            # Affichage du panier s'il contient des éléments
            if st.session_state.lignes_achat:
                st.markdown("### Récapitulatif du panier")
                df_panier = pd.DataFrame(st.session_state.lignes_achat)
                st.dataframe(df_panier, hide_index=True, use_container_width=True)
                
                # Calcul et affichage pro du total
                montant = sum(Decimal(str(l["Total (€)"])) for l in st.session_state.lignes_achat)
                
                col_m1, col_m2 = st.columns([2, 1])
                with col_m1:
                    if st.button("🗑️ Vider le panier", type="secondary"):
                        st.session_state.lignes_achat = []
                        st.toast("Panier vidé.", icon="🗑️")
                        st.rerun()
                with col_m2:
                    st.metric(label="Montant Total de la Commande", value=f"{montant:.2f} €")
                    if st.button("💾 Valider et Enregistrer l'Achat", type="primary", use_container_width=True):
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
                            pu_decimal = Decimal(str(l["P.U. (€)"]))
                            tot_decimal = Decimal(str(l["Total (€)"]))
                            session.add(
                                LigneAchat(
                                    id_achat=achat.id_achat,
                                    code_produit=l["Code"],
                                    quantite=l["Quantité"],
                                    prix_unitaire=pu_decimal,
                                    total=tot_decimal,
                                )
                            )
                            # Mise à jour automatique du dernier prix d'achat
                            p = session.get(Produit, l["Code"])
                            p.prix_achat = pu_decimal
                            mouvement_stock(session, l["Code"], "Entrée", l["Quantité"], f"Achat-{achat.id_achat}", user.id_user)
                        
                        log_action(session, user.id_user, f"Création achat #{achat.id_achat}")
                        session.commit()
                        st.session_state.lignes_achat = []
                        st.toast(f"Achat #{achat.id_achat} enregistré avec succès !", icon="✅")
                        st.rerun()

    # ----------------------------------------------------
    # TAB 2 : HISTORIQUE
    # ----------------------------------------------------
    with tab_hist:
        achats = session.scalars(
            select(Achat).options(joinedload(Achat.fournisseur)).where(Achat.annule == False).order_by(Achat.date.desc())
        ).unique().all()
        
        if achats:
            df = pd.DataFrame(
                [
                    {
                        "N° Achat": a.id_achat,
                        "Date": a.date.strftime("%d/%m/%Y %H:%M") if a.date else "",
                        "Fournisseur": a.fournisseur.raison_sociale if a.fournisseur else "Inconnu",
                        "Montant Total (€)": float(a.montant_total),
                        "Mode Paiement": a.mode_paiement,
                        "Statut": "🟢 Payé" if a.statut == "Payé" else "🟠 En attente",
                    }
                    for a in achats
                ]
            )
            render_dataframe(df)
        else:
            st.info("Aucun achat enregistré dans l'historique.")

    # ----------------------------------------------------
    # TAB 3 : MODIFIER
    # ----------------------------------------------------
    with tab_modifier:
        achats = session.scalars(select(Achat).where(Achat.annule == False)).all()
        if achats:
            st.subheader("Mise à jour rapide des statuts")
            aid = st.selectbox("Sélectionner le numéro du Bon d'Achat", [a.id_achat for a in achats], key="mod_aid")
            a = session.get(Achat, aid)
            
            c_mod1, c_mod2 = st.columns(2)
            with c_mod1:
                statut = st.selectbox("Nouveau statut", ["Payé", "En attente"], index=0 if a.statut == "Payé" else 1, key="modifier_achat_statut")
            with c_mod2:
                liste_mp = ["Espèces", "Virement", "Chèque"]
                index_mp = liste_mp.index(a.mode_paiement) if a.mode_paiement in liste_mp else 0
                mp = st.selectbox("Mode paiement", liste_mp, index=index_mp, key="modifier_achat_mp")
            
            if st.button("💾 Enregistrer les modifications", type="primary"):
                a.statut = statut
                a.mode_paiement = mp
                log_action(session, user.id_user, f"Modification achat #{aid}")
                session.commit()
                st.toast(f"Le bon d'achat #{aid} a été mis à jour.", icon="💾")
                st.rerun()
        else:
            st.info("Aucun achat modifiable.")

    # ----------------------------------------------------
    # TAB 4 : ANNULER
    # ----------------------------------------------------
    with tab_annuler:
        achats = session.scalars(select(Achat).where(Achat.annule == False)).all()
        if achats:
            st.subheader("Zone de Danger")
            st.warning("⚠️ L'annulation d'un achat retirera automatiquement les quantités injectées dans le stock.")
            
            aid = st.selectbox("Sélectionner le numéro du Bon d'Achat à annuler", [a.id_achat for a in achats], key="annul_aid")
            
            # Demande de confirmation
            confirmer = st.checkbox("Je confirme vouloir annuler définitivement cette opération et impacter le stock.", key="annul_achat_confirm")
            
            if st.button("❌ Confirmer l'annulation", type="primary", disabled=not confirmer):
                a = session.get(Achat, aid)
                for l in a.lignes:
                    try:
                        mouvement_stock(session, l.code_produit, "Sortie", l.quantite, f"Annul-Achat-{aid}", user.id_user)
                    except ValueError as e:
                        st.error(f"Erreur Stock : {str(e)}. Impossible d'annuler l'achat car le stock deviendrait négatif.")
                        session.rollback()
                        return
                a.annule = True
                log_action(session, user.id_user, f"Annulation achat #{aid}")
                session.commit()
                st.toast(f"L'achat #{aid} a été annulé et le stock corrigé.", icon="🗑️")
                st.rerun()
        else:
            st.info("Aucun achat disponible pour annulation.")