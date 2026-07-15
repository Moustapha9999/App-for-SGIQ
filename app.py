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
from utils.dialogs import dialog_logout, request_dialog

# ── Config page ──────────────────────────────────────────────────────────
st.set_page_config(
    page_title="SGIQ — Quincaillerie",
    page_icon="🔧",
    layout="wide",
    initial_sidebar_state="expanded",
)

# ── Injection CSS global ─────────────────────────────────────────────────
def _load_css(dark: bool = False):
    css_path = Path(__file__).parent / ".streamlit" / "style.css"
    if css_path.exists():
        with open(css_path, encoding="utf-8") as f:
            css = f.read()
    else:
        css = ""

    if dark:
        theme_css = """
        .stApp {
          background:
            radial-gradient(ellipse 70% 50% at 10% 0%, rgba(37,99,235,0.12), transparent 50%),
            linear-gradient(180deg, #0B1220 0%, #0F172A 40%, #111827 100%) !important;
        }
        .main .block-container { color: #E2E8F0; }
        h1 { color: #F8FAFC !important; }
        h2 { color: #E2E8F0 !important; }
        h3 { color: #CBD5E1 !important; }
        p, label, span, .stMarkdown { color: #CBD5E1; }
        [data-testid="stCaptionContainer"],
        [data-testid="stCaptionContainer"] * { color: #94A3B8 !important; }

        [data-testid="metric-container"] {
          background: #1E293B !important; border: 1px solid #334155 !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.35) !important;
        }
        [data-testid="stMetricLabel"] { color: #94A3B8 !important; }
        [data-testid="stMetricValue"] { color: #F1F5F9 !important; }

        .stTabs [data-baseweb="tab-list"] {
          background: #1E293B !important; border: 1px solid #334155;
        }
        .stTabs [data-baseweb="tab"] { color: #94A3B8 !important; }
        .stTabs [aria-selected="true"] {
          background: #0F172A !important; color: #60A5FA !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.35) !important;
        }

        .stButton button[kind="secondary"] {
          background: #1E293B !important; border: 1px solid #334155 !important;
          color: #E2E8F0 !important;
        }
        .stButton button[kind="secondary"]:hover {
          background: #334155 !important; border-color: #475569 !important;
        }

        .stTextInput input, .stNumberInput input, .stTextArea textarea,
        [data-baseweb="select"] > div, [data-baseweb="base-input"] {
          border: 1px solid #334155 !important; background: #0F172A !important;
          color: #E2E8F0 !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
          border-color: #3B82F6 !important;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.2) !important;
        }

        [data-testid="stForm"],
        [data-testid="stVerticalBlockBorderWrapper"] {
          background: #1E293B !important; border: 1px solid #334155 !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.3) !important;
        }
        [data-testid="stDataFrame"] {
          border: 1px solid #334155 !important;
        }
        hr { border-color: #334155 !important; }
        .stAlert { background: #1E293B !important; }
        ::-webkit-scrollbar-track { background: #0F172A; }
        ::-webkit-scrollbar-thumb { background: #475569; }

        div[data-testid="stDialog"] > div[role="dialog"] {
          background: #1E293B !important;
          border: 1px solid #334155 !important;
          color: #E2E8F0 !important;
        }
        """
    else:
        theme_css = """
        .stApp {
          background:
            radial-gradient(ellipse 80% 50% at 0% 0%, rgba(37,99,235,0.06), transparent 55%),
            radial-gradient(ellipse 60% 40% at 100% 0%, rgba(30,58,95,0.05), transparent 50%),
            #F8FAFC !important;
        }
        [data-testid="metric-container"] {
          background: white !important; border: 1px solid #E2E8F0 !important;
          border-radius: 12px !important; padding: 1rem 1.25rem !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
          transition: box-shadow 0.2s, transform 0.2s;
        }
        [data-testid="stMetricLabel"] {
          font-size: 0.75rem !important; font-weight: 500 !important;
          color: #94A3B8 !important; text-transform: uppercase; letter-spacing: 0.05em;
        }
        [data-testid="stMetricValue"] {
          font-size: 1.5rem !important; font-weight: 600 !important;
          color: #0F172A !important; font-family: 'DM Mono', monospace !important;
        }
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
        .stButton button[kind="secondary"] {
          background: white !important; border: 1px solid #E2E8F0 !important;
          color: #334155 !important; border-radius: 8px !important;
          font-weight: 500 !important; transition: all 0.2s !important;
        }
        .stButton button[kind="secondary"]:hover {
          background: #F8FAFC !important; border-color: #94A3B8 !important;
        }
        .stTextInput input, .stNumberInput input, .stTextArea textarea {
          border: 1px solid #E2E8F0 !important; border-radius: 8px !important;
          background: white !important; font-size: 0.875rem !important;
        }
        .stTextInput input:focus, .stNumberInput input:focus, .stTextArea textarea:focus {
          border-color: #3B82F6 !important;
          box-shadow: 0 0 0 3px rgba(59,130,246,0.1) !important;
        }
        [data-testid="stForm"] {
          background: white !important; border: 1px solid #E2E8F0 !important;
          border-radius: 12px !important; padding: 1.5rem !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }
        [data-testid="stVerticalBlockBorderWrapper"] {
          background: white !important; border: 1px solid #E2E8F0 !important;
          border-radius: 12px !important;
          box-shadow: 0 1px 3px rgba(0,0,0,0.06) !important;
        }
        [data-testid="stDataFrame"] {
          border: 1px solid #E2E8F0 !important; border-radius: 10px !important;
          overflow: hidden !important;
        }
        hr { border-color: #E2E8F0 !important; margin: 1.25rem 0 !important; }
        h1 { color: #0F172A !important; }
        h2 { color: #1E293B !important; }
        h3 { color: #475569 !important; }
        ::-webkit-scrollbar-track { background: #F1F5F9; }
        ::-webkit-scrollbar-thumb { background: #CBD5E1; }
        div[data-testid="stDialog"] > div[role="dialog"] {
          background: #FFFFFF !important;
          border: 1px solid #E2E8F0 !important;
          border-radius: 16px !important;
          box-shadow: 0 20px 50px rgba(15,23,42,0.18) !important;
        }
        """

    base_css = """
    @import url('https://fonts.googleapis.com/css2?family=DM+Sans:ital,opsz,wght@0,9..40,300;0,9..40,400;0,9..40,500;0,9..40,600;1,9..40,400&family=DM+Mono:wght@400;500&display=swap');

    html, body, [class*="css"] { font-family: 'DM Sans', sans-serif !important; }
    #MainMenu, footer, header, .stDeployButton { visibility: hidden; display: none; }

    [data-testid="collapsedControl"],
    [data-testid="stSidebarCollapseButton"],
    button[data-testid="collapsedControl"],
    section[data-testid="stSidebar"] button[kind="header"] {
        display: none !important;
        visibility: hidden !important;
        width: 0 !important;
        pointer-events: none !important;
    }

    [data-testid="stSidebar"] {
      background: linear-gradient(180deg, #152A45 0%, #1E3A5F 55%, #16304F 100%) !important;
      border-right: 1px solid rgba(255,255,255,0.06) !important;
    }
    [data-testid="stSidebar"] * { color: #CBD5E1 !important; }
    [data-testid="stSidebar"] strong, [data-testid="stSidebar"] h1,
    [data-testid="stSidebar"] h2, [data-testid="stSidebar"] h3 { color: #F1F5F9 !important; }

    [data-testid="stSidebar"] .stButton button {
        background: rgba(255,255,255,0.07) !important;
        border: 1px solid rgba(255,255,255,0.12) !important;
        border-radius: 8px !important;
        transition: all 0.2s;
    }
    [data-testid="stSidebar"] .stButton button,
    [data-testid="stSidebar"] .stButton button * { color: #CBD5E1 !important; }
    [data-testid="stSidebar"] .stButton button:hover {
        background: rgba(255,255,255,0.14) !important;
    }
    [data-testid="stSidebar"] .stButton button:hover * { color: #FFFFFF !important; }

    [data-testid="stSidebar"] .stRadio label {
        color: #CBD5E1 !important;
        font-size: 0.88rem !important;
        border-radius: 8px !important;
        padding: 0.35rem 0.55rem !important;
        transition: background 0.15s, color 0.15s;
    }
    [data-testid="stSidebar"] .stRadio label:hover {
        background: rgba(255,255,255,0.08) !important;
        color: #FFFFFF !important;
    }
    [data-testid="stSidebar"] .stRadio label:hover * { color: #FFFFFF !important; }
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] {
        background: rgba(37,99,235,0.28) !important;
    }
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] *,
    [data-testid="stSidebar"] .stRadio [aria-checked="true"] {
        color: #FFFFFF !important;
    }

    .stButton button[kind="primary"] {
        background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
        border: none !important; color: white !important;
        border-radius: 8px !important; font-weight: 500 !important;
        transition: all 0.2s !important;
        box-shadow: 0 1px 3px rgba(37,99,235,0.25) !important;
    }
    .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
        transform: translateY(-1px);
        box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
    }

    .stAlert { border-radius: 8px !important; font-size: 0.875rem !important; }
    h1 { font-weight: 600 !important; font-size: 1.55rem !important; letter-spacing: -0.02em; }
    h2 { font-weight: 600 !important; font-size: 1.15rem !important; }
    h3 { font-weight: 500 !important; font-size: 0.95rem !important; }

    ::-webkit-scrollbar { width: 5px; height: 5px; }
    ::-webkit-scrollbar-thumb { border-radius: 3px; }

    div[data-testid="stDialog"] > div[role="dialog"] {
      border-radius: 16px !important;
      padding: 0.5rem !important;
    }
    """ + theme_css + css

    st.markdown(f"<style>{base_css}</style>", unsafe_allow_html=True)


def _ensure_theme(session):
    """Charge le thème depuis la DB si pas encore en session."""
    if "dark_mode" not in st.session_state:
        from database.models import Parametre
        p = session.query(Parametre).filter(Parametre.cle == "theme").first()
        st.session_state.dark_mode = bool(p and p.valeur == "dark")


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

    st.markdown("""
    <style>
      /* Masquer sidebar + header sur le login */
      [data-testid="stSidebar"],
      [data-testid="stSidebarCollapsedControl"],
      [data-testid="collapsedControl"] {
        display: none !important;
      }
      [data-testid="stAppViewContainer"] > .main {
        padding: 0 !important;
      }
      .main .block-container {
        max-width: 420px !important;
        padding: 0 1.25rem 2rem !important;
        margin: 0 auto !important;
      }
      .stApp {
        background:
          radial-gradient(ellipse 80% 60% at 20% 10%, rgba(37,99,235,0.14), transparent 55%),
          radial-gradient(ellipse 70% 50% at 85% 90%, rgba(30,58,95,0.12), transparent 50%),
          linear-gradient(165deg, #F1F5F9 0%, #E8EEF6 45%, #F8FAFC 100%) !important;
      }
      .stApp::before {
        content: "";
        position: fixed;
        inset: 0;
        pointer-events: none;
        opacity: 0.35;
        background-image:
          linear-gradient(rgba(30,58,95,0.04) 1px, transparent 1px),
          linear-gradient(90deg, rgba(30,58,95,0.04) 1px, transparent 1px);
        background-size: 48px 48px;
        mask-image: radial-gradient(ellipse 70% 60% at 50% 40%, black, transparent);
      }
      [data-testid="stForm"] {
        background: transparent !important;
        border: none !important;
        box-shadow: none !important;
        padding: 0 !important;
      }
      .login-shell [data-testid="stForm"] .stTextInput label,
      .login-shell [data-testid="stForm"] .stTextInput label p {
        font-size: 0.8rem !important;
        font-weight: 600 !important;
        color: #475569 !important;
      }
      .login-shell .stTextInput input {
        height: 2.75rem !important;
        border: 1.5px solid #E2E8F0 !important;
        border-radius: 10px !important;
        background: #F8FAFC !important;
        font-size: 0.9rem !important;
        transition: border-color 0.2s, box-shadow 0.2s, background 0.2s !important;
      }
      .login-shell .stTextInput input:focus {
        background: white !important;
        border-color: #2563EB !important;
        box-shadow: 0 0 0 3px rgba(37,99,235,0.12) !important;
      }
      .login-shell .stButton button[kind="primary"] {
        height: 2.85rem !important;
        border-radius: 10px !important;
        font-size: 0.95rem !important;
        font-weight: 600 !important;
        letter-spacing: 0.01em !important;
        background: linear-gradient(135deg, #2563EB, #1D4ED8) !important;
        box-shadow: 0 4px 14px rgba(37,99,235,0.28) !important;
      }
      .login-shell .stButton button[kind="primary"]:hover {
        background: linear-gradient(135deg, #1D4ED8, #1E40AF) !important;
        transform: translateY(-1px);
        box-shadow: 0 6px 20px rgba(37,99,235,0.35) !important;
      }
      @keyframes loginFadeUp {
        from { opacity: 0; transform: translateY(14px); }
        to   { opacity: 1; transform: translateY(0); }
      }
      .login-brand, .login-card, .login-foot {
        animation: loginFadeUp 0.55s ease both;
      }
      .login-card { animation-delay: 0.08s; }
      .login-foot { animation-delay: 0.16s; }
    </style>
    """, unsafe_allow_html=True)

    st.markdown('<div class="login-shell">', unsafe_allow_html=True)

    st.markdown("""
    <div class="login-brand" style="text-align:center; padding: 3.5rem 0 1.75rem;">
      <div style="
        display: inline-flex; align-items: center; justify-content: center;
        width: 72px; height: 72px;
        background: linear-gradient(145deg, #1E3A5F 0%, #2563EB 100%);
        border-radius: 20px;
        box-shadow:
          0 8px 28px rgba(30,58,95,0.28),
          inset 0 1px 0 rgba(255,255,255,0.18);
        margin-bottom: 1.15rem;
        font-size: 32px;
        position: relative;
      ">
        <span style="filter: drop-shadow(0 2px 4px rgba(0,0,0,0.2));">🔧</span>
      </div>
      <h1 style="
        font-family: 'DM Sans', sans-serif;
        font-size: 2.15rem; font-weight: 700;
        color: #0F172A; margin: 0; letter-spacing: -0.04em;
        line-height: 1.1;
      ">SGIQ</h1>
      <p style="
        color: #64748B; font-size: 0.92rem;
        margin: 0.45rem 0 0; font-weight: 400;
        letter-spacing: 0.01em;
      ">Gestion intégrée pour votre quincaillerie</p>
    </div>
    """, unsafe_allow_html=True)

    st.markdown("""
    <div class="login-card" style="
      background: rgba(255,255,255,0.92);
      backdrop-filter: blur(12px);
      -webkit-backdrop-filter: blur(12px);
      border: 1px solid rgba(226,232,240,0.9);
      border-radius: 18px;
      padding: 1.75rem 1.75rem 1.5rem;
      box-shadow:
        0 1px 2px rgba(15,23,42,0.04),
        0 12px 40px rgba(15,23,42,0.08);
      margin-bottom: 0.5rem;
    ">
      <div style="margin-bottom: 1.15rem;">
        <p style="
          font-size: 1.05rem; font-weight: 600; color: #0F172A;
          margin: 0 0 0.2rem; letter-spacing: -0.02em;
        ">Bienvenue</p>
        <p style="
          font-size: 0.84rem; color: #94A3B8; margin: 0;
        ">Connectez-vous pour accéder à votre espace</p>
      </div>
    """, unsafe_allow_html=True)

    with st.form("login", clear_on_submit=False):
        username = st.text_input(
            "Nom d'utilisateur",
            placeholder="votre.identifiant",
        )
        password = st.text_input(
            "Mot de passe",
            type="password",
            placeholder="••••••••",
        )
        st.markdown("<div style='height:6px'></div>", unsafe_allow_html=True)
        submitted = st.form_submit_button(
            "Se connecter",
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

    st.markdown("""
    <p class="login-foot" style="
      text-align:center; color:#94A3B8; font-size:0.72rem;
      margin-top:1.75rem; letter-spacing:0.02em;
    ">
      SGIQ v1.0 · © 2026 · Tous droits réservés
    </p>
    </div>
    """, unsafe_allow_html=True)


# ── Sidebar ───────────────────────────────────────────────────────────────
def render_sidebar(user_info: dict, allowed: list) -> str:
    with st.sidebar:
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
            request_dialog("_logout_dlg")

        if "_logout_dlg" in st.session_state:
            def _do_logout():
                st.session_state.pop("_logout_dlg", None)
                st.session_state.pop("user", None)
                for key in ("lignes_vente", "lignes_achat", "lignes_cmd"):
                    st.session_state.pop(key, None)

            dialog_logout(
                _do_logout,
                on_cancel=lambda: st.session_state.pop("_logout_dlg", None),
            )

        theme_label = "🌙 Sombre" if st.session_state.get("dark_mode") else "☀️ Clair"
        st.markdown(
            f"<p style='font-size:0.68rem; color:#64748B; text-align:center;"
            f"margin-top:1.5rem;'>v1.0.0 · {theme_label}</p>",
            unsafe_allow_html=True,
        )

    return menu_map.get(choice, allowed[0])


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    bootstrap_db()

    if "user" not in st.session_state:
        login_page()
        return

    session = SessionLocal()
    try:
        _ensure_theme(session)
        _load_css(dark=st.session_state.get("dark_mode", False))

        user_info = st.session_state.user
        role      = user_info["role"]
        allowed   = MENU_ACCESS.get(role, [])

        page_name = render_sidebar(user_info, allowed)

        class UserCtx:
            id_user = user_info["id"]
            role    = user_info["role"]

        user = UserCtx()
        page_fn = PAGES.get(page_name)
        if page_fn:
            page_fn(session, user)
    finally:
        session.close()


if __name__ == "__main__":
    main()