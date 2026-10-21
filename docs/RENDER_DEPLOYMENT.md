# NCMS VerifyFlow — Render deployment and recovery

This repository uses an existing PostgreSQL database and a **single Docker web service** for non-sensitive pilot use. The worker runs alongside FastAPI in the web container. It does not provision another database.

## Use the correct Render workspace

The existing service belongs to the workspace associated with `1nc24cs150@ncetmail.com`. The separate `expressfreefire40@gmail.com` Render account does **not** have access. Both dashboards may call their workspace "My Workspace". Sign in to the owning account, or arrange authorized access, before changing the service. Do not accidentally create a duplicate service in the other account.

## Service settings

- GitHub: `https://github.com/hackerncet/tuxnestsite` — `main` branch
- Runtime: Docker, `./Dockerfile`, root directory blank
- Region: Oregon, matching the existing external PostgreSQL endpoint
- Health check: `/healthz`
- Public URL (when deployment succeeds): `https://ncet-verifyflow.onrender.com`

Configure these values **privately** in Render → web service → Environment:

| Variable | Value |
| --- | --- |
| `APP_ENV` | `production` |
| `DATABASE_URL` | A valid existing PostgreSQL connection URL, **after rotation of exposed credentials** |
| `PUBLIC_ORIGIN` | `https://ncet-verifyflow.onrender.com` |
| `SETTINGS_ENCRYPTION_KEY` | Stable valid Fernet key |
| `NCET_BOOTSTRAP_ADMIN_PASSWORD` | One-time strong initial admin password |
| `STORAGE_BACKEND` | `database` |
| `APP_RUN_WORKER_IN_WEB` | `true` |
| `SCAN_MODE` | `off` for non-sensitive trial use **only** |

Prefer internal database URL if web service and DB share a Render workspace/region. External Render PostgreSQL endpoints require **TLS**, so their URL must have `sslmode=require` in the query string. Never commit environment values, database passwords, or API keys to GitHub.

Generate a Fernet key locally:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Preserve this key for all deployments; changing it without migrating stored settings will make encrypted OpenRouter keys unreadable.

**Rotate the exposed PostgreSQL password before real use.** Coordinate with the database owner first, as other applications may use the same database user. Update the Render `DATABASE_URL` immediately after rotation.

## Deploy and test

1. Save environment variables in the **owning** Render workspace and deploy the current `main` branch.
2. Startup validates secrets, runs Alembic migrations, initializes the admin if needed, and launches FastAPI and the worker.
3. Wait for Render status **Live**, then verify `/healthz` returns HTTP 200 with `{"ok":true}`.
4. Sign in at `/app` as `admin` with the password configured in Render, create Staff/HOD/Principal/IQAC users, and add the OpenRouter key under Super Admin.
5. Test rules → a non-sensitive document upload → AI verification → HOD approval → Principal/IQAC visibility.
6. Confirm documents survive a service restart and that logs do not expose secrets.

## Troubleshooting

| Problem | What to verify |
| --- | --- |
| Render Dashboard **Access denied** | Render login account and service ownership |
| Missing `DATABASE_URL` | Set variable on the correct Render service |
| TLS / `sslmode=require` failure | Add TLS option to *external* PostgreSQL URL |
| Database connect timeout | Database is running, credentials rotated correctly, network allows access |
| POST /login returns 403 | Set exact HTTPS `PUBLIC_ORIGIN` without `/app` |
| Invalid Fernet key | Generate a valid `SETTINGS_ENCRYPTION_KEY` |
| No administrator | Set `NCET_BOOTSTRAP_ADMIN_PASSWORD` for initial creation |
| Verification remains stuck | Confirm `APP_RUN_WORKER_IN_WEB=true` and review worker logs |

**Not yet institutional-production ready:** Render Free suspends the worker when idle, and limited CPU/RAM can interrupt OCR. Use always-on paid compute and preferably a separate worker; turn on malware scanning, backups, audit retention, privacy policies and monitoring. Obtain college approval before sending extracted staff/student documents to an external OpenRouter model. Never treat a created Render service as live until its startup and health checks pass.
