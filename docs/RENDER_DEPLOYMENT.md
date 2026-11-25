# NCMS VerifyFlow — Render deployment and recovery

This repository uses an existing PostgreSQL database and a **single Docker web service** for non-sensitive pilot use. The worker runs alongside FastAPI in the web container. It does not provision another database.

## Use the correct Render workspace

The existing service belongs to the workspace associated with `1nc24cs150@ncetmail.com`. The separate `expressfreefire40@gmail.com` Render account does **not** have access. Both dashboards may call their workspace "My Workspace". Sign in to the owning account, or arrange authorized access, before changing the service. Do not accidentally create a duplicate service in the other account.

## Service settings

- GitHub: `https://github.com/paladuguganeshnaidu/ncet` — `main` branch
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

## Recovering an expired Render PostgreSQL database

Free Render PostgreSQL expires after 30 days. Render documents a 14-day grace period to upgrade the existing instance before it and its data are deleted. See https://render.com/docs/free#free-postgres. If the database is suspended, restore the existing database through its dashboard before redeploying. Obtain approval for paid compute. Do not replace the database with an empty instance or switch to ephemeral SQLite to make a health check pass: accounts, submissions and uploaded documents may be lost or unavailable. Keep the existing encryption key unchanged. Once the instance is available, confirm the connection using a read-only `SELECT 1`, export a secure backup, deploy `main`, and verify `/healthz` and authenticated workflows. Configure the service's HTTP Health Check Path to `/healthz` in Render Settings if it is blank; this route checks the database.

## Troubleshooting

| Problem | What to verify |
| --- | --- |
| Render Dashboard **Access denied** | Render login account and service ownership |
| Missing `DATABASE_URL` | Set variable on the correct Render service |
| TLS / `sslmode=require` failure | Add TLS option to *external* PostgreSQL URL |
| Database connect timeout or internal hostname not resolving | Check PostgreSQL status and expiry first, then credentials and network access |
| POST /login returns 403 | Set exact HTTPS `PUBLIC_ORIGIN` without `/app` |
| Invalid Fernet key | Generate a valid `SETTINGS_ENCRYPTION_KEY` |
| No administrator | Set `NCET_BOOTSTRAP_ADMIN_PASSWORD` for initial creation |
| Verification remains stuck | Confirm `APP_RUN_WORKER_IN_WEB=true` and review worker logs |

**Not yet institutional-production ready:** Render Free suspends the worker when idle, and limited CPU/RAM can interrupt OCR. Use always-on paid compute and preferably a separate worker; turn on malware scanning, backups, audit retention, privacy policies and monitoring. Obtain college approval before sending extracted staff/student documents to an external OpenRouter model. Never treat a created Render service as live until its startup and health checks pass.
