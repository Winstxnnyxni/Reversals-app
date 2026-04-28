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

        section[data-testid="stSidebar"] {
            width: 280px !important;
            min-width: 280px !important;
        }

        div[data-testid="stSidebarCollapsedControl"] {
            left: 0.6rem !important;
        }

        div[data-testid="stPopover"] button {
            min-height: 1.75rem !important;
            width: 1.9rem !important;
            padding: 0 !important;
            font-size: 0.92rem !important;
            line-height: 1 !important;
            opacity: 0.04;
            transition: opacity 0.15s ease;
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
        }

        div[data-testid="stPopover"] button:hover,
        div[data-testid="stPopover"] button:focus,
        div[data-testid="stPopover"] button:focus-visible {
            opacity: 1;
        }

        .st-key-fact_button button {
            min-height: 2.2rem !important;
            width: 2.2rem !important;
            padding: 0 !important;
            font-size: 1.3rem !important;
            line-height: 1 !important;
            border: none !important;
            box-shadow: none !important;
            background: transparent !important;
            color: #facc15 !important;
        }

        .note-card,
        .note-card * {
            color: #111827 !important;
        }

        .note-card {
            display: inline-flex;
            align-items: center;
            width: fit-content;
            max-width: 100%;
            background: #e5e7eb !important;
            border: 1px solid #cbd5e1 !important;
            border-radius: 999px;
            padding: 0.22rem 0.65rem;
            margin-top: 0.3rem;
            font-size: 0.9rem;
            line-height: 1.25rem;
        }

        .cell-card {
            border-radius: 0.35rem;
            padding: 0.24rem 0.45rem;
            min-height: 1.95rem;
            display: flex;
            align-items: center;
            color: inherit;
            font-size: 0.95rem;
            line-height: 1.2rem;
        }

        .tiny-download button {
            min-height: 2rem !important;
            width: 2rem !important;
            padding: 0 !important;
            border-radius: 8px !important;
        }

        @media (prefers-color-scheme: dark) {
            .st-key-fact_button button {
                color: #fde68a !important;
            }
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


def inject_login_styles():
    st.markdown(
        """
        <style>
        .stApp [data-testid="block-container"] {
            max-width: 1120px;
            padding-top: 3rem;
        }
        </style>
        """,
        unsafe_allow_html=True,
    )


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


def build_recent_entries_excel(df: pd.DataFrame):
    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Recent Entries"

    worksheet.append(
        [
            "Date Reversed",
            "TX date",
            "Branch",
            "Reversal Reference",
            "Replacement Reference",
            "Amount",
            "Saved by",
            "Note",
        ]
    )

    for _, row in df.iterrows():
        worksheet.append(
            [
                format_date(row.get("date_reversed", "")),
                format_date(row.get("tx_date", "")),
                row.get("branch", "") or "",
                row.get("reversal_ref", "") or "",
                row.get("replacement_ref", "") or "",
                row.get("amount", "") or "",
                row.get("saved_by", "") or "",
                row.get("note", "") or "",
            ]
        )

    for column_cells in worksheet.columns:
        max_length = max(len(str(cell.value or "")) for cell in column_cells)
        worksheet.column_dimensions[column_cells[0].column_letter].width = min(max_length + 2, 40)

    buffer = BytesIO()
    workbook.save(buffer)
    buffer.seek(0)
    return buffer.getvalue()


def create_transaction(branch, reversal, replacement, amount_text, replacement_tx_date, date_reversed, note, fill_name):
    conn = get_connection()
    try:
        if reversal_exists(reversal):
            return False, "Reversal reference already exists"

        cursor = conn.cursor()
        cursor.execute(
            """
            INSERT INTO reversals (
                tx_date,
                branch,
                reversal_ref,
                replacement_ref,
                amount,
                note,
                highlight_color,
                is_highlighted,
                date_reversed,
                saved_by
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                format_date(replacement_tx_date),
                branch.strip(),
                reversal.strip(),
                replacement.strip(),
                amount_text.strip() if amount_text else "0.00",
                note.strip(),
                HIGHLIGHT_OPTIONS.get(fill_name, ""),
                1 if HIGHLIGHT_OPTIONS.get(fill_name) else 0,
                format_date(date_reversed),
                get_current_username(),
            ),
        )
        conn.commit()
        return True, "Successfully saved"
    except Exception:
        return False, "Something went wrong while saving. Please try again."
    finally:
        conn.close()


def update_transaction_note_and_color(tx_id, note, fill_name):
    conn = get_connection()
    try:
        cursor = conn.cursor()
        cursor.execute(
            """
            UPDATE reversals
            SET note = ?, highlight_color = ?, is_highlighted = ?
            WHERE id = ?
            """,
            (
                note.strip(),
                HIGHLIGHT_OPTIONS.get(fill_name, ""),
                1 if HIGHLIGHT_OPTIONS.get(fill_name) else 0,
                tx_id,
            ),
        )
        conn.commit()

        if cursor.rowcount == 0:
            return False, "That entry no longer exists. Refresh and try again."

        return True, "Entry updated successfully"
    except Exception:
        return False, "Something went wrong while updating the entry."
    finally:
        conn.close()


def form_has_unsaved_data():
    return any(
        [
            str(st.session_state.get("branch", "")).strip(),
            str(st.session_state.get("reversal", "")).strip(),
            str(st.session_state.get("amount", "")).strip(),
            str(st.session_state.get("replacement", "")).strip(),
            str(st.session_state.get("draft_note", "")).strip(),
            st.session_state.get("draft_highlight", "No Fill") != "No Fill",
        ]
    )


init_db()
ensure_optional_columns()

from create_user import create_user
try:
    create_user("admin", "1234")
except:
    pass

if "logged_in" not in st.session_state:
    st.session_state.logged_in = False
if "clear_draft_note" not in st.session_state:
    st.session_state.clear_draft_note = False
if "draft_highlight" not in st.session_state:
    st.session_state.draft_highlight = "No Fill"
if "reset_form" not in st.session_state:
    st.session_state.reset_form = False
if "show_saved_popup" not in st.session_state:
    st.session_state.show_saved_popup = False
if "date_reversed" not in st.session_state:
    st.session_state.date_reversed = datetime.today().date()
if "branch" not in st.session_state:
    st.session_state.branch = ""
if "reversal" not in st.session_state:
    st.session_state.reversal = ""
if "amount" not in st.session_state:
    st.session_state.amount = ""
if "replacement_tx_date" not in st.session_state:
    st.session_state.replacement_tx_date = datetime.today().date()
if "replacement" not in st.session_state:
    st.session_state.replacement = ""
if "draft_note" not in st.session_state:
    st.session_state.draft_note = ""

if not st.session_state.logged_in:
    inject_login_styles()
    left, center, right = st.columns([1.2, 1.6, 1.2])
    with center:
        login()
    st.stop()

inject_app_styles()

if st.session_state.get("reset_form"):
    st.session_state.date_reversed = datetime.today().date()
    st.session_state.branch = ""
    st.session_state.reversal = ""
    st.session_state.amount = ""
    st.session_state.replacement_tx_date = datetime.today().date()
    st.session_state.replacement = ""
    st.session_state.draft_note = ""
    st.session_state.draft_highlight = "No Fill"
    st.session_state.reset_form = False

if not form_has_unsaved_data():
    st_autorefresh(interval=30000, key="recent_entries_refresh")
else:
    st.caption("Auto refresh paused while form has unsaved data.")

if st.session_state.get("show_saved_popup"):
    st.toast("Successfully saved", icon="✅")
    st.session_state.show_saved_popup = False

if st.session_state.get("clear_draft_note"):
    st.session_state.clear_draft_note = False
    st.session_state.pop("draft_note", None)
    st.session_state.draft_highlight = "No Fill"

with st.sidebar:
    if st.button("Logout"):
        st.session_state.logged_in = False
        st.rerun()

title_col, fact_col = st.columns([0.84, 0.16])
with title_col:
    st.title("Reversals Sheet")
with fact_col:
    fact_clicked = st.button("💡", key="fact_button", help="Did you know?", use_container_width=False)
    if fact_clicked:
        category, fact = get_random_fact()
        st.toast(f"{category}: {fact}", icon="💡")

form_header_1, form_header_2, form_header_3, form_header_4 = st.columns([0.45, 1, 1, 0.45])
with form_header_1:
    st.markdown("**Date Reversed**")
with form_header_2:
    st.markdown("**Branch**")
with form_header_3:
    st.markdown("**Reversal Reference**")
with form_header_4:
    st.markdown("**Amount**")

row1_col1, row1_col2, row1_col3, row1_col4 = st.columns([0.45, 1, 1, 0.45])
with row1_col1:
    date_reversed = st.date_input(
        "date_reversed",
        key="date_reversed",
        label_visibility="collapsed",
    )
with row1_col2:
    branch = st.text_input(
        "branch",
        key="branch",
        label_visibility="collapsed",
    )
with row1_col3:
    reversal = st.text_input(
        "Reversal Reference",
        key="reversal",
        label_visibility="collapsed",
    )
with row1_col4:
    amount_text = st.text_input(
        "amount",
        key="amount",
        label_visibility="collapsed",
    )

form_header_5, form_header_6, form_header_7, form_header_8 = st.columns([0.45, 1, 1, 0.45])
with form_header_5:
    st.markdown("**Tx Date**")
with form_header_6:
    st.markdown("**Branch**")
with form_header_7:
    st.markdown("**Replacement Reference**")
with form_header_8:
    st.markdown("**Amount**")

row2_col1, row2_col2, row2_col3, row2_col4 = st.columns([0.45, 1, 1, 0.45])
with row2_col1:
    replacement_tx_date = st.date_input(
        "replacement_tx_date",
        key="replacement_tx_date",
        label_visibility="collapsed",
    )
with row2_col2:
    st.text_input("branch_display", value=branch, disabled=True, label_visibility="collapsed")
with row2_col3:
    replacement = st.text_input(
        "Replacement Reference",
        key="replacement",
        label_visibility="collapsed",
    )
with row2_col4:
    st.text_input("amount_display", value=amount_text, disabled=True, label_visibility="collapsed")

action_col1, action_col2, action_col3 = st.columns([0.22, 0.08, 0.7])
with action_col1:
    submit_clicked = st.button("Submit", use_container_width=True)
with action_col2:
    with st.popover("≡", use_container_width=True):
        st.text_area("Note", key="draft_note", placeholder="Add a short note")
        st.radio(
            "Fill Color",
            options=list(HIGHLIGHT_OPTIONS.keys()),
            key="draft_highlight",
            horizontal=True,
        )
with action_col3:
    st.write("")

if submit_clicked:
    if not branch or not reversal or not replacement:
        st.error("Branch, Reversal Reference, and Replacement Reference are required")
    elif amount_text and not amount_text.replace(".", "", 1).isdigit():
        st.error("Amount must be a valid number")
    else:
        ok, message = create_transaction(
            branch=branch,
            reversal=reversal,
            replacement=replacement,
            amount_text=amount_text,
            replacement_tx_date=replacement_tx_date,
            date_reversed=date_reversed,
            note=st.session_state.get("draft_note", ""),
            fill_name=st.session_state.get("draft_highlight", "No Fill"),
        )
        if ok:
            st.session_state.reset_form = True
            st.session_state.show_saved_popup = True
            st.rerun()
        else:
            st.error(message)

st.markdown("---")

recent = fetch_recent_entries()

recent_title_col, recent_download_col = st.columns([0.94, 0.06])
with recent_title_col:
    st.subheader("Recent Entries")
with recent_download_col:
    st.markdown("<div class='tiny-download'>", unsafe_allow_html=True)
    st.download_button(
        "⭳",
        data=build_recent_entries_excel(recent),
        file_name=f"recent_entries_{datetime.now().strftime('%Y%m%d_%H%M%S')}.xlsx",
        mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
        key="download_recent_entries",
        use_container_width=True,
    )
    st.markdown("</div>", unsafe_allow_html=True)

col1, col2, col3, col4, col5, col6, col7 = st.columns([0.55, 0.55, 1, 1, 1, 0.45, 0.08])
with col1:
    st.markdown("**Date Reversed**")
with col2:
    st.markdown("**Tx Date**")
with col3:
    st.markdown("**Branch**")
with col4:
    st.markdown("**Reversal Reference**")
with col5:
    st.markdown("**Replacement Reference**")
with col6:
    st.markdown("**Amount**")

st.markdown("---")

for _, tx in recent.iterrows():
    row_color = tx["highlight_color"] or "transparent"

    row1_col1, row1_col2, row1_col3, row1_col4, row1_col5, row1_col6, row1_col7 = st.columns([0.55, 0.55, 1, 1, 1, 0.45, 0.08])
    with row1_col1:
        render_cell(format_date(tx["date_reversed"]), row_color)
    with row1_col2:
        render_cell(format_date(tx["tx_date"]), row_color)
    with row1_col3:
        render_cell(tx["branch"], row_color)
    with row1_col4:
        render_cell(tx["reversal_ref"], row_color)
    with row1_col5:
        render_cell(tx["replacement_ref"], row_color)
    with row1_col6:
        render_cell(tx["amount"], row_color)
    with row1_col7:
        with st.popover("≡", use_container_width=True):
            updated_note = st.text_area(
                "Note",
                value=tx["note"] or "",
                key=f"note_{tx['id']}",
            )
            updated_color_name = st.radio(
                "Fill Color",
                options=list(HIGHLIGHT_OPTIONS.keys()),
                index=list(HIGHLIGHT_OPTIONS.keys()).index(
                    color_name_from_value(tx["highlight_color"])
                ),
                key=f"highlight_{tx['id']}",
                horizontal=True,
            )
            if st.button("Save", key=f"save_{tx['id']}", use_container_width=True):
                ok, message = update_transaction_note_and_color(
                    int(tx["id"]),
                    updated_note,
                    updated_color_name,
                )
                if ok:
                    st.success(message)
                    st.rerun()
                else:
                    st.error(message)

    if tx["note"]:
        st.markdown(f"<div class='note-card'>{escape(tx['note'])}</div>", unsafe_allow_html=True)

    st.markdown("---")
