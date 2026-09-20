from datetime import date

from auth import (
    AuthorizationError,
    caller_from_event,
    require_access_to,
    require_officer,
)
from http_helpers import error_response, json_response, parse_body, path_param
from models import (
    ValidationError,
    derive_compliance_status,
    validate_subcontractor_input,
)
from observability import logger, observed
from repository import ComplianceDocumentRepository, SubcontractorRepository

subcontractors = SubcontractorRepository()
documents = ComplianceDocumentRepository()


@observed
def handler(event, context):
    method = event.get("httpMethod")
    subcontractor_id = path_param(event, "subcontractorId")

    try:
        caller = caller_from_event(event)

        if method == "GET" and subcontractor_id is None:
            return _list(caller)
        if method == "POST" and subcontractor_id is None:
            return _create(event, caller)
        if method == "GET":
            return _get(subcontractor_id, caller)
        if method == "PUT":
            return _update(event, subcontractor_id, caller)
        if method == "DELETE":
            return _delete(subcontractor_id, caller)
        return error_response(405, f"Method {method} not allowed")
    except AuthorizationError as exc:
        return error_response(403, str(exc))
    except ValidationError as exc:
        return error_response(400, str(exc))
    except ValueError as exc:
        return error_response(400, str(exc))
    except Exception:
        # Log the detail for CloudWatch, return a generic message to the caller
        # so internal errors never leak stack traces to clients.
        logger.exception("Unhandled error in subcontractors handler")
        return error_response(500, "Internal server error")


def _list(caller):
    if caller.is_officer:
        return json_response(200, subcontractors.list())

    # A subcontractor gets a list of exactly themselves, so the client can use
    # one code path for both roles.
    if caller.subcontractor_id:
        own = subcontractors.get(caller.subcontractor_id)
        return json_response(200, [own] if own else [])

    return json_response(200, [])


def _get(subcontractor_id, caller):
    require_access_to(caller, subcontractor_id)
    item = subcontractors.get(subcontractor_id)
    if item is None:
        return error_response(404, "Subcontractor not found")
    return json_response(200, item)


def _create(event, caller):
    # Only officers onboard subcontractors; a subcontractor cannot create
    # further records for themselves or anyone else.
    require_officer(caller)
    attributes = validate_subcontractor_input(parse_body(event))
    # A brand new subcontractor has no documents on file yet.
    status = derive_compliance_status([], date.today())
    return json_response(201, subcontractors.create(attributes, status))


def _update(event, subcontractor_id, caller):
    require_access_to(caller, subcontractor_id)
    existing = subcontractors.get(subcontractor_id)
    if existing is None:
        return error_response(404, "Subcontractor not found")

    attributes = validate_subcontractor_input(parse_body(event))
    return json_response(200, subcontractors.update(existing, attributes))


def _delete(subcontractor_id, caller):
    require_officer(caller)
    if subcontractors.get(subcontractor_id) is None:
        return error_response(404, "Subcontractor not found")

    # Cascade: DynamoDB has no foreign keys, so orphaned documents would
    # linger forever unless we clean them up explicitly.
    for document in documents.list_by_subcontractor(subcontractor_id):
        documents.delete(document["id"])

    subcontractors.delete(subcontractor_id)
    return json_response(204)
