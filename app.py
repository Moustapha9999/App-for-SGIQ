"""
SGIQ — Système de Gestion Intégré pour Quincaillerie
Point d'entrée Streamlit — version avec UI améliorée
"""

from pathlib import Path

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

# ── Config page ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SGIQ — Quincaillerie",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Injection CSS global ─────────────────────────────────────────────────
def _load_css():
    css_path = Path(__file__).parent / ".streamlit" / "style.css"
    if css_path.exists():
        with open(css_path) as f:
            css = f.read()
    else:
        css = ""
    # CSS inline de base (toujours chargé)
    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }
    .stApp { background: #F8FAFC; }

    /* Sidebar */
    [data-testid="stSidebar"] { background: #1E3A5F !important; }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    [data-testid="stSidebar"] strong, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }
    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        color: #CBD5E1 !important; border-radius: 8px !important;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.14) !important; color: white !important;
    }

    /* Metric cards */
    [data-testid="metric-container"] {
        background: white !important; border: 1px solid #E2E8F0 !important;
        border-radius: 10px !important; padding: 1rem 1.25rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.07) !important;
    }
    [data-testid="stMetricLabel"] {
        font-size: 0.75rem !important; font-weight: 500 !important;
        color: #94A3B8 !important; text-transform: uppercase; letter-spacing: 0.05em;
    }
    [data-testid="stMetricValue"] {
        font-size: 1.5rem !important; font-weight: 600 !important;
        color: #0F172A !important; font-family: 'DM Mono', monospace !important;
    }

    /* Tabs */
    .stTabs [data-baseweb="tab-list"] {
        background: #F1F5F9; border-radius: 10px; padding: 4px; gap: 2px;
    }
    .stTabs [data-baseweb="tab"] {
        border-radius: 7px !important; padding: 6px 18px !important;
        font-size: 0.84rem !important; font-weight: 500 !important;
        color: #64748B !important; background: transparent !important;
        border: none !important; transition: all 0.15s !important;
    }
    .stTabs [aria-selected="true"] {
        background: white !important; color: #2563EB !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.08) !important;
    }

    /* Primary button */
    .stButton button[kind="primary"] {
        background: #2563EB !important; border: none !important;
        color: white !important; border-radius: 8px !important;
        font-weight: 500 !important; transition: all 0.2s !important;
        box-shadow: 0 1px 3px rgba(37,99,235,0.25) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: #1D4ED8 !important; transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    }
    .stButton button[kind="secondary"] {
        background: white !important; border: 1px solid #E2E8F0 !important;
        color: #334155 !important; border-radius: 8px !important;
        font-weight: 500 !important; transition: all 0.2s !important;
    }
    .stButton button[kind="secondary"]:hover {
        background: #F8FAFC !important; border-color: #94A3B8 !important;
    }

    /* Inputs */
    .stTextInput input, .stNumberInput input, .stTextArea textarea {
        border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
        background: white !important; font-size: 0.875rem !important;
    }
    .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
        border-color: #3B82F6 !important;
        box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
    }

    /* Forms */
    [data-testid="stForm"] {
        background: white !important; border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important; padding: 1.5rem !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    }

    /* Containers avec bordure */
    [data-testid="stVerticalBlockBorderWrapper"] {
        background: white !important; border: 1px solid #E2E8F0 !important;
        border-radius: 12px !important;
        box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
    }

    /* DataFrames */
    [data-testid="stDataFrame"] {
        border: 1px solid #E2E8F0 !important; border-radius: 10px !important;
        overflow: hidden !important;
    }

    /* Alerts */
    .stAlert { border-radius: 8px !important; font-size: 0.875rem !important; }

    /* Dividers */
    hr { border-color: #E2E8F0 !important; margin: 1.25rem 0 !important; }

    /* Titres */
    h1 { font-weight: 600 !important; color: #0F172A !important;
         font-size: 1.55rem !important; letter-spacing: -0.02em; }
    h2 { font-weight: 600 !important; color: #1E293B !important; font-size: 1.15rem !important; }
    h3 { font-weight: 500 !important; color: #475569 !important; font-size: 0.95rem !important; }

    /* Scrollbar */
    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-track { background: #F1F5F9; }
    ::-webkit-scrollbar-thumb { background: #CBD5E1; border-radius: 3px; }
    """ + css

    st.markdown(f"<style>{base_css}</style>", unsafe_allow_html=True)


# ── Pages mapping ─────────────────────────────────────────────────────────
PAGES = {
    "Dashboard":     page_dashboard,
    "Utilisateurs":  page_utilisateurs,
    "Clients":       page_clients,
    "Fournisseurs":  page_fournisseurs,
    "Produits":      page_produits,
    "Stock":         page_stock,
    "Achats":        page_achats,
    "Ventes":        page_ventes,
    "Commandes":     page_commandes,
    "Crédits":       page_credits,
    "Rapports":      page_rapports,
    "Paramètres":    page_parametres,
}

# Icônes par page
PAGE_ICONS = {
    "Dashboard":    "🏠",
    "Utilisateurs": "👥",
    "Clients":      "👤",
    "Fournisseurs": "🏭",
    "Produits":     "📦",
    "Stock":        "📊",
    "Achats":       "🛒",
    "Ventes":       "💰",
    "Commandes":    "📋",
    "Crédits":      "💳",
    "Rapports":     "📈",
    "Paramètres":   "⚙️",
}


# ── Bootstrap DB ─────────────────────────────────────────────────────────
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


# ── Page connexion ────────────────────────────────────────────────────────
def login_page():
    _load_css()

    # Layout centré avec colonne étroite
    col_l, col_c, col_r = st.columns([1, 1.1, 1])
    with col_c:
        # Logo / en-tête
        st.markdown("""
        <div style="text-align:center; padding: 2.5rem 0 1.5rem;">
            <div style="
                display: inline-flex; align-items: center; justify-content: center;
                width: 64px; height: 64px;
                background: linear-gradient(135deg, #2563EB, #1D4ED8);
                border-radius: 16px;
                box-shadow: 0 4px 16px rgba(37,99,235,0.35);
                margin-bottom: 1rem;
                font-size: 28px;
            ">🔧</div>
            <h1 style="
                font-family: 'DM Sans', sans-serif;
                font-size: 1.8rem; font-weight: 700;
                color: #0F172A; margin: 0; letter-spacing: -0.03em;
            ">SGIQ</h1>
            <p style="
                color: #64748B; font-size: 0.9rem;
                margin: 4px 0 0; font-weight: 400;
            ">Système de Gestion Intégré · Quincaillerie</p>
        </div>
        """, unsafe_allow_html=True)

        # Carte de connexion
        st.markdown("""
        <div style="
            background: white; border: 1px solid #E2E8F0;
            border-radius: 16px; padding: 2rem;
            box-shadow: 0 4px 24px rgba(0,0,0,0.07);
            margin-bottom: 1rem;
        ">
        """, unsafe_allow_html=True)

        with st.form("login", clear_on_submit=False):
            st.markdown(
                "<p style='font-size:0.8rem;font-weight:600;color:#94A3B8;"
                "text-transform:uppercase;letter-spacing:0.08em;"
                "margin-bottom:1rem'>Connexion</p>",
                unsafe_allow_html=True,
            )
            username = st.text_input(
                "Nom d'utilisateur",
                placeholder="Entrez votre identifiant",
            )
            password = st.text_input(
                "Mot de passe",
                type="password",
                placeholder="••••••••",
            )
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button(
                "Se connecter →",
                type="primary",
                use_container_width=True,
            )

        st.markdown("</div>", unsafe_allow_html=True)

        if submitted:
            if not username or not password:
                st.error("Veuillez remplir tous les champs.")
            else:
                session = SessionLocal()
                try:
                    user = authenticate(session, username, password)
                    if user:
                        st.session_state.user = {
                            "id":       user.id_user,
                            "username": user.username,
                            "nom":      f"{user.nom} {user.prenom}",
                            "role":     user.role,
                        }
                        st.rerun()
                    else:
                        st.error("Identifiants incorrects ou compte inactif.")
                finally:
                    session.close()

#         with st.expander("Comptes de démonstration"):
#             st.markdown("""
# | Rôle | Username | Mot de passe |
# |------|----------|--------------|
# | Admin | `admin` | `admin123` |
# | Caissier | `caissier` | `caissier123` |
# | Magasinier | `magasinier` | `magasin123` |
#             """)

        # Pied de page
        st.markdown("""
        <p style="text-align:center; color:#CBD5E1; font-size:0.75rem; margin-top:1.5rem;">
            SGIQ v1.0 · © 2026 · Tous droits réservés
        </p>
        """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────
def render_sidebar(user_info: dict, allowed: list) -> str:
    with st.sidebar:
        # Header sidebar
        st.markdown(f"""
        <div style="padding: 1.25rem 0 1rem;">
            <div style="display:flex; align-items:center; gap:10px; margin-bottom:12px;">
                <div style="
                    width:38px; height:38px;
                    background: rgba(255,255,255,0.12);
                    border-radius: 10px;
                    display:flex; align-items:center; justify-content:center;
                    font-size:18px;
                ">🔧</div>
                <div>
                    <div style="font-size:1rem; font-weight:700; color:#F1F5F9;">SGIQ</div>
                    <div style="font-size:0.7rem; color:#64748B;">Quincaillerie Pro</div>
                </div>
            </div>
            <div style="
                background: rgba(255,255,255,0.06);
                border: 1px solid rgba(255,255,255,0.08);
                border-radius: 10px;
                padding: 10px 12px;
                margin-bottom: 8px;
            ">
                <div style="font-size:0.82rem; font-weight:600; color:#E2E8F0;">
                    {user_info['nom']}
                </div>
                <div style="
                    display:inline-block; margin-top:4px;
                    background: rgba(37,99,235,0.35);
                    color: #93C5FD; font-size:0.68rem; font-weight:600;
                    padding: 2px 8px; border-radius: 20px;
                    text-transform: uppercase; letter-spacing: 0.05em;
                ">{user_info['role']}</div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(
            "<p style='font-size:0.68rem; font-weight:600; color:#475569;"
            "text-transform:uppercase; letter-spacing:0.1em;"
            "padding: 0 0 6px; margin:0'>Navigation</p>",
            unsafe_allow_html=True,
        )

        # Menu radio avec icônes
        menu_labels = [f"{PAGE_ICONS.get(p, '')}  {p}" for p in allowed]
        menu_map    = {f"{PAGE_ICONS.get(p, '')}  {p}": p for p in allowed}

        if "page_active" not in st.session_state:
            st.session_state.page_active = menu_labels[0]

        choice = st.radio(
            "nav",
            menu_labels,
            label_visibility="collapsed",
            key="sidebar_nav",
        )

        st.markdown("<div style='height:1rem'></div>", unsafe_allow_html=True)
        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08); margin:0 0 12px'>",
            unsafe_allow_html=True,
        )

        if st.button("🚪  Déconnexion", use_container_width=True):
            del st.session_state.user
            for key in ("lignes_vente", "lignes_achat", "lignes_cmd"):
                st.session_state.pop(key, None)
            st.rerun()

        # Version en bas
        st.markdown(
            "<p style='font-size:0.68rem; color:#334155; text-align:center;"
            "margin-top:1.5rem;'>v1.0.0</p>",
            unsafe_allow_html=True,
        )

    return menu_map.get(choice, allowed[0])


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    bootstrap_db()

    if "user" not in st.session_state:
        login_page()
        return

    # CSS chargé pour toutes les pages authentifiées
    _load_css()

    user_info = st.session_state.user
    role      = user_info["role"]
    allowed   = MENU_ACCESS.get(role, [])

    page_name = render_sidebar(user_info, allowed)

    # Contexte utilisateur minimal
    class UserCtx:
        id_user = user_info["id"]
        role    = user_info["role"]

    user    = UserCtx()
    session = SessionLocal()
    try:
        page_fn = PAGES.get(page_name)
        if page_fn:
            page_fn(session, user)
    finally:
        session.close()


if __name__ == "__main__":
    main()