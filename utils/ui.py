"""Helpers UI partagés."""

import streamlit as st


def page_header(title: str, subtitle: str | None = None, icon: str = ""):
    """En-tête de page plus soigné."""
    dark = st.session_state.get("dark_mode", False)
    muted = "#94A3B8" if dark else "#64748B"
    border = "#334155" if dark else "#E2E8F0"
    label = f"{icon} {title}".strip() if icon else title
    sub = (
        f'<p style="margin:0.2rem 0 0; font-size:0.88rem; color:{muted};">{subtitle}</p>'
        if subtitle
        else ""
    )
    st.markdown(
        f"""
        <div style="
          margin: 0 0 1.25rem; padding-bottom: 0.9rem;
          border-bottom: 1px solid {border};
        ">
          <h1 style="margin:0 !important; padding:0 !important; border:none !important;">
            {label}
          </h1>
          {sub}
        </div>
        """,
        unsafe_allow_html=True,
    )
