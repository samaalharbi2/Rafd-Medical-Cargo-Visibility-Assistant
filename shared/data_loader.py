"""Load chunks.json and build lookup indexes."""
import os, json
import pandas as pd
import streamlit as st

@st.cache_data
def load_chunks():
    root = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
    for p in [os.path.join(root, "chunks.json"), "chunks.json", "data/chunks.json"]:
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None

def build_indexes(chunks):
    ships    = [c for c in chunks if c["document_type"] == "shipment"]
    tracks   = {c["shipment_id"]: c for c in chunks if c["document_type"] == "tracking"}
    policies = {c["policy_rule"]: c for c in chunks if c["document_type"] == "policy"}
    by_awb   = {c["air_waybill_number"]: c for c in ships}
    return ships, tracks, policies, by_awb

def ships_df(ships):
    return pd.DataFrame(ships)
