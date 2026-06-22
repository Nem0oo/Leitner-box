# Leitner Box

Personal spaced-repetition flashcard app (Leitner system), self-hosted as a single Docker container.

## Stack

- Backend: FastAPI + SQLite, served from a single container (API + scheduler + static frontend)
- Frontend: Vite + React + TypeScript PWA, built into `backend/static` and served by FastAPI
- Storage: SQLite for metadata, content-addressed blob volume for media, separate volume for the manual-edit folder
- Push notifications: Web Push (VAPID) for the daily review reminder

## Deployment

The app is designed to run behind an existing `nginx-proxy` + Let's Encrypt setup, on the external Docker network `nginx-proxy`. CI (`.github/workflows/ci.yml`) builds the image and pushes it to Docker Hub on every push to `main`, then triggers a `watchtower` redeploy via the existing n8n webhook. On the server, only `docker-compose.yml` and `.env` need to be managed — there is no local build step.

1. Generate VAPID keys for Web Push:

   ```bash
   docker run --rm python:3.11-slim bash -c "pip install -q py-vapid && python -c \"
   from py_vapid import Vapid02
   from cryptography.hazmat.primitives.serialization import Encoding, PublicFormat, PrivateFormat, NoEncryption
   import base64
   v = Vapid02()
   v.generate_keys()
   def b64(b): return base64.urlsafe_b64encode(b).decode().rstrip('=')
   pub = v.public_key.public_bytes(Encoding.X962, PublicFormat.UncompressedPoint)
   priv = v.private_key.private_bytes(Encoding.DER, PrivateFormat.PKCS8, NoEncryption())
   print('LEITNER_VAPID_PUBLIC_KEY=' + b64(pub))
   print('LEITNER_VAPID_PRIVATE_KEY=' + b64(priv))
   \""
   ```

2. Copy `.env.example` to `.env`, fill in `DOCKERHUB_USERNAME` (the account CI publishes the image to) and the two VAPID keys from step 1, then encrypt it with `age` before committing anywhere:

   ```bash
   cp .env.example .env
   # edit .env
   age -p -e .env > .env.age
   ```

3. Pull and start:

   ```bash
   docker compose pull
   docker compose up -d
   ```

   From then on, pushes to `main` publish a new image and `watchtower` redeploys it automatically; the server only ever needs `docker-compose.yml` + `.env`.

The container exposes port 8000 internally; `nginx-proxy` routes `leitner.gcourtot.fr` to it via `VIRTUAL_HOST`/`LETSENCRYPT_HOST`.

### Required GitHub Actions secrets

- `DOCKERHUB_USERNAME`, `DOCKERHUB_TOKEN` — push access to the `leitner-box` image
- `N8N_WEBHOOK_ID_LEITNER` — webhook id that triggers the watchtower redeploy for this service

## Data layout

- `leitner_data` volume (`/data`): SQLite DB + content-addressed media blobs
- `leitner_edit` volume (`/edit`): manual editing folder, scanned by the indexer on startup and via `POST /api/indexer/rescan`. Cards live under `<edit>/<deck_name>/carte_XXXX/` with `recto.*`/`verso.*` files.

## Development

```bash
# backend
cd backend && python3 -m venv .venv && .venv/bin/pip install -r requirements-dev.txt
.venv/bin/pytest

# frontend
cd frontend && npm install
npm run build   # outputs into ../backend/static
npx vitest run
```
