**Dual-DB FastMCP — minimal read-only DB tools**

Short description

This repository provides a small Python service (`server.py`) that exposes two read-only FastMCP tools for inspecting PostgreSQL and MySQL databases:

- `execute_read_query` — run read-only `SELECT` queries (validated).
- `get_database_schema` — list tables and columns.

Tech stack

- Docker Compose (optional): Postgres, MySQL, Adminer.
- Python 3.10+ (recommended)
- Node.js/npm (optional, for `npx n8n`)
- Key Python packages (pinned in `requirements.txt`): `PyMySQL`, `psycopg2-binary`, `fastmcp`, `mcp`

Quick start (recommended for local development)

1) Start containerized DBs and UIs (optional):

```powershell
docker-compose up -d
docker ps
```

2) Start the Python FastMCP server (terminal A):

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python server.py
```

3) Start n8n (terminal B) — n8n editor available at http://localhost:5678:

```powershell
npx n8n
```

Notes

- Run each command in its own terminal so services stay active.
- `server.py` defaults connect to local DBs; override using these env vars: `PG_HOST`, `PG_DATABASE`, `PG_USER`, `PG_PASSWORD`, `PG_PORT`, `MYSQL_HOST`, `MYSQL_DATABASE`, `MYSQL_USER`, `MYSQL_PASSWORD`, `MYSQL_PORT`.
- The `execute_read_query` tool only allows `SELECT` queries; non-SELECT queries are rejected.

Environment file

- Copy `.env.example` to `.env` and fill in real passwords for local development. `.env` is ignored by `.gitignore` and should not be committed.

Export n8n workflows and push to GitHub

```

If the endpoint path differs in your FastMCP deployment, adapt the URL accordingly.

**n8n (optional)**

- Access the local n8n UI at http://localhost:5678 (if you started the n8n container).

- Exporting a workflow (manual UI method):
  1. Open the workflow in the n8n editor UI.
  2. Click the workflow menu (three dots) and choose **Export** → **Download JSON**.
  3. Save the downloaded JSON into this repository under a folder such as `n8n-workflows/` (create it if needed).



