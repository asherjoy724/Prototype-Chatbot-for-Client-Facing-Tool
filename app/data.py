from app.models import FaqRecord, FieldRecord, SectionRecord, TemplateRecord


template_record = TemplateRecord(
    template_id="client-intake-v1",
    name="Client Intake Template",
    version="2026.05",
    sections=[
        SectionRecord(
            section_id="company-information",
            title="Company Information",
            description="Core company attributes that define which part of the business the submitted data applies to.",
            fields=[
                FieldRecord(
                    field_id="business-unit",
                    label="Business Unit",
                    key="businessUnit",
                    required=True,
                    type="text",
                    description=(
                        "Enter the business unit to which the data applies. If the data applies "
                        "to all business units, enter 'All'."
                    ),
                    format_rules=[
                        "Use the business unit name exactly as it is recognized internally.",
                        "If selecting all business units, type 'All'.",
                    ],
                    example_value="All",
                    common_mistakes=[
                        "Leaving the field blank when the data applies to every business unit."
                    ],
                ),
                FieldRecord(
                    field_id="geography",
                    label="Geography",
                    key="geography",
                    required=True,
                    type="text",
                    description=(
                        "Enter the primary geography to which the data applies. If the data "
                        "cannot be separated by geography, use the geography that represents "
                        "more than 75% of the data being entered."
                    ),
                    format_rules=[
                        "Use the primary geography for the data set.",
                        "If the data spans multiple geographies, choose the geography that comprises more than 75% of the data.",
                    ],
                    example_value="North America",
                    common_mistakes=[
                        "Choosing a minor geography that represents only a small share of the data."
                    ],
                ),
            ],
        ),
        SectionRecord(
            section_id="marketing-design",
            title="Marketing Design",
            description="Marketing performance metrics tied to a distinct traffic source.",
            fields=[
                FieldRecord(
                    field_id="marketing-revenue",
                    label="Marketing Revenue",
                    key="marketingRevenue",
                    required=True,
                    type="currency",
                    description=(
                        "Enter the revenue that is attributed to a distinct traffic source."
                    ),
                    format_rules=[
                        "Use digits only, with an optional decimal point.",
                        "Do not include commas or a currency symbol."
                    ],
                    example_value="250000.00",
                    common_mistakes=[
                        "Including revenue that cannot be tied to a distinct traffic source."
                    ],
                ),
                FieldRecord(
                    field_id="new-customers",
                    label="New Customers",
                    key="newCustomers",
                    required=True,
                    type="number",
                    description=(
                        "Enter the number of new customers purchased in the past 12 months. "
                        "Do not include customers who were customers before that 12-month period."
                    ),
                    format_rules=["Use a whole number with no commas or extra text."],
                    example_value="480",
                    common_mistakes=["Counting returning customers as new customers."],
                ),
            ],
        ),
        SectionRecord(
            section_id="role-design",
            title="Role Design",
            description="Organization-wide staffing information excluding marketing-specific personnel.",
            fields=[
                FieldRecord(
                    field_id="headcount",
                    label="Headcount",
                    key="headcount",
                    required=True,
                    type="number",
                    description=(
                        "Enter the number of all individuals in the organization. Do not "
                        "include marketing individuals."
                    ),
                    format_rules=["Use a whole number with no commas or extra text."],
                    example_value="1320",
                    common_mistakes=["Including marketing personnel in the role-design headcount."],
                ),
            ],
        ),
    ],
    faqs=[
        FaqRecord(
            faq_id="faq-business-unit",
            question="What should I enter for business unit?",
            answer=(
                "Use the business unit the data applies to. If the data applies across all business units, enter 'All'."
            ),
            related_field_ids=["business-unit"],
        ),
        FaqRecord(
            faq_id="faq-geography",
            question="How do I choose the geography?",
            answer=(
                "Use the primary geography for the data. If the data cannot be split cleanly, choose the geography that represents more than 75% of it."
            ),
            related_field_ids=["geography"],
        ),
        FaqRecord(
            faq_id="faq-new-customers",
            question="Who counts as a new customer?",
            answer=(
                "Only count customers acquired in the last 12 months. Do not include people who were customers before that period and returned."
            ),
            related_field_ids=["new-customers"],
        ),
        FaqRecord(
            faq_id="faq-headcount",
            question="Should marketing individuals be included in headcount?",
            answer=(
                "No. For the Role Design section, headcount should exclude marketing individuals."
            ),
            related_field_ids=["headcount"],
        ),
    ],
)
