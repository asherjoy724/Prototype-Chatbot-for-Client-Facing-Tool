from typing import List, Optional

from pydantic import BaseModel, Field


class FieldRecord(BaseModel):
    field_id: str
    label: str
    key: str
    required: bool
    type: str
    description: str
    format_rules: List[str] = Field(default_factory=list)
    allowed_values: List[str] = Field(default_factory=list)
    example_value: Optional[str] = None
    common_mistakes: List[str] = Field(default_factory=list)


class SectionRecord(BaseModel):
    section_id: str
    title: str
    description: str
    fields: List[FieldRecord]


class FaqRecord(BaseModel):
    faq_id: str
    question: str
    answer: str
    related_field_ids: List[str] = Field(default_factory=list)


class TemplateRecord(BaseModel):
    template_id: str
    name: str
    version: str
    sections: List[SectionRecord]
    faqs: List[FaqRecord]


class Citation(BaseModel):
    type: str
    label: str


class AssistantSuggestion(BaseModel):
    label: str
    message: str


class AssistantChecklistItem(BaseModel):
    label: str
    status: str


class AssistantFieldSummary(BaseModel):
    field_id: str
    label: str
    section_title: str
    required: bool
    description: str


class AssistantSectionSummary(BaseModel):
    section_id: str
    title: str
    description: str


class ChatMatchedContext(BaseModel):
    field_id: Optional[str] = None
    section_id: Optional[str] = None
    faq_ids: List[str] = Field(default_factory=list)


class ChatResponse(BaseModel):
    answer: str
    citations: List[Citation]
    matched_context: ChatMatchedContext
    intent: str
    title: str
    supporting_points: List[str] = Field(default_factory=list)
    suggestions: List[AssistantSuggestion] = Field(default_factory=list)
    checklist: List[AssistantChecklistItem] = Field(default_factory=list)
    related_fields: List[AssistantFieldSummary] = Field(default_factory=list)
    related_sections: List[AssistantSectionSummary] = Field(default_factory=list)
    session_id: Optional[str] = None


class ChatRequest(BaseModel):
    template_id: str
    message: str
    current_field_id: Optional[str] = None
    current_section_id: Optional[str] = None
    draft_value: Optional[str] = None
    session_id: Optional[str] = None


class ValidateFieldRequest(BaseModel):
    field_id: str
    value: Optional[str] = None


class ValidateFieldResponse(BaseModel):
    valid: bool
    error: Optional[str] = None
    citation: Optional[str] = None


class AssistantBootstrapResponse(BaseModel):
    welcome_title: str
    welcome_message: str
    suggestions: List[AssistantSuggestion]
    template_name: str
    template_version: str
    assistant_mode: str
    assistant_status: str
    embeddings_enabled: bool
