# DMS AI System

DataQ review assistant. It reads a case, retrieves the matching rules from Handbook v3, checks the
evidence against them, and recommends FILE, DO_NOT_FILE or NEEDS_MORE_INFO with citations and, for FILE,
a draft request. Staff make the final decision.

- Results for the public cases: `predictions.json`
- How quality was measured, and what failed: `EVAL.md`
- Dashcam alert design note: `DESIGN_NOTE.md`
- AI tools used and the main trade-offs: `AI_TOOLS_AND_TRADEOFFS.md`

## Run with Docker

Needs Docker and an OpenAI or Gemini API key.

```powershell
Copy-Item .env.example .env      # then set LLM_PROVIDER, LLM_MODEL and the API key in .env
docker compose up --build        # API on http://localhost:8000 (docs at /docs)
```

In a second terminal:

```powershell
# Review a whole case file
docker compose run --rm app python -m server.cli review data/cases/public_cases.json --out results/predictions.json

# Score the dev cases
docker compose run --rm app python -m server.cli eval --runs 3 --out results/eval_results.json

# After adding or changing a file in data/knowledge_base or data/evidence
docker compose run --rm app python -m server.cli index
docker compose restart app       # the API loads the index at startup
```

`data/` is mounted from this folder, so new documents and case files need no rebuild. Outputs go to `results/`.
The tested setting is `LLM_PROVIDER=openai` with `LLM_MODEL=gpt-4.1`.

## Run locally

Run these from this folder in PowerShell:

```powershell
python -m venv .venv
.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
uvicorn server.main:app --reload
```

All models, API keys and folder paths are set in `.env`. Never commit or submit that file.

- Health check: http://localhost:8000/health
- API docs: http://localhost:8000/docs

## Re-index documents

After adding or changing a file in `data/knowledge_base/` or `data/evidence/`, run:

```powershell
python -m server.cli index
```

The first run downloads the local embedding model.

## Review cases

Set `LLM_PROVIDER`, `LLM_MODEL` and the matching API key in `.env` first.

```powershell
# Review every case in a file and write the results (matches data/output_schema.json)
python -m server.cli review data/cases/public_cases.json --out predictions.json

# Score the dev cases against their expected answers.
# --runs 3 reviews each case three times to show whether answers are stable.
python -m server.cli eval --runs 3
```

`eval` prints each case and a summary, and writes the full report to `eval_results.json`.

## Review one case over the API

`POST /review` takes one case, in the same shape as an entry in a case file, and returns one result.
Add `"as_of_date"` to the body to fix "today"; otherwise the server's date is used.

```powershell
curl.exe -X POST http://localhost:8000/review -H "Content-Type: application/json" -d '@case.json'
```

## Project layout

- `server/main.py`: starts the app.
- `server/cli.py`: all terminal commands, in the `CommandLine` class.
- `server/config.py`: loads the global settings from `.env`.
- `server/documents/embedder.py`: the one embedding model, used for indexing and retrieval.
- `server/api/routes.py`: all API endpoints, in the `ApiRoutes` class.
- `server/documents/reader.py`: reads TXT and PDF files, with OCR for scans.
- `server/documents/chunker.py`: splits rules by section and keeps evidence whole.
- `server/documents/index_builder.py`: embeds the chunks and saves the index.
- `server/documents/retriever.py`: finds the active rule groups for a case and looks up evidence by file name.
- `server/review/engine.py`: reviews one case: retrieval, the model call, then checks on the answer.
- `server/review/llm_client.py`: the chat model (OpenAI, or Gemini through its OpenAI-compatible endpoint).
- `server/review/schemas.py`: the case input and the result output, matching `data/output_schema.json`.
- `server/review/evaluator.py`: scores the engine against the expected answers in a case file.
- `server/review/system_prompt.txt`: the reviewer instructions. Edit them without changing code.
- `data/`: rule documents, evidence, cases and the output schema.
- `index/`: generated search index, not committed.

## Add a new API

Add a method to `ApiRoutes` and register it in `__init__` with `add_api_route`.
