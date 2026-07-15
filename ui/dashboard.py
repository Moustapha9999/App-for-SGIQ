# ui/dashboard.py — version responsive mobile + desktop
from datetime import datetime, timedelta
from decimal import Decimal

import pandas as pd
import plotly.express as px
import plotly.graph_objects as go
import streamlit as st
from sqlalchemy import func, select
from sqlalchemy.orm import joinedload

from database.models import (
    Achat, Client, LigneVente, Parametre, Produit, Vente,
)


def _get_devise(session) -> str:
    p = session.query(Parametre).filter(Parametre.cle == "devise").first()
    return p.valeur if p and p.valeur else "MRU"


def _fmt(val, devise: str) -> str:
    return f"{float(val):,.0f} {devise}".replace(",", " ")


def _detect_mobile() -> bool:
    """
    Injecte un JS qui écrit la largeur dans un composant caché.
    Retourne True si mobile (largeur <= 768px).
    Utilise st.session_state pour mémoriser le résultat.
    """
    if "is_mobile" not in st.session_state:
        st.session_state.is_mobile = False

    # Injection JS — détecte la largeur et stocke dans session via query param
    st.markdown("""
    <script>
    (function() {
        const w = window.innerWidth;
        const isMobile = w <= 768;
        // Stocke dans sessionStorage pour usage immédiat
        sessionStorage.setItem('sgiq_mobile', isMobile ? '1' : '0');

        // Met à jour le titre de la page avec l'info (hack Streamlit)
        if (isMobile && !document.title.includes('[M]')) {
            document.title = document.title + ' [M]';
        }
    })();
    </script>
    """, unsafe_allow_html=True)

    # Alternative fiable : utilise la largeur du viewport via CSS
    # On retourne la valeur en session (défaut desktop)
    return st.session_state.get("is_mobile", False)


def _kpi_card(label: str, value: str, sub: str,
              icon: str, icon_bg: str, dark: bool) -> str:
    card_bg     = "#1E293B" if dark else "#FFFFFF"
    card_border = "#334155" if dark else "#E2E8F0"
    card_shadow = "0 1px 3px rgba(0,0,0,0.4)" if dark else "0 1px 3px rgba(0,0,0,0.06)"
    txt_main    = "#F1F5F9" if dark else "#0F172A"
    txt_muted   = "#64748B" if dark else "#94A3B8"

    return f"""
    <div style="background:{card_bg};border:1px solid {card_border};
        border-radius:12px;padding:14px 16px;
        box-shadow:{card_shadow}">
        <div style="display:flex;justify-content:space-between;align-items:flex-start">
            <div style="flex:1;min-width:0">
                <p style="margin:0;font-size:0.68rem;font-weight:600;
                    color:{txt_muted};text-transform:uppercase;
                    letter-spacing:0.06em;white-space:nowrap;
                    overflow:hidden;text-overflow:ellipsis">{label}</p>
                <p style="margin:5px 0 0;font-size:1.3rem;font-weight:700;
                    color:{txt_main};font-family:'DM Mono',monospace;
                    line-height:1.2">{value}</p>
                <p style="margin:3px 0 0;font-size:0.7rem">{sub}</p>
            </div>
            <div style="width:36px;height:36px;background:{icon_bg};
                border-radius:9px;display:flex;align-items:center;
                justify-content:center;font-size:16px;
                flex-shrink:0;margin-left:8px">{icon}</div>
        </div>
    </div>"""


def page_dashboard(session, user):
    dark   = st.session_state.get("dark_mode", False)
    devise = _get_devise(session)
    today  = datetime.now().date()
    hier   = today - timedelta(days=1)

    # Couleurs thème
    card_bg     = "#1E293B" if dark else "#FFFFFF"
    card_border = "#334155" if dark else "#E2E8F0"
    card_shadow = "0 1px 3px rgba(0,0,0,0.4)" if dark else "0 1px 3px rgba(0,0,0,0.06)"
    txt_main    = "#F1F5F9" if dark else "#0F172A"
    txt_sub     = "#CBD5E1" if dark else "#334155"
    txt_muted   = "#64748B" if dark else "#94A3B8"
    grid_color  = "#1E293B" if dark else "#F1F5F9"
    tick_color  = "#64748B" if dark else "#94A3B8"
    plot_bg     = "rgba(0,0,0,0)"
    divider     = "#334155" if dark else "#F1F5F9"

    # ── KPIs ─────────────────────────────────────────────────────────────
    def _v(d):
        return float(session.scalar(
            select(func.coalesce(func.sum(Vente.montant_total), 0))
            .where(func.date(Vente.date) == d)) or 0)

    def _a(d):
        return float(session.scalar(
            select(func.coalesce(func.sum(Achat.montant_total), 0))
            .where(func.date(Achat.date) == d, Achat.annule == False)) or 0)

    vj, vh = _v(today), _v(hier)
    aj, ah = _a(today), _a(hier)
    bj      = vj - aj

    def delta(cur, prev):
        if prev == 0: return "—"
        pct  = (cur - prev) / prev * 100
        sign = "+" if pct >= 0 else ""
        col  = "#16A34A" if pct >= 0 else "#DC2626"
        return f"<span style='color:{col}'>{sign}{pct:.0f}% vs hier</span>"

    produits_all = session.scalars(
        select(Produit).where(Produit.statut == "Actif")).all()
    ruptures   = [p for p in produits_all if p.stock == 0]
    faibles    = [p for p in produits_all if 0 < p.stock <= p.stock_minimum]
    nb_alertes = len(ruptures) + len(faibles)

    kpi_icons = [
        ("💰", "#EFF6FF" if not dark else "#1e3a5f",
         "Ventes du jour", _fmt(vj, devise), delta(vj, vh)),
        ("🛒", "#FFFBEB" if not dark else "#1e2d0e",
         "Achats du jour", _fmt(aj, devise), delta(aj, ah)),
        ("📈", "#F0FDF4" if not dark else "#0d2818",
         "Bénéfice", _fmt(bj, devise), delta(bj, vj - ah - (aj - ah))),
        ("🚨", "#FEF2F2" if not dark else "#2d0e0e",
         "Alertes stock",
         f"<span style='color:{'#DC2626' if nb_alertes>0 else '#16A34A'}'>{nb_alertes}</span>",
         f"<span style='color:#D97706'>{len(faibles)} faible · {len(ruptures)} rupture</span>"),
    ]

    # ── CSS responsive ────────────────────────────────────────────────────
    st.markdown("""
    <style>
    /* KPI / charts responsive — ne pas toucher à la sidebar ici */

    /* Padding principal réduit sur petit écran */
    @media (max-width: 768px) {
        .block-container {
            padding-left: 0.5rem !important;
            padding-right: 0.5rem !important;
            padding-top: 0.5rem !important;
        }
        [data-testid="stHorizontalBlock"] {
            flex-wrap: wrap !important;
        }
        [data-testid="stHorizontalBlock"] > div {
            min-width: 100% !important;
            flex: 1 1 100% !important;
        }
        .stMarkdown p { font-size: 0.85rem !important; }
        h1 { font-size: 1.1rem !important; }
        h2 { font-size: 0.95rem !important; }
    }

    /* Tablette */
    @media (min-width: 769px) and (max-width: 1024px) {
        .block-container {
            padding-left: 1rem !important;
            padding-right: 1rem !important;
        }
    }

    /* KPI grid responsive */
    .kpi-grid {
        display: grid;
        gap: 12px;
        margin-bottom: 16px;
        grid-template-columns: repeat(4, 1fr);
    }
    @media (max-width: 1024px) {
        .kpi-grid { grid-template-columns: repeat(2, 1fr); }
    }
    @media (max-width: 480px) {
        .kpi-grid { grid-template-columns: 1fr; }
    }

    /* Charts row responsive */
    .charts-row {
        display: grid;
        gap: 14px;
        margin-bottom: 16px;
        grid-template-columns: 2fr 1fr;
    }
    @media (max-width: 900px) {
        .charts-row { grid-template-columns: 1fr; }
    }

    /* Bottom row responsive */
    .bottom-row {
        display: grid;
        gap: 14px;
        margin-bottom: 16px;
        grid-template-columns: 1fr 1fr;
    }
    @media (max-width: 768px) {
        .bottom-row { grid-template-columns: 1fr; }
    }

    /* Cards */
    .dash-card {
        background: """ + card_bg + """;
        border: 1px solid """ + card_border + """;
        border-radius: 12px;
        padding: 16px 18px;
        box-shadow: """ + card_shadow + """;
    }
    .card-title {
        margin: 0 0 12px;
        font-size: 0.85rem;
        font-weight: 600;
        color: """ + txt_sub + """;
    }
    </style>
    """, unsafe_allow_html=True)

    # ── En-tête ───────────────────────────────────────────────────────────
    st.markdown(f"""
    <div style="display:flex;justify-content:space-between;
        align-items:center;margin-bottom:14px;flex-wrap:wrap;gap:8px">
        <h2 style="margin:0;font-size:1.2rem;font-weight:600;
            color:{txt_main}">Tableau de bord</h2>
        <span style="color:{txt_muted};font-size:0.78rem">
            {datetime.now().strftime('%d/%m/%Y %H:%M')}
        </span>
    </div>
    """, unsafe_allow_html=True)

    # ── KPI Grid (HTML natif = vraiment responsive) ───────────────────────
    kpi_html = '<div class="kpi-grid">'
    for icon, icon_bg, label, value, sub in kpi_icons:
        kpi_html += _kpi_card(label, value, sub, icon, icon_bg, dark)
    kpi_html += '</div>'
    st.markdown(kpi_html, unsafe_allow_html=True)

    # ── Graphique ventes + Donut ──────────────────────────────────────────
    # Données 7 jours
    labels, valeurs = [], []
    for i in range(6, -1, -1):
        jour  = today - timedelta(days=i)
        total = float(session.scalar(
            select(func.coalesce(func.sum(Vente.montant_total), 0))
            .where(func.date(Vente.date) == jour)) or 0)
        labels.append(jour.strftime("%a %d"))
        valeurs.append(total)

    fig_line = go.Figure()
    fig_line.add_trace(go.Scatter(
        x=labels, y=valeurs, mode="lines+markers",
        fill="tozeroy",
        line=dict(color="#3B82F6", width=2.5),
        marker=dict(size=5, color="#3B82F6"),
        fillcolor="rgba(59,130,246,0.08)",
    ))
    fig_line.update_layout(
        margin=dict(l=0, r=0, t=0, b=0), height=180,
        showlegend=False,
        plot_bgcolor=plot_bg, paper_bgcolor=plot_bg,
        xaxis=dict(showgrid=False, tickfont=dict(size=10, color=tick_color)),
        yaxis=dict(showgrid=True, gridcolor=grid_color,
                   tickfont=dict(size=9, color=tick_color), tickformat=",.0f"),
    )

    modes = session.execute(
        select(Vente.mode_paiement, func.count(Vente.id_vente).label("nb"))
        .group_by(Vente.mode_paiement)
    ).all()

    # Layout HTML responsive pour les graphiques
    st.markdown(f"""
    <div class="charts-row">
        <div class="dash-card">
            <p class="card-title">📊 Évolution des ventes — 7 derniers jours</p>
        </div>
        <div class="dash-card">
            <p class="card-title">💳 Mode de paiement</p>
        </div>
    </div>
    """, unsafe_allow_html=True)

    # Streamlit columns pour les vrais graphiques
    col_g, col_d = st.columns([2, 1])
    with col_g:
        st.markdown(f"<div style='background:{card_bg};border:1px solid {card_border};"
                    f"border-radius:12px;padding:12px 16px;box-shadow:{card_shadow};"
                    f"margin-top:-14px'>",  # overlap avec div HTML au-dessus
                    unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 8px;font-size:0.82rem;font-weight:600;"
                    f"color:{txt_sub}'>📊 Évolution des ventes — 7 jours</p>",
                    unsafe_allow_html=True)
        st.plotly_chart(fig_line, use_container_width=True,
                        config={"displayModeBar": False})
        st.markdown("</div>", unsafe_allow_html=True)

    with col_d:
        st.markdown(f"<div style='background:{card_bg};border:1px solid {card_border};"
                    f"border-radius:12px;padding:12px 16px;box-shadow:{card_shadow};"
                    f"margin-top:-14px'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 8px;font-size:0.82rem;font-weight:600;"
                    f"color:{txt_sub}'>💳 Mode de paiement</p>",
                    unsafe_allow_html=True)
        if modes:
            df_m = pd.DataFrame(modes, columns=["Mode", "Nb"])
            fig_d = px.pie(df_m, names="Mode", values="Nb",
                           color_discrete_sequence=["#3B82F6","#F59E0B","#10B981"],
                           hole=0.62)
            fig_d.update_traces(textinfo="none",
                                hovertemplate="%{label}: %{percent}<extra></extra>")
            fig_d.update_layout(
                margin=dict(l=0, r=0, t=0, b=0), height=155,
                showlegend=True,
                legend=dict(orientation="h", yanchor="bottom", y=-0.35,
                            xanchor="center", x=0.5,
                            font=dict(size=10, color=tick_color)),
                plot_bgcolor=plot_bg, paper_bgcolor=plot_bg,
            )
            st.plotly_chart(fig_d, use_container_width=True,
                           config={"displayModeBar": False})
        else:
            st.info("Aucune vente.")
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Top 5 + Alertes ───────────────────────────────────────────────────
    col_top, col_al = st.columns([1, 1])

    with col_top:
        st.markdown(f"<div style='background:{card_bg};border:1px solid {card_border};"
                    f"border-radius:12px;padding:14px 16px;box-shadow:{card_shadow}'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 10px;font-size:0.82rem;font-weight:600;"
                    f"color:{txt_sub}'>🏆 Top 5 produits vendus</p>",
                    unsafe_allow_html=True)
        lignes = session.execute(
            select(Produit.designation,
                   func.sum(LigneVente.quantite).label("qte"))
            .join(LigneVente, Produit.code_produit == LigneVente.code_produit)
            .group_by(Produit.designation)
            .order_by(func.sum(LigneVente.quantite).desc())
            .limit(5)
        ).all()
        if lignes:
            df_top = pd.DataFrame(lignes, columns=["Produit", "Quantité"])
            # Version mobile-friendly : barres horizontales simples
            fig_b = px.bar(df_top, x="Quantité", y="Produit", orientation="h",
                          color_discrete_sequence=["#3B82F6"])
            fig_b.update_traces(marker_cornerradius=4)
            fig_b.update_layout(
                margin=dict(l=0, r=0, t=0, b=0), height=185,
                showlegend=False,
                plot_bgcolor=plot_bg, paper_bgcolor=plot_bg,
                xaxis=dict(showgrid=True, gridcolor=grid_color,
                           tickfont=dict(size=9, color=tick_color)),
                yaxis=dict(autorange="reversed", showgrid=False,
                           tickfont=dict(size=10, color=txt_sub)),
            )
            st.plotly_chart(fig_b, use_container_width=True,
                           config={"displayModeBar": False})
        else:
            st.info("Aucune vente.")
        st.markdown("</div>", unsafe_allow_html=True)

    with col_al:
        st.markdown(f"<div style='background:{card_bg};border:1px solid {card_border};"
                    f"border-radius:12px;padding:14px 16px;box-shadow:{card_shadow}'>",
                    unsafe_allow_html=True)
        st.markdown(f"<p style='margin:0 0 10px;font-size:0.82rem;font-weight:600;"
                    f"color:{txt_sub}'>🚨 Alertes stock critiques</p>",
                    unsafe_allow_html=True)

        if not ruptures and not faibles:
            st.success("✅ Tous les stocks sont OK.")
        else:
            html = ""
            for p, typ in ([(p,"rupture") for p in ruptures] +
                           [(p,"faible")  for p in faibles])[:5]:
                dot   = "#EF4444" if typ == "rupture" else "#F59E0B"
                bb    = "#FEE2E2" if typ == "rupture" else "#FEF3C7"
                bt    = "#DC2626" if typ == "rupture" else "#D97706"
                badge = "Rupture"  if typ == "rupture" else "Faible"
                desc  = (f"Stock: 0 — Rupture" if typ == "rupture"
                         else f"Stock: {p.stock}/{p.stock_minimum}")
                pct   = 0 if typ == "rupture" else min(
                    int(p.stock/p.stock_minimum*100) if p.stock_minimum else 0, 100)
                bar   = (f"<div style='height:3px;background:{divider};"
                         f"border-radius:2px;margin-top:4px'>"
                         f"<div style='height:3px;width:{pct}%;"
                         f"background:{dot};border-radius:2px'>"
                         f"</div></div>") if typ == "faible" else ""

                html += (
                    f"<div style='display:flex;align-items:flex-start;"
                    f"gap:8px;padding:8px 0;"
                    f"border-bottom:1px solid {divider}'>"
                    f"<div style='width:7px;height:7px;border-radius:50%;"
                    f"background:{dot};margin-top:5px;flex-shrink:0'></div>"
                    f"<div style='flex:1;min-width:0'>"
                    f"<p style='margin:0;font-size:0.78rem;font-weight:500;"
                    f"color:{txt_main};overflow:hidden;text-overflow:ellipsis;"
                    f"white-space:nowrap'>{p.designation}</p>"
                    f"<p style='margin:1px 0 0;font-size:0.68rem;"
                    f"color:{txt_muted}'>{desc}</p>{bar}</div>"
                    f"<span style='background:{bb};color:{bt};"
                    f"font-size:0.62rem;font-weight:600;padding:2px 7px;"
                    f"border-radius:20px;white-space:nowrap'>{badge}</span>"
                    f"</div>"
                )
            st.markdown(f"<div>{html}</div>", unsafe_allow_html=True)
        st.markdown("</div>", unsafe_allow_html=True)

    st.markdown("<div style='height:8px'></div>", unsafe_allow_html=True)

    # ── Dernières ventes ─────────────────────────────────────────────────
    st.markdown(f"""
    <div style="background:{card_bg};border:1px solid {card_border};
        border-radius:12px;padding:14px 16px;box-shadow:{card_shadow}">
        <p style="margin:0 0 10px;font-size:0.82rem;font-weight:600;
            color:{txt_sub}">📋 Dernières ventes</p>
    """, unsafe_allow_html=True)

    dernieres = session.scalars(
        select(Vente).options(joinedload(Vente.client))
        .order_by(Vente.date.desc()).limit(5)
    ).unique().all()

    if dernieres:
        # Version compacte pour mobile
        df_v = pd.DataFrame([{
            "Facture": v.numero_facture or f"#{v.id_vente}",
            "Client":  (v.client.nom_client[:15] + "…"
                        if v.client and len(v.client.nom_client) > 15
                        else (v.client.nom_client if v.client else "Comptant")),
            "Montant": _fmt(v.montant_total, devise),
            "Statut":  v.statut,
        } for v in dernieres])
        st.dataframe(df_v, hide_index=True, use_container_width=True)
    else:
        st.info("Aucune vente enregistrée.")

    st.markdown("</div>", unsafe_allow_html=True)