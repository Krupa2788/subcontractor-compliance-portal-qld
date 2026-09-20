"""Structured logging.

CloudWatch stores whatever a Lambda prints, but only JSON is queryable —
Logs Insights can filter on `status = 403` or `durationMs > 500` when the
fields are real fields rather than words inside a sentence.

Hand-rolled rather than pulled from a library, because the Lambda deployment
package has no third-party dependencies and this is a small amount of code.
"""

import json
import logging
import time
from functools import wraps


class JsonFormatter(logging.Formatter):
    def format(self, record):
        payload = {
            "level": record.levelname,
            "message": record.getMessage(),
        }
        # Anything passed as extra={"context": {...}} becomes top-level fields,
        # which is what makes them queryable in Logs Insights.
        payload.update(getattr(record, "context", None) or {})
        if record.exc_info:
            payload["exception"] = self.formatException(record.exc_info)
        return json.dumps(payload, default=str)


def get_logger():
    logger = logging.getLogger()
    logger.setLevel(logging.INFO)
    # The Lambda runtime installs its own handler before any of our code runs,
    # so reformat that one rather than adding a second and logging twice.
    for handler in logger.handlers:
        handler.setFormatter(JsonFormatter())
    if not logger.handlers:
        handler = logging.StreamHandler()
        handler.setFormatter(JsonFormatter())
        logger.addHandler(handler)
    return logger


logger = get_logger()


def _caller_fields(event):
    """Who made this request. In a compliance system the audit trail matters
    as much as the debugging: a refusal should record who was refused."""
    claims = (
        (event.get("requestContext") or {}).get("authorizer") or {}
    ).get("claims") or {}
    groups = claims.get("cognito:groups") or []
    if isinstance(groups, str):
        groups = groups.strip("[]").replace(",", " ").split()
    return {
        "userId": claims.get("sub"),
        "userEmail": claims.get("email"),
        "userGroups": groups or None,
    }


def observed(handler):
    """Log one structured line per request, whatever the outcome."""

    @wraps(handler)
    def wrapper(event, context):
        started = time.perf_counter()
        fields = {
            "requestId": getattr(context, "aws_request_id", None),
            "method": event.get("httpMethod"),
            # The route template, not the concrete path, so log queries group
            # by endpoint instead of scattering across every record id.
            "route": event.get("resource"),
            **_caller_fields(event),
        }

        try:
            response = handler(event, context)
        except Exception:
            fields["durationMs"] = round((time.perf_counter() - started) * 1000, 1)
            fields["status"] = 500
            logger.exception("request failed", extra={"context": fields})
            raise

        fields["durationMs"] = round((time.perf_counter() - started) * 1000, 1)
        fields["status"] = response.get("statusCode")
        logger.info("request", extra={"context": fields})
        return response

    return wrapper
