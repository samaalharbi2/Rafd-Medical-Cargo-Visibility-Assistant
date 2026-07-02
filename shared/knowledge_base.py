"""Safe learning loop storage: unanswered questions + approved knowledge base."""
import os, json, re
from shared.chat_memory import now_iso

DATA = "data"
UNANSWERED = os.path.join(DATA, "unanswered_questions.jsonl")
APPROVED   = os.path.join(DATA, "approved_knowledge_base.json")

def _ensure():
    os.makedirs(DATA, exist_ok=True)

def save_unanswered(language, question, intent, shipment_id, reason):
    _ensure()
    rec = {"timestamp": now_iso(), "language": language, "question": question,
           "intent": intent, "shipment_id": shipment_id, "reason": reason}
    with open(UNANSWERED, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def load_unanswered(language=None):
    if not os.path.exists(UNANSWERED):
        return []
    out = []
    for line in open(UNANSWERED, encoding="utf-8"):
        line = line.strip()
        if not line: continue
        try: rec = json.loads(line)
        except Exception: continue
        if language is None or rec.get("language") == language:
            out.append(rec)
    return out

def remove_unanswered(entry):
    items = load_unanswered()
    items = [x for x in items
             if not (x.get("timestamp") == entry.get("timestamp")
                     and x.get("question") == entry.get("question"))]
    _ensure()
    with open(UNANSWERED, "w", encoding="utf-8") as f:
        for x in items:
            f.write(json.dumps(x, ensure_ascii=False) + "\n")

def load_approved():
    if not os.path.exists(APPROVED):
        return []
    try:
        return json.load(open(APPROVED, encoding="utf-8"))
    except Exception:
        return []

def save_approved(language, question, answer, intent):
    _ensure()
    items = load_approved()
    items.append({"timestamp": now_iso(), "language": language,
                  "question": question, "answer": answer, "intent": intent})
    json.dump(items, open(APPROVED, "w", encoding="utf-8"), ensure_ascii=False, indent=2)

def _tokens(s):
    return set(re.findall(r"[\w\u0600-\u06FF]+", s.lower()))

def search_approved(question, language):
    """Token-overlap similarity against approved Q&A. Returns best entry or None."""
    qt = _tokens(question)
    if not qt:
        return None
    best, best_score = None, 0.0
    for item in load_approved():
        if item.get("language") != language:
            continue
        it = _tokens(item.get("question", ""))
        if not it:
            continue
        score = len(qt & it) / max(len(qt), 1)
        if score > best_score:
            best, best_score = item, score
    return best if best_score >= 0.6 else None
