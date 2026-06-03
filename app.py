"""
SGIQ — Système de Gestion Intégré pour Quincaillerie
Point d'entrée Streamlit
"""

import streamlit as st

from config import MENU_ACCESS
from database.connection import SessionLocal, init_db
from services.auth import authenticate
from services.seed import seed_if_empty
from ui.achats import page_achats
from ui.clients import page_clients
from ui.commandes import page_commandes
from ui.credits import page_credits
from ui.dashboard import page_dashboard
from ui.fournisseurs import page_fournisseurs
from ui.parametres import page_parametres
from ui.produits import page_produits
from ui.rapports import page_rapports
from ui.stock import page_stock
from ui.utilisateurs import page_utilisateurs
from ui.ventes import page_ventes

st.set_page_config(
    page_title="SGIQ — Quincaillerie",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

PAGES = {
    "Dashboard": page_dashboard,
    "Utilisateurs": page_utilisateurs,
    "Clients": page_clients,
    "Fournisseurs": page_fournisseurs,
    "Produits": page_produits,
    "Stock": page_stock,
    "Achats": page_achats,
    "Ventes": page_ventes,
    "Commandes": page_commandes,
    "Crédits": page_credits,
    "Rapports": page_rapports,
    "Paramètres": page_parametres,
}


@st.cache_resource
def bootstrap_db():
    init_db()
    session = SessionLocal()
    try:
        seed_if_empty(session)
        session.commit()
    finally:
        session.close()
    from services.backup_service import run_auto_backup_if_needed

    backup_path = run_auto_backup_if_needed()
    return str(backup_path) if backup_path else None


def login_page():
    st.title("🔧 SGIQ")
    st.caption("Système de Gestion Intégré pour Quincaillerie")
    with st.form("login"):
        username = st.text_input("Nom d'utilisateur")
        password = st.text_input("Mot de passe", type="password")
        if st.form_submit_button("Connexion", type="primary", use_container_width=True):
            session = SessionLocal()
            try:
                user = authenticate(session, username, password)
                if user:
                    st.session_state.user = {
                        "id": user.id_user,
                        "username": user.username,
                        "nom": f"{user.nom} {user.prenom}",
                        "role": user.role,
                    }
                    st.rerun()
                else:
                    st.error("Identifiants incorrects ou compte inactif.")
            finally:
                session.close()
    with st.expander("Comptes de démonstration"):
        st.markdown(
            """
            | Rôle | Username | Mot de passe |
            |------|----------|--------------|
            | Admin | `admin` | `admin123` |
            | Caissier | `caissier` | `caissier123` |
            | Magasinier | `magasinier` | `magasin123` |
            """
        )


def main():
    backup_msg = bootstrap_db()
    if backup_msg and "backup_notified" not in st.session_state:
        st.session_state.backup_notified = True

    if "user" not in st.session_state:
        login_page()
        return

    user_info = st.session_state.user
    role = user_info["role"]
    allowed = MENU_ACCESS.get(role, [])

    with st.sidebar:
        st.markdown(f"### Bienvenue, {user_info['nom']}")
        st.caption(f"Rôle: **{role}**")
        if backup_msg:
            st.caption(f"💾 Sauvegarde auto : OK")
        menu = st.radio("Navigation", allowed, label_visibility="collapsed")
        if st.button("Déconnexion", use_container_width=True):
            del st.session_state.user
            for key in ("lignes_vente", "lignes_achat", "lignes_cmd"):
                st.session_state.pop(key, None)
            st.rerun()

    session = SessionLocal()
    try:

        class UserCtx:
            id_user = user_info["id"]
            role = user_info["role"]

        user = UserCtx()
        page_fn = PAGES.get(menu)
        if page_fn:
            page_fn(session, user)
    finally:
        session.close()


if __name__ == "__main__":
    main()

