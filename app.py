"""Rafd — entry point. Two fully separate language pages (Arabic RTL / English LTR)."""
import streamlit as st

st.set_page_config(page_title="Rafd", page_icon="🕌", layout="wide",
                   initial_sidebar_state="expanded")

pg = st.navigation([
    st.Page("pages/arabic_app.py",  title="رَفد — العربية",  icon="🕌", default=True),
    st.Page("pages/english_app.py", title="Rafd — English", icon="🌐"),
])
pg.run()
