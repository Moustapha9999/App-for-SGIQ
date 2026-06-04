# services/notification_service.py
# ============================================================
#  Notifications email — alertes stock faible / rupture
# ============================================================

import smtplib
from datetime import datetime
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

from sqlalchemy.orm import Session

from database.models import Parametre, Produit


# ── Helpers paramètres ────────────────────────────────────────────────────

def _param(session: Session, cle: str, default: str = "") -> str:
    p = session.query(Parametre).filter(Parametre.cle == cle).first()
    return p.valeur if p and p.valeur else default


def is_notification_configured(session: Session) -> bool:
    """Vérifie que SMTP + email destinataire sont configurés."""
    return bool(
        _param(session, "smtp_host") and
        _param(session, "smtp_user") and
        _param(session, "notif_email_dest")
    )


# ── Récupération des produits en alerte ───────────────────────────────────

def get_produits_alerte(session: Session) -> dict:
    """Retourne les produits en rupture et en stock faible."""
    produits = session.query(Produit).filter(Produit.statut == "Actif").all()
    return {
        "rupture": [p for p in produits if p.stock == 0],
        "faible":  [p for p in produits if 0 < p.stock <= p.stock_minimum],
    }


# ── Template HTML email ───────────────────────────────────────────────────

def _build_html(session: Session, alertes: dict) -> str:
    societe   = _param(session, "societe_nom",  "SGIQ")
    devise    = _param(session, "devise",        "FCFA")
    ruptures  = alertes["rupture"]
    faibles   = alertes["faible"]
    now       = datetime.now().strftime("%d/%m/%Y à %H:%M")

    # Lignes tableau ruptures
    rows_rupture = ""
    for p in ruptures:
        rows_rupture += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2">
                <strong>{p.code_produit}</strong>
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2">{p.designation}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2">{p.categorie}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2;color:#DC2626;font-weight:700">
                0 {p.unite}
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2;color:#6B7280">
                {p.stock_minimum} {p.unite}
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEE2E2">
                <span style="background:#FEE2E2;color:#DC2626;padding:2px 10px;
                border-radius:20px;font-size:12px;font-weight:600">RUPTURE</span>
            </td>
        </tr>"""

    # Lignes tableau stocks faibles
    rows_faible = ""
    for p in faibles:
        pct = int(p.stock / p.stock_minimum * 100) if p.stock_minimum > 0 else 0
        rows_faible += f"""
        <tr>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7">
                <strong>{p.code_produit}</strong>
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7">{p.designation}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7">{p.categorie}</td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7;
                color:#D97706;font-weight:700">
                {p.stock} {p.unite}
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7;color:#6B7280">
                {p.stock_minimum} {p.unite}
            </td>
            <td style="padding:10px 14px;border-bottom:1px solid #FEF3C7">
                <span style="background:#FEF3C7;color:#D97706;padding:2px 10px;
                border-radius:20px;font-size:12px;font-weight:600">
                    FAIBLE ({pct}%)
                </span>
            </td>
        </tr>"""

    section_rupture = ""
    if ruptures:
        section_rupture = f"""
        <div style="margin-bottom:28px">
            <h2 style="font-size:16px;font-weight:700;color:#DC2626;margin:0 0 12px;
                display:flex;align-items:center;gap:8px">
                🔴 Produits en rupture totale ({len(ruptures)})
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0"
                style="border-collapse:collapse;background:#FFF5F5;
                border-radius:8px;overflow:hidden;font-size:13px">
                <thead>
                    <tr style="background:#FEE2E2">
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Code</th>
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Désignation</th>
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Catégorie</th>
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Stock</th>
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Min.</th>
                        <th style="padding:10px 14px;text-align:left;color:#991B1B;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Statut</th>
                    </tr>
                </thead>
                <tbody>{rows_rupture}</tbody>
            </table>
        </div>"""

    section_faible = ""
    if faibles:
        section_faible = f"""
        <div style="margin-bottom:28px">
            <h2 style="font-size:16px;font-weight:700;color:#D97706;margin:0 0 12px">
                🟡 Produits en stock faible ({len(faibles)})
            </h2>
            <table width="100%" cellpadding="0" cellspacing="0"
                style="border-collapse:collapse;background:#FFFBEB;
                border-radius:8px;overflow:hidden;font-size:13px">
                <thead>
                    <tr style="background:#FEF3C7">
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Code</th>
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Désignation</th>
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Catégorie</th>
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Stock</th>
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Min.</th>
                        <th style="padding:10px 14px;text-align:left;color:#92400E;
                            font-size:11px;text-transform:uppercase;letter-spacing:0.05em">Statut</th>
                    </tr>
                </thead>
                <tbody>{rows_faible}</tbody>
            </table>
        </div>"""

    total = len(ruptures) + len(faibles)

    return f"""
<!DOCTYPE html>
<html lang="fr">
<head><meta charset="UTF-8"><meta name="viewport" content="width=device-width,initial-scale=1"></head>
<body style="margin:0;padding:0;background:#F8FAFC;font-family:'Segoe UI',Arial,sans-serif">
<table width="100%" cellpadding="0" cellspacing="0" style="background:#F8FAFC;padding:32px 16px">
<tr><td align="center">
<table width="600" cellpadding="0" cellspacing="0"
    style="background:white;border-radius:12px;overflow:hidden;
    box-shadow:0 4px 24px rgba(0,0,0,0.08)">

    <!-- Header -->
    <tr>
        <td style="background:linear-gradient(135deg,#1E3A5F,#2563EB);
            padding:28px 32px;text-align:center">
            <div style="font-size:28px;margin-bottom:8px">🔧</div>
            <h1 style="margin:0;color:white;font-size:20px;font-weight:700
                ;letter-spacing:-0.02em">{societe}</h1>
            <p style="margin:6px 0 0;color:#93C5FD;font-size:13px">
                Alerte Stock — {now}
            </p>
        </td>
    </tr>

    <!-- Résumé -->
    <tr>
        <td style="padding:24px 32px 16px">
            <div style="background:#EFF6FF;border:1px solid #DBEAFE;
                border-radius:8px;padding:16px 20px;margin-bottom:24px">
                <p style="margin:0;font-size:14px;color:#1E40AF;font-weight:500">
                    ⚠️ <strong>{total} produit(s)</strong> nécessitent une attention immédiate :
                    <strong style="color:#DC2626">{len(ruptures)} en rupture</strong> et
                    <strong style="color:#D97706">{len(faibles)} en stock faible</strong>.
                </p>
            </div>

            {section_rupture}
            {section_faible}

            <!-- CTA -->
            <div style="text-align:center;margin-top:8px">
                <p style="font-size:13px;color:#6B7280;margin:0">
                    Connectez-vous à SGIQ pour passer vos commandes de réapprovisionnement.
                </p>
            </div>
        </td>
    </tr>

    <!-- Footer -->
    <tr>
        <td style="background:#F8FAFC;padding:20px 32px;
            border-top:1px solid #E2E8F0;text-align:center">
            <p style="margin:0;font-size:12px;color:#94A3B8">
                {societe} · Système de Gestion Intégré · Email automatique
            </p>
        </td>
    </tr>

</table>
</td></tr>
</table>
</body>
</html>"""


# ── Envoi de la notification ──────────────────────────────────────────────

def send_stock_alert(session: Session, force: bool = False) -> dict:
    """
    Envoie un email d'alerte stock si des produits sont en alerte.
    Retourne un dict avec le résultat : {sent, nb_alertes, message}
    """
    alertes = get_produits_alerte(session)
    nb_rupture = len(alertes["rupture"])
    nb_faible  = len(alertes["faible"])
    total      = nb_rupture + nb_faible

    if total == 0:
        return {"sent": False, "nb_alertes": 0, "message": "Aucune alerte stock."}

    if not is_notification_configured(session):
        return {
            "sent": False, "nb_alertes": total,
            "message": "SMTP ou email destinataire non configuré.",
        }

    # Paramètres SMTP
    host     = _param(session, "smtp_host")
    port     = int(_param(session, "smtp_port", "587"))
    user     = _param(session, "smtp_user")
    password = _param(session, "smtp_password")
    from_addr= _param(session, "smtp_from", user)
    use_tls  = _param(session, "smtp_tls", "true").lower() in ("true", "1", "oui")
    dest     = _param(session, "notif_email_dest")
    societe  = _param(session, "societe_nom", "SGIQ")

    subject = (
        f"[{societe}] 🚨 Alerte Stock — "
        f"{nb_rupture} rupture(s), {nb_faible} stock(s) faible(s)"
    )

    html_body = _build_html(session, alertes)

    msg = MIMEMultipart("alternative")
    msg["From"]    = from_addr
    msg["To"]      = dest
    msg["Subject"] = subject
    msg.attach(MIMEText(html_body, "html", "utf-8"))

    try:
        with smtplib.SMTP(host, port, timeout=30) as server:
            if use_tls:
                server.starttls()
            if password:
                server.login(user, password)
            server.sendmail(from_addr, [dest], msg.as_string())

        # Enregistre la date du dernier envoi
        p = session.query(Parametre).filter(
            Parametre.cle == "notif_last_sent"
        ).first()
        now_str = datetime.now().strftime("%d/%m/%Y %H:%M")
        if p:
            p.valeur = now_str
        else:
            session.add(Parametre(cle="notif_last_sent", valeur=now_str))
        session.commit()

        return {
            "sent": True,
            "nb_alertes": total,
            "nb_rupture": nb_rupture,
            "nb_faible":  nb_faible,
            "message": f"Alerte envoyée à {dest} ({total} produit(s)).",
        }

    except Exception as e:
        return {"sent": False, "nb_alertes": total, "message": f"Erreur SMTP : {e}"}


# ── Vérification automatique au démarrage ────────────────────────────────

def auto_check_stock_alert(session: Session) -> dict | None:
    """
    Envoie automatiquement si :
    - Des alertes existent
    - Notification configurée
    - Pas d'envoi dans les dernières 24h
    """
    from datetime import timedelta

    last_sent_str = _param(session, "notif_last_sent", "")
    if last_sent_str:
        try:
            last_sent = datetime.strptime(last_sent_str, "%d/%m/%Y %H:%M")
            if datetime.now() - last_sent < timedelta(hours=24):
                return None  # Déjà envoyé dans les 24h
        except ValueError:
            pass

    alertes = get_produits_alerte(session)
    if len(alertes["rupture"]) + len(alertes["faible"]) == 0:
        return None

    if not is_notification_configured(session):
        return None

    return send_stock_alert(session)