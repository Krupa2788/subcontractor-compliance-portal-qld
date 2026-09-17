"""Shared request parsing and response building for API Gateway handlers."""

import json
from decimal import Decimal

CORS_HEADERS = {
    "Content-Type": "application/json",
    "Access-Control-Allow-Origin": "*",
}


class _DecimalEncoder(json.JSONEncoder):
    """DynamoDB returns every number as Decimal, which json cannot serialize."""

    def default(self, o):
        if isinstance(o, Decimal):
            return int(o) if o % 1 == 0 else float(o)
        return super().default(o)


def json_response(status_code, body=None):
    response = {"statusCode": status_code, "headers": CORS_HEADERS}
    if body is not None:
        response["body"] = json.dumps(body, cls=_DecimalEncoder)
    return response


def error_response(status_code, message):
    return json_response(status_code, {"message": message})


def parse_body(event):
    raw = event.get("body")
    if not raw:
        return {}
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        raise ValueError("Request body must be valid JSON")


def path_param(event, name):
    return (event.get("pathParameters") or {}).get(name)
