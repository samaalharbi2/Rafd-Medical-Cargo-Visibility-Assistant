"""
Rafd / رفد — Medical Cargo Visibility & Escalation Assistant
One UI language switch (Arabic / English) controls the WHOLE interface.
Light/Dark theme toggle. Metadata-aware retrieval + optional GPT rephrasing.
"""
import os, json, re
import pandas as pd
import streamlit as st
from translations import ap, fac, evt

@st.cache_data
def load_chunks():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(here, "chunks.json"), os.path.join(here, "data", "chunks.json"),
              "chunks.json", "data/chunks.json"]:
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None

chunks = load_chunks()

# ===========================================================================
# UI STRINGS (single source of truth for both languages)
# ===========================================================================
T = {
    "title_sub":   {"ar": "مساعد رؤية وتصعيد الشحنات الطبية", "en": "Medical Cargo Visibility & Escalation Assistant"},
    "title_ctx":   {"ar": "لعمليات لوجستيات الحج والعمرة الطبية", "en": "For Hajj & Umrah medical logistics operations"},
    "settings":    {"ar": "الإعدادات", "en": "Settings"},
    "language":    {"ar": "اللغة", "en": "Language"},
    "theme":       {"ar": "المظهر", "en": "Theme"},
    "light":       {"ar": "فاتح", "en": "Light"},
    "dark":        {"ar": "داكن", "en": "Dark"},
    "tier":        {"ar": "طبقة الإجابة", "en": "Answer tier"},
    "tier_rule":   {"ar": "قواعد محلية (بدون مفتاح)", "en": "Rule-based (No API)"},
    "tier_ai":     {"ar": "صياغة بالذكاء الاصطناعي (GPT)", "en": "AI-phrased (GPT)"},
    "tier_help":   {"ar": "قواعد محلية: فلترة دقيقة ومجانية. GPT: يعيد صياغة نفس الحقائق المؤكدة.",
                    "en": "Rule-based: exact local filtering, free. GPT: rephrases the same verified facts."},
    "tab_ask":     {"ar": "💬 اسأل", "en": "💬 Ask"},
    "tab_dash":    {"ar": "📊 لوحة", "en": "📊 Dashboard"},
    "tab_val":     {"ar": "✅ التحقق", "en": "✅ Validation"},
    "tab_about":   {"ar": "ℹ️ حول", "en": "ℹ️ About"},
    "examples":    {"ar": "أمثلة", "en": "Examples"},
    "ask_ph":      {"ar": "اكتب سؤالك", "en": "Ask a question"},
    "ask_hint":    {"ar": "مثال: هل الشحنة AWB-10024 تحتاج تصعيد؟", "en": "e.g. Does shipment AWB-10024 need escalation?"},
    "sources":     {"ar": "المصادر", "en": "Sources"},
    "raw":         {"ar": "المصادر المسترجعة (خام)", "en": "Retrieved context (raw)"},
    "not_found":   {"ar": "لم أجد هذه المعلومة في البيانات المتاحة. جرّب سؤالاً محدداً من الأمثلة أعلاه.",
                    "en": "I could not find this in the available data. Try one of the examples above."},
    "top_cases":   {"ar": "أعلى الحالات للمراجعة:", "en": "Top cases to review:"},
    "show_all":    {"ar": "عرض كل النتائج", "en": "Show all results"},
    "esc_reason":  {"ar": "سبب التصعيد", "en": "Escalation reason"},
    "ai_fail":     {"ar": "تعذّر الاتصال بالذكاء الاصطناعي — عرض الإجابة المحلية.", "en": "AI unavailable — showing the local answer."},
    "kpi_total":   {"ar": "إجمالي الشحنات", "en": "Total shipments"},
    "kpi_esc":     {"ar": "تحتاج تصعيد", "en": "Need escalation"},
    "kpi_missed":  {"ar": "فاتت الموعد", "en": "Missed deadline"},
    "kpi_cold":    {"ar": "تنبيه تبريد", "en": "Cold chain alert"},
    "kpi_sfda":    {"ar": "معلّقة SFDA", "en": "SFDA hold"},
    "dash_title":  {"ar": "لوحة التحليلات", "en": "Operations Dashboard"},
    "dash_sub":    {"ar": "نظرة إجمالية على الشحنات الطبية للموسم.", "en": "Season-wide overview of medical shipments."},
    "ch_status":   {"ar": "توزيع الحالات", "en": "Status distribution"},
    "ch_airport":  {"ar": "الشحنات حسب مطار الوجهة", "en": "Shipments by destination airport"},
    "ch_priority": {"ar": "توزيع الأولوية", "en": "Priority distribution"},
    "ch_deadline": {"ar": "حالة الموعد النهائي", "en": "Deadline status"},
    "ch_cargo":    {"ar": "أكثر أنواع البضائع الطبية", "en": "Top medical cargo types"},
    "show_table":  {"ar": "عرض جدول البيانات", "en": "Show data table"},
    "val_title":   {"ar": "التحقق الآلي", "en": "Automated Validation"},
    "val_sub":     {"ar": "كل إجابة تُقارن بالحقيقة المستخرجة من الـ metadata. الدقة يجب أن تكون 100%.",
                    "en": "Every answer is compared to the metadata ground truth. Accuracy must be 100%."},
    "val_score":   {"ar": "النتيجة", "en": "Score"},
    "val_note":    {"ar": "هذا التبويب مقابل تقييم RAGAS، لكنه يقيس الدقة المطلقة للفلترة التشغيلية.",
                    "en": "This tab is the equivalent of a RAGAS eval, but measures exact operational accuracy."},
}
def t(key, lang): return T[key][lang]

# Examples per language
EXAMPLES = {
    "ar": {
        "فحص شحنة": ["هل الشحنة AWB-10024 تحتاج تصعيد؟", "ما آخر تحديث للشحنة AWB-10024؟"],
        "المخاطر": ["ما الشحنات التي فاتت الموعد النهائي؟", "ما الشحنات التي عليها تنبيه سلسلة التبريد؟"],
        "الامتثال": ["ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟", "ما سياسة التصعيد؟"],
    },
    "en": {
        "Shipment": ["Does shipment AWB-10024 need escalation?", "What is the latest update for AWB-10024?"],
        "Risk": ["Which shipments missed the deadline?", "Which shipments have a cold chain alert?"],
        "Compliance": ["Which shipments are held at SFDA?", "What is the escalation policy?"],
    },
}

# ===========================================================================
# ENGINE  (answer language follows the chosen UI language via `ar`)
# ===========================================================================
def is_arabic(s): return bool(re.search(r"[\u0600-\u06FF]", s))
def cargo(c, ar): return c.get("cargo_type_ar" if ar else "cargo_type_en", c.get("medical_cargo_type", ""))

def build_indexes(chunks):
    ships    = [c for c in chunks if c["document_type"] == "shipment"]
    tracks   = {c["shipment_id"]: c for c in chunks if c["document_type"] == "tracking"}
    policies = {c["policy_rule"]: c for c in chunks if c["document_type"] == "policy"}
    by_awb   = {c["air_waybill_number"]: c for c in ships}
    return ships, tracks, policies, by_awb

def find_awb(text, by_awb, ships):
    m = re.search(r"(\d{4,6})", text)
    if not m: return None
    d = m.group(1)
    for awb, c in by_awb.items():
        if re.sub(r"\D", "", awb) == d or re.sub(r"\D", "", c["shipment_id"]) == d:
            return c
    return None

def recommend(c, ar):
    s = c["shipment_status"]
    if s == "SFDA Hold":
        return "متابعة التخليص النظامي عبر منصة فسح" if ar else "Follow up SFDA clearance via the Fasah platform"
    if s == "Cold Chain Alert":
        return "تصعيد لفريق الجودة وحجز الشحنة مؤقتاً للتقييم" if ar else "Escalate to quality; quarantine for assessment"
    if c["requires_escalation"]:
        return "تصعيد لفريق العمليات ومراجعة آخر تحديثات التتبع" if ar else "Escalate to operations; review latest tracking"
    return "لا يتطلب إجراءً عاجلاً" if ar else "No urgent action required"

def severity(c): return (c["requires_escalation"], c["delay_minutes"] or 0)

def get_result(question, chunks, ar):
    """ar = chosen UI language (controls answer language)."""
    ships, tracks, policies, by_awb = build_indexes(chunks)
    q = question.lower()
    c = find_awb(question, by_awb, ships)
    if c:
        tr = tracks.get(c["shipment_id"], {})
        raw = [c["content"], tr.get("content", "")]
        if any(k in q for k in ["آخر", "تحديث", "latest", "update", "وين", "where", "تتبع", "track"]) \
           and not any(k in q for k in ["تصعيد", "escalat"]):
            return {"kind": "latest", "ar": ar, "awb": c["air_waybill_number"],
                    "event": evt(tr.get("latest_event_type", ""), ar),
                    "location": ap(tr.get("latest_event_location", ""), ar),
                    "time": tr.get("latest_event_time", ""),
                    "sources": ["hajj_medical_tracking_events.csv"], "raw": raw}
        return {"kind": "detail", "ar": ar, "shipment": c, "track": tr,
                "recommendation": recommend(c, ar),
                "sources": ["hajj_medical_shipments.xlsx", "hajj_medical_tracking_events.csv"], "raw": raw}

    def lst(hits, title_ar, title_en, note_ar="", note_en=""):
        hits = sorted(hits, key=severity, reverse=True)
        return {"kind": "list", "ar": ar, "title": title_ar if ar else title_en,
                "count": len(hits), "items": hits, "note": note_ar if ar else note_en,
                "sources": ["hajj_medical_shipments.xlsx"], "raw": [h["content"] for h in hits[:8]]}

    if any(k in q for k in ["فات", "فوّت", "فوت", "الموعد النهائي", "missed", "deadline"]):
        return lst([x for x in ships if x["deadline_status"] == "MISSED Deadline"],
                   "الشحنات التي فاتت الموعد النهائي", "Shipments that missed the deadline")
    if "cold chain" in q or "سلسلة التبريد" in q or "تبريد" in q:
        return lst([x for x in ships if x["shipment_status"] == "Cold Chain Alert"],
                   "الشحنات التي عليها تنبيه سلسلة التبريد", "Shipments with a cold chain alert",
                   "حسب السياسة: تُصعَّد فوراً لفريق الجودة وتُحجز مؤقتاً للتقييم.",
                   "Per policy: escalate to quality, quarantine, and assess before delivery.")
    if "sfda" in q or "الغذاء والدواء" in q or "فسح" in q:
        return lst([x for x in ships if x["shipment_status"] == "SFDA Hold"],
                   "الشحنات المعلّقة لدى هيئة الغذاء والدواء", "Shipments held at SFDA",
                   "حسب السياسة: تواصل مع الشؤون التنظيمية وتابع عبر منصة فسح.",
                   "Per policy: contact regulatory affairs and track via the Fasah platform.")
    if ("حرج" in q and ("متأخر" in q or "تأخير" in q)) or "critical delay" in q:
        return lst([x for x in ships if x["shipment_status"] == "Critical Delay"],
                   "الشحنات ذات التأخير الحرج", "Critically delayed shipments")
    if "تصعيد" in q or "escalat" in q:
        return lst([x for x in ships if x["requires_escalation"]],
                   "الشحنات التي تحتاج تصعيد", "Shipments needing escalation")
    if any(k in q for k in ["سياسة", "policy", "قاعدة", "rule", "sla"]):
        rule = policies.get("escalation_rules")
        if "تأخير" in q or "delay" in q: rule = policies.get("delay_definition")
        if "تبريد" in q or "cold" in q:  rule = policies.get("cold_chain")
        parts = rule["content"].split("\n")
        return {"kind": "policy", "ar": ar, "text": parts[1] if (ar and len(parts) > 1) else parts[0],
                "sources": ["hajj_medical_sla_policy_ar_en.pdf"], "raw": [rule["content"]]}
    return {"kind": "none", "ar": ar}

def result_to_text(r):
    ar = r["ar"]
    if r["kind"] == "detail":
        c, tr = r["shipment"], r["track"]; d = c["delay_minutes"]
        if ar:
            L = [f"الشحنة {c['air_waybill_number']} — {cargo(c, True)}",
                 f"الحالة: {c['shipment_status_ar']}" + (f" (تأخير {d} دقيقة)" if d is not None else ""),
                 f"الوجهة: {fac(c['destination_facility'], True)}", f"الأولوية: {c['priority_level_ar']}"]
            L.append("القرار: نعم، تحتاج إلى تصعيد." if c["requires_escalation"] else "القرار: لا تحتاج تصعيد.")
            if c["requires_escalation"]: L.append("السبب: " + "، ".join(c["escalation_reasons_ar"]) + ".")
            L.append("التوصية: " + r["recommendation"])
        else:
            L = [f"Shipment {c['air_waybill_number']} — {cargo(c, False)}",
                 f"Status: {c['shipment_status']}" + (f" (delay {d} min)" if d is not None else ""),
                 f"Destination: {c['destination_facility']}", f"Priority: {c['priority_level']}"]
            L.append("Decision: Yes, escalation needed." if c["requires_escalation"] else "Decision: No escalation needed.")
            if c["requires_escalation"]: L.append("Reason: " + "; ".join(c["escalation_reasons"]) + ".")
            L.append("Recommendation: " + r["recommendation"])
        return "\n".join(L)
    if r["kind"] == "latest":
        if ar: return f"آخر تحديث للشحنة {r['awb']}: {r['event']} في {r['location']} بتاريخ {r['time']}."
        return f"Latest update for {r['awb']}: {r['event']} at {r['location']} on {r['time']}."
    if r["kind"] == "list":
        rows = [f"{h['air_waybill_number']} — {cargo(h, ar)} — {(h['shipment_status_ar'] if ar else h['shipment_status'])}" for h in r["items"]]
        return f"{r['title']}: {r['count']}\n" + "\n".join(rows) + (("\n" + r["note"]) if r["note"] else "")
    if r["kind"] == "policy": return r["text"]
    return ""

def llm_rephrase(question, facts_text, ar, api_key, model="gpt-4o-mini"):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    lang = "Arabic" if ar else "English"
    system = ("You are Rafd, an assistant for Hajj & Umrah medical cargo operations. You are given FACTS "
              "already verified from the data. Rewrite them into a clear, professional answer. Do NOT add, "
              "remove, or change any number, count, AWB code, airport code, status, or date. Do NOT invent "
              "anything. You RECOMMEND escalation; you never approve or reject. "
              f"Answer ONLY in {lang}. Keep identifiers (AWB-10024, file names) as-is.")
    user = f"Question: {question}\n\nVerified facts:\n{facts_text}\n\nRewrite as a clear answer."
    resp = client.chat.completions.create(model=model, temperature=0.3,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return resp.choices[0].message.content

# ===========================================================================
# PAGE + THEME
# ===========================================================================
st.set_page_config(page_title="Rafd — Medical Cargo Assistant", page_icon="🩺", layout="wide")

# language + theme are chosen in the sidebar; read early via session defaults
if "lang" not in st.session_state: st.session_state.lang = "ar"
if "dark" not in st.session_state: st.session_state.dark = False

with st.sidebar:
    lang_choice = st.radio("اللغة · Language", ["العربية", "English"],
                           index=0 if st.session_state.lang == "ar" else 1)
    st.session_state.lang = "ar" if lang_choice == "العربية" else "en"
    lang = st.session_state.lang
    dark = st.toggle("🌙 " + t("dark", lang) + " · " + t("theme", lang), value=st.session_state.dark)
    st.session_state.dark = dark

    st.divider()
    st.header(t("settings", lang))
    tier = st.radio(t("tier", lang), [t("tier_rule", lang), t("tier_ai", lang)],
                    index=0, help=t("tier_help", lang))
    use_ai = (tier == t("tier_ai", lang))
    api_key, model = "", "gpt-4o-mini"
    if use_ai:
        api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = st.text_input("OpenAI API Key", type="password")
        model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)

ar_ui = (lang == "ar")
# theme colors
if dark:
    BG, FG, CARD, BORDER, MUTED = "#0e1512", "#e8f0ee", "#14201c", "#274039", "#9db3ad"
else:
    BG, FG, CARD, BORDER, MUTED = "#ffffff", "#1c2b27", "#f2f8f6", "#cfe6df", "#5f5e5a"
ACCENT = "#12a37f" if dark else "#0f6e56"
dir_attr = "rtl" if ar_ui else "ltr"; align = "right" if ar_ui else "left"

st.markdown(f"""
<style>
.stApp {{ background:{BG}; color:{FG}; }}
[data-testid="stSidebar"] {{ background:{CARD}; }}
.block-container {{ direction:{dir_attr}; text-align:{align}; }}
.card {{ background:{CARD}; border:1px solid {BORDER};
    border-{'right' if ar_ui else 'left'}:4px solid {ACCENT};
    border-radius:10px; padding:14px 18px; margin-bottom:10px; line-height:1.7;
    direction:{dir_attr}; text-align:{align}; color:{FG}; }}
.awb {{ font-weight:700; color:{ACCENT}; }}
.esc {{ color:#e0533d; font-weight:600; }} .ok {{ color:{ACCENT}; font-weight:600; }}
.kpi {{ background:{ACCENT}; color:#fff; border-radius:12px; padding:14px 8px; text-align:center; }}
.kpi .n {{ font-size:1.7rem; font-weight:700; line-height:1; }}
.kpi .l {{ font-size:0.74rem; opacity:0.92; margin-top:5px; }}
.hdr {{ color:{ACCENT}; margin-bottom:0; }} .sub {{ color:{MUTED}; margin-top:2px; }}
div.stButton > button {{ border-radius:20px; border:1px solid {BORDER}; background:{CARD};
    color:{ACCENT}; font-size:0.85rem; }}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='hdr'>رفد · Rafd</h1>", unsafe_allow_html=True)
st.markdown(f"<p class='sub'>{t('title_sub', lang)}<br><span style='font-size:0.85rem'>{t('title_ctx', lang)}</span></p>",
            unsafe_allow_html=True)

if chunks is None:
    st.error("chunks.json not found next to app.py."); st.stop()

ships, tracks, policies, by_awb = build_indexes(chunks)
df = pd.DataFrame(ships)

tabs = st.tabs([t("tab_ask", lang), t("tab_dash", lang), t("tab_val", lang), t("tab_about", lang)])

# ---------- helper ----------
def render_card(h, ar, idx):
    esc = (f"<span class='esc'>{'يحتاج تصعيد' if ar else 'Needs escalation'}</span>"
           if h["requires_escalation"] else f"<span class='ok'>{'لا تصعيد' if ar else 'No escalation'}</span>")
    d = h["delay_minutes"]
    if ar:
        body = (f"<span class='awb'>{idx}. {h['air_waybill_number']}</span> — {cargo(h, True)}<br>"
                f"الحالة: {h['shipment_status_ar']}" + (f" (تأخير {d} دقيقة)" if d is not None else "") + "<br>"
                f"الوجهة: {fac(h['destination_facility'], True)} · الأولوية: {h['priority_level_ar']}<br>"
                f"{esc} · التوصية: {recommend(h, True)}")
    else:
        body = (f"<span class='awb'>{idx}. {h['air_waybill_number']}</span> — {cargo(h, False)}<br>"
                f"Status: {h['shipment_status']}" + (f" (delay {d} min)" if d is not None else "") + "<br>"
                f"Destination: {h['destination_facility']} · Priority: {h['priority_level']}<br>"
                f"{esc} · Recommendation: {recommend(h, False)}")
    st.markdown(f"<div class='card'>{body}</div>", unsafe_allow_html=True)

# ===================== TAB 1 — ASK =====================
with tabs[0]:
    kpis = [(t("kpi_total", lang), len(ships)),
            (t("kpi_esc", lang), sum(1 for c in ships if c["requires_escalation"])),
            (t("kpi_missed", lang), sum(1 for c in ships if c["deadline_status"] == "MISSED Deadline")),
            (t("kpi_cold", lang), sum(1 for c in ships if c["shipment_status"] == "Cold Chain Alert")),
            (t("kpi_sfda", lang), sum(1 for c in ships if c["shipment_status"] == "SFDA Hold"))]
    for col, (label, n) in zip(st.columns(len(kpis)), kpis):
        col.markdown(f"<div class='kpi'><div class='n'>{n}</div><div class='l'>{label}</div></div>", unsafe_allow_html=True)
    st.write("")

    st.caption(t("examples", lang))
    if "q" not in st.session_state: st.session_state.q = ""
    for gtitle, exs in EXAMPLES[lang].items():
        st.markdown(f"<span style='font-size:0.8rem;color:{MUTED}'>{gtitle}</span>", unsafe_allow_html=True)
        gc = st.columns(2)
        for i, ex in enumerate(exs):
            if gc[i].button(ex, key=f"{gtitle}{i}", use_container_width=True):
                st.session_state.q = ex

    question = st.text_input(t("ask_ph", lang), value=st.session_state.q, placeholder=t("ask_hint", lang))
    if question:
        r = get_result(question, chunks, ar_ui)
        used_local = True
        if use_ai and api_key and r["kind"] != "none":
            try:
                txt = llm_rephrase(question, result_to_text(r), ar_ui, api_key, model)
                st.markdown(f"<div class='card'>{txt}</div>", unsafe_allow_html=True); used_local = False
            except Exception as e:
                st.warning(t("ai_fail", lang) + f" ({str(e)[:50]})")
        if used_local:
            if r["kind"] == "detail":
                render_card(r["shipment"], ar_ui, "")
                if r["shipment"]["requires_escalation"]:
                    reasons = "، ".join(r["shipment"]["escalation_reasons_ar"]) if ar_ui else "; ".join(r["shipment"]["escalation_reasons"])
                    st.markdown(f"<div class='card'><b>{t('esc_reason', lang)}:</b> {reasons}</div>", unsafe_allow_html=True)
            elif r["kind"] == "latest":
                if ar_ui: body = f"<b>آخر تحديث للشحنة {r['awb']}</b><br>الحدث: {r['event']}<br>الموقع: {r['location']}<br>الوقت: {r['time']}"
                else:     body = f"<b>Latest update for {r['awb']}</b><br>Event: {r['event']}<br>Location: {r['location']}<br>Time: {r['time']}"
                st.markdown(f"<div class='card'>{body}</div>", unsafe_allow_html=True)
            elif r["kind"] == "list":
                st.markdown(f"<div class='card'><b>{r['title']}: {r['count']}</b></div>", unsafe_allow_html=True)
                st.markdown(f"<span style='font-size:0.8rem;color:{MUTED}'>{t('top_cases', lang)}</span>", unsafe_allow_html=True)
                for i, h in enumerate(r["items"][:5], 1): render_card(h, ar_ui, i)
                if r["count"] > 5:
                    with st.expander(t("show_all", lang) + f" ({r['count']})"):
                        for i, h in enumerate(r["items"], 1): render_card(h, ar_ui, i)
                if r["note"]: st.markdown(f"<div class='card'>{r['note']}</div>", unsafe_allow_html=True)
            elif r["kind"] == "policy":
                st.markdown(f"<div class='card'>{r['text']}</div>", unsafe_allow_html=True)
            else:
                st.info(t("not_found", lang))
        if r.get("sources") and r["kind"] != "none":
            st.markdown(f"**{t('sources', lang)}:** " + " · ".join(r["sources"]))
        if r.get("raw") and r["kind"] != "none":
            with st.expander(t("raw", lang)):
                st.text("\n\n".join(r["raw"]))

# ===================== TAB 2 — DASHBOARD =====================
with tabs[1]:
    st.subheader(t("dash_title", lang)); st.caption(t("dash_sub", lang))
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("**" + t("ch_status", lang) + "**"); st.bar_chart(df["shipment_status"].value_counts())
        st.markdown("**" + t("ch_airport", lang) + "**"); st.bar_chart(df["destination_airport"].value_counts())
    with c2:
        st.markdown("**" + t("ch_priority", lang) + "**"); st.bar_chart(df["priority_level"].value_counts())
        st.markdown("**" + t("ch_deadline", lang) + "**"); st.bar_chart(df["deadline_status"].value_counts())
    st.markdown("**" + t("ch_cargo", lang) + "**"); st.bar_chart(df["cargo_type_en"].value_counts())
    with st.expander(t("show_table", lang)):
        st.dataframe(df[["air_waybill_number", "cargo_type_en", "destination_airport", "destination_facility",
                         "priority_level", "shipment_status", "delay_minutes", "deadline_status", "requires_escalation"]],
                     use_container_width=True, height=320)

# ===================== TAB 3 — VALIDATION =====================
with tabs[2]:
    st.subheader(t("val_title", lang)); st.caption(t("val_sub", lang))
    truth = {"MISSED Deadline": sum(1 for c in ships if c["deadline_status"] == "MISSED Deadline"),
             "SFDA Hold": sum(1 for c in ships if c["shipment_status"] == "SFDA Hold"),
             "Cold Chain Alert": sum(1 for c in ships if c["shipment_status"] == "Cold Chain Alert"),
             "Critical Delay": sum(1 for c in ships if c["shipment_status"] == "Critical Delay"),
             "Requires escalation": sum(1 for c in ships if c["requires_escalation"])}
    qmap = {"MISSED Deadline": "ما الشحنات التي فاتت الموعد النهائي؟",
            "SFDA Hold": "ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟",
            "Cold Chain Alert": "ما الشحنات التي عليها تنبيه سلسلة التبريد؟",
            "Critical Delay": "ما الشحنات الحرجة المتأخرة؟",
            "Requires escalation": "ما الشحنات التي تحتاج تصعيد؟"}
    rows, passed = [], 0
    for key, expected in truth.items():
        got = get_result(qmap[key], chunks, True)["count"]; ok = (got == expected); passed += ok
        rows.append({"Check": key, "Expected": expected, "Answered": got, "Result": "✅ PASS" if ok else "❌ FAIL"})
    awb_r = get_result("هل الشحنة AWB-10024 تحتاج تصعيد؟", chunks, True)
    awb_ok = awb_r["kind"] == "detail" and awb_r["shipment"]["air_waybill_number"] == "AWB-10024"; passed += awb_ok
    rows.append({"Check": "AWB isolation", "Expected": "AWB-10024",
                 "Answered": awb_r.get("shipment", {}).get("air_waybill_number", "—"),
                 "Result": "✅ PASS" if awb_ok else "❌ FAIL"})
    total = len(rows)
    st.metric(t("val_score", lang), f"{passed}/{total} PASS")
    st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
    st.caption(t("val_note", lang))

# ===================== TAB 4 — ABOUT =====================
with tabs[3]:
    left, right = st.columns([2, 1])
    with left:
        st.subheader("حول رفد · About Rafd")
        if ar_ui:
            st.markdown("""**رفد** مساعد رؤية وتصعيد للشحنات الطبية في موسم الحج والعمرة. يجمع بيانات الشحنات،
وسجلات التتبع، وقواعد اتفاقية مستوى الخدمة (SLA) لتحديد الشحنات المتأخرة، والتي فاتت الموعد النهائي،
وتنبيهات سلسلة التبريد، وحالات التعليق لدى هيئة الغذاء والدواء، واحتياجات التصعيد.

**لماذا الفلترة على metadata بدل vector search؟** البيانات هنا تشغيلية جدولية، والأسئلة مثل «فاتت
الموعد» تحتاج فلاتر دقيقة لا تشابهاً دلالياً. لذلك اخترنا *metadata-aware retrieval* — أدق وأصفر هلوسة.

**الذكاء المسؤول:** بيانات اصطناعية فقط · المصادر مع كل إجابة · يقول «لم أجد» عند غياب المعلومة ·
توصية فقط والقرار لفريق العمليات (human-in-the-loop).

**التوافق مع رؤية 2030:** خدمة ضيوف الرحمن · الاستراتيجية الوطنية للنقل واللوجستيات · الصحة الرقمية والبيانات والذكاء الاصطناعي.""")
        else:
            st.markdown("""**Rafd** is a metadata-aware RAG assistant for Hajj & Umrah medical cargo operations.
It combines shipment metadata, tracking timelines, and SLA policy rules to identify missed deadlines,
cold-chain alerts, SFDA holds, and escalation needs.

**Why metadata-aware (not vector search)?** The data is structured & operational; questions like
"missed the deadline" need exact filters, not semantic similarity. A deliberate accuracy-first choice.

**Responsible AI:** synthetic data only · sources with every answer · says "not found" when data is
missing · recommends escalation, never decides (human-in-the-loop).

**Vision 2030 alignment:** serving the Guests of God · National Transport & Logistics Strategy ·
digital health, data & AI.""")
        st.code("""User question
   -> metadata filter over chunks.json  (exact, no hallucination)
   -> verified facts + SLA rule + latest tracking event
   -> [Rule-based answer] OR [GPT rephrases verified facts]
   -> same-language answer + recommendation + sources""", language="text")
    with right:
        st.markdown("### Tech Stack")
        st.markdown("- **Retrieval:** Metadata-aware filtering\n- **Data:** chunks.json\n- **LLM (optional):** OpenAI GPT-4o-mini\n- **Frontend:** Streamlit\n- **Bilingual:** Arabic / English (RTL)")
        st.markdown("### Knowledge Base")
        a, b = st.columns(2)
        a.metric("Shipments", len(ships)); b.metric("Chunks", len(chunks))
        a.metric("Tracking", len(tracks)); b.metric("Policy rules", len(policies))
        st.caption("جميع البيانات اصطناعية لأغراض العرض فقط · All data is synthetic (demo only).")
