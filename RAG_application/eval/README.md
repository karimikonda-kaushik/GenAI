# RAGAS Evaluation Framework

Offline evaluation of this project's hybrid RAG pipeline using [RAGAS](https://docs.ragas.io/).

## Metrics

| Metric | What it measures | Needs ground truth? |
|--------|------------------|---------------------|
| **Faithfulness** | Is the answer grounded in retrieved context (no hallucination)? | No |
| **Answer Relevancy** | Does the answer address the question? | No |
| **Context Precision** | Are useful chunks ranked near the top? | Yes |
| **Context Recall** | Was the info needed for the ground-truth answer retrieved? | Yes |

Scores are in **0–1** (higher is better). Judge LLM = Gemini (`gemini-2.5-flash`), same API key as the app.

## Pipeline under test

```
question
   │
   ▼
hybrid_retrieve_from_postgres (vector + FTS → RRF)
   │
   ├── retrieved_contexts  ──► RAGAS (precision / recall / faithfulness)
   │
   ▼
invoke_rag (guardrailed Gemini)
   │
   └── response  ──► RAGAS (faithfulness / answer relevancy)
```

## Setup

Use the **backend venv** (already has Langchain + Gemini deps):

```bash
cd RAG_application
source backend/.venv/bin/activate
pip install -r eval/requirements.txt
```

Ensure `.env` has:

```bash
GOOGLE_API_KEY=...
DATABASE_URL=...
```

Documents must already be indexed for the `user_id` you evaluate against.

| How you uploaded | `user_id` to pass |
|------------------|-------------------|
| Local `REQUIRE_AUTH=false` | `dev-user` (or `DEV_USER_ID` in `.env`) |
| K8s / API key auth | `api-key-user` |

## Create a golden dataset

```bash
cp eval/dataset/golden_dataset.example.json eval/dataset/golden_dataset.json
```

Edit `golden_dataset.json`:

```json
[
  {
    "question": "What does the document say about X?",
    "ground_truth": "A short factual answer that appears in your uploaded text."
  }
]
```

Tips:
- Write questions that **require** your docs (not general knowledge).
- `ground_truth` should be answerable from the indexed content.
- Start with **3–10** questions.

## Run evaluation

```bash
# Full run: RAG answers + RAGAS scores
python -m eval.run_ragas \
  --dataset eval/dataset/golden_dataset.json \
  --user-id api-key-user

# Only generate answers/contexts (no scoring)
python -m eval.run_ragas --predictions-only --user-id api-key-user

# Score a previous predictions file
python -m eval.run_ragas --from-predictions eval/results/predictions_YYYYMMDD....json
```

Reports are written to `eval/results/`:

- `predictions_*.json` — question, contexts, answer, sources
- `ragas_report_*.json` — average metric scores

## Interpreting results

| Score band | Meaning |
|------------|---------|
| ≥ 0.80 | Strong |
| 0.60–0.79 | Usable; inspect weak samples |
| < 0.60 | Investigate retrieval or prompts |

**Low faithfulness** → model inventing facts → tighten prompts / reduce temperature.  
**Low context recall** → retriever missing key chunks → tune `TOP_K`, chunk size, or hybrid weights.  
**Low context precision** → noisy top ranks → improve ranking / RRF / filtering.  
**Low answer relevancy** → off-topic answers → check system prompt / empty-context path.

## Cost / time

Each sample calls Gemini for generation **plus** several judge calls per metric. A 5-question run typically takes a few minutes and uses API quota.

## Not included (by design)

- Live API endpoint for eval (run offline CLI)
- Auto-generated golden answers (you curate ground truth for quality)
- Production CI gate (easy to add later: fail if faithfulness < threshold)
