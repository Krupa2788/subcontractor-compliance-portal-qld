# Workflow

How this project is developed, shipped, and how a request actually moves
through it at runtime.

- [Local development](#local-development)
- [Commit, CI and deployment](#commit-ci-and-deployment)
- [Request lifecycle](#request-lifecycle)
- [Keeping compliance status honest](#keeping-compliance-status-honest)
- [Operating it](#operating-it)

---

## Local development

```bash
# Domain logic, validation, authorization rules — offline, no AWS
cd backend && .venv/Scripts/python -m pytest

# Infrastructure — assert the generated CloudFormation, then preview changes
cd infra && .venv/Scripts/python -m pytest
cdk diff

# Frontend — served locally, talking to the real deployed API
cd frontend && npm run dev          # http://localhost:5173

# Ship infrastructure and backend
cd infra && cdk deploy CompliancePortalStack
```

### The split that matters

Pure logic is tested **offline**; everything else is exercised against **real
AWS**. There is no local DynamoDB emulator, deliberately — one less environment
to drift out of sync with production.

That only works because `backend/src/models.py` and `backend/src/auth.py`
import no `boto3` and know nothing about AWS. They take plain dictionaries and
return plain values, which is why the whole suite runs in a fraction of a
second and needs no credentials.

The cost is that repository and handler behaviour is verified by deploying and
calling the real API, rather than by unit tests with mocks.

### Which loop to use

| Changing | Feedback loop |
| --- | --- |
| Status rules, validation, auth rules | `pytest` — instant |
| Resources, permissions, schedules | `cdk diff`, then `cdk deploy` |
| UI | `npm run dev` against the deployed API |
| Anything reaching DynamoDB | `cdk deploy`, then call the API |

---

## Commit, CI and deployment

Commits follow [Conventional Commits](https://www.conventionalcommits.org)
(`feat(api):`, `fix(web):`, `docs:`).

```
push to master
      │
      ├──► CI ─────────── backend tests
      │                   infrastructure tests
      │                   frontend lint, typecheck, build
      │
      └──► Deploy ─────── waits for every CI job to pass
                          OIDC → temporary AWS credentials
                          cdk deploy CompliancePortalStack
```

Pull requests run CI only. A push to `master` runs CI and, if it is green,
deploys.

### No AWS keys in GitHub

The deploy job presents its short-lived GitHub identity token to AWS STS and
receives temporary credentials in exchange. Nothing long-lived is stored.

Two properties keep that safe:

1. The IAM role's trust policy requires
   `token.actions.githubusercontent.com:sub` to match `repo:<owner>/<repo>:*`.
   **Without that condition, any GitHub repository could assume the role.**
2. The role grants no deployment permissions of its own. It may only
   `sts:AssumeRole` into CDK's bootstrap roles, so compromising it yields
   nothing directly.

### Serialised deploys

```yaml
concurrency:
  group: deploy-production
  cancel-in-progress: false
```

Two deploys racing into one CloudFormation stack will collide, so they queue.
In-flight runs are **not** cancelled — interrupting a deployment midway
through changing infrastructure is worse than making the next one wait.

### One-time setup

The deploy role lives in a separate stack, because an account-wide OIDC
provider should not disappear when the application stack does:

```bash
cd infra && cdk deploy CompliancePortalCicdStack
```

Take its `DeployRoleArn` output and set it as a repository **variable** named
`AWS_DEPLOY_ROLE_ARN` (Settings → Secrets and variables → Actions → Variables).

---

## Request lifecycle

```
Browser
  │   signs in once — SRP, so the password is proved, never transmitted
  │   Cognito returns a JWT; the SDK refreshes it silently from here on
  │
  ├── every request carries it: Authorization: <token>
  │
  v
API Gateway
  │   authorizer validates signature, expiry and issuer
  │   invalid or missing ──► 401, and the Lambda never runs
  v
Lambda
  │   caller_from_event()    role + custom:subcontractorId, read from claims
  │   require_access_to()    officer: anyone · subcontractor: only their own
  │                          otherwise ──► 403
  │   validate_*_input()     ABN shape, date order, enum membership
  │                          otherwise ──► 400
  v
DynamoDB
  │
  v
Response  ──►  one structured JSON log line: who, route, status, duration
```

### Three failure points, three status codes

| Code | Where | Meaning |
| --- | --- | --- |
| 401 | API Gateway | Not signed in, or the token is invalid/expired |
| 403 | Lambda | Signed in, but not permitted for this resource |
| 400 | Lambda | Permitted, but the payload is invalid |

A 403 is deliberately identical whether the record belongs to somebody else or
does not exist at all — otherwise the error message becomes a way to probe
which ids are real.

### Authorization is server-side

The UI hides controls a role cannot use, but that is presentation, not the
control. Every handler authorizes independently.

Documents are addressed by their own id (`/documents/{documentId}`), where the
owner does **not** appear in the URL. Those handlers load the record first and
authorize against *its* subcontractor — otherwise one tenant could reach
another's document by guessing an id.

---

## Keeping compliance status honest

`complianceStatus` is stored on the subcontractor record so the list view is a
single query rather than N+1. Stored derived state needs re-deriving, or it
quietly becomes a lie.

```
On write ──────  a document is added, edited or deleted
                    └──► re-derive that subcontractor's status, store it

On schedule ───  EventBridge, 14:00 UTC daily  (= midnight in Brisbane)
                    └──► walk every subcontractor
                         └──► re-derive, and write only where it changed
```

The scheduled sweep exists because **time passing changes compliance with no
write to trigger it.** A certificate lapsing overnight fires no event; without
the sweep, the record would go on claiming `Compliant` indefinitely.

Worst-case staleness is therefore 24 hours, and the cron runs at Brisbane
midnight so statuses roll over at the start of the local business day rather
than partway through it.

### Verifying the sweep

Write a deliberately wrong status straight into DynamoDB, bypassing the API,
then run the job and confirm it corrects itself:

```bash
aws dynamodb update-item --table-name <SubcontractorsTable> \
  --key '{"id":{"S":"<id>"}}' \
  --update-expression "SET complianceStatus = :s" \
  --expression-attribute-values '{":s":{"S":"VALID"}}'

aws lambda invoke --function-name <RecomputeStatusFunction> \
  --payload '{}' /tmp/out.json && cat /tmp/out.json
# {"checked": 3, "updated": 1}
```

---

## Operating it

### Issuing accounts

Self sign-up is disabled — accounts are issued, not requested. A compliance
officer needs a group; a subcontractor also needs binding to their record via
`custom:subcontractorId`. See the README for the commands.

### Reading the logs

Every handler emits one JSON line per request, so CloudWatch Logs Insights
filters on real fields instead of grepping prose:

```
fields @timestamp, userEmail, route, status, durationMs
| filter status >= 400
| sort @timestamp desc
```

The route is logged as its template (`/subcontractors/{subcontractorId}`), not
the concrete path, so results group by endpoint rather than scattering across
every record id. Each line records who made the request — in a compliance
system, knowing *who was refused* is part of the audit trail, not just
debugging.

### Tearing it down

```bash
cd infra
cdk destroy CompliancePortalStack      # tables, functions, API, user pool
cdk destroy CompliancePortalCicdStack  # OIDC provider and deploy role
```

Note the asymmetry, which is deliberate but easy to be caught out by:

- **DynamoDB tables retain.** Compliance records outlive the stack and must be
  deleted separately if that is what you want. Redeploying afterwards creates
  *new* tables, leaving the old ones orphaned and invisible to CloudFormation.
- **The Cognito user pool is destroyed.** Every account goes with it, so a
  redeploy needs users issued again — and any subcontractor login must be
  re-bound to its record, since the ids it pointed at were in the retained
  tables.
