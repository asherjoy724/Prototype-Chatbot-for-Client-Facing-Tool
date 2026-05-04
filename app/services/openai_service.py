import json
from typing import Optional

from openai import OpenAI

from app.models import ChatRequest
from app.settings import settings


_client: Optional[OpenAI] = None


def openai_available() -> bool:
    return settings.llm_enabled


def get_client() -> OpenAI:
    global _client
    if _client is None:
        _client = OpenAI(api_key=settings.openai_api_key)
    return _client


def generate_grounded_response(
    payload: ChatRequest,
    prompt_context: str,
    conversation_context: str,
    output_schema: dict,
) -> dict:
    client = get_client()

    response = client.responses.create(
        model=settings.openai_model,
        input=[
            {
                "role": "system",
                "content": (
                    "You are a template-completion assistant. Answer only using the "
                    "provided template context. Answer as succinctly as possible. "
                    "Only answer what the user asked; do not add extra guidance such "
                    "as requirements, formatting, examples, or exclusions unless the "
                    "user asked for them. Do not invent requirements. If the context "
                    "is insufficient, say so plainly. Return JSON that matches the "
                    "requested schema."
                ),
            },
            {
                "role": "user",
                "content": (
                    f"User question: {payload.message}\n"
                    f"Current field id: {payload.current_field_id or 'none'}\n"
                    f"Current section id: {payload.current_section_id or 'none'}\n"
                    f"Draft value: {payload.draft_value or 'none'}\n\n"
                    f"Recent conversation:\n{conversation_context}\n\n"
                    f"Template context:\n{prompt_context}"
                ),
            },
        ],
        text={
            "format": {
                "type": "json_schema",
                "name": "template_assistant_response",
                "strict": True,
                "schema": output_schema,
            }
        },
    )

    return json.loads(response.output_text)


def embed_texts(texts):
    client = get_client()
    response = client.embeddings.create(
        model=settings.openai_embedding_model,
        input=texts,
    )
    return [item.embedding for item in response.data]
