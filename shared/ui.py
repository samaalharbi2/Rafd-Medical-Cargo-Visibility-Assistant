"""Shared UI renderer. Each language page calls render_page('ar') or render_page('en').
Enterprise palette: navy #0B1F33 · teal #0E7C7B · gold #C9A227 · bg #F7F9FA."""
import streamlit as st
import pandas as pd
from shared.data_loader import load_chunks, build_indexes, ships_df
from shared import rules_engine as eng
from shared import chat_memory as mem
from shared import knowledge_base as kb
from shared.dashboard import kpi_row, render_operations, render_insights

# ---------------------------------------------------------------------------
# UI strings (each page uses ONE language only)
# ---------------------------------------------------------------------------
STR = {
"ar": {
 "app_title": "رَفد", "hero_sub": "مساعد رؤية وتصعيد الشحنات الطبية",
 "hero_desc": "لعمليات لوجستيات الحج والعمرة الطبية — متابعة الحالة، اكتشاف التصعيد، تنبيهات سلسلة التبريد، وحالات هيئة الغذاء والدواء.",
 "tabs": ["المساعد", "لوحة البيانات", "مراجعة المعرفة", "حول"],
 "settings": "الإعدادات", "mode": "وضع الإجابة",
 "mode_rule": "قواعد محلية (بدون مفتاح)", "mode_ai": "صياغة ذكية (GPT)",
 "theme_dark": "الوضع الداكن", "clear": "مسح المحادثة",
 "intro": "اسألي عن حالة الشحنات، احتياج التصعيد، مخاطر التأخير، تنبيهات سلسلة التبريد، والتعليق لدى هيئة الغذاء والدواء.",
 "ask_ph": "اكتبي سؤالك هنا…",
 "grp": {"الشحنات": ["ما حالة الشحنة AWB-10024؟", "هل تحتاج الشحنة AWB-10024 إلى تصعيد؟", "متى آخر تحديث للشحنة AWB-10024؟"],
         "المخاطر": ["ما الشحنات التي تجاوزت الموعد النهائي؟", "ما الشحنات التي لديها تنبيه سلسلة تبريد؟", "ما أعلى الشحنات خطورة اليوم؟"],
         "الامتثال": ["ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟", "ما سبب تعليق الشحنة AWB-10011؟", "ما سياسة التصعيد للشحنات الطبية الحرجة؟"],
         "ملخص": ["أعطني ملخص اليوم بشكل مختصر."]},
 "confidence": "الثقة", "source": "المصدر", "shipment": "الشحنة",
 "src_rule": "القواعد المحلية", "src_kb": "قاعدة المعرفة المعتمدة", "src_gpt": "GPT (مستند للحقائق)", "src_fb": "غير مجاب",
 "fb_help": "👍 مفيد", "fb_not": "👎 غير مفيد", "fb_fix": "✏️ يحتاج تصحيح", "fb_thanks": "تم تسجيل تقييمك — شكراً.",
 "fallback": "لم أجد إجابة مؤكدة لهذا السؤال. تم حفظه للمراجعة، وسيتمكن المساعد من الإجابة عليه بعد اعتماد الجواب في «مراجعة المعرفة».",
 "kpi_total": "إجمالي الشحنات", "kpi_esc": "تحتاج تصعيد", "kpi_missed": "فاتت الموعد",
 "kpi_cold": "تنبيه تبريد", "kpi_sfda": "معلّقة SFDA",
 "dash_ops": "لوحة العمليات", "dash_ai": "مؤشرات المساعد",
 "ch_status": "توزيع الحالات", "ch_priority": "توزيع الأولوية",
 "ch_deadline": "حالة الموعد النهائي", "ch_facility": "التوزيع حسب المنشأة",
 "show_table": "عرض جدول البيانات",
 "insights_empty": "ستظهر مؤشرات المساعد بعد استخدام الشات.",
 "ins_total": "عدد الأسئلة", "ins_unanswered": "أسئلة بلا إجابة", "ins_lowconf": "ثقة منخفضة",
 "ins_feedback": "التقييمات", "ins_intents": "أكثر النوايا", "ins_awb": "أكثر الشحنات سؤالاً",
 "ins_topq": "أكثر الأسئلة تكراراً",
 "kb_title": "مراجعة المعرفة", "kb_desc": "الأسئلة التي لم يستطع المساعد الإجابة عليها بثقة. اكتبي الإجابة الصحيحة واعتمديها لتدخل قاعدة المعرفة.",
 "kb_empty": "لا توجد أسئلة بانتظار المراجعة.", "kb_answer": "الإجابة الصحيحة",
 "kb_intent": "تصنيف النية", "kb_approve": "اعتماد وإضافة لقاعدة المعرفة",
 "kb_approved": "تم الاعتماد. سيستخدمها المساعد في الأسئلة المشابهة.",
 "kb_count": "إجابات معتمدة",
 "about_title": "عن رَفد",
 "about_intro": "رَفد هو مساعد ذكي لدعم رؤية ومتابعة الشحنات الطبية خلال عمليات الحج والعمرة. يساعد فرق العمليات على معرفة حالة الشحنات، اكتشاف الشحنات التي تحتاج إلى تصعيد، متابعة تنبيهات سلسلة التبريد، ورصد الشحنات المعلّقة لدى هيئة الغذاء والدواء.",
 "about_problem_h": "المشكلة",
 "about_problem": "بيانات الشحنات الطبية تتوزع بين ملفات وسجلات تتبع وسياسات، مما يبطئ اكتشاف الشحنات المتأخرة أو الحرجة قبل تأثيرها على الخدمات الصحية الميدانية.",
 "about_solution_h": "الحل",
 "about_solution": "محرّك استرجاع يعتمد على حقول البيانات (Metadata-aware) يعطي إجابات دقيقة وقابلة للتحقق، مع طبقة صياغة ذكية اختيارية لا تغيّر أي رقم أو معرّف. ويعمل تصنيف النوايا محلياً قبل استدعاء أي نموذج لغوي، مما يخفض التكلفة وزمن الاستجابة.",
 "about_how_h": "كيف يعمل النظام",
 "about_value_h": "القيمة التشغيلية",
 "about_value": "قرارات تصعيد أسرع، رؤية فورية للمخاطر (تأخير، تبريد، تعليق نظامي)، وتوثيق كل إجابة بمصدرها — مع بقاء القرار النهائي لفريق العمليات.",
 "about_next_h": "التطوير القادم",
 "about_next": "ربط Azure AI Search للبحث الهجين، إشعارات استباقية، وتوسيع قاعدة المعرفة المعتمدة من الأسئلة الواقعية.",
 "about_loop_h": "منهجية التحسين المستمر",
 "about_loop": "تم تصميم رَفد بمنهجية تحسين مستمر: كل سؤال يُحفظ مع الإجابة ومستوى الثقة وتقييم المستخدم. وإذا لم يستطع المساعد الإجابة بثقة، يُحفظ السؤال للمراجعة، وبعد اعتماد الإجابة الصحيحة تُضاف إلى قاعدة المعرفة ليستخدمها في المحادثات القادمة — تحسّن آمن بدون تدريب تلقائي غير خاضع للمراجعة.",
 "about_market_h": "توافق مع توجهات السوق السعودي",
 "about_market": "أطلقت الخطوط السعودية للشحن مبادرة إستراتيجية مع الهيئة العامة للغذاء والدواء لدعم سلاسل إمداد الأدوية والمستلزمات الطبية، تتضمن تسهيلات في أسعار الشحن تصل إلى 50%، وترتكز على شهادتي IATA CEIV Pharma وCEIV Fresh وقدرات متقدمة في سلسلة التبريد. يعمل رَفد في المساحة نفسها تماماً — رؤية الشحنات الدوائية، متابعة تخليص الهيئة، وتنبيهات سلسلة التبريد — أي أن المشروع يعالج أولوية وطنية قائمة فعلاً. كما تتجه منظومة الحج نحو منصات رقمية ذكية لتنظيم الطلبات اللوجستية ومراقبة استهلاك الموارد وتقليل الهدر خلال الموسم، وهو النمط الذي صُمم رَفد ليتكامل معه.",
 "about_quality_h": "جودة النظام (تحقق آلي)",
 "about_data_note": "جميع البيانات اصطناعية لأغراض العرض فقط، ولا تمثل أي جهة أو مريض حقيقي. التوصيات استرشادية والقرار النهائي لفريق العمليات.",
 "how_lines": "سؤال المستخدم\n → تصنيف النية (حالة/تصعيد/تبريد/موعد/تعليق/سياسة/ملخص)\n → فلترة دقيقة على حقول البيانات\n → حقائق مؤكدة + قاعدة SLA + آخر حدث تتبع\n → [إجابة قواعد] أو [صياغة GPT للحقائق نفسها]\n → إجابة مهيكلة + توصية + المصدر",
},
"en": {
 "app_title": "Rafd", "hero_sub": "Medical Cargo Visibility & Escalation Assistant",
 "hero_desc": "For Hajj & Umrah medical logistics — track status, detect escalation needs, cold-chain alerts, and SFDA holds.",
 "tabs": ["Assistant", "Dashboard", "Knowledge Review", "About"],
 "settings": "Settings", "mode": "Answer mode",
 "mode_rule": "Rule-based (No API)", "mode_ai": "AI-phrased (GPT)",
 "theme_dark": "Dark mode", "clear": "Clear chat",
 "intro": "Ask about shipment status, escalation needs, deadline risks, cold-chain alerts, and SFDA holds.",
 "ask_ph": "Type your question…",
 "grp": {"Shipment": ["What is the status of shipment AWB-10024?", "Does shipment AWB-10024 need escalation?", "What is the latest update for AWB-10024?"],
         "Risk": ["Which shipments missed the deadline?", "Which shipments have a cold chain alert?", "What are the highest-risk shipments today?"],
         "Compliance": ["Which shipments are on SFDA hold?", "Why is shipment AWB-10011 on hold?", "What is the escalation policy for critical medical shipments?"],
         "Summary": ["Give me a short daily summary."]},
 "confidence": "Confidence", "source": "Source", "shipment": "Shipment",
 "src_rule": "Rule engine", "src_kb": "Approved knowledge base", "src_gpt": "GPT (grounded)", "src_fb": "Unanswered",
 "fb_help": "👍 Helpful", "fb_not": "👎 Not helpful", "fb_fix": "✏️ Needs correction", "fb_thanks": "Feedback recorded — thank you.",
 "fallback": "I could not answer this confidently. It has been saved for review; once an approved answer is added in Knowledge Review, the assistant will use it.",
 "kpi_total": "Total shipments", "kpi_esc": "Need escalation", "kpi_missed": "Missed deadline",
 "kpi_cold": "Cold chain alerts", "kpi_sfda": "SFDA holds",
 "dash_ops": "Operations Dashboard", "dash_ai": "Assistant Insights",
 "ch_status": "Status distribution", "ch_priority": "Priority distribution",
 "ch_deadline": "Deadline status", "ch_facility": "Distribution by facility",
 "show_table": "Show data table",
 "insights_empty": "Assistant insights will appear after users start asking questions.",
 "ins_total": "Questions asked", "ins_unanswered": "Unanswered", "ins_lowconf": "Low confidence",
 "ins_feedback": "Feedback", "ins_intents": "Top intents", "ins_awb": "Most-asked shipments",
 "ins_topq": "Top repeated questions",
 "kb_title": "Knowledge Review", "kb_desc": "Questions the assistant could not answer confidently. Write the correct answer and approve it into the knowledge base.",
 "kb_empty": "No questions pending review.", "kb_answer": "Correct answer",
 "kb_intent": "Intent tag", "kb_approve": "Approve into knowledge base",
 "kb_approved": "Approved. The assistant will use it for similar questions.",
 "kb_count": "Approved answers",
 "about_title": "About Rafd",
 "about_intro": "Rafd is an intelligent assistant for medical cargo visibility and escalation during Hajj and Umrah logistics operations. It helps operations teams track shipment status, identify escalation needs, monitor cold-chain alerts, and detect SFDA-related holds.",
 "about_problem_h": "Problem",
 "about_problem": "Medical shipment data is fragmented across files, tracking logs, and policies — slowing the discovery of delayed or critical shipments before they impact field healthcare.",
 "about_solution_h": "Solution",
 "about_solution": "A metadata-aware retrieval engine gives exact, verifiable answers, with an optional AI phrasing layer that never changes a number or identifier. Intent classification runs locally before any LLM call, cutting cost and response time.",
 "about_how_h": "How it works",
 "about_value_h": "Operational value",
 "about_value": "Faster escalation decisions, instant risk visibility (delays, cold chain, regulatory holds), and every answer documented with its source — while the final decision stays with the operations team.",
 "about_next_h": "Next improvements",
 "about_next": "Azure AI Search integration for hybrid retrieval, proactive alerts, and growing the approved knowledge base from real operational questions.",
 "about_loop_h": "Continuous improvement loop",
 "about_loop": "Rafd is designed with a continuous improvement loop. Every question is logged with its answer, confidence level, and user feedback. If the assistant cannot answer confidently, the question is stored for review. After an approved answer is added to the knowledge base, the assistant can use it in future conversations — improving over time without unsafe automatic retraining.",
 "about_market_h": "Saudi market alignment",
 "about_market": "Saudia Cargo has launched a strategic initiative with the Saudi Food & Drug Authority (SFDA) to strengthen pharmaceutical and medical-supply cargo chains, including shipping-cost facilitation of up to 50%, backed by IATA CEIV Pharma and CEIV Fresh certifications and advanced cold-chain capabilities. Rafd operates in exactly this space — pharma-cargo visibility, SFDA clearance follow-up, and cold-chain alerts — meaning the project addresses a live national priority. Hajj operations are also moving toward smart digital platforms for logistics requests and resource monitoring; Rafd is designed to integrate with that pattern.",
 "about_quality_h": "System quality (automated checks)",
 "about_data_note": "All data is synthetic, for demonstration only; it represents no real entity or patient. Recommendations are advisory — the final decision belongs to the operations team.",
 "how_lines": "User question\n → Intent classification (status/escalation/cold-chain/deadline/hold/policy/summary)\n → Exact metadata filtering\n → Verified facts + SLA rule + latest tracking event\n → [Rule-based answer] OR [GPT rephrases the same facts]\n → Structured answer + recommendation + source",
},
}

# ---------------------------------------------------------------------------
def _css(ar, dark):
    if dark:
        bg, card, text, border, muted = "#0D1520", "#152030", "#E6EDF3", "#26313D", "#9AA8B5"
        navy, teal, gold = "#13273D", "#17A398", "#D4AF37"
        navy_text = "#CFE3FF"
    else:
        bg, card, text, border, muted = "#F7F9FA", "#FFFFFF", "#1F2933", "#E3E8EE", "#5B6770"
        navy, teal, gold = "#0B1F33", "#0E7C7B", "#C9A227"
        navy_text = navy

    if ar:
        al, side = "right", "right"
        # FULL right-to-left layout for the Arabic page.
        dir_rules = """
/* ================= FULL RTL (Arabic page) ================= */
[data-testid="stAppViewContainer"] { direction: rtl; }
/* Sidebar moves to the RIGHT. If a future Streamlit version misplaces it,
   delete ONLY the next line. */
[data-testid="stAppViewContainer"] { flex-direction: row-reverse; }
[data-testid="stMain"] .block-container { direction: rtl; text-align: right; }
[data-testid="stSidebar"] { direction: rtl; text-align: right; }
[data-testid="stSidebar"] label, [data-testid="stSidebar"] p { text-align: right; }
.stTabs [data-baseweb="tab-list"] { direction: rtl; }
[data-testid="stChatMessage"] { direction: rtl; text-align: right; }
[data-testid="stChatMessageContent"] { direction: rtl; text-align: right; }
[data-testid="stChatInput"] textarea { direction: rtl; text-align: right; }
[data-testid="stTextInput"] input, [data-testid="stTextArea"] textarea { direction: rtl; text-align: right; }
[data-testid="stMetric"] { direction: rtl; text-align: right; }
[data-testid="stExpander"] summary { direction: rtl; text-align: right; }
[data-testid="stMarkdownContainer"] { text-align: right; }
/* Technical content stays readable left-to-right on purpose */
[data-testid="stCode"], pre, code { direction: ltr; text-align: left; }
[data-testid="stDataFrame"] { direction: ltr; }
"""
    else:
        al, side = "left", "left"
        # Explicit left-to-right layout for the English page.
        dir_rules = """
/* ================= FULL LTR (English page) ================= */
[data-testid="stAppViewContainer"] { direction: ltr; flex-direction: row; }
[data-testid="stMain"] .block-container { direction: ltr; text-align: left; }
[data-testid="stSidebar"] { direction: ltr; text-align: left; }
[data-testid="stChatMessage"], [data-testid="stChatMessageContent"] { direction: ltr; text-align: left; }
[data-testid="stChatInput"] textarea, [data-testid="stTextInput"] input { direction: ltr; text-align: left; }
"""

    st.markdown(f"""<style>
.stApp {{ background:{bg}; color:{text}; }}
{dir_rules}
[data-testid="stSidebar"] {{ background:{card}; }}
.block-container {{ padding-top:0.8rem; max-width:1080px; }}
.hero {{ background:linear-gradient(135deg, {navy} 0%, #14324E 100%); color:#fff;
  border-radius:14px; padding:22px 26px; margin-bottom:14px;
  border-{side}:5px solid {gold}; text-align:{al}; }}
.hero h1 {{ margin:0; font-size:1.9rem; }}
.hero .s {{ opacity:.92; font-size:1.02rem; margin-top:2px; }}
.hero .d {{ opacity:.75; font-size:.85rem; margin-top:6px; }}
.kpi {{ background:{card}; border:1px solid {border}; border-top:3px solid {gold};
  border-radius:10px; padding:10px 6px; text-align:center; }}
.kpi .n {{ color:{navy_text}; font-size:1.35rem; font-weight:700; line-height:1; }}
.kpi .l {{ color:{teal}; font-size:.7rem; margin-top:4px; }}
.intro {{ background:{card}; border:1px solid {border}; border-radius:10px;
  padding:12px 16px; color:{muted}; font-size:.92rem; margin-bottom:8px; text-align:{al}; }}
[data-testid="stChatMessageContent"] p {{ line-height:1.75; }}
div.stButton > button {{ border-radius:16px; border:1px solid {teal}; background:{card};
  color:{teal}; font-size:.8rem; padding:2px 12px; }}
div.stButton > button:hover {{ background:{teal}; color:#fff; }}
h4 {{ color:{navy_text}; }}
</style>""", unsafe_allow_html=True)

def _src_label(S, source):
    return {"rule-based": S["src_rule"], "knowledge_base": S["src_kb"],
            "gpt": S["src_gpt"], "fallback": S["src_fb"]}.get(source, source)

def _gpt_rephrase(question, facts_text, ar, api_key, model):
    from openai import OpenAI
    client = OpenAI(api_key=api_key)
    lang = "Arabic" if ar else "English"
    system = ("You are Rafd, an assistant for Hajj & Umrah medical cargo operations. You are given FACTS "
              "already verified from the data. Rewrite them into a clear, professional answer keeping the "
              "same four-part structure (Answer / Reason / Recommended action / Source). Do NOT add, remove, "
              "or change any number, count, AWB code, airport code, status, or date. Do NOT invent anything. "
              f"You RECOMMEND escalation; you never approve or reject. Answer ONLY in {lang}.")
    user = f"Question: {question}\n\nVerified facts:\n{facts_text}\n\nRewrite."
    r = client.chat.completions.create(model=model, temperature=0.3,
        messages=[{"role": "system", "content": system}, {"role": "user", "content": user}])
    return r.choices[0].message.content

# ---------------------------------------------------------------------------
def render_page(lang):
    S = STR[lang]
    ar = (lang == "ar")

    # ---- sidebar (minimal: mode + theme + clear) ----
    with st.sidebar:
        st.subheader(S["settings"])
        mode = st.radio(S["mode"], [S["mode_rule"], S["mode_ai"]], index=0, key=f"mode_{lang}")
        use_ai = (mode == S["mode_ai"])
        api_key, model = "", "gpt-4o-mini"
        if use_ai:
            api_key = st.secrets.get("OPENAI_API_KEY", "") if hasattr(st, "secrets") else ""
            if not api_key:
                api_key = st.text_input("OpenAI API Key", type="password", key=f"key_{lang}")
            model = st.selectbox("Model", ["gpt-4o-mini", "gpt-4o"], index=0, key=f"model_{lang}")
        dark = st.toggle("🌙 " + S["theme_dark"], value=st.session_state.get("dark", False), key=f"dark_{lang}")
        st.session_state["dark"] = dark
        if st.button("🗑️ " + S["clear"], key=f"clear_{lang}", use_container_width=True):
            st.session_state[f"hist_{lang}"] = []
            st.rerun()

    _css(ar, st.session_state.get("dark", False))

    # ---- hero ----
    st.markdown(f"""<div class="hero"><h1>{S['app_title']}</h1>
<div class="s">{S['hero_sub']}</div><div class="d">{S['hero_desc']}</div></div>""",
                unsafe_allow_html=True)

    chunks = load_chunks()
    if chunks is None:
        st.error("chunks.json not found."); st.stop()
    ships, tracks, policies, by_awb = build_indexes(chunks)
    df = ships_df(ships)

    def run_engine(question):
        return eng.answer(question, lang, ships, tracks, policies, by_awb)

    tabs = st.tabs(S["tabs"])

    # =================== TAB 1: ASSISTANT ===================
    with tabs[0]:
        kpi_row(ships, S)
        st.write("")
        st.markdown(f"<div class='intro'>{S['intro']}</div>", unsafe_allow_html=True)

        # suggestion chips grouped
        for g, qs in S["grp"].items():
            st.caption(g)
            cols = st.columns(3)
            for i, ex in enumerate(qs):
                if cols[i % 3].button(ex, key=f"chip_{lang}_{g}_{i}", use_container_width=True):
                    st.session_state[f"pending_{lang}"] = ex
                    st.rerun()

        hist_key = f"hist_{lang}"
        if hist_key not in st.session_state:
            st.session_state[hist_key] = []

        # render history
        for i, m in enumerate(st.session_state[hist_key]):
            with st.chat_message(m["role"]):
                st.markdown(m["content"], unsafe_allow_html=True)
                if m["role"] == "assistant":
                    meta = m.get("meta", {})
                    cap = (f"{S['confidence']}: {int(meta.get('confidence', 0) * 100)}% · "
                           f"{S['source']}: {_src_label(S, meta.get('source', ''))}")
                    if meta.get("awb"):
                        cap += f" · {S['shipment']}: {meta['awb']}"
                    st.caption(cap)
                    fbk = f"fb_{lang}_{i}"
                    if st.session_state.get(fbk):
                        st.caption(S["fb_thanks"])
                    else:
                        c1, c2, c3, _ = st.columns([1, 1, 1.2, 3])
                        for col, label, val in [(c1, S["fb_help"], "helpful"),
                                                 (c2, S["fb_not"], "not_helpful"),
                                                 (c3, S["fb_fix"], "needs_correction")]:
                            if col.button(label, key=f"{fbk}_{val}"):
                                mem.log_feedback(lang, meta.get("question", ""), m["content"], val)
                                st.session_state[fbk] = val
                                st.rerun()

        # input (chips inject a pending question)
        q = st.chat_input(S["ask_ph"], key=f"chatin_{lang}")
        pending = st.session_state.pop(f"pending_{lang}", None)
        if pending:
            q = pending
        if q:
            res = run_engine(q)
            # learning loop: KB fallback then unanswered
            if res["source"] == "fallback":
                hit = kb.search_approved(q, lang)
                if hit:
                    res.update(text=hit["answer"], source="knowledge_base",
                               confidence=0.7, intent=hit.get("intent", "unknown"))
                else:
                    kb.save_unanswered(lang, q, res["intent"], res["awb"], "no_match")
                    res.update(text=S["fallback"], confidence=0.2)
            elif use_ai and api_key:
                try:
                    res["text"] = _gpt_rephrase(q, res["text"], ar, api_key, model)
                    res["source"] = "gpt"
                except Exception:
                    pass  # keep the rule-based text silently
            res["question"] = q
            st.session_state[hist_key].append({"role": "user", "content": q})
            st.session_state[hist_key].append({"role": "assistant", "content": res["text"], "meta": res})
            mem.log_conversation(lang, q, res["text"], res["intent"], res["awb"],
                                 res["confidence"], res["source"])
            st.rerun()

    # =================== TAB 2: DASHBOARD ===================
    with tabs[1]:
        render_operations(df, S)
        st.divider()
        render_insights(S, lang)

    # =================== TAB 3: KNOWLEDGE REVIEW ===================
    with tabs[2]:
        st.markdown(f"#### {S['kb_title']}")
        st.caption(S["kb_desc"])
        approved_n = len([x for x in kb.load_approved() if x.get("language") == lang])
        st.metric(S["kb_count"], approved_n)
        items = kb.load_unanswered(language=lang)
        if not items:
            st.info(S["kb_empty"])
        for idx, item in enumerate(items):
            with st.container(border=True):
                st.markdown(f"**{item['question']}**")
                st.caption(f"{item['timestamp']} · intent: {item.get('intent','unknown')} · reason: {item.get('reason','')}")
                ans = st.text_area(S["kb_answer"], key=f"kb_a_{lang}_{idx}")
                intent = st.selectbox(S["kb_intent"], eng.INTENT_LIST,
                                      index=len(eng.INTENT_LIST) - 1, key=f"kb_i_{lang}_{idx}")
                if st.button(S["kb_approve"], key=f"kb_b_{lang}_{idx}") and ans.strip():
                    kb.save_approved(lang, item["question"], ans.strip(), intent)
                    kb.remove_unanswered(item)
                    st.success(S["kb_approved"])
                    st.rerun()

    # =================== TAB 4: ABOUT ===================
    with tabs[3]:
        st.markdown(f"#### {S['about_title']}")
        st.markdown(S["about_intro"])
        c1, c2 = st.columns(2)
        with c1:
            st.markdown(f"**{S['about_problem_h']}**");  st.markdown(S["about_problem"])
            st.markdown(f"**{S['about_how_h']}**");      st.code(S["how_lines"], language="text")
            st.markdown(f"**{S['about_loop_h']}**");     st.markdown(S["about_loop"])
        with c2:
            st.markdown(f"**{S['about_solution_h']}**"); st.markdown(S["about_solution"])
            st.markdown(f"**{S['about_value_h']}**");    st.markdown(S["about_value"])
            st.markdown(f"**{S['about_next_h']}**");     st.markdown(S["about_next"])
        st.markdown(f"**{S['about_market_h']}**")
        st.markdown(S["about_market"])
        st.markdown(f"**{S['about_quality_h']}**")
        rows, passed, total = eng.run_validation(ships, run_engine)
        st.metric("Score", f"{passed}/{total} PASS")
        st.dataframe(pd.DataFrame(rows), use_container_width=True, hide_index=True)
        st.caption(S["about_data_note"])
