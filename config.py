# config.py
# ============================================================
#  Configuration — lit depuis .env (local) ou secrets (Cloud)
# ============================================================

import os
from pathlib import Path

# Charge .env en local (ignoré si pas présent — Streamlit Cloud utilise secrets)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

# ── Base de données ──────────────────────────────────────────────────────
# Priorité : variable d'env → st.secrets → SQLite fallback
def _get_database_url() -> str:
    # 1. Variable d'environnement (.env local ou Cloud env)
    url = os.getenv("DATABASE_URL", "")

    # 2. Streamlit secrets (Streamlit Cloud)
    if not url:
        try:
            import streamlit as st
            url = st.secrets.get("DATABASE_URL", "")
        except Exception:
            pass

    # 3. Fallback SQLite local
    if not url:
        url = f"sqlite:///{DATA_DIR / 'sgiq.db'}"

    # Corrige postgres:// → postgresql://
    if url.startswith("postgres://"):
        url = url.replace("postgres://", "postgresql://", 1)

    return url


DATABASE_URL = _get_database_url()

# ── App ──────────────────────────────────────────────────────────────────
def _get_param(key: str, default: str) -> str:
    val = os.getenv(key, "")
    if not val:
        try:
            import streamlit as st
            val = st.secrets.get(key, "")
        except Exception:
            pass
    return val or default


TVA_DEFAULT    = float(_get_param("TVA", "16"))
DEVISE_DEFAULT = _get_param("DEVISE", "MRU")

ROLES = ("ADMIN", "CAISSIER", "MAGASINIER")

MENU_ACCESS = {
    "ADMIN": [
        "Dashboard", "Utilisateurs", "Clients", "Fournisseurs",
        "Produits", "Stock", "Achats", "Ventes", "Commandes",
        "Crédits", "Rapports", "Paramètres",
    ],
    "CAISSIER":   ["Dashboard", "Clients", "Ventes", "Commandes", "Crédits"],
    "MAGASINIER": ["Dashboard", "Fournisseurs", "Produits", "Stock", "Achats"],
}