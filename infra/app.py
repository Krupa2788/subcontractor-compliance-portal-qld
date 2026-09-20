#!/usr/bin/env python3
import os

import aws_cdk as cdk

from compliance_portal.cicd_stack import CicdStack
from compliance_portal.compliance_portal_stack import CompliancePortalStack


app = cdk.App()
env = cdk.Environment(
    account=os.getenv("CDK_DEFAULT_ACCOUNT"),
    region=os.getenv("CDK_DEFAULT_REGION"),
)
CompliancePortalStack(app, "CompliancePortalStack", env=env)

# Deployed once by hand; CI then assumes the role it creates.
CicdStack(
    app,
    "CompliancePortalCicdStack",
    repository=app.node.try_get_context("githubRepository")
    or "Krupa2788/subcontractor-compliance-portal-qld",
    env=env,
)

app.synth()
