# app.py  
from pathlib import Path

import streamlit as st

from pipeline import pipeliner_run
from renderer import dfa_to_dot, program_to_dfa

TESTS = Path(__file__).parent / "samples"

st.set_page_config(page_title="DFA Language", layout="wide")
st.title("DFA Formal Description Language")

# Sidebar: load a sample program
samples = {"(blank)": ""}
for f in sorted(TESTS.glob("*.txt")):
    samples[f.name] = f.read_text(encoding="utf-8")
choice = st.sidebar.selectbox("Load a sample", list(samples))

left, right = st.columns(2)

with left:
    text = st.text_area("Program", value=samples[choice], height=420,
                        key=f"editor_{choice}")
    run = st.button("Run", type="primary")

with right:
    if run:
        program, errors = pipeliner_run(text)
        if errors:
            st.subheader("Errors")
            for message, line, column in errors:
                st.error(f"{message} (line {line}, column {column})")
        else:
            dfa = program_to_dfa(program)
            st.subheader(f"State diagram: {dfa['name']}")
            st.graphviz_chart(dfa_to_dot(dfa))
            rows = [
                {"state": s, **{a: dfa["transitions"].get((s, a), "") for a in dfa["alphabet"]}}
                for s in dfa["states"]
            ]
            st.table(rows)