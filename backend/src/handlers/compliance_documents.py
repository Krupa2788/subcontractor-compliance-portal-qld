import logging
from datetime import date

from http_helpers import error_response, json_response, parse_body, path_param
from models import (
    ValidationError,
    derive_compliance_status,
    derive_document_status,
    parse_date,
    validate_document_input,
)
from repository import ComplianceDocumentRepository, SubcontractorRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

subcontractors = SubcontractorRepository()
documents = ComplianceDocumentRepository()


def handler(event, context):
    method = event.get("httpMethod")
    subcontractor_id = path_param(event, "subcontractorId")
    document_id = path_param(event, "documentId")

    try:
        if subcontractor_id is not None:
            if method == "GET":
                return _list_for_subcontractor(subcontractor_id)
            if method == "POST":
                return _create(event, subcontractor_id)
        if document_id is not None:
            if method == "GET":
                return _get(document_id)
            if method == "PUT":
                return _update(event, document_id)
            if method == "DELETE":
                return _delete(document_id)
        return error_response(405, f"Method {method} not allowed")
    except ValidationError as exc:
        return error_response(400, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        logger.exception("Unhandled error in compliance documents handler")
        return error_response(500, "Internal server error")


def _with_status(document):
    """Individual document status stays derived at read time — it is cheap,
    and unlike the subcontractor rollup it needs no cross-table lookup."""
    return {
        **document,
        "status": derive_document_status(
            parse_date(document.get("expirationDate")), date.today()
        ).value,
    }


def _refresh_subcontractor_status(subcontractor_id):
    """Re-derive and persist the subcontractor's denormalized status.

    Called after every write, because the stored status on the subcontractor
    record is only as correct as the last thing that recomputed it.
    """
    status = derive_compliance_status(
        documents.list_by_subcontractor(subcontractor_id), date.today()
    )
    subcontractors.set_compliance_status(subcontractor_id, status.value)


def _list_for_subcontractor(subcontractor_id):
    if subcontractors.get(subcontractor_id) is None:
        return error_response(404, "Subcontractor not found")
    items = documents.list_by_subcontractor(subcontractor_id)
    return json_response(200, [_with_status(item) for item in items])


def _get(document_id):
    document = documents.get(document_id)
    if document is None:
        return error_response(404, "Compliance document not found")
    return json_response(200, _with_status(document))


def _create(event, subcontractor_id):
    if subcontractors.get(subcontractor_id) is None:
        return error_response(404, "Subcontractor not found")

    attributes = validate_document_input(parse_body(event))
    created = documents.create(subcontractor_id, attributes)
    _refresh_subcontractor_status(subcontractor_id)
    return json_response(201, _with_status(created))


def _update(event, document_id):
    existing = documents.get(document_id)
    if existing is None:
        return error_response(404, "Compliance document not found")

    attributes = validate_document_input(parse_body(event))
    updated = documents.update(existing, attributes)
    _refresh_subcontractor_status(existing["subcontractorId"])
    return json_response(200, _with_status(updated))


def _delete(document_id):
    existing = documents.get(document_id)
    if existing is None:
        return error_response(404, "Compliance document not found")

    documents.delete(document_id)
    _refresh_subcontractor_status(existing["subcontractorId"])
    return json_response(204)
