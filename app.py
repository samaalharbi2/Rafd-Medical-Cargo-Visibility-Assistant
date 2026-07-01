"""
Rafd / رفد — Medical Cargo Visibility & Escalation Assistant
For Hajj & Umrah medical logistics operations.

Facts come from LOCAL metadata filtering (always accurate). An optional OpenAI
layer only rephrases the verified facts. Answers are clean & single-language:
Arabic question -> Arabic answer (statuses, priority, destinations translated);
identifiers (AWB, file names) stay as-is.
"""
import os, json, re
import streamlit as st
from translations import ap, fac, evt

# ---------------------------------------------------------------------------
# Load chunks.json
# ---------------------------------------------------------------------------
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
# LANGUAGE + INDEXES
# ===========================================================================
def is_arabic(t): return bool(re.search(r"[\u0600-\u06FF]", t))
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
    """Operational recommendation based on the shipment status (advisory only)."""
    s = c["shipment_status"]
    if s == "SFDA Hold":
        return "متابعة التخليص النظامي عبر منصة فسح" if ar else "Follow up SFDA clearance via the Fasah platform"
    if s == "Cold Chain Alert":
        return "تصعيد لفريق الجودة وحجز الشحنة مؤقتًا للتقييم" if ar else "Escalate to quality; quarantine for assessment"
    if c["requires_escalation"]:
        return "تصعيد لفريق العمليات ومراجعة آخر تحديثات التتبع" if ar else "Escalate to operations; review latest tracking"
    return "لا يتطلب إجراءً عاجلاً" if ar else "No urgent action required"

def severity(c):
    """Sort key: escalation first, then longer delay."""
    return (c["requires_escalation"], c["delay_minutes"] or 0)

# ===========================================================================
# FACT ENGINE -> returns a STRUCTURED result (rendered as cards by the UI)
# ===========================================================================
def get_result(question, chunks):
    ships, tracks, policies, by_awb = build_indexes(chunks)
    ar = is_arabic(question)
    q  = question.lower()
    c  = find_awb(question, by_awb, ships)

    # ---- specific shipment ----
    if c:
        t = tracks.get(c["shipment_id"], {})
        raw = [c["content"], t.get("content", "")]
        # latest update intent
        if any(k in q for k in ["آخر", "تحديث", "latest", "update", "وين", "where", "تتبع", "track"]) \
           and not any(k in q for k in ["تصعيد", "escalat"]):
            return {"kind": "latest", "ar": ar, "awb": c["air_waybill_number"],
                    "event": evt(t.get("latest_event_type", ""), ar),
                    "location": ap(t.get("latest_event_location", ""), ar),
                    "time": t.get("latest_event_time", ""),
                    "desc": t.get("latest_event_description", ""),
                    "sources": ["hajj_medical_tracking_events.csv"], "raw": raw}
        return {"kind": "detail", "ar": ar, "shipment": c, "track": t,
                "recommendation": recommend(c, ar),
                "sources": ["hajj_medical_shipments.xlsx", "hajj_medical_tracking_events.csv"],
                "raw": raw}

    # ---- list filters ----
    def lst(hits, title_ar, title_en, note_ar="", note_en=""):
        hits = sorted(hits, key=severity, reverse=True)
        return {"kind": "list", "ar": ar, "title": title_ar if ar else title_en,
                "count": len(hits), "items": hits, "note": note_ar if ar else note_en,
                "sources": ["hajj_medical_shipments.xlsx"],
                "raw": [h["content"] for h in hits[:8]]}

    if any(k in q for k in ["فات", "فوّت", "فوت", "الموعد النهائي", "missed", "deadline"]):
        return lst([x for x in ships if x["deadline_status"] == "MISSED Deadline"],
                   "الشحنات التي فاتت الموعد النهائي", "Shipments that missed the deadline")
    if "cold chain" in q or "سلسلة التبريد" in q or "تبريد" in q:
        return lst([x for x in ships if x["shipment_status"] == "Cold Chain Alert"],
                   "الشحنات التي عليها تنبيه سلسلة التبريد", "Shipments with a cold chain alert",
                   "حسب السياسة: تُصعَّد فورًا لفريق الجودة وتُحجز مؤقتًا للتقييم.",
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

    # ---- policy ----
    if any(k in q for k in ["سياسة", "policy", "قاعدة", "rule", "sla"]):
        rule = policies.get("escalation_rules")
        if "تأخير" in q or "delay" in q: rule = policies.get("delay_definition")
        if "تبريد" in q or "cold" in q:  rule = policies.get("cold_chain")
        parts = rule["content"].split("\n")
        return {"kind": "policy", "ar": ar,
                "text": parts[1] if (ar and len(parts) > 1) else parts[0],
                "sources": ["hajj_medical_sla_policy_ar_en.pdf"], "raw": [rule["content"]]}

    return {"kind": "none", "ar": ar}

# ===========================================================================
# RENDER FACTS AS PLAIN TEXT (for the LLM layer and as a fallback)
# ===========================================================================
def result_to_text(r):
    ar = r["ar"]
    if r["kind"] == "detail":
        c, t = r["shipment"], r["track"]
        d = c["delay_minutes"]
        if ar:
            L = [f"الشحنة {c['air_waybill_number']} — {cargo(c, True)}",
                 f"النوع: {cargo(c, True)}",
                 f"الحالة: {c['shipment_status_ar']}" + (f" (تأخير {d} دقيقة)" if d is not None else ""),
                 f"الوجهة: {fac(c['destination_facility'], True)}",
                 f"الأولوية: {c['priority_level_ar']}",
                 f"آخر حدث: {evt(t.get('latest_event_type',''), True)} في {ap(t.get('latest_event_location',''), True)}"]
            L.append("القرار: نعم، تحتاج إلى تصعيد." if c["requires_escalation"] else "القرار: لا تحتاج تصعيد حسب سياسة SLA.")
            if c["requires_escalation"]:
                L.append("السبب: " + "، ".join(c["escalation_reasons_ar"]) + ".")
            L.append("التوصية: " + r["recommendation"])
        else:
            L = [f"Shipment {c['air_waybill_number']} — {cargo(c, False)}",
                 f"Status: {c['shipment_status']}" + (f" (delay {d} min)" if d is not None else ""),
                 f"Destination: {c['destination_facility']}",
                 f"Priority: {c['priority_level']}",
                 f"Latest event: {t.get('latest_event_type','')} at {t.get('latest_event_location','')}"]
            L.append("Decision: Yes, escalation needed." if c["requires_escalation"] else "Decision: No escalation needed per SLA.")
            if c["requires_escalation"]:
                L.append("Reason: " + "; ".join(c["escalation_reasons"]) + ".")
            L.append("Recommendation: " + r["recommendation"])
        return "\n".join(L)
    if r["kind"] == "latest":
        if ar:
            return (f"آخر تحديث للشحنة {r['awb']}: {r['event']} في {r['location']} "
                    f"بتاريخ {r['time']}.")
        return (f"Latest update for {r['awb']}: {r['event']} at {r['location']} "
                f"on {r['time']}.")
    if r["kind"] == "list":
        rows = [f"{h['air_waybill_number']} — {cargo(h, ar)} — "
                f"{(h['shipment_status_ar'] if ar else h['shipment_status'])}" for h in r["items"]]
        return f"{r['title']}: {r['count']}\n" + "\n".join(rows) + (("\n" + r["note"]) if r["note"] else "")
    if r["kind"] == "policy":
        return r["text"]
    return "لم أجد هذه المعلومة في البيانات المتاحة." if ar else "I could not find this in the available data."

# ===========================================================================
# OPTIONAL OpenAI LAYER (rephrases verified facts only)
# ===========================================================================
def llm_rephrase(question, facts_text, api_key, model="gpt-4o-mini"):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    lang = "Arabic" if is_arabic(question) else "English"
    system = ("You are Rafd, an assistant for Hajj & Umrah medical cargo operations. "
              "You are given FACTS already verified from the data. Rewrite them into a clear, "
              "professional answer. Do NOT add, remove, or change any number, count, AWB code, "
              "airport code, status, or date. Do NOT invent anything. You RECOMMEND escalation, "
              "you never approve or reject. "
              f"Answer ONLY in {lang}. Keep identifiers (AWB-10024, file names) as-is.")
    user = f"Question: {question}\n\nVerified facts:\n{facts_text}\n\nRewrite as a clear answer."
    resp = client.chat.completions.create(model=model, temperature=0.3,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return resp.choices[0].message.content

# ===========================================================================
# UI
# ===========================================================================
st.set_page_config(page_title="Rafd — Medical Cargo Assistant", page_icon="🩺", layout="centered")
st.markdown("""
<style>
.main .block-container {max-width: 860px; padding-top: 1.5rem;}
.rtl {direction: rtl; text-align: right;}
.hdr {color:#0f6e56; margin-bottom:0;}
.sub {color:#5f5e5a; font-size:0.95rem; margin-top:2px;}
.card {background:#f6faf9; border:1px solid #cfe6df; border-left:4px solid #0f6e56;
    border-radius:10px; padding:14px 18px; margin-bottom:10px; line-height:1.7;}
.card.rtl {border-left:none; border-right:4px solid #0f6e56;}
.awb {font-weight:700; color:#0f6e56;}
.esc {color:#b3261e; font-weight:600;}
.ok {color:#0f6e56; font-weight:600;}
.kpi {background:#0f6e56; color:#fff; border-radius:12px; padding:12px 8px; text-align:center;}
.kpi .n {font-size:1.6rem; font-weight:700; line-height:1;}
.kpi .l {font-size:0.72rem; opacity:0.9; margin-top:4px;}
div.stButton > button {border-radius:20px; border:1px solid #cfe6df; background:#f6faf9;
    color:#0f6e56; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='hdr'>رفد · Rafd</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub'>مساعد رؤية وتصعيد الشحنات الطبية · Medical Cargo Visibility &amp; Escalation Assistant"
            "<br><span style='font-size:0.85rem'>لعمليات لوجستيات الحج والعمرة الطبية · For Hajj &amp; Umrah medical logistics</span></p>",
            unsafe_allow_html=True)

with st.sidebar:
    st.header("الإعدادات · Settings")
    use_ai = st.toggle("صياغة أذكى بالذكاء الاصطناعي · AI phrasing", value=False)
    api_key, model = "", "gpt-4o-mini"
    if use_ai:
        api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = st.text_input("OpenAI API Key", type="password")
        model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    st.caption("بدون مفتاح، المساعد يعمل بالكامل بالفلترة المحلية (مجاني ودقيق).")
    st.divider()
    st.caption("توصيات فقط — القرار النهائي لفريق العمليات (human-in-the-loop).")
    st.caption("جميع البيانات اصطناعية لأغراض العرض · All data is synthetic (demo only).")

if chunks is None:
    st.error("chunks.json غير موجود. ضعي الملف بجانب app.py.")
    st.stop()

ships, tracks, policies, by_awb = build_indexes(chunks)

# ---- KPI cards ----
kpis = [
    ("إجمالي الشحنات", len(ships)),
    ("تحتاج تصعيد", sum(1 for c in ships if c["requires_escalation"])),
    ("فاتت الموعد", sum(1 for c in ships if c["deadline_status"] == "MISSED Deadline")),
    ("تنبيه تبريد", sum(1 for c in ships if c["shipment_status"] == "Cold Chain Alert")),
    ("معلّقة SFDA", sum(1 for c in ships if c["shipment_status"] == "SFDA Hold")),
]
cols = st.columns(len(kpis))
for col, (label, n) in zip(cols, kpis):
    col.markdown(f"<div class='kpi'><div class='n'>{n}</div><div class='l'>{label}</div></div>",
                 unsafe_allow_html=True)
st.write("")

# ---- examples grouped ----
st.caption("أمثلة · Examples")
groups = {
    "فحص شحنة · Shipment": ["هل الشحنة AWB-10024 تحتاج تصعيد؟", "ما آخر تحديث للشحنة AWB-10024؟"],
    "المخاطر · Risk": ["ما الشحنات التي فاتت الموعد النهائي؟", "ما الشحنات التي عليها تنبيه سلسلة التبريد؟"],
    "الامتثال · Compliance": ["ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟", "ما سياسة التصعيد؟"],
}
if "q" not in st.session_state: st.session_state.q = ""
for gtitle, exs in groups.items():
    st.markdown(f"<span style='font-size:0.8rem;color:#5f5e5a'>{gtitle}</span>", unsafe_allow_html=True)
    gc = st.columns(2)
    for i, ex in enumerate(exs):
        if gc[i].button(ex, key=f"{gtitle}{i}", use_container_width=True):
            st.session_state.q = ex

question = st.text_input("اكتب سؤالك · Ask a question", value=st.session_state.q,
                         placeholder="مثال: هل الشحنة AWB-10024 تحتاج تصعيد؟")

# ---- render helpers ----
def render_card(h, ar, idx):
    rtl = "rtl" if ar else ""
    esc = ("<span class='esc'>يحتاج تصعيد</span>" if ar else "<span class='esc'>Needs escalation</span>") \
          if h["requires_escalation"] else ("<span class='ok'>لا تصعيد</span>" if ar else "<span class='ok'>No escalation</span>")
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
    st.markdown(f"<div class='card {rtl}'>{body}</div>", unsafe_allow_html=True)

if question:
    r = get_result(question, chunks)
    ar = r["ar"]; rtl = "rtl" if ar else ""

    # AI phrasing path (rephrases the plain-text facts)
    if use_ai and api_key and r["kind"] != "none":
        try:
            txt = llm_rephrase(question, result_to_text(r), api_key, model)
            st.markdown(f"<div class='card {rtl}'>{txt}</div>", unsafe_allow_html=True)
        except Exception as e:
            st.warning(f"تعذّر الذكاء الاصطناعي، سيتم عرض الإجابة المحلية. ({str(e)[:70]})")
            r_use_local = True
        else:
            r_use_local = False
    else:
        r_use_local = True

    if r_use_local:
        if r["kind"] == "detail":
            render_card(r["shipment"], ar, "")
            if r["shipment"]["requires_escalation"]:
                reasons = "، ".join(r["shipment"]["escalation_reasons_ar"]) if ar else "; ".join(r["shipment"]["escalation_reasons"])
                lbl = "سبب التصعيد" if ar else "Escalation reason"
                st.markdown(f"<div class='card {rtl}'><b>{lbl}:</b> {reasons}</div>", unsafe_allow_html=True)
        elif r["kind"] == "latest":
            if ar:
                body = (f"<b>آخر تحديث للشحنة {r['awb']}</b><br>الحدث: {r['event']}<br>"
                        f"الموقع: {r['location']}<br>الوقت: {r['time']}")
            else:
                body = (f"<b>Latest update for {r['awb']}</b><br>Event: {r['event']}<br>"
                        f"Location: {r['location']}<br>Time: {r['time']}")
            st.markdown(f"<div class='card {rtl}'>{body}</div>", unsafe_allow_html=True)
        elif r["kind"] == "list":
            title = f"{r['title']}: {r['count']}"
            st.markdown(f"<div class='card {rtl}'><b>{title}</b></div>", unsafe_allow_html=True)
            top = r["items"][:5]
            sub = ("أعلى الحالات للمراجعة:" if ar else "Top cases to review:")
            st.markdown(f"<span style='font-size:0.8rem;color:#5f5e5a'>{sub}</span>", unsafe_allow_html=True)
            for i, h in enumerate(top, 1):
                render_card(h, ar, i)
            if r["count"] > 5:
                with st.expander(("عرض كل النتائج" if ar else "Show all results") + f" ({r['count']})"):
                    for i, h in enumerate(r["items"], 1):
                        render_card(h, ar, i)
            if r["note"]:
                st.markdown(f"<div class='card {rtl}'>{r['note']}</div>", unsafe_allow_html=True)
        elif r["kind"] == "policy":
            st.markdown(f"<div class='card {rtl}'>{r['text']}</div>", unsafe_allow_html=True)
        else:
            msg = ("لم أجد هذه المعلومة في البيانات المتاحة. جرّب سؤالاً محددًا."
                   if ar else "I could not find this in the available data. Try a specific question.")
            st.info(msg)

    if r.get("sources"):
        label = "المصادر" if ar else "Sources"
        st.markdown(f"**{label}:** " + " · ".join(r["sources"]))
    if r.get("raw"):
        with st.expander("المصادر المسترجعة (raw context)"):
            st.text("\n\n".join(r["raw"]))
