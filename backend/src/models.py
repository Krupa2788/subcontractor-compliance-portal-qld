"""Domain enums and status-derivation logic.

Mirrors the enums defined in openapi.yaml. Status derivation (the
EXPIRED / EXPIRING_SOON / VALID / MISSING_DOCS logic) is implemented Day 2.
"""

from enum import StrEnum


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


# Document types required of every subcontractor, regardless of trade.
REQUIRED_DOC_TYPES = frozenset(
    {
        DocType.QBCC_LICENCE,
        DocType.PUBLIC_LIABILITY_INSURANCE,
        DocType.WORKERS_COMPENSATION_INSURANCE,
        DocType.WHITE_CARD,
    }
)

# Document types that never expire once issued.
NON_EXPIRING_DOC_TYPES = frozenset({DocType.WHITE_CARD})


class DocumentStatus(StrEnum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"


class ComplianceStatus(StrEnum):
    VALID = "VALID"
    EXPIRING_SOON = "EXPIRING_SOON"
    EXPIRED = "EXPIRED"
    MISSING_DOCS = "MISSING_DOCS"
