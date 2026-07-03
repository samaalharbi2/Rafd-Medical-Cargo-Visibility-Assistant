"""Operations dashboard (from shipment data) + Assistant insights (from chat logs)."""
from collections import Counter
import pandas as pd
import streamlit as st
from shared.chat_memory import read_conversations, read_feedback
from shared.knowledge_base import load_unanswered

def kpi_row(ships, S):
    vals = [(S["kpi_total"], len(ships)),
            (S["kpi_esc"], sum(1 for c in ships if c["requires_escalation"])),
            (S["kpi_missed"], sum(1 for c in ships if c["deadline_status"] == "MISSED Deadline")),
            (S["kpi_cold"], sum(1 for c in ships if c["shipment_status"] == "Cold Chain Alert")),
            (S["kpi_sfda"], sum(1 for c in ships if c["shipment_status"] == "SFDA Hold"))]
    cols = st.columns(len(vals))
    for col, (label, n) in zip(cols, vals):
        col.markdown(f"<div class='kpi'><div class='n'>{n}</div><div class='l'>{label}</div></div>",
                     unsafe_allow_html=True)

def render_operations(df, S):
    st.markdown(f"#### {S['dash_ops']}")
    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{S['ch_status']}**");   st.bar_chart(df["shipment_status"].value_counts())
        st.markdown(f"**{S['ch_facility']}**"); st.bar_chart(df["destination_facility"].value_counts())
    with c2:
        st.markdown(f"**{S['ch_priority']}**"); st.bar_chart(df["priority_level"].value_counts())
        st.markdown(f"**{S['ch_deadline']}**"); st.bar_chart(df["deadline_status"].value_counts())
    with st.expander(S["show_table"]):
        st.dataframe(df[["air_waybill_number", "cargo_type_en", "destination_airport",
                         "destination_facility", "priority_level", "shipment_status",
                         "delay_minutes", "deadline_status", "requires_escalation"]],
                     use_container_width=True, height=300)

def render_insights(S, lang):
    st.markdown(f"#### {S['dash_ai']}")
    conv = read_conversations()
    if not conv:
        st.info(S["insights_empty"])
        return
    feed = read_feedback()
    n_q = len(conv)
    intents = Counter(r.get("intent", "unknown") for r in conv)
    awbs = Counter(r["shipment_id"] for r in conv if r.get("shipment_id"))
    low_conf = sum(1 for r in conv if (r.get("confidence") or 0) < 0.5)
    unanswered = len(load_unanswered())
    helpful = sum(1 for r in feed if r.get("rating") == "helpful")
    not_helpful = sum(1 for r in feed if r.get("rating") in ("not_helpful", "needs_correction"))
    top_q = Counter(r.get("question", "") for r in conv).most_common(3)

    m = st.columns(4)
    m[0].metric(S["ins_total"], n_q)
    m[1].metric(S["ins_unanswered"], unanswered)
    m[2].metric(S["ins_lowconf"], low_conf)
    m[3].metric(S["ins_feedback"], f"{helpful} 👍 / {not_helpful} 👎")

    c1, c2 = st.columns(2)
    with c1:
        st.markdown(f"**{S['ins_intents']}**")
        st.bar_chart(pd.Series(dict(intents)))
    with c2:
        st.markdown(f"**{S['ins_awb']}**")
        if awbs:
            st.bar_chart(pd.Series(dict(awbs.most_common(5))))
        else:
            st.caption("—")
    st.markdown(f"**{S['ins_topq']}**")
    for q, n in top_q:
        st.markdown(f"- {q} × {n}")
