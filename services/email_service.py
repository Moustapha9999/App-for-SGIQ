"""Envoi de factures par e-mail (SMTP)."""

import os
import smtplib
from email import encoders
from email.mime.application import MIMEApplication
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from database.models import Parametre


def _param(session: Session, cle: str, default: str = "") -> str:
    p = session.query(Parametre).filter(Parametre.cle == cle).first()
    if p and p.valeur:
        return p.valeur
    return os.getenv(cle.upper(), default)


def is_email_configured(session: Session) -> bool:
    host = _param(session, "smtp_host")
    user = _param(session, "smtp_user")
    return bool(host and user)


def send_invoice_email(
    session: Session,
    to_email: str,
    subject: str,
    body: str,
    pdf_bytes: bytes,
    filename: str,
) -> None:
    host = _param(session, "smtp_host")
    port = int(_param(session, "smtp_port", "587"))
    user = _param(session, "smtp_user")
    password = _param(session, "smtp_password")
    use_tls = _param(session, "smtp_tls", "true").lower() in ("1", "true", "oui", "yes")
    from_addr = _param(session, "smtp_from", user)

    if not host or not user:
        raise ValueError("SMTP non configuré. Renseignez les paramètres dans Paramètres → E-mail.")

    msg = MIMEMultipart()
    msg["From"] = from_addr
    msg["To"] = to_email
    msg["Subject"] = subject
    msg.attach(MIMEText(body, "plain", "utf-8"))

    part = MIMEApplication(pdf_bytes, _subtype="pdf")
    part.add_header("Content-Disposition", "attachment", filename=filename)
    msg.attach(part)

    with smtplib.SMTP(host, port, timeout=30) as server:
        if use_tls:
            server.starttls()
        if password:
            server.login(user, password)
        server.sendmail(from_addr, [to_email], msg.as_string())
