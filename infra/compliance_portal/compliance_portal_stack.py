from aws_cdk import (
    Stack,
    aws_apigateway as apigateway,
    aws_dynamodb as dynamodb,
    aws_lambda as _lambda,
)
from constructs import Construct


class CompliancePortalStack(Stack):
    def __init__(self, scope: Construct, construct_id: str, **kwargs) -> None:
        super().__init__(scope, construct_id, **kwargs)

        # DynamoDB tables. On-demand billing means we pay per request instead
        # of provisioning fixed capacity — the right choice for a low-traffic
        # demo app.
        subcontractors_table = dynamodb.Table(
            self,
            "SubcontractorsTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )

        compliance_documents_table = dynamodb.Table(
            self,
            "ComplianceDocumentsTable",
            partition_key=dynamodb.Attribute(
                name="id", type=dynamodb.AttributeType.STRING
            ),
            billing_mode=dynamodb.BillingMode.PAY_PER_REQUEST,
        )
        # GSI so we can look up "all documents for this subcontractor"
        # without scanning the whole table.
        compliance_documents_table.add_global_secondary_index(
            index_name="bySubcontractorId",
            partition_key=dynamodb.Attribute(
                name="subcontractorId", type=dynamodb.AttributeType.STRING
            ),
        )

        # Lambda functions. Each is packaged from backend/src, and only gets
        # env vars / IAM permissions for the tables it actually needs.
        common_lambda_kwargs = dict(
            runtime=_lambda.Runtime.PYTHON_3_13,
            code=_lambda.Code.from_asset("../backend/src"),
        )

        health_fn = _lambda.Function(
            self,
            "HealthFunction",
            handler="handlers.health.handler",
            **common_lambda_kwargs,
        )

        subcontractors_fn = _lambda.Function(
            self,
            "SubcontractorsFunction",
            handler="handlers.subcontractors.handler",
            environment={
                "SUBCONTRACTORS_TABLE_NAME": subcontractors_table.table_name,
            },
            **common_lambda_kwargs,
        )
        subcontractors_table.grant_read_write_data(subcontractors_fn)

        compliance_documents_fn = _lambda.Function(
            self,
            "ComplianceDocumentsFunction",
            handler="handlers.compliance_documents.handler",
            environment={
                "COMPLIANCE_DOCUMENTS_TABLE_NAME": compliance_documents_table.table_name,
                "SUBCONTRACTORS_TABLE_NAME": subcontractors_table.table_name,
            },
            **common_lambda_kwargs,
        )
        compliance_documents_table.grant_read_write_data(compliance_documents_fn)
        subcontractors_table.grant_read_data(compliance_documents_fn)

        # API Gateway REST API, wired to match openapi.yaml's paths.
        api = apigateway.RestApi(
            self,
            "ComplianceApi",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
            ),
        )

        health = api.root.add_resource("health")
        health.add_method("GET", apigateway.LambdaIntegration(health_fn))

        subcontractors = api.root.add_resource("subcontractors")
        subcontractors.add_method(
            "GET", apigateway.LambdaIntegration(subcontractors_fn)
        )
        subcontractors.add_method(
            "POST", apigateway.LambdaIntegration(subcontractors_fn)
        )

        subcontractor = subcontractors.add_resource("{subcontractorId}")
        subcontractor.add_method("GET", apigateway.LambdaIntegration(subcontractors_fn))
        subcontractor.add_method("PUT", apigateway.LambdaIntegration(subcontractors_fn))
        subcontractor.add_method(
            "DELETE", apigateway.LambdaIntegration(subcontractors_fn)
        )

        subcontractor_documents = subcontractor.add_resource("documents")
        subcontractor_documents.add_method(
            "GET", apigateway.LambdaIntegration(compliance_documents_fn)
        )
        subcontractor_documents.add_method(
            "POST", apigateway.LambdaIntegration(compliance_documents_fn)
        )

        documents = api.root.add_resource("documents")
        document = documents.add_resource("{documentId}")
        document.add_method("GET", apigateway.LambdaIntegration(compliance_documents_fn))
        document.add_method("PUT", apigateway.LambdaIntegration(compliance_documents_fn))
        document.add_method(
            "DELETE", apigateway.LambdaIntegration(compliance_documents_fn)
        )
