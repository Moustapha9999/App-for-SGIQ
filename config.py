import os
from pathlib import Path

from dotenv import load_dotenv

load_dotenv()

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
DATA_DIR.mkdir(exist_ok=True)

DEFAULT_DB = f"sqlite:///{DATA_DIR / 'sgiq.db'}"
DATABASE_URL = os.getenv("DATABASE_URL", DEFAULT_DB)

TVA_DEFAULT = float(os.getenv("TVA", "19"))
DEVISE_DEFAULT = os.getenv("DEVISE", "MAD")

ROLES = ("ADMIN", "CAISSIER", "MAGASINIER")

MENU_ACCESS = {
    "ADMIN": [
        "Dashboard",
        "Utilisateurs",
        "Clients",
        "Fournisseurs",
        "Produits",
        "Stock",
        "Achats",
        "Ventes",
        "Commandes",
        "Crédits",
        "Rapports",
        "Paramètres",
    ],
    "CAISSIER": ["Dashboard", "Clients", "Ventes", "Commandes", "Crédits"],
    "MAGASINIER": [
        "Dashboard",
        "Fournisseurs",
        "Produits",
        "Stock",
        "Achats",
    ],
}
