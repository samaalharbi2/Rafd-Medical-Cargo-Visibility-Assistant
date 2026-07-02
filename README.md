# رَفد · Rafd — Medical Cargo Visibility & Escalation Assistant

Two fully separate interfaces (Arabic RTL page / English LTR page) for Hajj & Umrah
medical cargo operations: shipment status, escalation checks, deadline risks,
cold-chain alerts, and SFDA holds.

Architecture: **metadata-aware retrieval** (exact filters, zero hallucination on
numbers/IDs) + intent classifier + **safe learning loop** (unanswered questions →
admin review → approved knowledge base → better future answers) + optional GPT
layer that only rephrases verified facts.

> All data is synthetic, for demonstration only. Recommendations are advisory —
> the final decision belongs to the operations team (human-in-the-loop).

## Project structure
```
app.py                      # entry: two language pages via st.navigation
pages/arabic_app.py         # Arabic page (RTL, Arabic-only UI)
pages/english_app.py        # English page (LTR, English-only UI)
shared/translations.py      # AR display names (airports, facilities, events)
shared/data_loader.py       # chunks.json loading + indexes
shared/rules_engine.py      # intent classifier + structured answers + validation
shared/chat_memory.py       # session history + JSONL logs (conversation, feedback)
shared/knowledge_base.py    # unanswered queue + approved knowledge base
shared/dashboard.py         # operations dashboard + assistant insights
chunks.json                 # the knowledge data
.streamlit/config.toml      # enterprise theme
```

## Features
- Chat interface (st.chat_message / st.chat_input) with persistent session memory,
  clickable suggestion chips, per-answer confidence + source + feedback buttons.
- Structured answers: Answer → Reason → Recommended action → Source/Rule.
- Operations Dashboard + Assistant Insights (built from real usage logs).
- Knowledge Review page: approve answers for unanswered questions (safe learning loop).
- About page: problem, solution, how it works, value, roadmap, quality checks.

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud
Push everything (including the `pages/`, `shared/`, `.streamlit/` folders) to a
public GitHub repo → share.streamlit.io → New app → main file `app.py`.
Optional AI phrasing: add `OPENAI_API_KEY = "sk-..."` under App → Settings → Secrets.

**Note (honest limitation):** `logs/` and `data/` files persist locally, but on
Streamlit Cloud the filesystem is ephemeral — they reset on app restart. For
permanent storage, connect an external database (future improvement).
