"""Popups / dialogues de confirmation Streamlit."""

from __future__ import annotations

from typing import Callable

import streamlit as st


def request_dialog(key: str, payload=True):
    """Marque une popup à ouvrir au prochain rendu."""
    st.session_state[key] = payload


def clear_dialog(key: str):
    st.session_state.pop(key, None)


@st.dialog("Confirmer la suppression", width="small")
def dialog_confirm_delete(
    label: str,
    on_confirm: Callable[[], None],
    *,
    on_cancel: Callable[[], None] | None = None,
):
    """Popup de suppression dangereuse."""
    st.markdown(
        f"""
        <div style="text-align:center; padding: 0.25rem 0 0.75rem;">
          <div style="
            width:52px; height:52px; margin:0 auto 0.85rem;
            border-radius:14px; display:flex; align-items:center; justify-content:center;
            background:rgba(239,68,68,0.12); font-size:1.45rem;
          ">🗑️</div>
          <p style="margin:0; font-size:1rem; font-weight:600; color:inherit;">
            Supprimer <strong>{label}</strong> ?
          </p>
          <p style="margin:0.4rem 0 0; font-size:0.84rem; opacity:0.7;">
            Cette action est irréversible.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True, key="dlg_del_cancel"):
            if on_cancel:
                on_cancel()
            st.rerun()
    with c2:
        if st.button("Supprimer", type="primary", use_container_width=True, key="dlg_del_ok"):
            on_confirm()
            st.rerun()


@st.dialog("Confirmer l'action", width="small")
def dialog_confirm(
    title: str,
    message: str,
    on_confirm: Callable[[], None],
    *,
    confirm_label: str = "Confirmer",
    icon: str = "⚠️",
    on_cancel: Callable[[], None] | None = None,
):
    """Popup de confirmation générique."""
    st.markdown(
        f"""
        <div style="text-align:center; padding: 0.25rem 0 0.75rem;">
          <div style="
            width:52px; height:52px; margin:0 auto 0.85rem;
            border-radius:14px; display:flex; align-items:center; justify-content:center;
            background:rgba(37,99,235,0.12); font-size:1.45rem;
          ">{icon}</div>
          <p style="margin:0; font-size:1rem; font-weight:600;">{title}</p>
          <p style="margin:0.4rem 0 0; font-size:0.84rem; opacity:0.7;">{message}</p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Annuler", use_container_width=True, key="dlg_confirm_cancel"):
            if on_cancel:
                on_cancel()
            st.rerun()
    with c2:
        if st.button(confirm_label, type="primary", use_container_width=True, key="dlg_confirm_ok"):
            on_confirm()
            st.rerun()


@st.dialog("Déconnexion", width="small")
def dialog_logout(
    on_confirm: Callable[[], None],
    *,
    on_cancel: Callable[[], None] | None = None,
):
    """Popup de déconnexion."""
    st.markdown(
        """
        <div style="text-align:center; padding: 0.25rem 0 0.75rem;">
          <div style="
            width:52px; height:52px; margin:0 auto 0.85rem;
            border-radius:14px; display:flex; align-items:center; justify-content:center;
            background:rgba(30,58,95,0.12); font-size:1.45rem;
          ">🚪</div>
          <p style="margin:0; font-size:1rem; font-weight:600;">Se déconnecter ?</p>
          <p style="margin:0.4rem 0 0; font-size:0.84rem; opacity:0.7;">
            Vous pourrez vous reconnecter à tout moment.
          </p>
        </div>
        """,
        unsafe_allow_html=True,
    )
    c1, c2 = st.columns(2)
    with c1:
        if st.button("Rester", use_container_width=True, key="dlg_logout_cancel"):
            if on_cancel:
                on_cancel()
            st.rerun()
    with c2:
        if st.button("Déconnexion", type="primary", use_container_width=True, key="dlg_logout_ok"):
            on_confirm()
            st.rerun()


def run_delete_dialog(key: str, label: str, on_confirm: Callable[[], None]):
    """Affiche la popup de suppression si demandée via request_dialog(key, label)."""
    if key not in st.session_state:
        return

    def _ok():
        on_confirm()
        clear_dialog(key)

    def _cancel():
        clear_dialog(key)

    dialog_confirm_delete(label, _ok, on_cancel=_cancel)


def run_confirm_dialog(
    key: str,
    title: str,
    message: str,
    on_confirm: Callable[[], None],
    *,
    confirm_label: str = "Confirmer",
    icon: str = "⚠️",
):
    if key not in st.session_state:
        return

    def _ok():
        on_confirm()
        clear_dialog(key)

    def _cancel():
        clear_dialog(key)

    dialog_confirm(
        title, message, _ok,
        confirm_label=confirm_label, icon=icon, on_cancel=_cancel,
    )
