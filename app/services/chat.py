from typing import Any, Dict, Optional

from app.models import (
    AssistantChecklistItem,
    AssistantFieldSummary,
    AssistantSectionSummary,
    AssistantSuggestion,
    AssistantBootstrapResponse,
    ChatMatchedContext,
    ChatRequest,
    ChatResponse,
    Citation,
    ValidateFieldRequest,
)
from app.services.conversation import append_turn, render_recent_turns
from app.services.openai_service import generate_grounded_response, openai_available
from app.services.rag import render_rag_context, retrieve_rag_chunks
from app.services.retrieval import retrieve_context
from app.services.template_service import (
    find_field_by_id,
    find_section_by_id,
    list_all_fields,
)
from app.services.validation import validate_field_value
from app.settings import settings


def build_chat_response(payload: ChatRequest) -> ChatResponse:
    session_id = payload.session_id or "default-session"
    context = retrieve_context(
        message=payload.message,
        current_field_id=payload.current_field_id,
        current_section_id=payload.current_section_id,
    )
    target_section = context["primary_section"] or find_section_by_id(payload.current_section_id)
    target_field = context["primary_field"] or find_field_by_id(payload.current_field_id)
    intent = classify_intent(payload.message)
    help_mode = determine_help_mode(payload.message, target_field, target_section)
    ambiguity = detect_ambiguity(context, payload.message)

    if ambiguity is not None:
        response = build_clarification_response(
            ambiguity=ambiguity,
            session_id=session_id,
        )
        append_turn(session_id, "user", payload.message)
        append_turn(session_id, "assistant", response.answer)
        return response

    if help_mode == "section" and target_section is not None:
        response = build_section_help_response(
            payload=payload,
            target_section=target_section,
            context=context,
            session_id=session_id,
        )
        append_turn(session_id, "user", payload.message)
        append_turn(session_id, "assistant", response.answer)
        return response

    if target_field is None:
        return ChatResponse(
            answer=(
                "I can help with field questions like 'Is the company name field "
                "required?' and section questions like 'What goes in the marketing design section?'"
            ),
            citations=[],
            matched_context=ChatMatchedContext(),
            intent="general_help",
            title="",
            supporting_points=[],
            suggestions=[],
            checklist=[],
            related_fields=[],
            related_sections=[],
            session_id=session_id,
        )

    validation = None
    if payload.draft_value:
        validation = validate_field_value(
            ValidateFieldRequest(
                field_id=target_field.field_id,
                value=payload.draft_value,
            )
        )

    if openai_available():
        llm_response = try_llm_chat_response(payload, target_field, context, validation)
        if llm_response is not None:
            append_turn(session_id, "user", payload.message)
            append_turn(session_id, "assistant", llm_response.answer)
            return llm_response

    faqs = context["faqs"]
    primary_section = context["primary_section"]

    response = ChatResponse(
        answer=compose_primary_answer(target_field, intent, validation),
        citations=[],
        matched_context=ChatMatchedContext(
            field_id=target_field.field_id,
            section_id=primary_section.section_id if primary_section else None,
            faq_ids=[faq.faq_id for faq in faqs],
        ),
        intent=intent,
        title="",
        supporting_points=[],
        suggestions=[],
        checklist=[],
        related_fields=[],
        related_sections=[],
        session_id=session_id,
    )
    append_turn(session_id, "user", payload.message)
    append_turn(session_id, "assistant", response.answer)
    return response


def build_bootstrap_response() -> AssistantBootstrapResponse:
    return AssistantBootstrapResponse(
        welcome_title="Template Assistant",
        welcome_message=(
            "Ask about any field or section in the standard template. I can explain "
            "what a field means, whether it is required, what belongs in a section, "
            "or whether a draft answer looks valid."
        ),
        suggestions=build_global_suggestions(),
        template_name="Client Intake Template",
        template_version="2026.05",
        assistant_mode="openai_rag" if settings.llm_enabled else "rule_based",
        assistant_status=(
            f"OpenAI RAG enabled with {settings.openai_model}"
            if settings.llm_enabled
            else "Using local rule-based fallback until OPENAI_API_KEY is configured"
        ),
        embeddings_enabled=settings.embeddings_enabled,
    )


def classify_intent(message: str) -> str:
    normalized = message.lower()
    if "section" in normalized:
        return "section_help"
    if any(token in normalized for token in ["required", "optional", "need to fill"]):
        return "requirement_check"
    if any(token in normalized for token in ["format", "formatted", "pattern"]):
        return "format_help"
    if any(token in normalized for token in ["example", "sample"]):
        return "example_request"
    if any(token in normalized for token in ["what is", "what does", "mean", "enter"]):
        return "field_explanation"
    if any(token in normalized for token in ["missing", "wrong", "valid", "check"]):
        return "validation_help"
    return "field_guidance"


def determine_help_mode(message: str, target_field, target_section) -> str:
    normalized = message.lower()
    if "section" in normalized and target_section is not None:
        return "section"
    if target_field is None and target_section is not None:
        return "section"
    return "field"


def compose_primary_answer(target_field, intent: str, validation):
    if intent == "requirement_check":
        requirement = "required" if target_field.required else "optional"
        return f"{target_field.label} is {requirement}."

    if intent == "format_help":
        if target_field.format_rules:
            return f"{' '.join(target_field.format_rules)}"
        return "There is no specific format listed."

    if intent == "example_request" and target_field.example_value:
        return f"{target_field.example_value}"

    if intent == "validation_help" and validation and validation.error:
        return validation.error

    if intent == "validation_help" and validation:
        return "Yes, that looks valid."

    return target_field.description


def build_supporting_points(target_field, validation, faqs):
    points = []

    if target_field.example_value:
        points.append(f"Example value: {target_field.example_value}")

    if target_field.allowed_values:
        points.append(f"Approved values: {', '.join(target_field.allowed_values)}")

    if validation and validation.error:
        points.append(f"Validation note: {validation.error}")

    return points[:5]


def build_checklist(target_field, validation):
    checklist = [
        AssistantChecklistItem(
            label="Identify the correct field value",
            status="ready",
        ),
        AssistantChecklistItem(
            label="Follow the required format",
            status="ready" if target_field.format_rules else "not_applicable",
        ),
    ]

    if validation and validation.error:
        checklist.append(
            AssistantChecklistItem(
                label="Current draft value passes validation",
                status="needs_attention",
            )
        )
    elif validation:
        checklist.append(
            AssistantChecklistItem(
                label="Current draft value passes validation",
                status="done",
            )
        )

    return checklist


def build_field_suggestions(target_field):
    prompts = [
        ("Is this required?", f"Is {target_field.label} required?"),
        ("Show an example", f"Show me an example for {target_field.label}."),
        ("Explain the format", f"What format should I use for {target_field.label}?"),
    ]

    if target_field.allowed_values:
        prompts.append(
            ("List approved values", f"What are the approved values for {target_field.label}?")
        )

    return [
        AssistantSuggestion(label=label, message=message)
        for label, message in prompts[:4]
    ]


def build_global_suggestions():
    return [
        AssistantSuggestion(
            label="Business unit help",
            message="What should I enter for the Business Unit field?",
        ),
        AssistantSuggestion(
            label="Role section help",
            message="What goes in the Role Design section?",
        ),
        AssistantSuggestion(
            label="Geography help",
            message="How do I choose the Geography field?",
        ),
        AssistantSuggestion(
            label="Marketing revenue format",
            message="How should I format Marketing Revenue?",
        ),
    ]


def build_related_fields(field_id: Optional[str]):
    summaries = []
    for field in list_all_fields():
        if field_id and field.field_id == field_id:
            continue
        section_title = infer_section_title(field.field_id)
        summaries.append(
            AssistantFieldSummary(
                field_id=field.field_id,
                label=field.label,
                section_title=section_title,
                required=field.required,
                description=field.description,
            )
        )

    return summaries[:3]


def infer_section_title(field_id: str) -> str:
    from app.data import template_record

    for section in template_record.sections:
        for field in section.fields:
            if field.field_id == field_id:
                return section.title
    return "Template"


def build_title(field_label: str, intent: str) -> str:
    if intent == "section_help":
        return f"{field_label} Section"
    if intent == "requirement_check":
        return f"{field_label} Requirement"
    if intent == "format_help":
        return f"{field_label} Format"
    if intent == "example_request":
        return f"{field_label} Example"
    if intent == "validation_help":
        return f"{field_label} Validation"
    return field_label


def build_section_help_response(payload, target_section, context, session_id: str) -> ChatResponse:
    answer = (
        target_section.description
    )

    return ChatResponse(
        answer=answer,
        citations=[],
        matched_context=ChatMatchedContext(
            field_id=None,
            section_id=target_section.section_id,
            faq_ids=[],
        ),
        intent="section_help",
        title="",
        supporting_points=[],
        suggestions=[],
        checklist=[],
        related_fields=[],
        related_sections=[],
        session_id=session_id,
    )


def build_section_suggestions(target_section):
    prompts = [
        AssistantSuggestion(
            label="What fields are here?",
            message=f"What fields are in the {target_section.title} section?",
        ),
        AssistantSuggestion(
            label="Which are required?",
            message=f"Which fields in the {target_section.title} section are required?",
        ),
    ]

    first_field = target_section.fields[0] if target_section.fields else None
    if first_field is not None:
        prompts.append(
            AssistantSuggestion(
                label="Explain first field",
                message=f"What should I enter for {first_field.label}?",
            )
        )

    return prompts


def build_related_sections():
    from app.data import template_record

    return [
        AssistantSectionSummary(
            section_id=section.section_id,
            title=section.title,
            description=section.description,
        )
        for section in template_record.sections[:3]
    ]


def detect_ambiguity(context, message: str):
    normalized = message.lower()
    field_candidates = context.get("field_candidates", [])
    section_candidates = context.get("section_candidates", [])

    top_field = field_candidates[0] if field_candidates else None
    second_field = field_candidates[1] if len(field_candidates) > 1 else None
    top_section = section_candidates[0] if section_candidates else None
    second_section = section_candidates[1] if len(section_candidates) > 1 else None

    if top_field and second_field and abs(top_field["score"] - second_field["score"]) <= 1:
        return {
            "kind": "field_vs_field",
            "field_candidates": field_candidates[:2],
        }

    if top_section and second_section and abs(top_section["score"] - second_section["score"]) <= 1:
        return {
            "kind": "section_vs_section",
            "section_candidates": section_candidates[:2],
        }

    if (
        "section" not in normalized
        and top_field
        and top_section
        and abs(top_field["score"] - top_section["score"]) <= 1
    ):
        return {
            "kind": "field_vs_section",
            "field_candidates": field_candidates[:1],
            "section_candidates": section_candidates[:1],
        }

    return None


def build_clarification_response(ambiguity, session_id: str) -> ChatResponse:
    suggestions = []
    related_fields = []
    related_sections = []

    if ambiguity["kind"] == "field_vs_field":
        for candidate in ambiguity["field_candidates"]:
            field = candidate["field"]
            section = candidate["section"]
            suggestions.append(
                AssistantSuggestion(
                    label=field.label,
                    message=f"What should I enter for {field.label}?",
                )
            )
            related_fields.append(
                AssistantFieldSummary(
                    field_id=field.field_id,
                    label=field.label,
                    section_title=section.title,
                    required=field.required,
                    description=field.description,
                )
            )

    elif ambiguity["kind"] == "section_vs_section":
        for candidate in ambiguity["section_candidates"]:
            section = candidate["section"]
            suggestions.append(
                AssistantSuggestion(
                    label=section.title,
                    message=f"What goes in the {section.title} section?",
                )
            )
            related_sections.append(
                AssistantSectionSummary(
                    section_id=section.section_id,
                    title=section.title,
                    description=section.description,
                )
            )

    elif ambiguity["kind"] == "field_vs_section":
        field_candidate = ambiguity["field_candidates"][0]
        section_candidate = ambiguity["section_candidates"][0]
        field = field_candidate["field"]
        field_section = field_candidate["section"]
        section = section_candidate["section"]

        suggestions.extend(
            [
                AssistantSuggestion(
                    label=f"{field.label} field",
                    message=f"What should I enter for {field.label}?",
                ),
                AssistantSuggestion(
                    label=f"{section.title} section",
                    message=f"What goes in the {section.title} section?",
                ),
            ]
        )
        related_fields.append(
            AssistantFieldSummary(
                field_id=field.field_id,
                label=field.label,
                section_title=field_section.title,
                required=field.required,
                description=field.description,
            )
        )
        related_sections.append(
            AssistantSectionSummary(
                section_id=section.section_id,
                title=section.title,
                description=section.description,
            )
        )

    return ChatResponse(
        answer=(
            "I want to make sure I guide the client to the right part of the template. "
            "Please choose the field or section you mean."
        ),
        citations=[],
        matched_context=ChatMatchedContext(),
        intent="clarification",
        title="",
        supporting_points=[],
        suggestions=[],
        checklist=[],
        related_fields=[],
        related_sections=[],
        session_id=session_id,
    )


def try_llm_chat_response(
    payload, target_field, context, validation
) -> Optional[ChatResponse]:
    rag_chunks = retrieve_rag_chunks(payload.message, target_field=target_field)
    prompt_context = render_rag_context(rag_chunks)
    conversation_context = render_recent_turns(payload.session_id or "default-session")

    if validation:
        prompt_context += (
            f"\n[VALIDATION] valid={validation.valid}; "
            f"error={validation.error or 'none'}; citation={validation.citation or 'none'}"
        )

    try:
        parsed = generate_grounded_response(
            payload=payload,
            prompt_context=prompt_context,
            conversation_context=conversation_context,
            output_schema=chat_output_schema(),
        )
    except Exception:
        return None

    primary_section = context["primary_section"]
    faqs = context["faqs"]
    return ChatResponse(
        answer=parsed["answer"],
        citations=[],
        matched_context=ChatMatchedContext(
            field_id=target_field.field_id,
            section_id=primary_section.section_id if primary_section else None,
            faq_ids=[faq.faq_id for faq in faqs],
        ),
        intent=parsed["intent"],
        title="",
        supporting_points=[],
        suggestions=[],
        checklist=[],
        related_fields=[],
        related_sections=[],
        session_id=payload.session_id or "default-session",
    )


def chat_output_schema() -> Dict[str, Any]:
    return {
        "type": "object",
        "properties": {
            "intent": {
                "type": "string",
                "enum": [
                    "field_explanation",
                    "requirement_check",
                    "format_help",
                    "example_request",
                    "validation_help",
                    "field_guidance",
                ],
            },
            "title": {"type": "string"},
            "answer": {"type": "string"},
            "supporting_points": {
                "type": "array",
                "items": {"type": "string"},
            },
        },
        "required": ["intent", "title", "answer", "supporting_points"],
        "additionalProperties": False,
    }


def dedupe_citations(citations):
    seen = set()
    unique = []
    for citation in citations:
        key = (citation.type, citation.label)
        if key in seen:
            continue
        seen.add(key)
        unique.append(citation)
    return unique
