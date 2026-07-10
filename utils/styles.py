"""Reusable styling helpers for the Streamlit app.

Keeps all CSS in static/style.css so page modules (home.py, pages/chat.py, ...)
only ever deal with content, never inline style strings.
"""

from __future__ import annotations

from pathlib import Path

import streamlit as st

_STATIC_DIR = Path(__file__).resolve().parent.parent / "static"


def load_css(filename: str = "style.css") -> None:
    """Inject the shared stylesheet into the current page."""
    css_path = _STATIC_DIR / filename
    with css_path.open("r", encoding="utf-8") as f:
        st.markdown(f"<style>{f.read()}</style>", unsafe_allow_html=True)


def load_material_symbols_font() -> None:
    """Load the Material Symbols icon font used for section/benefit icons."""
    st.markdown(
        '<link rel="stylesheet" href="https://fonts.googleapis.com/css2?'
        'family=Material+Symbols+Outlined:opsz,wght,FILL,GRAD@20..48,100..700,0..1,-50..200" />',
        unsafe_allow_html=True,
    )


def apply_theme(primary_color: str) -> None:
    """Set the active company's accent color as a CSS custom property.

    This is the only piece of styling that legitimately depends on runtime
    data (the company config), so it's the only styling call that takes
    a parameter — everything else lives statically in style.css.
    """
    st.markdown(
        f"<style>:root {{ --primary-color: {primary_color}; }}</style>",
        unsafe_allow_html=True,
    )
