"""
Sistema de diseño compartido — Newell's Old Boys / Complejo Acuático.

Centraliza tokens de color, tipografía y componentes HTML reutilizables
para que `index.py` y las páginas de la app compartan una misma estética.
"""

import streamlit as st

# --- TOKENS DE MARCA ---
RED = "#E30613"
RED_DARK = "#8A0710"
GOLD = "#FFC93C"
BG = "#0A0B0E"
SURFACE = "#14151B"
SURFACE_2 = "#1C1E27"
BORDER = "#2A2C36"
TEXT = "#F5F6F8"
MUTED = "#8D93A1"


def inject_theme():
    """Inyecta fuentes, variables y estilos base compartidos por toda la app."""
    st.markdown(
        f"""
        <style>
        @import url('https://fonts.googleapis.com/css2?family=Oswald:wght@500;600;700;800&family=Inter:wght@400;500;600;700;800&display=swap');

        :root {{
            --nob-red: {RED};
            --nob-red-dark: {RED_DARK};
            --nob-gold: {GOLD};
            --nob-bg: {BG};
            --nob-surface: {SURFACE};
            --nob-surface-2: {SURFACE_2};
            --nob-border: {BORDER};
            --nob-text: {TEXT};
            --nob-muted: {MUTED};
        }}

        html, body, [class*="css"] {{
            font-family: 'Inter', sans-serif;
        }}

        [data-testid="stAppViewContainer"],
        [data-testid="stMain"] {{
            background: var(--nob-bg);
        }}

        [data-testid="stHeader"] {{
            background: transparent;
        }}

        h1, h2, h3, h4, h5, h6 {{
            font-family: 'Oswald', sans-serif;
            letter-spacing: 0.3px;
        }}

        p, span, div, label {{
            font-family: 'Inter', sans-serif;
        }}

        /* --- BOTONES --- */
        div[data-testid="stButton"] > button,
        div[data-testid="stFormSubmitButton"] > button {{
            border-radius: 10px;
            font-family: 'Inter', sans-serif;
            font-weight: 700;
            letter-spacing: 0.2px;
            transition: transform 0.15s ease, box-shadow 0.15s ease;
            border: 1px solid var(--nob-border);
        }}

        div[data-testid="stButton"] > button:hover,
        div[data-testid="stFormSubmitButton"] > button:hover {{
            transform: translateY(-1px);
        }}

        div[data-testid="stButton"] > button[kind="primary"],
        div[data-testid="stFormSubmitButton"] > button[kind="primary"] {{
            background: linear-gradient(180deg, var(--nob-red) 0%, var(--nob-red-dark) 100%);
            border: none;
            box-shadow: 0 6px 14px rgba(227, 6, 19, 0.28);
        }}

        div[data-testid="stButton"] > button[kind="primary"]:hover,
        div[data-testid="stFormSubmitButton"] > button[kind="primary"]:hover {{
            box-shadow: 0 8px 18px rgba(227, 6, 19, 0.4);
        }}

        div[data-testid="stButton"] > button[kind="secondary"] {{
            background: var(--nob-surface-2);
            color: var(--nob-text);
        }}

        /* --- INPUTS --- */
        div[data-testid="stTextInput"] input {{
            background: var(--nob-surface-2);
            border: 1px solid var(--nob-border);
            border-radius: 10px;
            color: var(--nob-text);
            font-family: 'Inter', sans-serif;
        }}

        div[data-testid="stTextInput"] input:focus {{
            border-color: var(--nob-red);
            box-shadow: 0 0 0 1px var(--nob-red);
        }}

        /* --- EXPANDERS --- */
        div[data-testid="stExpander"] {{
            background: var(--nob-surface);
            border: 1px solid var(--nob-border);
            border-radius: 12px;
        }}

        /* --- DIVIDER --- */
        hr {{
            border-color: var(--nob-border) !important;
        }}

        /* --- TABS --- */
        button[data-baseweb="tab"] {{
            font-family: 'Inter', sans-serif;
            font-weight: 600;
        }}
        </style>
        """,
        unsafe_allow_html=True,
    )


def hide_sidebar():
    st.markdown(
        """<style>[data-testid="stSidebar"] {display: none;}</style>""",
        unsafe_allow_html=True,
    )


def section_title(text: str, muted: bool = False):
    color = "var(--nob-muted)" if muted else "var(--nob-red)"
    st.markdown(
        f"""<div style="text-align:center; color:{color}; font-family:'Oswald',sans-serif;
        font-weight:700; letter-spacing:1.5px; font-size:13px; text-transform:uppercase;
        margin:6px 0 14px 0;">{text}</div>""",
        unsafe_allow_html=True,
    )


def stat_card(label: str, value, accent: str = "var(--nob-red)") -> str:
    return f"""
    <div style="flex:1; background:var(--nob-surface); border:1px solid var(--nob-border);
        border-top:3px solid {accent}; padding:16px 10px; border-radius:12px; text-align:center;">
        <div style="font-size:11px; color:var(--nob-muted); text-transform:uppercase;
            letter-spacing:0.6px; font-weight:600;">{label}</div>
        <div style="font-size:26px; font-weight:800; color:var(--nob-text); font-family:'Oswald',sans-serif;
            margin-top:4px;">{value}</div>
    </div>
    """


def medal_chip(symbol: str, count, color: str) -> str:
    return f"""
    <div style="flex:1; text-align:center;">
        <div style="font-size:20px; font-weight:800; color:{color}; font-family:'Oswald',sans-serif;">
            {symbol} {count}
        </div>
    </div>
    """
