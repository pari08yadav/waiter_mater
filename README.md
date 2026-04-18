# Waiter

Waiter is a contactless restaurant ordering platform with real-time order updates and a built-in AI assistant for both customers and staff.

Customers scan a table QR code, browse the menu, place orders, and track status live. Staff receive orders instantly on the dashboard and can update statuses manually or via AI.

---

## Features

- QR-based table ordering flow
- Restaurant dashboard for tables, categories, menu items, and live orders
- Real-time status updates via WebSockets
- Customer AI assistant (`/table/<table_uid>/chat/`)
- Staff AI assistant (`/dashboard/restaurant/<uid>/agent/`)
- REST API via DRF for core resources
- Qdrant + embeddings powered semantic menu search for AI fallback

---

## Tech Stack

- Backend: Django 5.1
- API: Django REST Framework
- Realtime: Django Channels + WebSockets
- ASGI server: Daphne
- DB: SQLite (default dev setup)
- Static/media: Whitenoise, optional S3/Cloudinary
- AI: Google Gemini + sentence-transformers + Qdrant

---

## Python version (important)

This repo is easiest to run on **Python 3.11** (also a good match for most cloud hosts).

If you use **Python 3.13**, you may hit extra native build issues for some packages. If installs fail, switch your venv to **3.11** and reinstall.

---

## Refactored Architecture

The project is now organized by app and layered concerns:

- `accounts`: authentication + user/chain profile
- `restaurants`: restaurants, tables, categories, menu items
- `orders`: order placement/status + realtime consumers
- `agent`: customer/staff chat orchestration and tools
- `shared`: cross-app reusable utilities/contracts
- `common`: compatibility + routing/templates shell during migration

### Layer intent inside apps

- `application/`: use-case orchestration services
- `domain/`: contracts/ports and domain-facing types
- `infrastructure/`: concrete adapters (auth/chat/realtime/vector/etc.)
- `interfaces/`: HTTP/WS-facing adapters

---

## Project Structure

```text
waiter-master/
├── waiter/
│   ├── settings.py
│   ├── urls.py
│   └── asgi.py
├── accounts/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── interfaces/
│   ├── templates/accounts/
│   ├── models.py
│   └── views.py
├── restaurants/
│   ├── application/
│   ├── interfaces/
│   ├── templates/restaurants/
│   ├── models.py
│   ├── forms.py
│   ├── serializers.py
│   ├── tasks.py
│   └── views.py
├── orders/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── interfaces/
│   ├── templates/orders/
│   ├── models.py
│   ├── serializers.py
│   ├── consumers.py
│   ├── routing.py
│   └── views.py
├── agent/
│   ├── application/
│   ├── domain/
│   ├── infrastructure/
│   ├── interfaces/
│   ├── agent.py
│   ├── tools.py
│   ├── prompts.py
│   ├── vector_store.py
│   └── views.py
├── shared/
│   ├── application/
│   └── common/
├── common/
│   ├── urls.py
│   ├── templates/common/
│   ├── views.py            # compatibility facade
│   ├── forms.py            # compatibility facade
│   ├── serializers.py      # compatibility facade
│   └── tasks.py            # compatibility facade
├── fixtures/
├── global_static/
├── manage.py
├── requirements.in
└── requirements.txt
```

---

## Quick Start (Local)

### 1) Clone and install

```bash
git clone <repo-url>
cd waiter-master
python3 -m venv venv
source venv/bin/activate
pip install -r requirements.txt
```

If you change `requirements.in` and want a clean lockfile:

```bash
pip install pip-tools
pip-compile requirements.in
pip install -r requirements.txt
```

### 2) Configure environment

```bash
cp env.template .env
```

Set at minimum:

- `DJANGO_SECRET_KEY`
- `DEBUG=True`
- `ALLOWED_HOSTS=127.0.0.1,localhost`
- `BASE_URL=http://127.0.0.1:8000` (include `http://` or `https://`)
- `GEMINI_API_KEY` (required for chat endpoints)
- `QDRANT_URL` (optional; defaults to `http://localhost:6333` if unset)

### 3) Migrate and run

```bash
python3 manage.py migrate
python3 manage.py runserver
```

Or with Daphne:

```bash
daphne waiter.asgi:application
```

Open: `http://127.0.0.1:8000`

---

## Deploying (Render, no logic changes)

Create a **Web Service** and use:

**Build command**

```bash
pip install -r requirements.txt && python manage.py collectstatic --noinput && python manage.py migrate
```

**Start command (ASGI + WebSockets)**

```bash
daphne -b 0.0.0.0 -p $PORT waiter.asgi:application
```

**Environment variables (minimum)**

- `DJANGO_SECRET_KEY`
- `DEBUG=False`
- `ALLOWED_HOSTS=<your-app>.onrender.com`
- `CSRF_TRUSTED_ORIGINS=https://<your-app>.onrender.com`
- `BASE_URL=https://<your-app>.onrender.com`
- `GEMINI_API_KEY` (if you use AI chat)
- `QDRANT_URL` (point to Qdrant Cloud / your hosted Qdrant)

**Database note**

The repo defaults to **SQLite** for local convenience. For production reliability on Render, use **managed Postgres** and point Django at it (small settings/config change only).

---

## Environment Variables

| Variable | Required | Description |
|---|---|---|
| `DJANGO_SECRET_KEY` | Yes | Django secret key |
| `DEBUG` | Yes | `True` for local development |
| `ALLOWED_HOSTS` | Yes | Comma-separated hostnames |
| `BASE_URL` | Yes | Used for generated QR URLs |
| `GEMINI_API_KEY` | For AI | Gemini API key |
| `QDRANT_URL` | Optional | Qdrant HTTP URL (defaults to local dev URL if unset) |
| `CSRF_TRUSTED_ORIGINS` | Optional | Comma-separated trusted origins |
| `AWS_STORAGE_*` | Optional | Needed only when S3 storage is enabled |

---

## Main URLs

| URL | Purpose |
|---|---|
| `/` | Home |
| `/login/` | Staff login |
| `/dashboard/` | Restaurants dashboard |
| `/dashboard/restaurant/<uid>/` | Restaurant details |
| `/dashboard/order/<uid>/` | Live order board |
| `/table/<table_uid>/` | Customer menu page |
| `/table/<table_uid>/order/` | Customer order tracking page |
| `/table/<table_uid>/chat/` | Customer AI API endpoint |
| `/dashboard/restaurant/<uid>/agent/` | Staff AI API endpoint |
| `/api/v1/...` | DRF resources (`user`, `restaurant`, `table`, `category`, `menu-item`, `order`) |

---

## Realtime Flow

WebSocket endpoint:

- `ws/order/<uid>/`

Group behavior:

- Customer connects with session UID
- Staff connects with restaurant UID

On order creation/status change:

- DB is updated
- WebSocket events are broadcast to both relevant groups

---

## AI Notes

- Customer AI uses menu context + order context and can place orders via tool calls.
- Staff AI reads live order state and can update order statuses.
- Menu semantic search uses Qdrant/embeddings as fallback beyond heuristic matching.

Important: chat history in session is stored in JSON-safe format only.


Manual smoke checks:

- Login/logout
- Dashboard -> restaurant -> tables/categories
- Customer place order from table page
- Staff sees order live and updates status
- Customer receives live status updates
- Customer/staff AI chat endpoints respond

---

## Common Issues

- `TypeError: Object of type Content is not JSON serializable` on chat endpoint  
  Fixed by storing JSON-safe chat history structure in session.

- `ModuleNotFoundError: No module named 'google.generativeai'`  
  Install deps (`pip install -r requirements.txt`) and ensure `google-generativeai` is present.

- HF Hub warning about unauthenticated downloads  
  Optional warning; set `HF_TOKEN` to reduce rate limits.

- Qdrant storage artifacts accidentally tracked  
  Keep `qdrant_storage/` ignored in git.

- Production caution  
  In-memory channel layer is not suitable for multi-process deployment; use Redis channel layer in production.

---

## Migration Status

- App/domain split is in place.
- Legacy `common` now primarily acts as compatibility and route shell.
- Remaining future hardening can gradually retire more `common` surface once all consumers are fully migrated.

---


