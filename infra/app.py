#!/usr/bin/env python3
import os

import aws_cdk as cdk

from compliance_portal.compliance_portal_stack import CompliancePortalStack


app = cdk.App()
CompliancePortalStack(
    app,
    "CompliancePortalStack",
    env=cdk.Environment(
        account=os.getenv("CDK_DEFAULT_ACCOUNT"),
        region=os.getenv("CDK_DEFAULT_REGION"),
    ),
)

app.synth()
