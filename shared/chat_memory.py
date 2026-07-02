"""Session chat history + JSONL logging (conversation + feedback)."""
import os, json
from datetime import datetime, timezone

LOGS = "logs"
CONV = os.path.join(LOGS, "conversation_history.jsonl")
FEED = os.path.join(LOGS, "answer_feedback.jsonl")

def _ensure():
    os.makedirs(LOGS, exist_ok=True)

def now_iso():
    return datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M:%S")

def _append(path, rec):
    _ensure()
    with open(path, "a", encoding="utf-8") as f:
        f.write(json.dumps(rec, ensure_ascii=False) + "\n")

def log_conversation(language, question, answer, intent, shipment_id, confidence, source):
    _append(CONV, {"timestamp": now_iso(), "language": language, "question": question,
                   "answer": answer, "intent": intent, "shipment_id": shipment_id,
                   "confidence": confidence, "source": source})

def log_feedback(language, question, answer, rating):
    _append(FEED, {"timestamp": now_iso(), "language": language, "question": question,
                   "answer": (answer or "")[:200], "rating": rating})

def read_jsonl(path):
    if not os.path.exists(path):
        return []
    out = []
    for line in open(path, encoding="utf-8"):
        line = line.strip()
        if line:
            try: out.append(json.loads(line))
            except Exception: pass
    return out

def read_conversations(): return read_jsonl(CONV)
def read_feedback():      return read_jsonl(FEED)
