# Railway Read-Only Demo

This deployment uses three Railway services in one project environment: a public frontend, a private FastAPI service, and private PostgreSQL. Keep all three in the same region. The API and database must not have public domains.

## Create the services

1. Create a Railway project and add a PostgreSQL service. Keep its default private networking enabled.
2. Add an API service connected to `jems0906/LaunchScope` on the `main` branch. Set the repository root directory to `/` and the `RAILWAY_DOCKERFILE_PATH` service variable to `/backend/Dockerfile`.
3. Add a frontend service from the same repository and branch. Keep the root directory `/` and set `RAILWAY_DOCKERFILE_PATH` to `/frontend/Dockerfile`.
4. Deploy PostgreSQL first, then the API, then the frontend. The frontend resolves the API using Railway private DNS.

## Configure the API

Set these service variables on `api`:

```text
DATABASE_URL=${{Postgres.DATABASE_URL}}
SESSION_COOKIE_SECURE=true
```

Use the exact PostgreSQL service name in the variable reference if you named it differently. Railway supplies `PORT`; the API listens on it. Configure the API healthcheck path as `/api/health`. Do not add a public domain to this service.

Leave `SESSION_SECRET`, `ANALYST_USERNAME`, `ANALYST_PASSWORD_HASH`, `REVIEWER_USERNAME`, and `REVIEWER_PASSWORD_HASH` unset for the public read-only demo. Do not add analyst or reviewer credentials to a public Railway environment: all configured accounts share the same project data.

## Configure the frontend

Set these service variables on `frontend`:

```text
API_HOST=${{api.RAILWAY_PRIVATE_DOMAIN}}:8000
PORT=80
```

Use the exact API service name in the private-domain reference if you named it differently. Set the public target port to `80`, configure the healthcheck path as `/api/health`, and generate a Railway domain for this service only.

## Verify the deployment

Open the generated frontend domain and confirm the application loads. Request `/api/health` through that same domain and confirm it returns `{"status":"ok","service":"launchscope-api"}`. Confirm the analyst/reviewer sign-in controls are unavailable, the API has no public domain, and the PostgreSQL service has no public networking enabled.

Before storing any non-disposable data, enable database backups and review Railway's backup retention and recovery behavior. This educational demo should contain synthetic data only.