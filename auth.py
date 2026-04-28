import streamlit as st
import sqlite3
from database import get_connection

def login():
    st.title("Login")

    username = st.text_input("Username")
    password = st.text_input("Password", type="password")

    if st.button("Login"):
        conn = get_connection()
        c = conn.cursor()

        c.execute("SELECT * FROM users WHERE username=? AND password=?", (username, password))
        user = c.fetchone()

        conn.close()

        if user:
            st.session_state.logged_in = True
            st.session_state.user = username
        else:
            st.error("Invalid credentials")