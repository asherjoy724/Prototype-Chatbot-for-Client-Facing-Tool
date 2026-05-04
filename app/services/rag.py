import json
import math
from pathlib import Path
from dataclasses import dataclass
from typing import Dict, List, Optional

from app.data import template_record
from app.models import FieldRecord
from app.services.openai_service import embed_texts, openai_available
from app.services.template_service import find_field_by_id
from app.settings import settings


@dataclass
class KnowledgeChunk:
    chunk_id: str
    chunk_type: str
    field_id: Optional[str]
    section_id: Optional[str]
    title: str
    text: str


def build_knowledge_chunks() -> List[KnowledgeChunk]:
    chunks: List[KnowledgeChunk] = []

    for section in template_record.sections:
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"section:{section.section_id}",
                chunk_type="section",
                field_id=None,
                section_id=section.section_id,
                title=section.title,
                text=f"{section.title}. {section.description}",
            )
        )

        for field in section.fields:
            details = [
                field.description,
                f"Required: {'yes' if field.required else 'no'}.",
            ]
            if field.format_rules:
                details.append(f"Format rules: {' '.join(field.format_rules)}")
            if field.allowed_values:
                details.append(f"Allowed values: {', '.join(field.allowed_values)}.")
            if field.example_value:
                details.append(f"Example: {field.example_value}.")
            if field.common_mistakes:
                details.append(f"Common mistake: {field.common_mistakes[0]}")

            chunks.append(
                KnowledgeChunk(
                    chunk_id=f"field:{field.field_id}",
                    chunk_type="field",
                    field_id=field.field_id,
                    section_id=section.section_id,
                    title=f"{section.title} / {field.label}",
                    text=" ".join(details),
                )
            )

    for faq in template_record.faqs:
        related_field = find_field_by_id(faq.related_field_ids[0]) if faq.related_field_ids else None
        chunks.append(
            KnowledgeChunk(
                chunk_id=f"faq:{faq.faq_id}",
                chunk_type="faq",
                field_id=related_field.field_id if related_field else None,
                section_id=None,
                title=faq.question,
                text=faq.answer,
            )
        )

    return chunks


KNOWLEDGE_CHUNKS = build_knowledge_chunks()
_embedding_cache: Optional[Dict[str, List[float]]] = None


def retrieve_rag_chunks(
    message: str,
    target_field: Optional[FieldRecord] = None,
    max_chunks: int = 5,
) -> List[KnowledgeChunk]:
    if settings.embeddings_enabled and openai_available():
        embedded = retrieve_rag_chunks_by_embedding(
            message=message,
            target_field=target_field,
            max_chunks=max_chunks,
        )
        if embedded:
            return embedded

    return retrieve_rag_chunks_by_lexical(
        message=message,
        target_field=target_field,
        max_chunks=max_chunks,
    )


def retrieve_rag_chunks_by_lexical(
    message: str,
    target_field: Optional[FieldRecord] = None,
    max_chunks: int = 5,
) -> List[KnowledgeChunk]:
    normalized_message = message.lower()
    scored = []

    for chunk in KNOWLEDGE_CHUNKS:
        score = 0
        if normalized_message and normalized_message in chunk.text.lower():
            score += 4
        if normalized_message and normalized_message in chunk.title.lower():
            score += 3
        if target_field and chunk.field_id == target_field.field_id:
            score += 8
        if target_field and target_field.label.lower() in chunk.text.lower():
            score += 2
        if target_field and target_field.key.lower() in chunk.text.lower():
            score += 2

        token_hits = 0
        for token in normalized_message.replace("?", " ").replace(",", " ").split():
            if len(token) < 3:
                continue
            if token in chunk.title.lower() or token in chunk.text.lower():
                token_hits += 1
        score += min(token_hits, 5)

        if score > 0:
            scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:max_chunks]]


def retrieve_rag_chunks_by_embedding(
    message: str,
    target_field: Optional[FieldRecord] = None,
    max_chunks: int = 5,
) -> List[KnowledgeChunk]:
    try:
        query_embedding = embed_texts([message])[0]
        cache = load_or_build_embedding_cache()
    except Exception:
        return []

    scored = []
    for chunk in KNOWLEDGE_CHUNKS:
        chunk_embedding = cache.get(chunk.chunk_id)
        if not chunk_embedding:
            continue

        score = cosine_similarity(query_embedding, chunk_embedding)
        if target_field and chunk.field_id == target_field.field_id:
            score += 0.18
        if target_field and chunk.section_id and target_field.label.lower() in chunk.text.lower():
            score += 0.04
        scored.append((score, chunk))

    scored.sort(key=lambda item: item[0], reverse=True)
    return [chunk for _, chunk in scored[:max_chunks] if _ > 0]


def render_rag_context(chunks: List[KnowledgeChunk]) -> str:
    if not chunks:
        return "No supporting knowledge was retrieved."

    lines = []
    for chunk in chunks:
        lines.append(f"[{chunk.chunk_type.upper()}] {chunk.title}: {chunk.text}")
    return "\n".join(lines)


def load_or_build_embedding_cache() -> Dict[str, List[float]]:
    global _embedding_cache
    if _embedding_cache is not None:
        return _embedding_cache

    cache_path = Path(settings.embedding_cache_dir)
    cache_path.mkdir(parents=True, exist_ok=True)
    embeddings_file = cache_path / "knowledge_embeddings.json"

    cache_payload = {}
    if embeddings_file.exists():
        try:
            cache_payload = json.loads(embeddings_file.read_text(encoding="utf-8"))
        except json.JSONDecodeError:
            cache_payload = {}

    if cache_payload.get("model") == settings.openai_embedding_model:
        cached_embeddings = cache_payload.get("embeddings", {})
        if set(cached_embeddings.keys()) == {chunk.chunk_id for chunk in KNOWLEDGE_CHUNKS}:
            _embedding_cache = cached_embeddings
            return _embedding_cache

    texts = [f"{chunk.title}\n{chunk.text}" for chunk in KNOWLEDGE_CHUNKS]
    vectors = embed_texts(texts)
    _embedding_cache = {
        chunk.chunk_id: vector for chunk, vector in zip(KNOWLEDGE_CHUNKS, vectors)
    }

    embeddings_file.write_text(
        json.dumps(
            {
                "model": settings.openai_embedding_model,
                "embeddings": _embedding_cache,
            },
            indent=2,
        ),
        encoding="utf-8",
    )

    return _embedding_cache


def cosine_similarity(left: List[float], right: List[float]) -> float:
    numerator = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if not left_norm or not right_norm:
        return 0.0
    return numerator / (left_norm * right_norm)
