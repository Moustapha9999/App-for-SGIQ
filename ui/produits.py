# ui/produits.py — avec onglet Import en masse
from decimal import Decimal
from pathlib import Path

import pandas as pd
import streamlit as st
from sqlalchemy import select

from database.models import Produit
from services.logging_service import log_action
from services.stock_service import calculer_marge
from utils.crud_ui import render_dataframe

CATEGORIES = [
    "Ciment", "Fer", "Peinture", "Électricité", "Plomberie",
    "Outillage", "Visserie", "Serrurerie", "Autre",
]
UNITES = ["Pièce", "Sac", "Mètre", "Rouleau", "Bidon", "Barre", "Boîte", "Kg"]


def page_produits(session, user):
    st.title("📦 Gestion des Produits")

    tab_liste, tab_ajouter, tab_import, tab_modifier, tab_supprimer, tab_cat = st.tabs([
        "📋 Liste", "➕ Ajouter", "📥 Import en masse",
        "✏️ Modifier", "🗑️ Supprimer", "📊 Catégories",
    ])

    # ── Liste ─────────────────────────────────────────────────────────────
    with tab_liste:
        c1, c2 = st.columns(2)
        filtre_code = c1.text_input("🔍 Code / Désignation",
                                    placeholder="PRD-001 ou Ciment...")
        filtre_cat  = c2.selectbox("Catégorie", ["Toutes"] + CATEGORIES,
                                   key="liste_prod_cat")

        produits = session.scalars(
            select(Produit).order_by(Produit.code_produit)
        ).all()
        df = pd.DataFrame([{
            "Code":        p.code_produit,
            "Désignation": p.designation,
            "Catégorie":   p.categorie,
            "P.Achat":     f"{float(p.prix_achat):,.0f}",
            "P.Vente":     f"{float(p.prix_vente):,.0f}",
            "Marge":       f"{float(p.marge):,.0f}",
            "Stock":       p.stock,
            "Min":         p.stock_minimum,
            "Alerte": (
                "🔴 Rupture" if p.stock == 0
                else ("🟡 Faible" if p.stock <= p.stock_minimum else "🟢 OK")
            ),
            "Statut": p.statut,
        } for p in produits])

        if filtre_code:
            df = df[
                df["Code"].str.contains(filtre_code, case=False, na=False) |
                df["Désignation"].str.contains(filtre_code, case=False, na=False)
            ]
        if filtre_cat != "Toutes":
            df = df[df["Catégorie"] == filtre_cat]

        st.caption(f"{len(df)} produit(s)")
        render_dataframe(df)

    # ── Ajouter ───────────────────────────────────────────────────────────
    with tab_ajouter:
        st.subheader("Nouveau produit")
        with st.form("add_prod", clear_on_submit=True):
            c1, c2 = st.columns(2)
            code  = c1.text_input("Code produit *", placeholder="PRD-008")
            desig = c2.text_input("Désignation *",  placeholder="Ciment CEM II 50kg")
            cat   = c1.selectbox("Catégorie *", CATEGORIES)
            unite = c2.selectbox("Unité", UNITES)
            pa    = c1.number_input("Prix achat", min_value=0.0, step=1.0)
            pv    = c2.number_input("Prix vente", min_value=0.0, step=1.0)
            stock = c1.number_input("Stock initial", min_value=0, step=1, value=0)
            smin  = c2.number_input("Stock minimum", min_value=0, step=1, value=5)
            emp   = c1.text_input("Emplacement", placeholder="Zone A-1")
            statut = c2.selectbox("Statut", ["Actif", "Inactif"])

            marge     = calculer_marge(Decimal(str(pa)), Decimal(str(pv)))
            marge_pct = (float(marge) / pa * 100) if pa > 0 else 0
            st.info(f"💡 Marge calculée : **{float(marge):,.0f}** ({marge_pct:.1f} %)")

            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            if not code.strip() or not desig.strip():
                st.error("❌ Le code et la désignation sont obligatoires.")
            elif session.get(Produit, code.upper()):
                st.error(f"❌ Le code **{code.upper()}** existe déjà.")
            else:
                session.add(Produit(
                    code_produit=code.upper().strip(),
                    designation=desig.strip(),
                    categorie=cat, unite=unite,
                    prix_achat=Decimal(str(pa)),
                    prix_vente=Decimal(str(pv)),
                    stock=int(stock), stock_minimum=int(smin),
                    marge=marge, emplacement=emp or None, statut=statut,
                ))
                log_action(session, user.id_user, f"Ajout produit {code.upper()}")
                session.commit()
                st.toast(f"✅ Produit **{desig}** ajouté !", icon="✅")
                st.rerun()

    # ── Import en masse ───────────────────────────────────────────────────
    with tab_import:
        _render_import(session, user)

    # ── Modifier ──────────────────────────────────────────────────────────
    with tab_modifier:
        produits = session.scalars(
            select(Produit).order_by(Produit.code_produit)
        ).all()
        if not produits:
            st.info("Aucun produit à modifier.")
        else:
            code = st.selectbox(
                "Sélectionner le produit",
                [p.code_produit for p in produits],
                format_func=lambda x: next(
                    f"{p.code_produit} — {p.designation}"
                    for p in produits if p.code_produit == x
                ),
                key="mod_prod_select",
            )
            p = session.get(Produit, code)
            with st.form("edit_prod"):
                c1, c2 = st.columns(2)
                desig_e = c1.text_input("Désignation", value=p.designation)
                cat_e   = c2.selectbox("Catégorie", CATEGORIES,
                            index=CATEGORIES.index(p.categorie)
                            if p.categorie in CATEGORIES else len(CATEGORIES)-1)
                unite_e = c1.selectbox("Unité", UNITES,
                            index=UNITES.index(p.unite)
                            if p.unite in UNITES else 0)
                pa_e    = c2.number_input("Prix achat",
                            value=float(p.prix_achat), step=1.0)
                pv_e    = c1.number_input("Prix vente",
                            value=float(p.prix_vente), step=1.0)
                smin_e  = c2.number_input("Stock minimum",
                            value=int(p.stock_minimum), step=1)
                emp_e   = c1.text_input("Emplacement", value=p.emplacement or "")
                st_e    = c2.selectbox("Statut", ["Actif", "Inactif"],
                            index=0 if p.statut == "Actif" else 1)
                update  = st.form_submit_button("💾 Mettre à jour", type="primary")

            if update:
                p.designation   = desig_e
                p.categorie     = cat_e
                p.unite         = unite_e
                p.prix_achat    = Decimal(str(pa_e))
                p.prix_vente    = Decimal(str(pv_e))
                p.marge         = calculer_marge(p.prix_achat, p.prix_vente)
                p.stock_minimum = smin_e
                p.emplacement   = emp_e or None
                p.statut        = st_e
                log_action(session, user.id_user, f"Modification produit {code}")
                session.commit()
                st.toast(f"✅ Produit **{desig_e}** mis à jour !", icon="✅")
                st.rerun()

    # ── Supprimer ─────────────────────────────────────────────────────────
    with tab_supprimer:
        produits = session.scalars(
            select(Produit).order_by(Produit.code_produit)
        ).all()
        if not produits:
            st.info("Aucun produit à supprimer.")
        else:
            code = st.selectbox(
                "Sélectionner le produit à supprimer",
                [p.code_produit for p in produits],
                format_func=lambda x: next(
                    f"{p.code_produit} — {p.designation}"
                    for p in produits if p.code_produit == x
                ),
                key="del_prod_select",
            )
            p = session.get(Produit, code)
            st.warning(
                f"⚠️ Vous allez supprimer **{p.designation}** ({p.code_produit})."
            )
            confirmer = st.checkbox("Je confirme", key="del_prod_confirm")
            if st.button("🗑️ Supprimer", type="primary",
                         disabled=not confirmer, key="del_prod_btn"):
                nom_supp = p.designation
                log_action(session, user.id_user, f"Suppression produit {code}")
                session.delete(p)
                session.commit()
                st.toast(f"🗑️ Produit **{nom_supp}** supprimé.", icon="🗑️")
                st.rerun()

    # ── Catégories ────────────────────────────────────────────────────────
    with tab_cat:
        produits = session.scalars(select(Produit)).all()
        if produits:
            df_cat = pd.DataFrame([{
                "Catégorie": p.categorie, "Stock": p.stock,
                "Valeur": float(p.stock * p.prix_achat),
            } for p in produits])
            col1, col2 = st.columns(2)
            with col1:
                st.markdown("**Produits par catégorie**")
                st.bar_chart(df_cat["Catégorie"].value_counts())
            with col2:
                st.markdown("**Stock par catégorie**")
                st.bar_chart(df_cat.groupby("Catégorie")["Stock"].sum())
        else:
            st.info("Aucun produit.")


# ── Onglet Import ─────────────────────────────────────────────────────────

def _render_import(session, user):
    from services.import_service import (
        lire_excel, lire_csv, lire_pdf,
        normaliser_dataframe, valider_dataframe,
        importer_produits, generer_template_excel,
    )

    st.subheader("📥 Import de produits en masse")

    # ── Télécharger le template ───────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Étape 1 — Télécharge le template Excel**")
        st.caption(
            "Remplis le fichier avec tes produits en respectant les colonnes. "
            "Les colonnes marquées * sont obligatoires."
        )
        col_dl, col_info = st.columns([1, 2])
        with col_dl:
            template_bytes = generer_template_excel()
            st.download_button(
                "📄 Télécharger le template Excel",
                data=template_bytes,
                file_name="template_produits_SGIQ.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
                type="primary",
                use_container_width=True,
            )
        with col_info:
            st.markdown("""
**Colonnes disponibles :**
`code_produit` `designation` `categorie` `unite` `prix_achat` `prix_vente`
`stock` `stock_minimum` `emplacement` `statut`

**Formats acceptés :** Excel (.xlsx, .xls) · CSV (.csv) · PDF catalogue
            """)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Upload fichier ────────────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Étape 2 — Importe ton fichier**")

        uploaded = st.file_uploader(
            "Glisse ton fichier ici ou clique pour choisir",
            type=["xlsx", "xls", "csv", "pdf"],
            key="import_produits_file",
            label_visibility="collapsed",
        )

        if not uploaded:
            st.info("📂 Formats acceptés : Excel (.xlsx/.xls), CSV (.csv), PDF catalogue")
            return

        # Lecture selon le format
        file_bytes = uploaded.read()
        ext = Path(uploaded.name).suffix.lower()

        try:
            with st.spinner("Lecture du fichier..."):
                if ext in [".xlsx", ".xls"]:
                    df_raw = lire_excel(file_bytes)
                    fmt = "Excel"
                elif ext == ".csv":
                    df_raw = lire_csv(file_bytes)
                    fmt = "CSV"
                elif ext == ".pdf":
                    df_raw = lire_pdf(file_bytes)
                    fmt = "PDF"
                else:
                    st.error("Format non supporté.")
                    return

            if df_raw.empty:
                st.error("❌ Fichier vide ou aucun tableau détecté.")
                return

            st.success(f"✅ Fichier **{uploaded.name}** lu ({fmt}) — "
                      f"{len(df_raw)} ligne(s) détectée(s)")

        except Exception as e:
            st.error(f"❌ Erreur de lecture : {e}")
            return

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Normalisation + Validation ────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Étape 3 — Validation des données**")

        try:
            df_norm  = normaliser_dataframe(df_raw)
            resultats = valider_dataframe(df_norm, session)
        except Exception as e:
            st.error(f"❌ Erreur de validation : {e}")
            return

        stats = resultats["stats"]
        col1, col2, col3, col4 = st.columns(4)
        col1.metric("Total lignes",   stats["total"])
        col2.metric("✅ Valides",      stats["valides"],
                    delta=None if stats["valides"] == 0 else f"+{stats['valides']}")
        col3.metric("❌ Erreurs",      stats["erreurs"],
                    delta=None if stats["erreurs"] == 0 else f"-{stats['erreurs']}",
                    delta_color="inverse")
        col4.metric("⚠️ Déjà en base", stats["doublons_db"])

        # Aperçu produits valides
        if resultats["valides"]:
            st.markdown(f"**Aperçu — {len(resultats['valides'])} produit(s) prêts à importer**")
            df_apercu = pd.DataFrame([{
                "Code":        v["code_produit"],
                "Désignation": v["designation"],
                "Catégorie":   v["categorie"],
                "Prix achat":  f"{float(v['prix_achat']):,.0f}",
                "Prix vente":  f"{float(v['prix_vente']):,.0f}",
                "Stock":       v["stock"],
                "Statut":      v["statut"],
            } for v in resultats["valides"]])
            st.dataframe(df_apercu, hide_index=True,
                        use_container_width=True, height=220)

        # Erreurs détectées
        if resultats["erreurs"]:
            with st.expander(
                f"❌ {len(resultats['erreurs'])} ligne(s) avec erreurs — cliquez pour voir",
                expanded=len(resultats["erreurs"]) <= 5,
            ):
                st.dataframe(
                    pd.DataFrame(resultats["erreurs"]),
                    hide_index=True, use_container_width=True,
                )
                st.caption(
                    "Corrigez ces lignes dans votre fichier et re-importez."
                )

        # Doublons en base
        if resultats["doublons_db"]:
            with st.expander(
                f"⚠️ {len(resultats['doublons_db'])} produit(s) déjà en base"
            ):
                st.write(", ".join(sorted(resultats["doublons_db"])))
                st.caption("Choisissez ci-dessous quoi faire avec ces produits.")

    if not resultats["valides"]:
        st.warning("⚠️ Aucun produit valide à importer. Corrigez les erreurs d'abord.")
        return

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Options + Confirmation ────────────────────────────────────────────
    with st.container(border=True):
        st.markdown("**Étape 4 — Options d'import**")

        col_opt1, col_opt2 = st.columns(2)

        if resultats["doublons_db"]:
            mode_doublon = col_opt1.radio(
                "Produits déjà existants en base",
                ["ignorer", "mettre_a_jour"],
                format_func=lambda x: (
                    "⏭️ Ignorer (garder les données actuelles)"
                    if x == "ignorer"
                    else "🔄 Mettre à jour avec les nouvelles données"
                ),
                key="import_mode_doublon",
            )
        else:
            mode_doublon = "ignorer"
            col_opt1.info("Aucun doublon détecté.")

        nb_a_importer = len(resultats["valides"])
        col_opt2.markdown(f"""
        <div style='background:#EFF6FF;border:1px solid #DBEAFE;
            border-radius:8px;padding:12px 16px'>
            <p style='margin:0;font-size:0.85rem;font-weight:600;color:#1E40AF'>
                Résumé de l'import
            </p>
            <p style='margin:6px 0 0;font-size:0.82rem;color:#1E3A5F'>
                📦 {nb_a_importer} produit(s) à insérer<br>
                ⚠️ {len(resultats['doublons_db'])} doublon(s) à traiter<br>
                ❌ {len(resultats['erreurs'])} ligne(s) ignorée(s)
            </p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

        confirmer = st.checkbox(
            f"Je confirme l'import de **{nb_a_importer}** produit(s)",
            key="import_confirm",
        )

        if st.button(
            f"🚀 Lancer l'import ({nb_a_importer} produits)",
            type="primary",
            disabled=not confirmer,
            use_container_width=True,
            key="btn_lancer_import",
        ):
            with st.spinner(f"Import en cours — {nb_a_importer} produits..."):
                try:
                    rapport = importer_produits(
                        session,
                        resultats["valides"],
                        resultats["doublons_db"],
                        mode_doublon=mode_doublon,
                    )
                    log_action(
                        session, user.id_user,
                        f"Import masse : {rapport['inseres']} insérés, "
                        f"{rapport['mis_a_jour']} maj, {rapport['ignores']} ignorés"
                    )
                    session.commit()
                except Exception as e:
                    st.error(f"❌ Erreur lors de l'import : {e}")
                    return

            # Rapport final
            st.balloons()
            st.success("🎉 Import terminé avec succès !")
            col_r1, col_r2, col_r3 = st.columns(3)
            col_r1.metric("✅ Insérés",    rapport["inseres"])
            col_r2.metric("🔄 Mis à jour", rapport["mis_a_jour"])
            col_r3.metric("⏭️ Ignorés",    rapport["ignores"])
            st.rerun()