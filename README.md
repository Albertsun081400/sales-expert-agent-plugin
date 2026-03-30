# Sales-Expert Plugin

Thin HTTP plugin wrapper that exposes `/api/v1/retrieve` and `/api/v1/sync`
to DeerFlow skills. Delegates all vector operations to the parent
**Sales-Expert-Agent** service.

## Endpoints

| Method | Path | Description |
|--------|------|-------------|
| POST | `/api/v1/retrieve` | Hybrid search (vector + BM25 + rerank) |
| POST | `/api/v1/sync` | Ingest conversation turns + customer profiles |
| GET | `/health` | Liveness probe |

## Local Development

```bash
pip install -r requirements.txt
SALES_EXPERT_BASE_URL=http://localhost:8000 uvicorn app.main:app --reload --port 8080
```

## Docker

```bash
# Point to local Sales-Expert-Agent
export SALES_EXPERT_BASE_URL=http://localhost:8000
docker compose up --build

# Point to cloud Sales-Expert-Agent
export SALES_EXPERT_BASE_URL=https://your-cloud-endpoint.com
docker compose up --build
```

## Tenant Isolation

Pass `X-Tenant-ID` header on every request. Falls back to `default` if omitted.
