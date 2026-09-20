from aws_cdk import CfnOutput, Stack, aws_iam as iam
from constructs import Construct

GITHUB_OIDC_URL = "https://token.actions.githubusercontent.com"

# CDK's bootstrap stack provisions these; a deployment assumes them rather than
# holding the underlying permissions itself.
CDK_BOOTSTRAP_QUALIFIER = "hnb659fds"


class CicdStack(Stack):
    """Lets GitHub Actions deploy without any long-lived AWS credentials.

    Kept separate from the application stack on purpose: the OIDC provider is
    account-wide identity infrastructure, and tearing down the app should not
    take the ability to deploy it with it.
    """

    def __init__(self, scope: Construct, construct_id: str, repository: str, **kwargs):
        super().__init__(scope, construct_id, **kwargs)

        provider = iam.OpenIdConnectProvider(
            self,
            "GitHubOidcProvider",
            url=GITHUB_OIDC_URL,
            client_ids=["sts.amazonaws.com"],
        )

        deploy_role = iam.Role(
            self,
            "GitHubDeployRole",
            role_name="github-actions-compliance-portal-deploy",
            assumed_by=iam.WebIdentityPrincipal(
                provider.open_id_connect_provider_arn,
                {
                    "StringEquals": {
                        "token.actions.githubusercontent.com:aud": "sts.amazonaws.com",
                    },
                    # Scoped to this repository. Without this condition any
                    # GitHub repository in the world could assume the role.
                    "StringLike": {
                        "token.actions.githubusercontent.com:sub": f"repo:{repository}:*",
                    },
                },
            ),
        )

        # The role itself can do nothing but step into CDK's own bootstrap
        # roles, which is where the real deployment permissions live.
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["sts:AssumeRole"],
                resources=[
                    f"arn:aws:iam::{self.account}:role/cdk-{CDK_BOOTSTRAP_QUALIFIER}-*"
                ],
            )
        )
        # cdk deploy reads the bootstrap version from SSM before it starts.
        deploy_role.add_to_policy(
            iam.PolicyStatement(
                actions=["ssm:GetParameter"],
                resources=[
                    f"arn:aws:ssm:{self.region}:{self.account}:parameter/cdk-bootstrap/*"
                ],
            )
        )

        CfnOutput(self, "DeployRoleArn", value=deploy_role.role_arn)
