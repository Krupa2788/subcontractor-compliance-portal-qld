import logging
from datetime import date

from http_helpers import error_response, json_response, parse_body, path_param
from models import (
    ValidationError,
    derive_compliance_status,
    validate_subcontractor_input,
)
from repository import ComplianceDocumentRepository, SubcontractorRepository

logger = logging.getLogger()
logger.setLevel(logging.INFO)

subcontractors = SubcontractorRepository()
documents = ComplianceDocumentRepository()


def handler(event, context):
    method = event.get("httpMethod")
    subcontractor_id = path_param(event, "subcontractorId")

    try:
        if method == "GET" and subcontractor_id is None:
            return _list()
        if method == "POST" and subcontractor_id is None:
            return _create(event)
        if method == "GET":
            return _get(subcontractor_id)
        if method == "PUT":
            return _update(event, subcontractor_id)
        if method == "DELETE":
            return _delete(subcontractor_id)
        return error_response(405, f"Method {method} not allowed")
    except ValidationError as exc:
        return error_response(400, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        # Log the detail for CloudWatch, return a generic message to the caller
        # so internal errors never leak stack traces to clients.
        logger.exception("Unhandled error in subcontractors handler")
        return error_response(500, "Internal server error")


def _list():
    return json_response(200, subcontractors.list())


def _get(subcontractor_id):
    item = subcontractors.get(subcontractor_id)
    if item is None:
        return error_response(404, "Subcontractor not found")
    return json_response(200, item)


def _create(event):
    attributes = validate_subcontractor_input(parse_body(event))
    # A brand new subcontractor has no documents on file yet.
    status = derive_compliance_status([], date.today())
    return json_response(201, subcontractors.create(attributes, status))


def _update(event, subcontractor_id):
    existing = subcontractors.get(subcontractor_id)
    if existing is None:
        return error_response(404, "Subcontractor not found")

    attributes = validate_subcontractor_input(parse_body(event))
    return json_response(200, subcontractors.update(existing, attributes))


def _delete(subcontractor_id):
    if subcontractors.get(subcontractor_id) is None:
        return error_response(404, "Subcontractor not found")

    # Cascade: DynamoDB has no foreign keys, so orphaned documents would
    # linger forever unless we clean them up explicitly.
    for document in documents.list_by_subcontractor(subcontractor_id):
        documents.delete(document["id"])

    subcontractors.delete(subcontractor_id)
    return json_response(204)
