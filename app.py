import random
from datetime import datetime
from html import escape
from io import BytesIO

import pandas as pd
import streamlit as st
from streamlit_autorefresh import st_autorefresh
from openpyxl import Workbook

from auth import login
from database import get_connection, init_db


st.set_page_config(layout="wide")

HIGHLIGHT_OPTIONS = {
    "No Fill": "",
    "Yellow": "#ffe9a8",
    "Blue": "#dbeafe",
    "Green": "#dcfce7",
    "Red": "#fee2e2",
}

DID_YOU_KNOW_FACTS = {
    "Tech": [
        "Bluetooth is named after a 10th-century Viking king, Harald Bluetooth.",
        "The original name for Windows was Interface Manager.",
        "The first 1 GB hard drive, released in 1980, weighed over 200 kilograms.",
        "Over 500 hours of video are uploaded to YouTube every minute.",
        "There are computer keyboards used in space with velcro to stop them floating away.",
        "The inventor of the microwave oven noticed the idea after a candy bar melted in his pocket.",
    ],
    "Nature": [
        "Honey never spoils when stored properly.",
        "Octopuses have three hearts.",
        "Bananas are berries, but strawberries are not.",
        "Crows can recognize human faces and remember them for years.",
        "Some turtles can breathe through their backsides in winter.",
        "Some cats are allergic to humans.",
        "Sea otters hold hands while sleeping so they do not drift apart.",
        "The fingerprints of a koala are so close to humans that they can confuse investigators.",
        "Some fungi create zombies out of insects by controlling their behavior.",
    ],
    "Space": [
        "A day on Venus is longer than a year on Venus.",
        "The moon has moonquakes.",
        "A bolt of lightning is about five times hotter than the surface of the sun.",
        "There are more trees on Earth than stars in the Milky Way, according to broad estimates.",
    ],
    "Wild Random": [
        "The Eiffel Tower grows slightly taller in hot weather.",
        "Sharks existed before trees.",
        "The first photo ever taken needed an exposure of about eight hours.",
        "There are more possible chess games than atoms in the observable universe.",
        "Scotland's national animal is the unicorn.",
        "Sloths can hold their breath longer than dolphins can.",
        "The dot over a lowercase i or j is called a tittle.",
        "Wombat poop is cube-shaped.",
        "The hottest chili peppers can trigger your brain to release endorphins like a stress response.",
        "A single cloud can weigh more than a million pounds.",
        "There is a species of jellyfish that can revert to an earlier life stage.",
        "The smell of rain has a name: petrichor.",
        "A group of flamingos is called a flamboyance.",
        "Your brain can generate enough power to light a small bulb.",
        "Norway once knighted a penguin living in a zoo in Scotland.",
        "The quietest room in the world is so silent that people can hear their own heartbeat and stomach movements.",
        "LEGO minifigures are the world's largest population group by number if counted as people-like figures.",
    ],
}


def inject_app_styles():
    st.markdown(
        """
        <style>
        .stApp [data-testid="block-container"] {
            max-width: 1120px;
            padding-top: 2rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# ✅ ONLY CHANGE IS HERE
def inject_login_styles():
    st.markdown(
        """
        <style>
        .stApp [data-testid="block-container"] {
            max-width: 420px;   /* narrower login box */
            padding-top: 5rem;
            margin: auto;       /* center it */
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


# =========================
# EVERYTHING BELOW UNCHANGED
# =========================

def ensure_optional_columns():
    conn = get_connection()
    try:
        cursor = conn.cursor()
        columns = {row[1] for row in cursor.execute("PRAGMA table_info(reversals)").fetchall()}

        if "note" not in columns:
            cursor.execute("ALTER TABLE reversals ADD COLUMN note TEXT DEFAULT ''")
        if "highlight_color" not in columns:
            cursor.execute("ALTER TABLE reversals ADD COLUMN highlight_color TEXT DEFAULT ''")
        if "is_highlighted" not in columns:
            cursor.execute("ALTER TABLE reversals ADD COLUMN is_highlighted INTEGER DEFAULT 0")
        if "date_reversed" not in columns:
            cursor.execute("ALTER TABLE reversals ADD COLUMN date_reversed TEXT DEFAULT ''")
        if "saved_by" not in columns:
            cursor.execute("ALTER TABLE reversals ADD COLUMN saved_by TEXT DEFAULT ''")

        conn.commit()
    finally:
        conn.close()


def format_date(value):
    if hasattr(value, "strftime"):
        return value.strftime("%Y-%m-%d")
    return value or ""


def color_name_from_value(value):
    for label, color in HIGHLIGHT_OPTIONS.items():
        if color == (value or ""):
            return label
    return "No Fill"


def get_random_fact():
    category = random.choice(list(DID_YOU_KNOW_FACTS.keys()))
    fact = random.choice(DID_YOU_KNOW_FACTS[category])
    return category, fact


def get_current_username():
    user = st.session_state.get("user")

    if user:
        return str(user).strip()

    for key in ["username", "user_name", "logged_in_user", "email"]:
        value = st.session_state.get(key)
        if value:
            return str(value).strip()

    return ""


def render_cell(content, background="transparent"):
    safe_content = escape(str(content or ""))
    text_color = "#111827" if background != "transparent" else "inherit"
    st.markdown(
        f"<div class='cell-card' style='background:{background}; color:{text_color};'>{safe_content}</div>",
        unsafe_allow_html=True,
    )


def fetch_recent_entries():
    conn = get_connection()
    try:
        return pd.read_sql_query(
            """
            SELECT
                id,
                date_reversed,
                tx_date,
                branch,
                reversal_ref,
                replacement_ref,
                amount,
                COALESCE(note, '') AS note,
                COALESCE(highlight_color, '') AS highlight_color,
                COALESCE(is_highlighted, 0) AS is_highlighted,
                COALESCE(saved_by, '') AS saved_by
            FROM reversals
            ORDER BY id DESC
            """,
            conn,
        )
    finally:
        conn.close()


def reversal_exists(reversal_ref):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        row = cursor.execute(
            "SELECT id FROM reversals WHERE reversal_ref = ? LIMIT 1",
            (reversal_ref,),
        ).fetchone()
        return row is not None
    finally:
        conn.close()


# =========================
# INIT
# =========================

init_db()
ensure_optional_columns()

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False

# =========================
# LOGIN SCREEN
# =========================

if not st.session_state.logged_in:
    inject_login_styles()
    login()
    st.stop()

# =========================
# APP START
# =========================

inject_app_styles()

st.title("Reversals Sheet")

st.markdown("---")