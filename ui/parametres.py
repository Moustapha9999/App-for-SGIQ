import streamlit as st
from sqlalchemy import select

from database.models import Log, Parametre
from services.logging_service import log_action


def _set_param(session, cle: str, valeur: str):
    p = session.query(Parametre).filter(Parametre.cle == cle).first()
    if p:
        p.valeur = valeur
    else:
        session.add(Parametre(cle=cle, valeur=valeur))


def _get_val(session, cle, default=""):
    p = session.query(Parametre).filter(Parametre.cle == cle).first()
    return p.valeur if p and p.valeur else default


def page_parametres(session, user):
    st.title("⚙️ Paramètres")

    tab_soc, tab_fact, tab_email, tab_backup, tab_logs = st.tabs([
        "🏢 Société", "🧾 Facturation", "📧 E-mail", "💾 Sauvegardes", "📋 Journal",
    ])

    # ── Société ───────────────────────────────────────────────────────────
    with tab_soc:
        st.subheader("Informations de la société")
        with st.form("params_soc"):
            c1, c2 = st.columns(2)
            nom    = c1.text_input("Nom société",   value=_get_val(session, "societe_nom"))
            devise = c2.text_input("Devise",        value=_get_val(session, "devise", "MRU"))
            adresse = st.text_area("Adresse",       value=_get_val(session, "societe_adresse"), height=80)
            tel    = c1.text_input("Téléphone",     value=_get_val(session, "societe_telephone"))
            email  = c2.text_input("Email",         value=_get_val(session, "societe_email"))
            nif    = c1.text_input("NIF / NINEA",   value=_get_val(session, "societe_nif"))
            logo   = c2.text_input("Chemin logo",   value=_get_val(session, "societe_logo"))
            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            for cle, val in [
                ("societe_nom", nom), ("societe_adresse", adresse),
                ("societe_telephone", tel), ("societe_email", email),
                ("societe_nif", nif), ("devise", devise), ("societe_logo", logo),
            ]:
                _set_param(session, cle, val)
            log_action(session, user.id_user, "Mise à jour paramètres société")
            session.commit()
            st.toast("✅ Paramètres société enregistrés !", icon="✅")

    # ── Facturation ───────────────────────────────────────────────────────
    with tab_fact:
        st.subheader("Paramètres de facturation")
        with st.form("params_fact"):
            c1, c2 = st.columns(2)
            tva     = c1.number_input("TVA (%)",
                        value=float(_get_val(session, "tva", "18")), step=0.5)
            prefixe = c2.text_input("Préfixe facture",
                        value=_get_val(session, "facture_prefixe", "FAC"))
            fmt     = st.text_input("Format facture",
                        value=_get_val(session, "facture_format", "{prefix}-{num:06d}"),
                        help="Variables : {prefix}, {num}")
            submitted = st.form_submit_button("💾 Enregistrer", type="primary")

        if submitted:
            _set_param(session, "tva", str(tva))
            _set_param(session, "facture_prefixe", prefixe)
            _set_param(session, "facture_format", fmt)
            session.commit()
            st.toast("✅ Paramètres de facturation enregistrés !", icon="✅")

    # ── E-mail SMTP ───────────────────────────────────────────────────────
    with tab_email:
        st.subheader("Configuration SMTP")
        st.caption("Pour l'envoi automatique des factures par e-mail.")
        with st.form("params_smtp"):
            c1, c2 = st.columns(2)
            host   = c1.text_input("Serveur SMTP",  value=_get_val(session, "smtp_host"),
                        placeholder="smtp.gmail.com")
            port   = c2.text_input("Port",          value=_get_val(session, "smtp_port", "587"))
            usr    = c1.text_input("Utilisateur",   value=_get_val(session, "smtp_user"))
            pwd    = c2.text_input("Mot de passe",  value=_get_val(session, "smtp_password"),
                        type="password")
            from_a = c1.text_input("Expéditeur",    value=_get_val(session, "smtp_from"))
            tls    = c2.checkbox("Utiliser TLS",
                        value=_get_val(session, "smtp_tls", "true").lower() in ("true","1","oui"))
            submitted = st.form_submit_button("💾 Enregistrer SMTP", type="primary")

        if submitted:
            for cle, val in [
                ("smtp_host", host), ("smtp_port", port), ("smtp_user", usr),
                ("smtp_password", pwd), ("smtp_from", from_a),
                ("smtp_tls", "true" if tls else "false"),
            ]:
                _set_param(session, cle, val)
            log_action(session, user.id_user, "Configuration SMTP mise à jour")
            session.commit()
            st.toast("✅ Configuration SMTP enregistrée !", icon="✅")

    # ── Sauvegardes ───────────────────────────────────────────────────────
    with tab_backup:
        from datetime import datetime
        import pandas as pd
        from services.backup_service import create_backup, list_backups

        st.subheader("Sauvegardes de la base de données")
        st.caption("Sauvegarde automatique toutes les 24h au démarrage.")

        c1, c2 = st.columns(2)
        backups = list_backups()
        c2.metric("Sauvegardes stockées", len(backups))

        if c1.button("💾 Sauvegarder maintenant", type="primary"):
            with st.spinner("Sauvegarde en cours..."):
                path = create_backup()
            if path:
                log_action(session, user.id_user, f"Sauvegarde manuelle {path.name}")
                session.commit()
                st.toast(f"✅ Sauvegarde créée : **{path.name}**", icon="💾")
                st.rerun()
            else:
                st.warning("Sauvegarde disponible uniquement avec SQLite.")

        if backups:
            st.divider()
            st.dataframe(pd.DataFrame([{
                "Fichier":      p.name,
                "Taille (Ko)":  round(p.stat().st_size / 1024, 1),
                "Date":         datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
            } for p in backups]), hide_index=True, use_container_width=True)

            sel = st.selectbox("Restaurer depuis", [p.name for p in backups])
            if st.button("♻️ Restaurer cette sauvegarde"):
                st.warning(
                    "Pour restaurer : arrêtez l'application, remplacez "
                    "`data/sgiq.db` par la sauvegarde ci-dessous, puis relancez."
                )
                st.code(str(next(p for p in backups if p.name == sel)))

    # ── Journal des actions ───────────────────────────────────────────────
    with tab_logs:
        import pandas as pd
        st.subheader("Journal des actions utilisateurs")
        logs = session.scalars(
            select(Log).order_by(Log.date_action.desc()).limit(200)
        ).all()
        if logs:
            df = pd.DataFrame([{
                "Date":   l.date_action.strftime("%d/%m/%Y %H:%M:%S") if l.date_action else "—",
                "User":   l.id_user or "—",
                "Action": l.action,
            } for l in logs])
            st.caption(f"{len(logs)} dernières actions")
            st.dataframe(df, hide_index=True, use_container_width=True)
        else:
            st.info("Aucune action enregistrée.")