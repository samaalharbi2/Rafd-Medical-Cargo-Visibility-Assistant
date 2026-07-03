"""Intent classification + rule-based structured answers.
Returns: {text, intent, confidence, source, awb, count}."""
import re
from shared.translations import ap, fac, evt

INTENT_LIST = ["shipment_status", "escalation_check", "latest_update", "missed_deadline",
               "cold_chain_alert", "sfda_hold", "escalation_policy", "daily_summary", "unknown"]

def cargo(c, ar):
    return c.get("cargo_type_ar" if ar else "cargo_type_en", c.get("medical_cargo_type", ""))

def find_awb(text, by_awb):
    m = re.search(r"(\d{4,6})", text)
    if not m:
        return None
    d = m.group(1)
    for awb, c in by_awb.items():
        if re.sub(r"\D", "", awb) == d or re.sub(r"\D", "", c["shipment_id"]) == d:
            return c
    return None

def classify(question, has_awb):
    q = question.lower()
    hit = lambda kws: any(k in q for k in kws)
    if hit(["ملخص", "summary"]):                        return "daily_summary", 0.9
    if hit(["سياسة", "policy"]):                         return "escalation_policy", 0.85
    if has_awb:
        if hit(["آخر", "تحديث", "latest", "update", "تتبع", "track"]): return "latest_update", 0.95
        if hit(["تصعيد", "escalat"]):                    return "escalation_check", 0.95
        if hit(["سبب", "why", "تعليق", "معل", "hold"]):  return "sfda_hold", 0.9
        return "shipment_status", 0.95
    if hit(["فات", "فوت", "الموعد", "missed", "deadline", "تجاوز"]):   return "missed_deadline", 0.9
    if hit(["تبريد", "cold"]):                           return "cold_chain_alert", 0.9
    if hit(["sfda", "الغذاء والدواء", "فسح", "معل", "hold"]):          return "sfda_hold", 0.9
    if hit(["خطورة", "خطر", "risk", "تصعيد", "escalat"]):              return "escalation_check", 0.88
    return "unknown", 0.2

def recommend(c, ar):
    s = c["shipment_status"]
    if s == "SFDA Hold":
        return "متابعة التخليص النظامي عبر منصة فسح مع الشؤون التنظيمية." if ar \
            else "Follow up SFDA clearance via the Fasah platform with regulatory affairs."
    if s == "Cold Chain Alert":
        return "تصعيد فوري لفريق الجودة وحجز الشحنة مؤقتاً للتقييم قبل التسليم." if ar \
            else "Escalate to the quality team immediately; quarantine and assess before delivery."
    if c["requires_escalation"]:
        return "تصعيد لفريق العمليات ومراجعة آخر تحديثات التتبع." if ar \
            else "Escalate to the operations team and review the latest tracking updates."
    return "لا يتطلب إجراءً عاجلاً حالياً." if ar else "No urgent action required at this time."

def severity(c):
    return (c["requires_escalation"], c["delay_minutes"] or 0)

def _fmt(ar, direct, reason, action, rule):
    if ar:
        return (f"**الإجابة:** {direct}\n\n**السبب:** {reason}\n\n"
                f"**الإجراء الموصى به:** {action}\n\n**المصدر/القاعدة:** {rule}")
    return (f"**Answer:** {direct}\n\n**Reason:** {reason}\n\n"
            f"**Recommended action:** {action}\n\n**Source/Rule:** {rule}")

def _status_line(c, ar):
    d = c["delay_minutes"]
    s = c["shipment_status_ar"] if ar else c["shipment_status"]
    if d is not None:
        return f"{s} ({'تأخير ' + str(d) + ' دقيقة' if ar else 'delay ' + str(d) + ' min'})"
    return s

def _list_answer(hits, ar, title_ar, title_en, rule_ar, rule_en, note_ar="", note_en=""):
    hits = sorted(hits, key=severity, reverse=True)
    n = len(hits)
    top = hits[:5]
    if ar:
        lines = [f"{i}. {h['air_waybill_number']} — {cargo(h, True)} — {h['shipment_status_ar']} — {fac(h['destination_facility'], True)}"
                 for i, h in enumerate(top, 1)]
        direct = f"{title_ar}: **{n}**.\n\nأعلى الحالات للمراجعة:\n" + "\n".join(lines)
        if n > 5:
            direct += f"\n\n(القائمة الكاملة في لوحة البيانات — {n} شحنة)"
        reason = note_ar or "استخراج مباشر عبر فلترة الحقول التشغيلية."
        action = "ابدئي بالحالات الأعلى خطورة أعلاه." if n else "لا توجد حالات حالياً."
        rule = rule_ar + " · hajj_medical_shipments.xlsx"
    else:
        lines = [f"{i}. {h['air_waybill_number']} — {cargo(h, False)} — {h['shipment_status']} — {h['destination_facility']}"
                 for i, h in enumerate(top, 1)]
        direct = f"{title_en}: **{n}**.\n\nTop cases to review:\n" + "\n".join(lines)
        if n > 5:
            direct += f"\n\n(Full list in the Dashboard — {n} shipments)"
        reason = note_en or "Direct extraction via operational metadata filters."
        action = "Start with the highest-severity cases above." if n else "No cases at the moment."
        rule = rule_en + " · hajj_medical_shipments.xlsx"
    return _fmt(ar, direct, reason, action, rule), n

def answer(question, lang, ships, tracks, policies, by_awb):
    ar = (lang == "ar")
    c = find_awb(question, by_awb)
    intent, conf = classify(question, c is not None)
    res = {"intent": intent, "confidence": conf, "source": "rule-based",
           "awb": c["air_waybill_number"] if c else None, "count": None, "text": ""}

    if intent == "daily_summary":
        tot = len(ships)
        esc = sum(1 for x in ships if x["requires_escalation"])
        mis = sum(1 for x in ships if x["deadline_status"] == "MISSED Deadline")
        cca = sum(1 for x in ships if x["shipment_status"] == "Cold Chain Alert")
        sf  = sum(1 for x in ships if x["shipment_status"] == "SFDA Hold")
        risky = sorted([x for x in ships if x["requires_escalation"]], key=severity, reverse=True)[:3]
        if ar:
            direct = (f"إجمالي الشحنات: **{tot}** · تحتاج تصعيد: **{esc}** · فاتت الموعد: **{mis}** · "
                      f"تنبيه تبريد: **{cca}** · معلّقة لدى هيئة الغذاء والدواء: **{sf}**.")
            reason = "أعلى 3 شحنات خطورة: " + "؛ ".join(
                f"{x['air_waybill_number']} ({x['shipment_status_ar']})" for x in risky)
            action = "مراجعة الشحنات الحرجة أولاً، ثم متابعة حالات هيئة الغذاء والدواء وسلسلة التبريد."
            rule = "تجميع مباشر من بيانات الموسم · hajj_medical_shipments.xlsx"
        else:
            direct = (f"Total shipments: **{tot}** · Need escalation: **{esc}** · Missed deadline: **{mis}** · "
                      f"Cold chain alerts: **{cca}** · SFDA holds: **{sf}**.")
            reason = "Top 3 highest-risk: " + "; ".join(
                f"{x['air_waybill_number']} ({x['shipment_status']})" for x in risky)
            action = "Review critical shipments first, then SFDA and cold-chain cases."
            rule = "Direct aggregation over the season data · hajj_medical_shipments.xlsx"
        res.update(text=_fmt(ar, direct, reason, action, rule), count=tot)
        return res

    if intent == "escalation_policy":
        q = question.lower()
        rule_key = "escalation_rules"
        if "تأخير" in q or "delay" in q: rule_key = "delay_definition"
        if "تبريد" in q or "cold" in q:  rule_key = "cold_chain"
        parts = policies[rule_key]["content"].split("\n")
        txt = parts[1] if (ar and len(parts) > 1) else parts[0]
        reason = "نص مباشر من وثيقة سياسة مستوى الخدمة." if ar else "Verbatim from the SLA policy document."
        action = "تطبيق القاعدة على الشحنات المطابقة." if ar else "Apply the rule to matching shipments."
        res.update(text=_fmt(ar, txt, reason, action, "hajj_medical_sla_policy_ar_en.pdf"))
        return res

    if c:
        t = tracks.get(c["shipment_id"], {})
        latest = f"{evt(t.get('latest_event_type',''), ar)} — {ap(t.get('latest_event_location',''), ar)} — {t.get('latest_event_time','')}"
        if intent == "latest_update":
            direct = (f"آخر تحديث للشحنة {c['air_waybill_number']}: {latest}." if ar
                      else f"Latest update for {c['air_waybill_number']}: {latest}.")
            reason = "بحسب سجل أحداث التتبع." if ar else "Per the tracking event log."
            res.update(text=_fmt(ar, direct, reason, recommend(c, ar), "hajj_medical_tracking_events.csv"))
            return res
        if intent == "sfda_hold":
            held = c["shipment_status"] == "SFDA Hold"
            if ar:
                direct = (f"الشحنة {c['air_waybill_number']} معلّقة لدى هيئة الغذاء والدواء." if held
                          else f"الشحنة {c['air_waybill_number']} ليست معلّقة لدى الهيئة — حالتها: {c['shipment_status_ar']}.")
                reason = f"البضائع الطبية تخضع لتخليص الهيئة قبل الإفراج. آخر حدث: {latest}."
                rule = "قاعدة تخليص هيئة الغذاء والدواء · hajj_medical_shipments.xlsx"
            else:
                direct = (f"Shipment {c['air_waybill_number']} is on SFDA hold." if held
                          else f"Shipment {c['air_waybill_number']} is not on SFDA hold — status: {c['shipment_status']}.")
                reason = f"Medical goods require SFDA clearance before release. Latest event: {latest}."
                rule = "SFDA clearance rule · hajj_medical_shipments.xlsx"
            res.update(text=_fmt(ar, direct, reason, recommend(c, ar), rule))
            return res
        req = c["requires_escalation"]
        if ar:
            if intent == "escalation_check":
                direct = f"نعم، الشحنة {c['air_waybill_number']} تحتاج إلى تصعيد." if req \
                    else f"لا، الشحنة {c['air_waybill_number']} لا تحتاج إلى تصعيد."
            else:
                direct = f"حالة الشحنة {c['air_waybill_number']}: {_status_line(c, True)}."
            bits = [f"الحالة: {_status_line(c, True)}", f"الوجهة: {fac(c['destination_facility'], True)}",
                    f"الأولوية: {c['priority_level_ar']}", f"الموعد النهائي: {c['deadline_status_ar']}",
                    f"آخر حدث: {latest}"]
            if req: bits.append("أسباب التصعيد: " + "، ".join(c["escalation_reasons_ar"]))
            reason = " · ".join(bits)
            rule = ("قاعدة التصعيد (SLA): تأخير>240 دقيقة أو أولوية حرجة أو سلسلة تبريد أو تجاوز الموعد"
                    " · hajj_medical_shipments.xlsx")
        else:
            if intent == "escalation_check":
                direct = f"Yes, shipment {c['air_waybill_number']} needs escalation." if req \
                    else f"No, shipment {c['air_waybill_number']} does not need escalation."
            else:
                direct = f"Status of shipment {c['air_waybill_number']}: {_status_line(c, False)}."
            bits = [f"Status: {_status_line(c, False)}", f"Destination: {c['destination_facility']}",
                    f"Priority: {c['priority_level']}", f"Deadline: {c['deadline_status']}",
                    f"Latest event: {latest}"]
            if req: bits.append("Escalation reasons: " + "; ".join(c["escalation_reasons"]))
            reason = " · ".join(bits)
            rule = ("Escalation rule (SLA): delay>240 min OR Critical priority OR cold chain OR missed deadline"
                    " · hajj_medical_shipments.xlsx")
        res.update(text=_fmt(ar, direct, reason, recommend(c, ar), rule))
        return res

    if intent == "missed_deadline":
        txt, n = _list_answer([x for x in ships if x["deadline_status"] == "MISSED Deadline"], ar,
                              "الشحنات التي تجاوزت الموعد النهائي", "Shipments that missed the deadline",
                              "فلترة: deadline_status = MISSED Deadline", "Filter: deadline_status = MISSED Deadline")
        res.update(text=txt, count=n); return res
    if intent == "cold_chain_alert":
        txt, n = _list_answer([x for x in ships if x["shipment_status"] == "Cold Chain Alert"], ar,
                              "الشحنات التي لديها تنبيه سلسلة التبريد", "Shipments with a cold chain alert",
                              "فلترة: shipment_status = Cold Chain Alert", "Filter: shipment_status = Cold Chain Alert",
                              "حسب السياسة: تُصعَّد فوراً لفريق الجودة وتُحجز للتقييم.",
                              "Per policy: escalate to quality and quarantine for assessment.")
        res.update(text=txt, count=n); return res
    if intent == "sfda_hold":
        txt, n = _list_answer([x for x in ships if x["shipment_status"] == "SFDA Hold"], ar,
                              "الشحنات المعلّقة لدى هيئة الغذاء والدواء", "Shipments on SFDA hold",
                              "فلترة: shipment_status = SFDA Hold", "Filter: shipment_status = SFDA Hold",
                              "حسب السياسة: المتابعة عبر منصة فسح مع الشؤون التنظيمية.",
                              "Per policy: follow up via the Fasah platform with regulatory affairs.")
        res.update(text=txt, count=n); return res
    if intent == "escalation_check":
        txt, n = _list_answer([x for x in ships if x["requires_escalation"]], ar,
                              "الشحنات الأعلى خطورة (تحتاج تصعيداً)", "Highest-risk shipments (need escalation)",
                              "فلترة: requires_escalation = true", "Filter: requires_escalation = true")
        res.update(text=txt, count=n); return res

    res.update(source="fallback")
    return res

def run_validation(ships, answer_fn):
    """Compare list answers to metadata ground truth. Returns (rows, passed, total)."""
    truth = {
        "MISSED Deadline":  sum(1 for c in ships if c["deadline_status"] == "MISSED Deadline"),
        "SFDA Hold":        sum(1 for c in ships if c["shipment_status"] == "SFDA Hold"),
        "Cold Chain Alert": sum(1 for c in ships if c["shipment_status"] == "Cold Chain Alert"),
        "Need escalation":  sum(1 for c in ships if c["requires_escalation"]),
    }
    qmap = {"MISSED Deadline": "ما الشحنات التي تجاوزت الموعد النهائي؟",
            "SFDA Hold": "ما الشحنات المعلّقة لدى هيئة الغذاء والدواء؟",
            "Cold Chain Alert": "ما الشحنات التي لديها تنبيه سلسلة تبريد؟",
            "Need escalation": "ما أعلى الشحنات خطورة اليوم؟"}
    rows, passed = [], 0
    for k, exp in truth.items():
        got = answer_fn(qmap[k])["count"]
        ok = (got == exp); passed += ok
        rows.append({"Check": k, "Expected": exp, "Answered": got, "Result": "PASS" if ok else "FAIL"})
    r = answer_fn("هل الشحنة AWB-10024 تحتاج تصعيد؟")
    ok = (r["awb"] == "AWB-10024"); passed += ok
    rows.append({"Check": "AWB isolation", "Expected": "AWB-10024", "Answered": r["awb"] or "—",
                 "Result": "PASS" if ok else "FAIL"})
    return rows, passed, len(rows)
