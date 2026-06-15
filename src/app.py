"""Streamlit UI for Meridian Bank SQL Agent.

Run:  streamlit run src/app.py
"""
import os
import sys

import streamlit as st

sys.path.insert(0, os.path.dirname(__file__))
from agent import ask  # noqa: E402

st.set_page_config(page_title="Meridian Bank SQL Agent", page_icon="🏦")
st.title("🏦 Meridian Bank — Natural Language SQL Agent")
st.caption("Ask in plain English. The agent writes safe read-only SQL, runs it, and answers.")

st.markdown("**Try:** *Which customers have loans in default?* · "
            "*Total balance by branch* · *Top 3 customers by credit score*")

q = st.text_input("Your question:")

if st.button("Ask") and q:
    with st.spinner("Writing SQL -> running -> answering..."):
        out = ask(q)

    st.subheader("Answer")
    st.write(out["answer"])

    st.subheader("Generated SQL")
    st.code(out["sql"], language="sql")

    if out.get("rows"):
        with st.expander("Raw rows"):
            st.write(out["rows"][:100])

    if out.get("log"):
        st.subheader("Agent trace")
        for line in out["log"]:
            st.warning(line) if "RETRY" in line or "BLOCK" in line else st.info(line)