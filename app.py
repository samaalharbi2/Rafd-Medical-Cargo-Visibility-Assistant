"""
Nazir / Sanad — Hajj & Umrah Medical Cargo Visibility Assistant
Streamlit app. Facts are found by LOCAL metadata filtering (always accurate).
An optional OpenAI layer only REPHRASES those verified facts (never invents numbers).
"""
import os, json, re
import streamlit as st

# ---------------------------------------------------------------------------
# Load chunks.json (must sit next to this file in the repo)
# ---------------------------------------------------------------------------
@st.cache_data
def load_chunks():
    here = os.path.dirname(os.path.abspath(__file__))
    for p in [os.path.join(here, "chunks.json"),
              os.path.join(here, "data", "chunks.json"),
              "chunks.json", "data/chunks.json"]:
        if os.path.exists(p):
            return json.load(open(p, encoding="utf-8"))
    return None

chunks = load_chunks()

# ===========================================================================
# PART 1 — LOCAL FACT ENGINE (metadata filters, always accurate, no API)
# ===========================================================================
def build_indexes(chunks):
    ships    = [c for c in chunks if c["document_type"] == "shipment"]
    tracks   = {c["shipment_id"]: c for c in chunks if c["document_type"] == "tracking"}
    policies = {c["policy_rule"]: c for c in chunks if c["document_type"] == "policy"}
    by_awb   = {c["air_waybill_number"]: c for c in ships}
    return ships, tracks, policies, by_awb

def is_arabic(t):
    return bool(re.search(r"[\u0600-\u06FF]", t))

def cargo(c, ar):
    return c.get("cargo_type_ar" if ar else "cargo_type_en", c.get("medical_cargo_type", ""))

def find_awb(text, by_awb, ships):
    m = re.search(r"(\d{4,6})", text)
    if not m:
        return None
    digits = m.group(1)
    for awb, c in by_awb.items():
        if re.sub(r"\D", "", awb) == digits or re.sub(r"\D", "", c["shipment_id"]) == digits:
            return c
    return None

SRC_LINES = "- hajj_medical_shipments.xlsx\n- hajj_medical_tracking_events.csv"

def get_facts(question, chunks):
    """Return (answer_text, source_files, raw_context) using local filters only."""
    ships, tracks, policies, by_awb = build_indexes(chunks)
    ar = is_arabic(question)
    q  = question.lower()
    c  = find_awb(question, by_awb, ships)
    raw = []

    # 1) Specific shipment
    if c:
        t = tracks.get(c["shipment_id"], {})
        raw = [c["content"], t.get("content", "")]
        if any(k in q for k in ["آخر", "تحديث", "latest", "update", "وين", "where", "تتبع", "track"]) \
           and not any(k in q for k in ["تصعيد", "escalat"]):
            if ar:
                txt = (f"آخر تحديث للشحنة {c['air_waybill_number']}:\n"
                       f"- الحدث: {t.get('latest_event_type','')}\n"
                       f"- الموقع: {t.get('latest_event_location','')}\n"
                       f"- الوقت: {t.get('latest_event_time','')}\n"
                       f"- الوصف: {t.get('latest_event_description','')}")
            else:
                txt = (f"Latest update for shipment {c['air_waybill_number']}:\n"
                       f"- Event: {t.get('latest_event_type','')}\n"
                       f"- Location: {t.get('latest_event_location','')}\n"
                       f"- Time: {t.get('latest_event_time','')}\n"
                       f"- Description: {t.get('latest_event_description','')}")
            return txt, ["hajj_medical_tracking_events.csv"], raw
        if ar:
            lines = [
                f"الشحنة {c['air_waybill_number']} — {cargo(c, True)}",
                f"- الوجهة: {c['destination_facility']}",
                f"- الأولوية: {c['priority_level_ar']}",
                f"- الحالة: {c['shipment_status_ar']}"
                + (f" (تأخير {c['delay_minutes']} دقيقة)" if c['delay_minutes'] is not None else ""),
                f"- حالة الموعد النهائي: {c['deadline_status_ar']}",
                f"- آخر حدث: {t.get('latest_event_type','')} في {t.get('latest_event_location','')}",
            ]
            if c["requires_escalation"]:
                lines += [f"\nالقرار: نعم، الشحنة {c['air_waybill_number']} تحتاج إلى تصعيد.",
                          "السبب: " + "، ".join(c["escalation_reasons_ar"]) + ".",
                          "التوصية: تصعيد الحالة لفريق العمليات ومراجعة آخر تحديثات التتبع."]
            else:
                lines.append(f"\nالقرار: لا، الشحنة {c['air_waybill_number']} لا تحتاج تصعيد حسب سياسة SLA.")
        else:
            lines = [
                f"Shipment {c['air_waybill_number']} — {cargo(c, False)}",
                f"- Destination: {c['destination_facility']}",
                f"- Priority: {c['priority_level']}",
                f"- Status: {c['shipment_status']}"
                + (f" (delay {c['delay_minutes']} min)" if c['delay_minutes'] is not None else ""),
                f"- Deadline status: {c['deadline_status']}",
                f"- Latest event: {t.get('latest_event_type','')} at {t.get('latest_event_location','')}",
            ]
            if c["requires_escalation"]:
                lines += [f"\nDecision: Yes, shipment {c['air_waybill_number']} needs escalation.",
                          "Reason: " + "; ".join(c["escalation_reasons"]) + ".",
                          "Recommendation: escalate to the operations team and review the latest tracking updates."]
            else:
                lines.append(f"\nDecision: No, shipment {c['air_waybill_number']} does not need escalation per SLA policy.")
        return "\n".join(lines), ["hajj_medical_shipments.xlsx", "hajj_medical_tracking_events.csv"], raw

    # 2) list filters
    def make_list(hits, title_ar, title_en, note_ar="", note_en=""):
        raw_local = [h["content"] for h in hits[:8]]
        if ar:
            rows = [f"{i}. {h['air_waybill_number']} — {cargo(h, True)} — "
                    f"{h['shipment_status_ar']} — {h['destination_facility']}"
                    for i, h in enumerate(hits, 1)]
            body = f"{title_ar}: {len(hits)}\n" + "\n".join(rows) + (("\n\n" + note_ar) if note_ar else "")
        else:
            rows = [f"{i}. {h['air_waybill_number']} — {cargo(h, False)} — "
                    f"{h['shipment_status']} — {h['destination_facility']}"
                    for i, h in enumerate(hits, 1)]
            body = f"{title_en}: {len(hits)}\n" + "\n".join(rows) + (("\n\n" + note_en) if note_en else "")
        return body, ["hajj_medical_shipments.xlsx"], raw_local

    if any(k in q for k in ["فات", "فوّت", "فوت", "الموعد النهائي", "missed", "deadline"]):
        hits = [x for x in ships if x["deadline_status"] == "MISSED Deadline"]
        return make_list(hits, "الشحنات التي فاتت الموعد النهائي", "Shipments that missed the deadline")

    if "cold chain" in q or "سلسلة التبريد" in q or "تبريد" in q:
        hits = [x for x in ships if x["shipment_status"] == "Cold Chain Alert"]
        return make_list(hits, "الشحنات التي عليها تنبيه سلسلة التبريد", "Shipments with a cold chain alert",
                         "حسب السياسة: تُصعَّد فورًا لفريق الجودة وتُحجز مؤقتًا للتقييم.",
                         "Per policy: escalate to quality, quarantine, and assess before delivery.")

    if "sfda" in q or "الغذاء والدواء" in q or "فسح" in q:
        hits = [x for x in ships if x["shipment_status"] == "SFDA Hold"]
        return make_list(hits, "الشحنات المعلّقة لدى هيئة الغذاء والدواء", "Shipments held at SFDA",
                         "حسب السياسة: تواصل مع الشؤون التنظيمية وتابع عبر منصة فسح.",
                         "Per policy: contact regulatory affairs and track via the Fasah platform.")

    if ("حرج" in q and ("متأخر" in q or "تأخير" in q)) or "critical delay" in q:
        hits = [x for x in ships if x["shipment_status"] == "Critical Delay"]
        return make_list(hits, "الشحنات ذات التأخير الحرج", "Critically delayed shipments")

    if "تصعيد" in q or "escalat" in q:
        hits = [x for x in ships if x["requires_escalation"]]
        total = len(hits)
        body, src, raw = make_list(hits[:20],
            f"الشحنات التي تحتاج تصعيد (إجمالي {total}، أول 20)",
            f"Shipments needing escalation (total {total}, first 20)")
        return body, src, raw

    if any(k in q for k in ["سياسة", "policy", "قاعدة", "rule", "sla"]):
        rule = policies.get("escalation_rules")
        if "تأخير" in q or "delay" in q: rule = policies.get("delay_definition")
        if "تبريد" in q or "cold" in q:  rule = policies.get("cold_chain")
        parts = rule["content"].split("\n")
        chosen = parts[1] if (ar and len(parts) > 1) else parts[0]
        label = "حسب السياسة" if ar else "Per the SLA policy"
        return f"{label}:\n{chosen}", ["hajj_medical_sla_policy_ar_en.pdf"], [rule["content"]]

    # not understood
    if ar:
        return ("لم أجد هذه المعلومة في البيانات المتاحة. جرّب سؤالاً محددًا مثل: "
                "هل الشحنة AWB-10024 تحتاج تصعيد؟", [], [])
    return ("I could not find this in the available data. Try a specific question like: "
            "Does shipment AWB-10024 need escalation?", [], [])

# ===========================================================================
# PART 2 — OPTIONAL OpenAI LAYER (only rephrases the verified facts)
# ===========================================================================
def llm_rephrase(question, facts, api_key, model="gpt-4o-mini"):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    ar = is_arabic(question)
    lang = "Arabic" if ar else "English"
    system = (
        "You are Sanad, an assistant for Hajj & Umrah medical cargo operations. "
        "You are given FACTS that were already verified from the data. "
        "Rewrite them into a clear, natural, professional answer. "
        "CRITICAL RULES: do NOT add, remove, or change any number, count, AWB code, "
        "airport code, status, or date. Do NOT invent information. "
        f"Answer ONLY in {lang}. Keep identifiers (AWB-10024, JED, file names) as-is. "
        "Be concise and operational.")
    user = f"Question: {question}\n\nVerified facts:\n{facts}\n\nRewrite as a clear answer."
    resp = client.chat.completions.create(
        model=model, temperature=0.3,
        messages=[{"role": "system", "content": system},
                  {"role": "user", "content": user}])
    return resp.choices[0].message.content

# ===========================================================================
# PART 3 — STREAMLIT UI
# ===========================================================================
st.set_page_config(page_title="Nazir — Medical Cargo Assistant",
                   page_icon="🩺", layout="centered")

st.markdown("""
<style>
.main .block-container {max-width: 820px; padding-top: 2rem;}
.rtl {direction: rtl; text-align: right;}
.answer-card {background: #f6faf9; border: 1px solid #cfe6df;
    border-left: 4px solid #0f6e56; border-radius: 10px; padding: 18px 20px;
    white-space: pre-wrap; font-size: 1.02rem; line-height: 1.7;}
.hdr {color:#0f6e56;}
.sub {color:#5f5e5a; font-size:0.95rem;}
div.stButton > button {border-radius: 20px; border:1px solid #cfe6df;
    background:#f6faf9; color:#0f6e56; font-size:0.85rem;}
</style>
""", unsafe_allow_html=True)

st.markdown("<h1 class='hdr'>ناظر · Nazir</h1>", unsafe_allow_html=True)
st.markdown("<p class='sub'>مساعد رؤية الشحنات الطبية لموسم الحج والعمرة · "
            "Hajj &amp; Umrah Medical Cargo Visibility Assistant</p>", unsafe_allow_html=True)

# --- Sidebar: optional AI phrasing ---
with st.sidebar:
    st.header("الإعدادات · Settings")
    use_ai = st.toggle("صياغة أذكى بالذكاء الاصطناعي · AI phrasing", value=False,
                       help="يستخدم OpenAI لصياغة نفس الحقائق بشكل أطبع. الأرقام تبقى من البيانات.")
    api_key = ""
    if use_ai:
        api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
        if not api_key:
            api_key = st.text_input("OpenAI API Key", type="password",
                                    help="sk-... — لا يُحفظ، يُستخدم في هذه الجلسة فقط.")
        model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0)
    st.caption("بدون مفتاح، المساعد يعمل بالكامل بالفلترة المحلية (مجاني ودقيق).")
    st.divider()
    st.caption("جميع البيانات اصطناعية لأغراض العرض فقط · All data is synthetic (demo only).")

if chunks is None:
    st.error("chunks.json غير موجود. ضعي الملف بجانب app.py في المستودع.")
    st.stop()

# --- Example questions ---
st.write("أمثلة · Examples:")
examples = [
    "هل الشحنة AWB-10024 تحتاج تصعيد؟",
    "ما الشحنات التي فاتت الموعد النهائي؟",
    "ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟",
    "Which shipments have a cold chain alert?",
]
cols = st.columns(2)
if "q" not in st.session_state:
    st.session_state.q = ""
for i, ex in enumerate(examples):
    if cols[i % 2].button(ex, key=f"ex{i}", use_container_width=True):
        st.session_state.q = ex

# --- Question input ---
question = st.text_input("اكتب سؤالك · Ask a question",
                         value=st.session_state.q,
                         placeholder="مثال: هل الشحنة AWB-10024 تحتاج تصعيد؟")

if question:
    facts, sources, raw = get_facts(question, chunks)

    # optional AI rephrasing of the verified facts
    display = facts
    if use_ai and api_key:
        try:
            display = llm_rephrase(question, facts, api_key, model)
        except Exception as e:
            st.warning(f"تعذّر استخدام الذكاء الاصطناعي، سيتم عرض الإجابة المحلية. ({str(e)[:80]})")

    rtl = "rtl" if is_arabic(question) else ""
    st.markdown(f"<div class='answer-card {rtl}'>{display}</div>", unsafe_allow_html=True)

    if sources:
        label = "المصادر" if is_arabic(question) else "Sources"
        st.markdown(f"**{label}:** " + " · ".join(sources))

    with st.expander("المصادر المسترجعة (raw context)"):
        st.text("\n\n".join(raw) if raw else "—")
