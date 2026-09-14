import json

# Routes implemented Day 2: list/create/get/update/delete subcontractors,
# dispatched on event["httpMethod"] and event["pathParameters"].


def handler(event, context):
    return {
        "statusCode": 501,
        "headers": {"Content-Type": "application/json"},
        "body": json.dumps({"message": "Not implemented yet"}),
    }
