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


def page_parametres(session, user):
    st.header("⚙️ Paramètres")

    def get_val(cle, default=""):
        p = session.query(Parametre).filter(Parametre.cle == cle).first()
        return p.valeur if p and p.valeur else default

    tab_soc, tab_fact, tab_email, tab_backup, tab_logs = st.tabs(
        ["Société", "Facturation", "E-mail", "Sauvegardes", "Journal"]
    )

    with tab_soc:
        with st.form("params_soc"):
            nom = st.text_input("Nom société", value=get_val("societe_nom"))
            adresse = st.text_area("Adresse", value=get_val("societe_adresse"))
            tel = st.text_input("Téléphone", value=get_val("societe_telephone"))
            email = st.text_input("Email", value=get_val("societe_email"))
            nif = st.text_input("NIF", value=get_val("societe_nif"))
            devise = st.text_input("Devise", value=get_val("devise", "MAD"))
            logo = st.text_input("Chemin logo (local)", value=get_val("societe_logo"))
            if st.form_submit_button("Enregistrer", type="primary"):
                for cle, val in [
                    ("societe_nom", nom), ("societe_adresse", adresse),
                    ("societe_telephone", tel), ("societe_email", email),
                    ("societe_nif", nif), ("devise", devise), ("societe_logo", logo),
                ]:
                    _set_param(session, cle, val)
                log_action(session, user.id_user, "Mise à jour paramètres société")
                session.commit()
                st.success("Paramètres enregistrés.")

    with tab_fact:
        with st.form("params_fact"):
            tva = st.number_input("TVA (%)", value=float(get_val("tva", "19")), step=0.5)
            prefixe = st.text_input("Préfixe facture", value=get_val("facture_prefixe", "FAC"))
            fmt = st.text_input("Format facture", value=get_val("facture_format", "{prefix}-{num:06d}"))
            if st.form_submit_button("Enregistrer", type="primary"):
                _set_param(session, "tva", str(tva))
                _set_param(session, "facture_prefixe", prefixe)
                _set_param(session, "facture_format", fmt)
                session.commit()
                st.success("Paramètres facture enregistrés.")

    with tab_email:
        st.caption("Configuration SMTP pour l'envoi des factures (Gmail, Outlook, serveur privé).")
        with st.form("params_smtp"):
            host = st.text_input("Serveur SMTP", value=get_val("smtp_host"), placeholder="smtp.gmail.com")
            port = st.text_input("Port", value=get_val("smtp_port", "587"))
            user = st.text_input("Utilisateur SMTP", value=get_val("smtp_user"))
            pwd = st.text_input("Mot de passe SMTP", value=get_val("smtp_password"), type="password")
            from_addr = st.text_input("Adresse expéditeur", value=get_val("smtp_from"))
            tls = st.checkbox("Utiliser TLS", value=get_val("smtp_tls", "true").lower() in ("true", "1", "oui"))
            if st.form_submit_button("Enregistrer SMTP", type="primary"):
                for cle, val in [
                    ("smtp_host", host), ("smtp_port", port), ("smtp_user", user),
                    ("smtp_password", pwd), ("smtp_from", from_addr), ("smtp_tls", "true" if tls else "false"),
                ]:
                    _set_param(session, cle, val)
                log_action(session, user.id_user, "Configuration SMTP")
                session.commit()
                st.success("Paramètres e-mail enregistrés.")

    with tab_backup:
        from pathlib import Path

        from services.backup_service import create_backup, list_backups

        st.caption("Sauvegarde automatique toutes les 24 h au démarrage de l'application.")
        c1, c2 = st.columns(2)
        if c1.button("Sauvegarder maintenant", type="primary"):
            path = create_backup()
            if path:
                log_action(session, user.id_user, f"Sauvegarde manuelle {path.name}")
                session.commit()
                st.success(f"Sauvegarde créée : `{path.name}`")
            else:
                st.warning("Sauvegarde disponible uniquement avec SQLite.")
        backups = list_backups()
        c2.metric("Sauvegardes stockées", len(backups))
        if backups:
            import pandas as pd
            from datetime import datetime

            st.dataframe(
                pd.DataFrame(
                    [
                        {
                            "Fichier": p.name,
                            "Taille (Ko)": round(p.stat().st_size / 1024, 1),
                            "Date": datetime.fromtimestamp(p.stat().st_mtime).strftime("%d/%m/%Y %H:%M"),
                        }
                        for p in backups
                    ]
                ),
                hide_index=True,
                use_container_width=True,
            )
            sel = st.selectbox("Restaurer depuis", [p.name for p in backups])
            if st.button("Restaurer cette sauvegarde"):
                st.warning("Fermez l'application, remplacez manuellement `data/sgiq.db` par la copie choisie, puis relancez.")
                st.code(str(next(p for p in backups if p.name == sel)), language=None)

    with tab_logs:
        logs = session.scalars(select(Log).order_by(Log.date_action.desc()).limit(100)).all()
        import pandas as pd
        st.dataframe(
            pd.DataFrame([{"Date": l.date_action, "User": l.id_user, "Action": l.action} for l in logs]),
            hide_index=True,
            use_container_width=True,
        )
