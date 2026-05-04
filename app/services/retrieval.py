from typing import Dict, List, Optional

from app.data import template_record
from app.models import FaqRecord, FieldRecord, SectionRecord


def retrieve_context(
    message: str = "",
    current_field_id: Optional[str] = None,
    current_section_id: Optional[str] = None,
) -> Dict[str, object]:
    normalized_message = message.lower()
    field_matches: List[Dict[str, object]] = []
    section_matches: List[Dict[str, object]] = []

    for section in template_record.sections:
        section_text = " ".join([section.title, section.description]).lower()
        section_score = (
            _score_includes(normalized_message, section.title)
            + _score_includes(section_text, message)
            + _score_token_overlap(normalized_message, section.title)
            + (5 if section.section_id == current_section_id else 0)
            + (4 if "section" in normalized_message and _score_token_overlap(normalized_message, section.title) > 0 else 0)
        )

        if section_score > 0:
            section_matches.append(
                {
                    "score": section_score,
                    "section": section,
                }
            )

        for field in section.fields:
            field_text = " ".join(
                [field.label, field.key, field.description, *field.format_rules]
            ).lower()
            score = (
                _score_includes(normalized_message, field.label)
                + _score_includes(normalized_message, field.key)
                + _score_includes(field_text, message)
                + _score_token_overlap(normalized_message, field.label)
                + (5 if field.field_id == current_field_id else 0)
                + (2 if section.section_id == current_section_id else 0)
            )

            if score > 0:
                field_matches.append(
                    {
                        "score": score,
                        "section": section,
                        "field": field,
                    }
                )

    faq_matches = []
    for faq in template_record.faqs:
        score = (
            _score_includes(normalized_message, faq.question)
            + _score_includes(normalized_message, faq.answer)
            + (4 if current_field_id in faq.related_field_ids else 0)
        )
        if score > 0:
            faq_matches.append({"faq": faq, "score": score})

    field_matches.sort(key=lambda item: item["score"], reverse=True)
    section_matches.sort(key=lambda item: item["score"], reverse=True)
    faq_matches.sort(key=lambda item: item["score"], reverse=True)

    primary_field = field_matches[0]["field"] if field_matches else None
    primary_section = section_matches[0]["section"] if section_matches else None
    if primary_section is None and field_matches:
        primary_section = field_matches[0]["section"]
    faqs = [item["faq"] for item in faq_matches[:3]]

    return {
        "primary_field": primary_field,
        "primary_section": primary_section,
        "field_candidates": field_matches[:3],
        "section_matches": [item["section"] for item in section_matches[:3]],
        "section_candidates": section_matches[:3],
        "faqs": faqs,
    }


def _score_includes(haystack: str, needle: str) -> int:
    if not needle:
        return 0

    return 2 if needle.lower() in haystack else 0


def _score_token_overlap(message_text: str, label_text: str) -> int:
    message_tokens = _normalize_tokens(message_text)
    label_tokens = _normalize_tokens(label_text)
    overlap = message_tokens.intersection(label_tokens)
    return min(len(overlap) * 2, 6)


def _normalize_tokens(text: str) -> set:
    replacements = (
        text.lower()
        .replace("?", " ")
        .replace(",", " ")
        .replace("-", " ")
        .replace("_", " ")
    )
    raw_tokens = replacements.split()
    tokens = set()

    for token in raw_tokens:
        if len(token) < 3:
            continue
        tokens.add(token)
        if token.endswith("s") and len(token) > 4:
            tokens.add(token[:-1])

    return tokens
