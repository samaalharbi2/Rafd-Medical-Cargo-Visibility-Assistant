
# رفد · Rafd — Medical Cargo Visibility & Escalation Assistant

Bilingual (Arabic/English) operational assistant for **Hajj & Umrah medical air cargo**.
Ask about shipment status, delays, escalation, cold-chain alerts, SFDA holds, and
pre-season deadlines — and get a clean, single-language answer with sources.

Rafd is a **metadata-aware RAG assistant**. Facts come from exact metadata filtering
(zero hallucination on numbers/IDs); an optional GPT layer only *rephrases* the
verified facts. Answers are always in the same language as the question.

> All data in this project is synthetic, generated for technical demonstration only,
> and does not represent any real company, patient, or shipment.

## Interface (4 tabs)
- **Ask** — question box, KPI cards, structured answer cards, sources.
- **Dashboard** — status / airport / priority / cargo charts + data table.
- **Validation** — automated accuracy checks (answers vs metadata ground truth).
- **About** — architecture, tech stack, Responsible AI, Vision 2030 alignment.

## Why metadata-aware (not vector search)?
The data is **structured & operational**. Questions like "missed the deadline" need
**exact filters**, not semantic similarity. Metadata filtering is more accurate here —
a deliberate architectural choice.

## Answer tiers
- **Rule-based (No API)** — local, free, exact.
- **AI-phrased (GPT)** — GPT rewrites the same verified facts (needs an OpenAI key).

## Run locally
```
pip install -r requirements.txt
streamlit run app.py
```

## Deploy on Streamlit Cloud
1. Push these files to a **public** GitHub repo: `app.py`, `translations.py`,
   `chunks.json`, `requirements.txt`, and the `.streamlit/` folder.
2. share.streamlit.io → New app → pick the repo and `app.py`.
3. (Optional) enable AI phrasing: App → Settings → Secrets:
   ```
   OPENAI_API_KEY = "sk-..."
   ```
4. Deploy → permanent public URL.

## Responsible AI
Synthetic data only · sources with every answer · says "not found" when data is missing ·
recommends escalation, never decides (human-in-the-loop).

## Tech stack
Python · Streamlit · pandas · OpenAI (optional) · metadata-aware retrieval · bilingual (AR/EN, RTL).
