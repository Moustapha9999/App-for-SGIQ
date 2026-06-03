from sqlalchemy.orm import Session

from database.models import Log


def log_action(session: Session, id_user: int | None, action: str):
    session.add(Log(id_user=id_user, action=action))
