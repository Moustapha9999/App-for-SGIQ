# database/connection.py
# ============================================================
#  Connexion SQLAlchemy — SQLite (dev) ou PostgreSQL/Supabase (prod)
# ============================================================

from contextlib import contextmanager

from sqlalchemy import create_engine, event, text
from sqlalchemy.orm import sessionmaker

from config import DATABASE_URL
from database.models import Base

# ── Engine ───────────────────────────────────────────────────────────────
_is_sqlite = DATABASE_URL.startswith("sqlite")

if _is_sqlite:
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        connect_args={"check_same_thread": False},
    )
    # Active les clés étrangères sur SQLite
    @event.listens_for(engine, "connect")
    def _set_sqlite_pragma(dbapi_conn, _):
        cursor = dbapi_conn.cursor()
        cursor.execute("PRAGMA foreign_keys=ON")
        cursor.close()
else:
    # PostgreSQL / Supabase
    # pool_pre_ping vérifie la connexion avant chaque requête
    # (important avec Supabase qui ferme les connexions inactives)
    engine = create_engine(
        DATABASE_URL,
        echo=False,
        pool_pre_ping=True,
        pool_size=5,
        max_overflow=10,
        pool_timeout=30,
        pool_recycle=1800,   # recycle les connexions toutes les 30min
        connect_args={
            "connect_timeout": 10,
            "application_name": "SGIQ",
        },
    )

SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


# ── Initialisation des tables ─────────────────────────────────────────────
def init_db():
    """Crée toutes les tables si elles n'existent pas encore."""
    Base.metadata.create_all(bind=engine)


# ── Session context manager ───────────────────────────────────────────────
@contextmanager
def get_session():
    """Session avec commit auto ou rollback en cas d'erreur."""
    session = SessionLocal()
    try:
        yield session
        session.commit()
    except Exception:
        session.rollback()
        raise
    finally:
        session.close()


# ── Health check ──────────────────────────────────────────────────────────
def test_connection() -> bool:
    """Teste la connexion à la base — utile au démarrage."""
    try:
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        return True
    except Exception:
        return False