"""DynamoDB access layer.

Table names come from environment variables set by CDK on the Lambda
functions, so the same code works in every deployed environment without
hardcoding table names. CRUD methods are implemented Day 2.
"""

import os

import boto3

_dynamodb = boto3.resource("dynamodb")

SUBCONTRACTORS_TABLE = os.environ.get("SUBCONTRACTORS_TABLE_NAME", "")
COMPLIANCE_DOCUMENTS_TABLE = os.environ.get("COMPLIANCE_DOCUMENTS_TABLE_NAME", "")


class SubcontractorRepository:
    def __init__(self):
        self._table = _dynamodb.Table(SUBCONTRACTORS_TABLE)


class ComplianceDocumentRepository:
    def __init__(self):
        self._table = _dynamodb.Table(COMPLIANCE_DOCUMENTS_TABLE)
