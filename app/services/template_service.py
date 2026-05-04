from typing import List, Optional

from app.data import template_record
from app.models import FieldRecord, SectionRecord, TemplateRecord


def get_template_schema(template_id: str) -> Optional[TemplateRecord]:
    if template_id != template_record.template_id:
        return None

    return template_record


def find_field_by_id(field_id: Optional[str]) -> Optional[FieldRecord]:
    if not field_id:
        return None

    for section in template_record.sections:
        for field in section.fields:
            if field.field_id == field_id:
                return field

    return None


def find_section_by_id(section_id: Optional[str]) -> Optional[SectionRecord]:
    if not section_id:
        return None

    for section in template_record.sections:
        if section.section_id == section_id:
            return section

    return None


def list_all_fields() -> List[FieldRecord]:
    fields: List[FieldRecord] = []
    for section in template_record.sections:
        fields.extend(section.fields)
    return fields
