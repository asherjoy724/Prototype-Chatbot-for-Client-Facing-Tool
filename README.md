# Template Assistant MVP

This repository contains an initial FastAPI scaffold for a template-completion chatbot.

## What is included

- A FastAPI backend with JSON API endpoints
- A browser UI for selecting fields and chatting with the assistant
- Mock template schema, FAQ content, and validation rules
- Grounded response construction based on field metadata and retrieved FAQ context
- An OpenAI-backed RAG path with local retrieval plus a safe rule-based fallback

## Endpoints

- `GET /api/health`
- `GET /api/template/client-intake-v1/schema`
- `POST /api/validate/field`
- `POST /api/chat/message`

## Run locally

```bash
python3 -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
cp .env.example .env
# then add your OPENAI_API_KEY to .env
python run.py
```

Then open `http://127.0.0.1:8000`.

## LLM / RAG setup

The assistant now supports two modes:

- `openai_rag`: uses local retrieval over template knowledge and sends the grounded context to the OpenAI Responses API
- `rule_based`: falls back to deterministic local guidance when `OPENAI_API_KEY` is not configured

Recommended environment variables:

- `OPENAI_API_KEY`
- `OPENAI_MODEL` default: `gpt-5-mini`
- `OPENAI_EMBEDDING_MODEL` default: `text-embedding-3-small`
- `ASSISTANT_USE_EMBEDDINGS` default: `true`

The app now loads a local `.env` file automatically.

## Memory and retrieval

- The frontend keeps a browser session id in `localStorage` so follow-up questions stay in the same assistant conversation.
- The backend keeps recent turns in memory and feeds them into the OpenAI prompt.
- Knowledge retrieval now prefers cached OpenAI embeddings and falls back to lexical retrieval if embeddings are disabled or unavailable.
- Knowledge embeddings are cached in `.assistant_cache/knowledge_embeddings.json`.

## Next steps

- Persist sessions and chat history beyond process memory
- Move template content into an admin-manageable store
