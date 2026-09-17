from datetime import date, timedelta
from decimal import Decimal

import pytest
from models import (
    ComplianceStatus,
    DocumentStatus,
    ValidationError,
    derive_compliance_status,
    derive_document_status,
    validate_document_input,
    validate_subcontractor_input,
)

TODAY = date(2026, 9, 17)


def _doc(doc_type, expiration_date):
    return {"docType": doc_type, "expirationDate": expiration_date}


def _all_required(expiration_date="2027-01-01"):
    return [
        _doc("QBCC_LICENCE", expiration_date),
        _doc("PUBLIC_LIABILITY_INSURANCE", expiration_date),
        _doc("WORKERS_COMPENSATION_INSURANCE", expiration_date),
        _doc("WHITE_CARD", None),
    ]


class TestDocumentStatus:
    def test_future_expiry_is_valid(self):
        assert (
            derive_document_status(TODAY + timedelta(days=90), TODAY)
            == DocumentStatus.VALID
        )

    def test_past_expiry_is_expired(self):
        assert (
            derive_document_status(TODAY - timedelta(days=1), TODAY)
            == DocumentStatus.EXPIRED
        )

    def test_expiry_within_30_days_is_expiring_soon(self):
        assert (
            derive_document_status(TODAY + timedelta(days=30), TODAY)
            == DocumentStatus.EXPIRING_SOON
        )

    def test_expiring_today_is_expiring_soon_not_expired(self):
        assert derive_document_status(TODAY, TODAY) == DocumentStatus.EXPIRING_SOON

    def test_day_31_is_still_valid(self):
        assert (
            derive_document_status(TODAY + timedelta(days=31), TODAY)
            == DocumentStatus.VALID
        )

    def test_white_card_has_no_expiry_and_is_always_valid(self):
        # A Queensland White Card does not expire once issued.
        assert derive_document_status(None, TODAY) == DocumentStatus.VALID


class TestComplianceStatus:
    def test_no_documents_is_missing_docs(self):
        assert derive_compliance_status([], TODAY) == ComplianceStatus.MISSING_DOCS

    def test_all_required_present_and_current_is_valid(self):
        assert derive_compliance_status(_all_required(), TODAY) == ComplianceStatus.VALID

    def test_one_missing_required_type_is_missing_docs(self):
        documents = _all_required()[:-1]  # drop the White Card
        assert (
            derive_compliance_status(documents, TODAY) == ComplianceStatus.MISSING_DOCS
        )

    def test_worst_status_across_types_wins(self):
        documents = _all_required()
        documents[1] = _doc("PUBLIC_LIABILITY_INSURANCE", "2026-01-01")
        assert derive_compliance_status(documents, TODAY) == ComplianceStatus.EXPIRED

    def test_expiring_soon_beats_valid_but_loses_to_expired(self):
        documents = _all_required()
        documents[0] = _doc("QBCC_LICENCE", (TODAY + timedelta(days=10)).isoformat())
        assert (
            derive_compliance_status(documents, TODAY) == ComplianceStatus.EXPIRING_SOON
        )

        documents[1] = _doc("PUBLIC_LIABILITY_INSURANCE", "2020-01-01")
        assert derive_compliance_status(documents, TODAY) == ComplianceStatus.EXPIRED

    def test_best_status_wins_within_a_single_type(self):
        # Holding a lapsed certificate alongside a current one is not a breach.
        documents = _all_required()
        documents.append(_doc("PUBLIC_LIABILITY_INSURANCE", "2020-01-01"))
        assert derive_compliance_status(documents, TODAY) == ComplianceStatus.VALID

    def test_professional_indemnity_is_ignored_in_rollup(self):
        documents = _all_required()
        documents.append(_doc("PROFESSIONAL_INDEMNITY_INSURANCE", "2020-01-01"))
        assert derive_compliance_status(documents, TODAY) == ComplianceStatus.VALID


class TestSubcontractorValidation:
    def _valid_payload(self, **overrides):
        return {
            "companyName": "Brisbane Sparkies Pty Ltd",
            "abn": "51824753556",
            "trade": "ELECTRICAL",
            "contactName": "Dana Nguyen",
            "contactEmail": "dana@example.com.au",
            "contactPhone": "0400 000 000",
            **overrides,
        }

    def test_accepts_valid_payload(self):
        assert validate_subcontractor_input(self._valid_payload())["abn"] == "51824753556"

    def test_strips_spaces_from_abn(self):
        cleaned = validate_subcontractor_input(self._valid_payload(abn="51 824 753 556"))
        assert cleaned["abn"] == "51824753556"

    @pytest.mark.parametrize("abn", ["1234567890", "123456789012", "abcdefghijk"])
    def test_rejects_malformed_abn(self, abn):
        with pytest.raises(ValidationError, match="11 digits"):
            validate_subcontractor_input(self._valid_payload(abn=abn))

    def test_rejects_unknown_trade(self):
        with pytest.raises(ValidationError, match="trade"):
            validate_subcontractor_input(self._valid_payload(trade="ASTRONAUT"))

    def test_rejects_missing_field(self):
        payload = self._valid_payload()
        del payload["companyName"]
        with pytest.raises(ValidationError, match="companyName"):
            validate_subcontractor_input(payload)


class TestDocumentValidation:
    def _valid_payload(self, **overrides):
        return {
            "docType": "PUBLIC_LIABILITY_INSURANCE",
            "referenceNumber": "POL-123456",
            "issuer": "Example Insurance Ltd",
            "coverAmount": 20000000,
            "issueDate": "2026-01-01",
            "expirationDate": "2027-01-01",
            **overrides,
        }

    def test_accepts_valid_payload(self):
        assert validate_document_input(self._valid_payload())["docType"] == (
            "PUBLIC_LIABILITY_INSURANCE"
        )

    def test_white_card_expiry_is_forced_to_none(self):
        cleaned = validate_document_input(
            self._valid_payload(docType="WHITE_CARD", expirationDate="2027-01-01")
        )
        assert cleaned["expirationDate"] is None

    def test_expiring_doc_type_requires_expiration_date(self):
        with pytest.raises(ValidationError, match="expirationDate"):
            validate_document_input(self._valid_payload(expirationDate=None))

    def test_rejects_expiry_before_issue(self):
        with pytest.raises(ValidationError, match="before"):
            validate_document_input(
                self._valid_payload(issueDate="2026-06-01", expirationDate="2026-01-01")
            )

    def test_rejects_unknown_doc_type(self):
        with pytest.raises(ValidationError, match="docType"):
            validate_document_input(self._valid_payload(docType="DRIVERS_LICENCE"))

    def test_cover_amount_becomes_decimal_not_float(self):
        # boto3 rejects floats outright when writing to DynamoDB.
        cleaned = validate_document_input(self._valid_payload(coverAmount=20000000))
        assert isinstance(cleaned["coverAmount"], Decimal)
        assert not isinstance(cleaned["coverAmount"], float)

    def test_fractional_cover_amount_keeps_exact_precision(self):
        cleaned = validate_document_input(self._valid_payload(coverAmount=1234.56))
        assert cleaned["coverAmount"] == Decimal("1234.56")

    def test_rejects_non_numeric_cover_amount(self):
        with pytest.raises(ValidationError, match="coverAmount"):
            validate_document_input(self._valid_payload(coverAmount="twenty million"))

    def test_rejects_negative_cover_amount(self):
        with pytest.raises(ValidationError, match="negative"):
            validate_document_input(self._valid_payload(coverAmount=-1))

    def test_rejects_malformed_date(self):
        with pytest.raises(ValidationError, match="Invalid date"):
            validate_document_input(self._valid_payload(issueDate="01/01/2026"))
