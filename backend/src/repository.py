"""DynamoDB access layer.

Table names come from environment variables set by CDK on the Lambda
functions, so the same code works in every deployed environment without
hardcoding table names.
"""

import os
import uuid
from datetime import datetime, timezone

import boto3
from boto3.dynamodb.conditions import Key

DOCUMENTS_BY_SUBCONTRACTOR_INDEX = "bySubcontractorId"


def _now():
    return datetime.now(timezone.utc).isoformat()


def _new_id():
    return str(uuid.uuid4())


def _table(env_var):
    # Resolved lazily so importing this module never requires AWS config,
    # which keeps unit tests fast and offline.
    return boto3.resource("dynamodb").Table(os.environ[env_var])


class SubcontractorRepository:
    @property
    def _tbl(self):
        return _table("SUBCONTRACTORS_TABLE_NAME")

    def list(self):
        items = []
        kwargs = {}
        while True:
            response = self._tbl.scan(**kwargs)
            items.extend(response.get("Items", []))
            last_key = response.get("LastEvaluatedKey")
            if not last_key:
                return items
            kwargs["ExclusiveStartKey"] = last_key

    def get(self, subcontractor_id):
        return self._tbl.get_item(Key={"id": subcontractor_id}).get("Item")

    def create(self, attributes, compliance_status):
        timestamp = _now()
        item = {
            "id": _new_id(),
            **attributes,
            "complianceStatus": compliance_status,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        self._tbl.put_item(Item=item)
        return item

    def update(self, existing, attributes):
        item = {
            **existing,
            **attributes,
            "updatedAt": _now(),
        }
        self._tbl.put_item(Item=item)
        return item

    def delete(self, subcontractor_id):
        self._tbl.delete_item(Key={"id": subcontractor_id})

    def set_compliance_status(self, subcontractor_id, compliance_status):
        """Write back the denormalized status without touching other fields."""
        self._tbl.update_item(
            Key={"id": subcontractor_id},
            UpdateExpression="SET complianceStatus = :s, updatedAt = :u",
            ExpressionAttributeValues={
                ":s": compliance_status,
                ":u": _now(),
            },
        )


class ComplianceDocumentRepository:
    @property
    def _tbl(self):
        return _table("COMPLIANCE_DOCUMENTS_TABLE_NAME")

    def list_by_subcontractor(self, subcontractor_id):
        response = self._tbl.query(
            IndexName=DOCUMENTS_BY_SUBCONTRACTOR_INDEX,
            KeyConditionExpression=Key("subcontractorId").eq(subcontractor_id),
        )
        return response.get("Items", [])

    def get(self, document_id):
        return self._tbl.get_item(Key={"id": document_id}).get("Item")

    def create(self, subcontractor_id, attributes):
        timestamp = _now()
        item = {
            "id": _new_id(),
            "subcontractorId": subcontractor_id,
            **attributes,
            "createdAt": timestamp,
            "updatedAt": timestamp,
        }
        self._tbl.put_item(Item=item)
        return item

    def update(self, existing, attributes):
        item = {
            **existing,
            **attributes,
            "updatedAt": _now(),
        }
        self._tbl.put_item(Item=item)
        return item

    def delete(self, document_id):
        self._tbl.delete_item(Key={"id": document_id})
