# Subcontractor Compliance Portal

Contract-first serverless app for tracking QLD (Queensland, Australia) construction subcontractor compliance — QBCC licences, insurances, and White Cards, with expiry-aware status tracking.

## Structure

- `backend/` — Lambda handlers (Python)
- `infra/` — CDK app (Python)
- `frontend/` — React + TS (Vite)
- `openapi.yaml` — API contract

## Development

All development targets real AWS resources (DynamoDB, Lambda, API Gateway) — no local emulation. See `infra/` for deployment.
