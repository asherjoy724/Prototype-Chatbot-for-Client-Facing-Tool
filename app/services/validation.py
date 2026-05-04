import re

from app.models import ValidateFieldRequest, ValidateFieldResponse
from app.services.template_service import find_field_by_id


def validate_field_value(payload: ValidateFieldRequest) -> ValidateFieldResponse:
    field = find_field_by_id(payload.field_id)

    if field is None:
        return ValidateFieldResponse(valid=False, error="Unknown field.")

    value = (payload.value or "").strip()

    if field.required and not value:
        return ValidateFieldResponse(
            valid=False,
            error=f"{field.label} is required.",
            citation=field.label,
        )

    if not value:
        return ValidateFieldResponse(valid=True, citation=field.label)

    if field.field_id in {"new-customers", "headcount"} and not re.fullmatch(r"\d+", value):
        return ValidateFieldResponse(
            valid=False,
            error=f"Use a whole number for {field.label.lower()}.",
            citation=field.label,
        )

    if field.field_id == "marketing-revenue" and not re.fullmatch(
        r"\d+(\.\d{1,2})?", value
    ):
        return ValidateFieldResponse(
            valid=False,
            error="Use digits only for marketing revenue, with an optional decimal point.",
            citation=field.label,
        )

    if field.allowed_values and value not in field.allowed_values:
        return ValidateFieldResponse(
            valid=False,
            error=f"Choose one approved option: {', '.join(field.allowed_values)}.",
            citation=field.label,
        )

    return ValidateFieldResponse(valid=True, citation=field.label)
