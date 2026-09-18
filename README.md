# Subcontractor Compliance Portal (QLD)

Contract-first serverless app for tracking Queensland construction subcontractor
compliance — QBCC licences, public liability and workers' compensation insurance,
and White Cards — with expiry-aware status tracking.

Built with Python on AWS (Lambda, DynamoDB, API Gateway, CDK) and a React +
TypeScript frontend.

## The domain

Queensland head contractors are exposed if a subcontractor works without current
cover, so the app tracks the documents that actually matter under QLD rules:

| Document | Issued by | Expires? |
| --- | --- | --- |
| QBCC licence | Queensland Building and Construction Commission | Yes |
| Public liability insurance | Insurer (certificate of currency) | Yes |
| Workers' compensation insurance | WorkCover Queensland | Yes |
| White Card (construction induction) | Registered training organisation | **No** |
| Professional indemnity insurance | Insurer — design/certification trades only | Yes |

The first four are required of every subcontractor. Professional indemnity is
tracked but excluded from the compliance rollup, since it only applies to some
trades.

### Status rules

A document is `EXPIRED` past its expiry, `EXPIRING_SOON` within 30 days, else
`VALID`. A White Card has no expiry and is `VALID` once on file.

A subcontractor's overall status takes the **best** status within each document
type, then the **worst** across the required types:

- Best-within-type — holding a lapsed 2024 certificate *and* a current one is
  not a breach; the old one is history.
- Worst-across-types — one expired requirement makes the subcontractor
  non-compliant.
- Any required type with no record at all yields `MISSING_DOCS`.

## Architecture

```
React SPA  ──>  API Gateway  ──>  Lambda (Python)  ──>  DynamoDB
                                        │
                     EventBridge (daily) ┘
```

- **Two DynamoDB tables**, `Subcontractors` and `ComplianceDocuments`, the latter
  with a `bySubcontractorId` GSI. Two tables rather than single-table design —
  the access patterns here are simple enough that the added indirection would
  cost more in clarity than it saves in requests.
- **Lambda per resource**, each routing on HTTP method. No third-party routing
  library, so the deployment package has no dependencies to bundle — `boto3`
  already ships in the Lambda runtime.
- **Least-privilege IAM**: each function is granted only the tables it uses.
- **CDK (Python)** defines all of it; `cdk deploy` is the only deployment step.

### Denormalized compliance status

`complianceStatus` is **stored** on the subcontractor record rather than derived
per read, so the list view is a single query instead of N+1.

That trade has a catch: stored derived state goes stale on its own. A certificate
lapsing overnight triggers no write, so nothing would update the record. Status is
therefore recomputed on two triggers:

1. **On write** — any document create/update/delete re-derives its subcontractor's
   status immediately.
2. **On schedule** — an EventBridge rule runs a Lambda daily at 14:00 UTC
   (midnight Brisbane) to catch purely time-driven transitions.

## Layout

```
backend/     Lambda handlers, domain logic, DynamoDB repository (Python)
infra/       CDK app defining every AWS resource (Python)
frontend/    React + TypeScript + Vite SPA
openapi.yaml The API contract, written before the code
```

## Running it

### Backend and infrastructure

```bash
cd infra
.venv/Scripts/python -m pip install -r requirements.txt
cdk deploy
```

Deploys to whichever account and region your AWS CLI is configured for, and
prints the API URL on completion.

### Frontend

```bash
cd frontend
npm install
cp .env.example .env     # then set VITE_API_BASE_URL to the deployed API URL
npm run dev
```

### Tests

```bash
cd backend && .venv/Scripts/python -m pytest   # domain logic and validation
cd infra   && .venv/Scripts/python -m pytest   # CDK synthesises the expected resources
```

## Not included

Authentication is deliberately out of scope — the API is open. Adding Cognito
with an API Gateway authorizer would be the first change before this went
anywhere real.
