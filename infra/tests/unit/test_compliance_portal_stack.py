import aws_cdk as core
import aws_cdk.assertions as assertions

from compliance_portal.compliance_portal_stack import CompliancePortalStack


def test_dynamodb_tables_created():
    app = core.App()
    stack = CompliancePortalStack(app, "CompliancePortalStack")
    template = assertions.Template.from_stack(stack)

    template.resource_count_is("AWS::DynamoDB::Table", 2)


def test_health_endpoint_created():
    app = core.App()
    stack = CompliancePortalStack(app, "CompliancePortalStack")
    template = assertions.Template.from_stack(stack)

    template.has_resource_properties(
        "AWS::ApiGateway::Method",
        {"HttpMethod": "GET", "ResourceId": {"Ref": assertions.Match.any_value()}},
    )
