from aws_cdk import (
    CfnOutput,
    Duration,
    RemovalPolicy,
    Stack,
    aws_apigateway as apigateway,
    aws_cognito as cognito,
    aws_dynamodb as dynamodb,
    aws_events as events,
    aws_events_targets as targets,
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
            # The 3s default is not enough for a cold start that also has to
            # initialise boto3 and make its first DynamoDB call. Lambda scales
            # CPU with memory, so 512MB is both faster to start and cheaper
            # per request than 128MB despite the higher per-ms rate.
            timeout=Duration.seconds(15),
            memory_size=512,
        )

        health_fn = _lambda.Function(
            self,
            "HealthFunction",
            handler="handlers.health.handler",
            **common_lambda_kwargs,
        )

        both_tables_env = {
            "SUBCONTRACTORS_TABLE_NAME": subcontractors_table.table_name,
            "COMPLIANCE_DOCUMENTS_TABLE_NAME": compliance_documents_table.table_name,
        }

        subcontractors_fn = _lambda.Function(
            self,
            "SubcontractorsFunction",
            handler="handlers.subcontractors.handler",
            environment=both_tables_env,
            **common_lambda_kwargs,
        )
        subcontractors_table.grant_read_write_data(subcontractors_fn)
        # Needed to cascade-delete a subcontractor's documents: DynamoDB has
        # no foreign keys, so nothing else would clean up the orphans.
        compliance_documents_table.grant_read_write_data(subcontractors_fn)

        compliance_documents_fn = _lambda.Function(
            self,
            "ComplianceDocumentsFunction",
            handler="handlers.compliance_documents.handler",
            environment=both_tables_env,
            **common_lambda_kwargs,
        )
        compliance_documents_table.grant_read_write_data(compliance_documents_fn)
        # Write (not just read) because every document change re-derives and
        # persists the subcontractor's denormalized complianceStatus.
        subcontractors_table.grant_read_write_data(compliance_documents_fn)

        # Compliance status is stored on the subcontractor record, so it would
        # drift out of date as certificates lapse with no write to trigger a
        # recalculation. This runs daily to re-derive every status.
        recompute_status_fn = _lambda.Function(
            self,
            "RecomputeStatusFunction",
            handler="handlers.recompute_status.handler",
            environment=both_tables_env,
            # Longer than the API functions: this one walks every
            # subcontractor rather than serving a single request.
            **{**common_lambda_kwargs, "timeout": Duration.minutes(5)},
        )
        subcontractors_table.grant_read_write_data(recompute_status_fn)
        compliance_documents_table.grant_read_data(recompute_status_fn)

        events.Rule(
            self,
            "DailyStatusRecompute",
            # EventBridge cron is always UTC. 14:00 UTC is midnight in
            # Brisbane (UTC+10, no daylight saving), so statuses roll over
            # at the start of the local business day.
            schedule=events.Schedule.cron(hour="14", minute="0"),
            targets=[targets.LambdaFunction(recompute_status_fn)],
        )

        # Cognito user pool. Self sign-up is disabled: this is a staff and
        # engaged-subcontractor tool, so accounts are issued, not requested.
        user_pool = cognito.UserPool(
            self,
            "UserPool",
            self_sign_up_enabled=False,
            sign_in_aliases=cognito.SignInAliases(email=True),
            standard_attributes=cognito.StandardAttributes(
                email=cognito.StandardAttribute(required=True, mutable=False),
            ),
            custom_attributes={
                # Binds a subcontractor login to the record it may act on. It
                # travels in the JWT, so a request carries its own scope and
                # the Lambda needs no extra lookup to know what the caller owns.
                "subcontractorId": cognito.StringAttribute(mutable=True),
            },
            password_policy=cognito.PasswordPolicy(min_length=12),
            account_recovery=cognito.AccountRecovery.EMAIL_ONLY,
            removal_policy=RemovalPolicy.DESTROY,
        )

        user_pool_client = user_pool.add_client(
            "WebClient",
            auth_flows=cognito.AuthFlow(
                # SRP is what the browser uses: the password is proved, never
                # sent. admin_user_password is for server-side scripts and
                # smoke tests — it is an IAM-authenticated API, so enabling it
                # widens nothing for an anonymous attacker. Plain
                # user_password auth stays off: that one would accept a raw
                # password from anyone holding the public client id.
                user_srp=True,
                admin_user_password=True,
            ),
            # A browser SPA cannot keep a secret, so it does not get one.
            generate_secret=False,
            access_token_validity=Duration.hours(1),
            id_token_validity=Duration.hours(1),
            refresh_token_validity=Duration.days(30),
        )

        # Authorization is group-based. The groups live in Cognito so they
        # arrive as a cognito:groups claim the API can trust.
        cognito.CfnUserPoolGroup(
            self,
            "ComplianceOfficerGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="ComplianceOfficer",
            description="Oversees every subcontractor's compliance.",
        )
        cognito.CfnUserPoolGroup(
            self,
            "SubcontractorGroup",
            user_pool_id=user_pool.user_pool_id,
            group_name="Subcontractor",
            description="Manages only their own compliance documents.",
        )

        # API Gateway REST API, wired to match openapi.yaml's paths.
        api = apigateway.RestApi(
            self,
            "ComplianceApi",
            default_cors_preflight_options=apigateway.CorsOptions(
                allow_origins=apigateway.Cors.ALL_ORIGINS,
                allow_methods=apigateway.Cors.ALL_METHODS,
                allow_headers=[*apigateway.Cors.DEFAULT_HEADERS, "Authorization"],
            ),
        )

        # A rejected request is generated by API Gateway itself, before any
        # integration runs, so it carries no CORS headers unless we add them.
        # Without this the browser reports an opaque CORS failure and hides
        # the 401 that actually happened.
        for name, response_type in (
            ("Unauthorized", apigateway.ResponseType.UNAUTHORIZED),
            ("AccessDenied", apigateway.ResponseType.ACCESS_DENIED),
        ):
            api.add_gateway_response(
                name,
                type=response_type,
                response_headers={
                    "Access-Control-Allow-Origin": "'*'",
                    "Access-Control-Allow-Headers": "'*'",
                },
            )

        authorizer = apigateway.CognitoUserPoolsAuthorizer(
            self,
            "ApiAuthorizer",
            cognito_user_pools=[user_pool],
        )

        # Applied to every business method below. /health stays open so it can
        # be used as an unauthenticated liveness check.
        authed = {
            "authorizer": authorizer,
            "authorization_type": apigateway.AuthorizationType.COGNITO,
        }

        health = api.root.add_resource("health")
        health.add_method("GET", apigateway.LambdaIntegration(health_fn))

        subcontractors_integration = apigateway.LambdaIntegration(subcontractors_fn)
        documents_integration = apigateway.LambdaIntegration(compliance_documents_fn)

        subcontractors = api.root.add_resource("subcontractors")
        subcontractors.add_method("GET", subcontractors_integration, **authed)
        subcontractors.add_method("POST", subcontractors_integration, **authed)

        subcontractor = subcontractors.add_resource("{subcontractorId}")
        subcontractor.add_method("GET", subcontractors_integration, **authed)
        subcontractor.add_method("PUT", subcontractors_integration, **authed)
        subcontractor.add_method("DELETE", subcontractors_integration, **authed)

        subcontractor_documents = subcontractor.add_resource("documents")
        subcontractor_documents.add_method("GET", documents_integration, **authed)
        subcontractor_documents.add_method("POST", documents_integration, **authed)

        documents = api.root.add_resource("documents")
        document = documents.add_resource("{documentId}")
        document.add_method("GET", documents_integration, **authed)
        document.add_method("PUT", documents_integration, **authed)
        document.add_method("DELETE", documents_integration, **authed)

        # The SPA needs these to talk to Cognito.
        CfnOutput(self, "UserPoolId", value=user_pool.user_pool_id)
        CfnOutput(self, "UserPoolClientId", value=user_pool_client.user_pool_client_id)
