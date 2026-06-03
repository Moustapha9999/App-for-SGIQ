import bcrypt
from sqlalchemy import select
from sqlalchemy.orm import Session

from database.models import Utilisateur


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode(), bcrypt.gensalt()).decode()


def verify_password(password: str, hashed: str) -> bool:
    return bcrypt.checkpw(password.encode(), hashed.encode())


def authenticate(session: Session, username: str, password: str) -> Utilisateur | None:
    user = session.scalar(
        select(Utilisateur).where(
            Utilisateur.username == username,
            Utilisateur.statut == "Actif",
        )
    )
    if user and verify_password(password, user.mot_de_passe):
        return user
    return None
