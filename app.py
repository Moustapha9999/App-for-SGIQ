"""SGIQ — Point d'entrée principal"""

from pathlib import Path
import streamlit as st
from sqlalchemy import func

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
    "Dashboard":    page_dashboard,
    "Utilisateurs": page_utilisateurs,
    "Clients":      page_clients,
    "Fournisseurs": page_fournisseurs,
    "Produits":     page_produits,
    "Stock":        page_stock,
    "Achats":       page_achats,
    "Ventes":       page_ventes,
    "Commandes":    page_commandes,
    "Crédits":      page_credits,
    "Rapports":     page_rapports,
    "Paramètres":   page_parametres,
}

SIDEBAR_SECTIONS = {
    "PRINCIPAL": ["Dashboard"],
    "GESTION":   ["Clients", "Fournisseurs", "Produits", "Stock"],
    "COMMERCE":  ["Achats", "Ventes", "Commandes", "Crédits"],
    "ANALYSE":   ["Rapports", "Utilisateurs", "Paramètres"],
}

PAGE_ICONS = {
    "Dashboard":    "🏠", "Utilisateurs": "👥", "Clients":      "👤",
    "Fournisseurs": "🏭", "Produits":     "📦", "Stock":        "📊",
    "Achats":       "🛒", "Ventes":       "💰", "Commandes":    "📋",
    "Crédits":      "💳", "Rapports":     "📈", "Paramètres":   "⚙️",
}

# ── Thèmes clair / sombre ─────────────────────────────────────────────────
LIGHT = dict(
    app_bg="#F8FAFC", card_bg="#FFFFFF", card_border="#E2E8F0",
    card_shadow="0 1px 3px rgba(0,0,0,0.06)",
    txt_primary="#0F172A", txt_secondary="#94A3B8", txt_muted="#64748B",
    input_bg="#FFFFFF", input_border="#E2E8F0",
    tab_bar="#F1F5F9", tab_active_bg="#FFFFFF",
    tab_active_txt="#2563EB", tab_txt="#64748B",
    divider="#E2E8F0", grid="#F1F5F9",
    h1="#0F172A", h2="#1E293B", h3="#475569",
    scrollbar="#CBD5E1",
)
DARK = dict(
    app_bg="#0F172A", card_bg="#1E293B", card_border="#334155",
    card_shadow="0 1px 3px rgba(0,0,0,0.4)",
    txt_primary="#F1F5F9", txt_secondary="#64748B", txt_muted="#94A3B8",
    input_bg="#1E293B", input_border="#334155",
    tab_bar="#1E293B", tab_active_bg="#0F172A",
    tab_active_txt="#60A5FA", tab_txt="#94A3B8",
    divider="#334155", grid="#1E293B",
    h1="#F1F5F9", h2="#E2E8F0", h3="#94A3B8",
    scrollbar="#334155",
)


# ── CSS global ────────────────────────────────────────────────────────────
def _load_css(dark: bool = False):
    c = DARK if dark else LIGHT
    shadow = "0.4" if dark else "0.06"

    css = f"""
@import url('https://fonts.googleapis.com/css2?family=DM+Sans:wght@300;400;500;600&family=DM+Mono:wght@400;500&display=swap');

html, body, [class*="css"] {{ font-family: 'DM Sans', sans-serif !important; }}
#MainMenu, footer, header, .stDeployButton {{ visibility:hidden; display:none; }}

/* ── App ── */
.stApp, .stApp > div, .block-container {{
    background: {c['app_bg']} !important;
}}

/* ══════════════════════════════════════════
   SIDEBAR — règles du plus général au plus spécifique
   ══════════════════════════════════════════ */
[data-testid="stSidebar"] {{
    background: #1E3A5F !important;
}}
/* 1. Tout le texte sidebar en gris clair par défaut */
[data-testid="stSidebar"],
[data-testid="stSidebar"] * {{
    color: #CBD5E1 !important;
}}
/* 2. Titres et forts en blanc */
[data-testid="stSidebar"] strong,
[data-testid="stSidebar"] h1,
[data-testid="stSidebar"] h2,
[data-testid="stSidebar"] h3 {{
    color: #F1F5F9 !important;
}}
/* 3. Tous les boutons sidebar — fond semi-transparent */
[data-testid="stSidebar"] button,
[data-testid="stSidebar"] .stButton > button,
[data-testid="stSidebar"] .stButton button {{
    background: rgba(255,255,255,0.07) !important;
    border: 1px solid rgba(255,255,255,0.13) !important;
    border-radius: 8px !important;
    transition: all 0.2s !important;
    font-size: 0.85rem !important;
    text-align: left !important;
    width: 100% !important;
}}
/* 4. Texte des boutons sidebar — TOUTES les couches internes */
[data-testid="stSidebar"] button *,
[data-testid="stSidebar"] .stButton button *,
[data-testid="stSidebar"] .stButton button p,
[data-testid="stSidebar"] .stButton button span,
[data-testid="stSidebar"] .stButton button div,
[data-testid="stSidebar"] .stButton button [data-testid],
[data-testid="stSidebar"] [data-testid="baseButton-secondary"] *,
[data-testid="stSidebar"] [data-testid="baseButton-secondary"] p {{
    color: #CBD5E1 !important;
    background: transparent !important;
}}
/* 5. Hover boutons navigation */
[data-testid="stSidebar"] button:hover,
[data-testid="stSidebar"] .stButton button:hover {{
    background: rgba(255,255,255,0.14) !important;
    border-color: rgba(255,255,255,0.22) !important;
}}
[data-testid="stSidebar"] button:hover *,
[data-testid="stSidebar"] .stButton button:hover *,
[data-testid="stSidebar"] .stButton button:hover p,
[data-testid="stSidebar"] .stButton button:hover span,
[data-testid="stSidebar"] .stButton button:hover div {{
    color: #FFFFFF !important;
}}
/* 6. Bouton Déconnexion — rouge discret */
[data-testid="stSidebar"] [key="btn_logout"],
[data-testid="stSidebar"] button[data-testid="btn_logout"] {{
    background: rgba(239,68,68,0.12) !important;
    border-color: rgba(239,68,68,0.28) !important;
}}
[data-testid="stSidebar"] [key="btn_logout"] *,
[data-testid="stSidebar"] button[data-testid="btn_logout"] * {{
    color: #FCA5A5 !important;
}}
[data-testid="stSidebar"] [key="btn_logout"]:hover,
[data-testid="stSidebar"] button[data-testid="btn_logout"]:hover {{
    background: rgba(239,68,68,0.28) !important;
    border-color: rgba(239,68,68,0.5) !important;
}}
[data-testid="stSidebar"] [key="btn_logout"]:hover *,
[data-testid="stSidebar"] button[data-testid="btn_logout"]:hover * {{
    color: #FFFFFF !important;
}}
/* 7. Toggle dark mode */
[data-testid="stSidebar"] .stToggle label {{
    color: #94A3B8 !important;
    font-size: 0.78rem !important;
}}

/* ══════════════════════════════════════════
   CONTENU PRINCIPAL
   ══════════════════════════════════════════ */

/* Metrics */
[data-testid="metric-container"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['card_border']} !important;
    border-radius: 10px !important;
    padding: 1rem 1.25rem !important;
    box-shadow: {c['card_shadow']} !important;
    transition: box-shadow 0.2s;
}}
[data-testid="metric-container"]:hover {{
    box-shadow: 0 4px 12px rgba(0,0,0,0.12) !important;
}}
[data-testid="stMetricLabel"] {{
    font-size: 0.75rem !important; font-weight: 500 !important;
    color: {c['txt_secondary']} !important;
    text-transform: uppercase; letter-spacing: 0.05em;
}}
[data-testid="stMetricValue"] {{
    font-size: 1.5rem !important; font-weight: 600 !important;
    color: {c['txt_primary']} !important;
    font-family: 'DM Mono', monospace !important;
}}

/* Tabs */
.stTabs [data-baseweb="tab-list"] {{
    background: {c['tab_bar']}; border-radius: 10px; padding: 4px; gap: 2px;
}}
.stTabs [data-baseweb="tab"] {{
    border-radius: 7px !important; padding: 6px 18px !important;
    font-size: 0.84rem !important; font-weight: 500 !important;
    color: {c['tab_txt']} !important; background: transparent !important;
    border: none !important; transition: all 0.15s !important;
}}
.stTabs [aria-selected="true"] {{
    background: {c['tab_active_bg']} !important;
    color: {c['tab_active_txt']} !important;
    box-shadow: 0 1px 3px rgba(0,0,0,0.1) !important;
}}

/* Boutons primaires */
.stButton button[kind="primary"] {{
    background: #2563EB !important; border: none !important;
    color: white !important; border-radius: 8px !important;
    font-weight: 500 !important; transition: all 0.2s !important;
    box-shadow: 0 1px 3px rgba(37,99,235,0.25) !important;
}}
.stButton button[kind="primary"]:hover {{
    background: #1D4ED8 !important; transform: translateY(-1px);
    box-shadow: 0 4px 12px rgba(37,99,235,0.3) !important;
}}
.stButton button[kind="secondary"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['card_border']} !important;
    color: {c['txt_primary']} !important;
    border-radius: 8px !important; font-weight: 500 !important;
    transition: all 0.2s !important;
}}

/* Inputs */
.stTextInput input,
.stNumberInput input,
.stTextArea textarea,
.stSelectbox div[data-baseweb="select"] > div {{
    border: 1px solid {c['input_border']} !important;
    border-radius: 8px !important;
    background: {c['input_bg']} !important;
    color: {c['txt_primary']} !important;
    font-size: 0.875rem !important;
}}
.stTextInput input:focus,
.stNumberInput input:focus,
.stTextArea textarea:focus {{
    border-color: #3B82F6 !important;
    box-shadow: 0 0 0 3px rgba(59,130,246,0.12) !important;
}}

/* Forms */
[data-testid="stForm"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['card_border']} !important;
    border-radius: 12px !important; padding: 1.5rem !important;
    box-shadow: {c['card_shadow']} !important;
}}

/* Containers */
[data-testid="stVerticalBlockBorderWrapper"] {{
    background: {c['card_bg']} !important;
    border: 1px solid {c['card_border']} !important;
    border-radius: 12px !important;
    box-shadow: {c['card_shadow']} !important;
}}

/* DataFrames */
[data-testid="stDataFrame"] {{
    border: 1px solid {c['card_border']} !important;
    border-radius: 10px !important; overflow: hidden !important;
}}

/* Alerts */
.stAlert {{ border-radius: 8px !important; font-size: 0.875rem !important; }}

/* Expander */
.streamlit-expanderHeader {{
    background: {c['tab_bar']} !important;
    border-radius: 8px !important; color: {c['txt_primary']} !important;
    font-weight: 500 !important;
}}

/* Texte général */
.stMarkdown p, .stMarkdown li {{
    color: {c['txt_primary']} !important;
}}
.stCaptionContainer p {{
    color: {c['txt_secondary']} !important;
}}
[data-testid="stCheckbox"] label,
[data-testid="stRadio"] label {{
    color: {c['txt_primary']} !important;
}}

/* Dividers */
hr {{ border-color: {c['divider']} !important; margin: 1.25rem 0 !important; }}

/* Titres */
h1 {{ font-weight:600 !important; color:{c['h1']} !important; font-size:1.45rem !important; letter-spacing:-0.02em; }}
h2 {{ font-weight:600 !important; color:{c['h2']} !important; font-size:1.1rem !important; }}
h3 {{ font-weight:500 !important; color:{c['h3']} !important; font-size:0.95rem !important; }}

/* Scrollbar */
::-webkit-scrollbar {{ width:5px; height:5px; }}
::-webkit-scrollbar-track {{ background:{c['app_bg']}; }}
::-webkit-scrollbar-thumb {{ background:{c['scrollbar']}; border-radius:3px; }}
"""

    # Charge aussi style.css si présent
    css_path = Path(__file__).parent / ".streamlit" / "style.css"
    if css_path.exists():
        with open(css_path) as f:
            css += f.read()

    st.markdown(f"<style>{css}</style>", unsafe_allow_html=True)


# ── Bootstrap ─────────────────────────────────────────────────────────────
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
    run_auto_backup_if_needed()


def _run_auto_notifications():
    if st.session_state.get("notif_checked"):
        return
    st.session_state.notif_checked = True
    try:
        from services.notification_service import auto_check_stock_alert
        session = SessionLocal()
        try:
            result = auto_check_stock_alert(session)
            if result and result.get("sent"):
                st.toast(
                    f"📧 Alerte stock envoyée — "
                    f"{result['nb_alertes']} produit(s) concerné(s).",
                    icon="🔔",
                )
        finally:
            session.close()
    except Exception:
        pass


# ── Page connexion ────────────────────────────────────────────────────────
def login_page(dark: bool):
    _load_css(dark)
    c = DARK if dark else LIGHT

    col_l, col_c, col_r = st.columns([1, 1.1, 1])
    with col_c:
        st.markdown(f"""
        <div style="text-align:center;padding:2.5rem 0 1.5rem">
            <div style="display:inline-flex;align-items:center;justify-content:center;
                width:64px;height:64px;
                background:linear-gradient(135deg,#2563EB,#1D4ED8);
                border-radius:16px;box-shadow:0 4px 16px rgba(37,99,235,0.35);
                margin-bottom:1rem;font-size:28px">🔧</div>
            <h1 style="font-size:1.8rem;font-weight:700;color:{c['h1']};
                margin:0;letter-spacing:-0.03em">SGIQ</h1>
            <p style="color:{c['txt_muted']};font-size:0.9rem;margin:4px 0 0">
                Système de Gestion Intégré · Quincaillerie</p>
        </div>
        """, unsafe_allow_html=True)

        st.markdown(f"""
        <div style="background:{c['card_bg']};border:1px solid {c['card_border']};
            border-radius:16px;padding:2rem;
            box-shadow:0 4px 24px rgba(0,0,0,{0.07 if not dark else 0.4});
            margin-bottom:1rem">
        """, unsafe_allow_html=True)

        with st.form("login", clear_on_submit=False):
            st.markdown(
                f"<p style='font-size:0.8rem;font-weight:600;"
                f"color:{c['txt_secondary']};text-transform:uppercase;"
                f"letter-spacing:0.08em;margin-bottom:1rem'>Connexion</p>",
                unsafe_allow_html=True,
            )
            username = st.text_input("Nom d'utilisateur",
                                     placeholder="Entrez votre identifiant")
            password = st.text_input("Mot de passe", type="password",
                                     placeholder="••••••••")
            st.markdown("<div style='height:4px'></div>", unsafe_allow_html=True)
            submitted = st.form_submit_button("Se connecter →", type="primary",
                                              use_container_width=True)
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

        st.markdown(
            f"<p style='text-align:center;color:{c['txt_secondary']};"
            f"font-size:0.75rem;margin-top:1.5rem'>"
            f"SGIQ v1.0 · © 2026 · Tous droits réservés</p>",
            unsafe_allow_html=True,
        )


# ── Badges sidebar ────────────────────────────────────────────────────────
def _get_badge(page_name: str, session) -> str:
    try:
        if page_name == "Stock":
            from database.models import Produit
            from sqlalchemy import select
            nb = session.scalar(
                select(func.count(Produit.code_produit))
                .where(Produit.stock <= Produit.stock_minimum,
                       Produit.statut == "Actif")
            ) or 0
            return str(nb) if nb > 0 else ""
        if page_name == "Crédits":
            from database.models import Credit
            from sqlalchemy import select
            nb = session.scalar(
                select(func.count(Credit.id_credit))
                .where(Credit.statut == "Ouvert")
            ) or 0
            return str(nb) if nb > 0 else ""
    except Exception:
        pass
    return ""


# ── Sidebar ───────────────────────────────────────────────────────────────
def render_sidebar(user_info: dict, allowed: list, session, dark: bool) -> str:
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Dashboard"

    with st.sidebar:
        # Logo + nom app
        st.markdown(f"""
        <div style="padding:1.25rem 0 0.5rem">
            <div style="display:flex;align-items:center;gap:10px;margin-bottom:14px">
                <div style="width:36px;height:36px;
                    background:rgba(255,255,255,0.12);border-radius:9px;
                    display:flex;align-items:center;justify-content:center;
                    font-size:17px">🔧</div>
                <div>
                    <div style="font-size:0.95rem;font-weight:700;color:#F1F5F9">SGIQ</div>
                    <div style="font-size:0.68rem;color:#64748B">Quincaillerie Pro</div>
                </div>
            </div>
            <div style="background:rgba(255,255,255,0.06);
                border:1px solid rgba(255,255,255,0.08);
                border-radius:9px;padding:9px 12px;margin-bottom:4px">
                <div style="font-size:0.8rem;font-weight:600;color:#E2E8F0">
                    {user_info['nom']}
                </div>
                <div style="display:inline-block;margin-top:3px;
                    background:rgba(37,99,235,0.35);color:#93C5FD;
                    font-size:0.65rem;font-weight:600;padding:1px 7px;
                    border-radius:20px;text-transform:uppercase;letter-spacing:0.05em">
                    {user_info['role']}
                </div>
            </div>
        </div>
        """, unsafe_allow_html=True)

        # Toggle mode sombre
        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08);margin:6px 0 10px'>",
            unsafe_allow_html=True,
        )
        col_lbl, col_tog = st.columns([3, 1])
        col_lbl.markdown(
            "<p style='color:#94A3B8;font-size:0.78rem;margin:6px 0 0;'>"
            "🌙 Mode sombre</p>",
            unsafe_allow_html=True,
        )
        new_dark = col_tog.toggle("", value=dark, key="dark_mode_toggle",
                                  label_visibility="collapsed")
        if new_dark != dark:
            st.session_state.dark_mode = new_dark
            st.rerun()

        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08);margin:10px 0 6px'>",
            unsafe_allow_html=True,
        )

        # Navigation par sections
        for section, pages in SIDEBAR_SECTIONS.items():
            pages_ok = [p for p in pages if p in allowed]
            if not pages_ok:
                continue

            st.markdown(
                f"<p style='font-size:0.63rem;font-weight:700;color:#4B5563;"
                f"text-transform:uppercase;letter-spacing:0.12em;"
                f"padding:8px 0 3px;margin:0'>{section}</p>",
                unsafe_allow_html=True,
            )

            for page in pages_ok:
                icon  = PAGE_ICONS.get(page, "")
                badge = _get_badge(page, session)
                is_active = st.session_state.current_page == page

                # Highlight page active
                if is_active:
                    st.markdown(f"""
                    <style>
                    div[data-testid="stSidebar"] div[key="nav_{page}"] button,
                    div[data-testid="stSidebar"] div[key="nav_{page}"] > div > div > div > button {{
                        background: rgba(59,130,246,0.22) !important;
                        border-left: 3px solid #3B82F6 !important;
                        border-color: rgba(59,130,246,0.35) !important;
                    }}
                    div[data-testid="stSidebar"] div[key="nav_{page}"] button *,
                    div[data-testid="stSidebar"] div[key="nav_{page}"] button p {{
                        color: #FFFFFF !important;
                    }}
                    </style>""", unsafe_allow_html=True)

                label = f"{icon}  {page}" + (f"   •{badge}" if badge else "")
                if st.button(label, key=f"nav_{page}", use_container_width=True):
                    st.session_state.current_page = page
                    st.rerun()

        # Déconnexion
        st.markdown(
            "<hr style='border-color:rgba(255,255,255,0.08);margin:12px 0 8px'>",
            unsafe_allow_html=True,
        )
        if st.button("🚪  Déconnexion", use_container_width=True,
                     key="btn_logout"):
            del st.session_state.user
            for key in ("lignes_vente", "lignes_achat", "lignes_cmd",
                        "notif_checked", "current_page"):
                st.session_state.pop(key, None)
            st.rerun()

        st.markdown(
            "<p style='font-size:0.65rem;color:#374151;text-align:center;"
            "margin-top:10px'>v1.0.0</p>",
            unsafe_allow_html=True,
        )

    return st.session_state.current_page


# ── Main ──────────────────────────────────────────────────────────────────
def main():
    bootstrap_db()

    if "dark_mode" not in st.session_state:
        st.session_state.dark_mode = False
    dark = st.session_state.dark_mode

    if "user" not in st.session_state:
        login_page(dark)
        return

    _load_css(dark)
    _run_auto_notifications()

    user_info = st.session_state.user
    role      = user_info["role"]
    allowed   = MENU_ACCESS.get(role, [])

    session = SessionLocal()
    try:
        page_name = render_sidebar(user_info, allowed, session, dark)

        class UserCtx:
            id_user = user_info["id"]
            role    = user_info["role"]

        page_fn = PAGES.get(page_name)
        if page_fn:
            page_fn(session, UserCtx())
    finally:
        session.close()


if __name__ == "__main__":
    main()