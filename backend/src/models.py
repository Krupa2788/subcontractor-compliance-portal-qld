"""Domain enums, validation, and compliance status derivation.

Deliberately free of AWS/boto3 imports so this logic can be unit-tested
without mocking anything.
"""

import re
from datetime import date, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum

EXPIRING_SOON_WINDOW_DAYS = 30


class Trade(StrEnum):
    BUILDER = "BUILDER"
    ELECTRICAL = "ELECTRICAL"
    PLUMBING = "PLUMBING"
    CARPENTRY = "CARPENTRY"
    PAINTING = "PAINTING"
    ROOFING = "ROOFING"
    TILING = "TILING"
    PLASTERING = "PLASTERING"
    CONCRETING = "CONCRETING"
    GENERAL = "GENERAL"


class DocType(StrEnum):
    QBCC_LICENCE = "QBCC_LICENCE"
    PUBLIC_LIABILITY_INSURANCE = "PUBLIC_LIABILITY_INSURANCE"
    WORKERS_COMPENSATION_INSURANCE = "WORKERS_COMPENSATION_INSURANCE"
    WHITE_CARD = "WHITE_CARD"
    PROFESSIONAL_INDEMNITY_INSURANCE = "PROFESSIONAL_INDEMNITY_INSURANCE"


class DocumentStatus(StrEnum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"


class ComplianceStatus(StrEnum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    MISSING_DOCS = "MISSING_DOCS"


# Required of every subcontractor regardless of trade. Professional indemnity
# is tracked but only applies to design/certification trades, so it is not here.
REQUIRED_DOC_TYPES = frozenset(
    {
        DocType.QBCC_LICENCE,
        DocType.PUBLIC_LIABILITY_INSURANCE,
        DocType.WORKERS_COMPENSATION_INSURANCE,
        DocType.WHITE_CARD,
    }
)

# A Queensland White Card does not expire once issued.
NON_EXPIRING_DOC_TYPES = frozenset({DocType.WHITE_CARD})

_SEVERITY = {
    DocumentStatus.VALID: 0,
    DocumentStatus.EXPIRING_SOON: 1,
    DocumentStatus.EXPIRED: 2,
}

_ABN_PATTERN = re.compile(r"^\d{11}$")


class ValidationError(Exception):
    """Raised when a request payload fails domain validation."""


def parse_date(value):
    if value is None or value == "":
        return None
    if isinstance(value, date):
        return value
    try:
        return date.fromisoformat(value)
    except (TypeError, ValueError):
        raise ValidationError(f"Invalid date '{value}', expected format YYYY-MM-DD")


def derive_document_status(expiration_date, today):
    """A document with no expiry is valid as soon as it is on file."""
    if expiration_date is None:
        return DocumentStatus.VALID
    if expiration_date < today:
        return DocumentStatus.EXPIRED
    if expiration_date <= today + timedelta(days=EXPIRING_SOON_WINDOW_DAYS):
        return DocumentStatus.EXPIRING_SOON
    return DocumentStatus.VALID


def derive_compliance_status(documents, today):
    """Roll a subcontractor's documents up into one overall status.

    Within a doc type the best status wins: holding a lapsed 2024 insurance
    cert alongside a current one is not a breach. Across doc types the worst
    status wins: one expired requirement makes the subcontractor non-compliant.
    """
    best_per_type = {}
    for document in documents:
        doc_type = document.get("docType")
        if doc_type not in REQUIRED_DOC_TYPES:
            continue
        status = derive_document_status(
            parse_date(document.get("expirationDate")), today
        )
        incumbent = best_per_type.get(doc_type)
        if incumbent is None or _SEVERITY[status] < _SEVERITY[incumbent]:
            best_per_type[doc_type] = status

    if REQUIRED_DOC_TYPES - best_per_type.keys():
        return ComplianceStatus.MISSING_DOCS

    worst = max(best_per_type.values(), key=lambda status: _SEVERITY[status])
    return ComplianceStatus(worst.value)


def _require_string(body, field):
    value = body.get(field)
    if not isinstance(value, str) or not value.strip():
        raise ValidationError(f"'{field}' is required")
    return value.strip()


def validate_subcontractor_input(body):
    """Validate a create/update payload and return cleaned attributes."""
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")

    abn = _require_string(body, "abn").replace(" ", "")
    if not _ABN_PATTERN.match(abn):
        raise ValidationError("'abn' must be 11 digits")

    trade = _require_string(body, "trade")
    if trade not in Trade.__members__:
        raise ValidationError(
            f"'trade' must be one of: {', '.join(sorted(Trade.__members__))}"
        )

    contact_email = _require_string(body, "contactEmail")
    if "@" not in contact_email:
        raise ValidationError("'contactEmail' must be a valid email address")

    return {
        "companyName": _require_string(body, "companyName"),
        "abn": abn,
        "trade": trade,
        "contactName": _require_string(body, "contactName"),
        "contactEmail": contact_email,
        "contactPhone": _require_string(body, "contactPhone"),
    }


def validate_document_input(body):
    """Validate a create/update payload and return cleaned attributes."""
    if not isinstance(body, dict):
        raise ValidationError("Request body must be a JSON object")

    doc_type = _require_string(body, "docType")
    if doc_type not in DocType.__members__:
        raise ValidationError(
            f"'docType' must be one of: {', '.join(sorted(DocType.__members__))}"
        )

    issue_date = parse_date(body.get("issueDate"))
    if issue_date is None:
        raise ValidationError("'issueDate' is required")

    expiration_date = parse_date(body.get("expirationDate"))
    if doc_type in NON_EXPIRING_DOC_TYPES:
        expiration_date = None
    elif expiration_date is None:
        raise ValidationError(f"'expirationDate' is required for {doc_type}")
    elif expiration_date < issue_date:
        raise ValidationError("'expirationDate' cannot be before 'issueDate'")

    cover_amount = body.get("coverAmount")
    if cover_amount is not None:
        # Decimal, not float: DynamoDB stores numbers at exact decimal
        # precision and boto3 rejects floats outright rather than silently
        # losing precision. str() first, or Decimal inherits the float's
        # binary rounding error.
        try:
            cover_amount = Decimal(str(cover_amount))
        except (TypeError, ValueError, InvalidOperation):
            raise ValidationError("'coverAmount' must be a number")
        if cover_amount < 0:
            raise ValidationError("'coverAmount' cannot be negative")

    notes = body.get("notes")
    if notes is not None and not isinstance(notes, str):
        raise ValidationError("'notes' must be a string")

    return {
        "docType": doc_type,
        "referenceNumber": _require_string(body, "referenceNumber"),
        "issuer": _require_string(body, "issuer"),
        "coverAmount": cover_amount,
        "issueDate": issue_date.isoformat(),
        "expirationDate": expiration_date.isoformat() if expiration_date else None,
        "notes": notes,
    }
