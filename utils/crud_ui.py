"""Composants réutilisables pour listes et formulaires CRUD Streamlit."""

import pandas as pd
import streamlit as st


def render_dataframe(df: pd.DataFrame, use_container_width: bool = True):
    if df.empty:
        st.info("Aucun enregistrement.")
    else:
        st.dataframe(df, use_container_width=use_container_width, hide_index=True)


def select_id_from_df(df: pd.DataFrame, id_col: str, label: str = "Sélectionner") -> int | None:
    if df.empty:
        return None
    options = {f"{row[id_col]} — {row.iloc[1] if len(row) > 1 else ''}": row[id_col] for _, row in df.iterrows()}
    choice = st.selectbox(label, ["—"] + list(options.keys()))
    return options[choice] if choice != "—" else None
