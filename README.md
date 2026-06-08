# Dual-DB FastMCP with n8n — AI-Powered Database Management

An intelligent database management system combining **FastMCP**, **n8n**, and **Google Gemini AI** to manage PostgreSQL and MySQL databases through natural language conversation.

## ⚠️ Recent Update: Streamable HTTP Transport

**Migration from SSE (Server-Sent Events) to Streamable HTTP:**
- The MCP specification deprecated SSE in early 2025 in favor of Streamable HTTP
- This project has been updated to use the new Streamable HTTP transport
- Server now runs on `http://127.0.0.1:8000` (previously `http://127.0.0.1:8000/sse`)
- n8n workflow configuration updated to use `serverTransport: "http"`

## Project Overview

This project enables users to create databases, design table schemas, insert data, and query information across both PostgreSQL and MySQL using a conversational AI interface. Instead of writing SQL manually, you chat with an AI assistant that understands your intent and executes the appropriate database operations safely.

**Key Features:**
- 🤖 Natural language database management via AI
- 🔒 SQL injection prevention and input validation
- 📊 Support for both PostgreSQL and MySQL
- 🛠️ Create databases, tables, and insert/query data
- 🔄 Conversation memory for multi-step workflows
- 🚀 Local development with Docker Compose

---

## Core Stack

### 1. **Docker Compose** (`docker-compose.yaml`)
Containerizes your database infrastructure:
- **PostgreSQL 15** — listens on `5432`
- **MySQL 8.0** — listens on `3306`
- **Adminer** — web UI for database browsing at `http://localhost:8080`

### 2. **Python FastMCP Server** (`server.py`)
A FastMCP server that exposes database operations as callable tools:
- Runs on `http://127.0.0.1:8000` (Streamable HTTP transport)
- Implements 5 database tools (create, read, write, schema inspection)
- Validates all inputs to prevent SQL injection
- Supports both PostgreSQL and MySQL with unified interface

### 3. **n8n Workflow** (`MCP Database Agent.json`)
Orchestrates the conversation flow:
- **Chat Trigger** — receives user messages
- **AI Agent** — routes requests to appropriate tools
- **Google Gemini** — generates SQL-safe function calls
- **Memory Buffer** — maintains conversation history
- **MCP Client** — communicates with FastMCP server

### 4. **Google Gemini AI**
Natural language understanding:
- Interprets user intent from plain English
- Generates structured database operation parameters
- Maintains context across conversation

---

## FastMCP Tools

All tools are implemented as `@mcp.tool()` functions and exposed via the server:

| Tool | Purpose | Parameters | Returns |
|------|---------|------------|---------|
| `create_database` | Create new database | `db_type`, `database_name` | Success/error message |
| `create_table` | Create table with columns | `db_type`, `table_name`, `columns` (JSON dict), `primary_key` (optional), `if_not_exists` (bool) | Success/error message |
| `insert_data` | Insert one row | `db_type`, `table_name`, `row_data` (JSON dict) | Success/error message |
| `read_data` | Query data (flexible) | `db_type`, `table_name` (or `sql_query`), `limit` | JSON array of rows |
| `get_database_schema` | List tables and columns | `db_type` | JSON with table structure |

### Tool Examples

**Simple fetch (first 3 rows):**
```python
read_data(db_type='mysql', table_name='products', limit=3)
```

**Custom SELECT:**
```python
read_data(db_type='postgres', sql_query='SELECT * FROM products WHERE price > 100')
```

**Create table:**
```python
create_table(
    db_type='mysql',
    table_name='users',
    columns={'id': 'INT AUTO_INCREMENT', 'name': 'VARCHAR(255)', 'email': 'VARCHAR(255)'},
    primary_key='id'
)
```

---

## Safety Mechanisms

### 1. **Input Validation**
- `validate_identifier()` — ensures table/column names contain only safe characters (`[A-Za-z_][A-Za-z0-9_]*`)
- `validate_column_type()` — restricts data types to safe patterns

### 2. **SQL Injection Prevention**
- **Parameterized queries** — uses `psycopg2.sql.Identifier()` and `%s` placeholders instead of string formatting
- **Read-only enforcement** — `read_data` with `sql_query` only allows `SELECT` statements

### 3. **JSON Parsing Safety**
- `parse_json_input()` — safely parses JSON from Gemini, validates structure

### 4. **Database Credentials**
- Loaded from `.env` file (never hardcoded)
- Supports environment variable overrides for production

### 5. **Connection Hygiene**
- All connections explicitly closed after use
- Transactions committed atomically
- Error messages don't leak database internals

---

## Architecture Diagram

```
┌─────────────────────────────────────────────────────────────────┐
│ User Input (Chat at http://localhost:5678)                      │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ n8n Chat Trigger Node                                           │
│ - Receives message                                              │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ n8n AI Agent Node                                               │
│ - Reads system prompt (tool definitions)                        │
│ - Accesses memory (conversation history)                        │
│ - Decides which tool to call                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ Google Gemini (AI Model)                                        │
│ - Understands natural language intent                           │
│ - Generates function parameters                                 │
│ - Maintains response context                                    │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ n8n MCP Client Tool                                             │
│ - Connects to FastMCP server at http://127.0.0.1:8000/sse      │
│ - Serializes parameters to JSON                                 │
└────────────────────────┬────────────────────────────────────────┘
                         │ HTTP/SSE
┌────────────────────────▼────────────────────────────────────────┐
│ Python FastMCP Server (server.py)                               │
│ - Validates all inputs                                          │
│ - Routes to tool function                                       │
│ - Executes database operation safely                            │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ Database Drivers (psycopg2 / PyMySQL)                           │
│ - Establish secure connections                                  │
│ - Execute parameterized queries                                 │
│ - Return results                                                │
└────────────────────────┬────────────────────────────────────────┘
                         │
┌────────────────────────▼────────────────────────────────────────┐
│ PostgreSQL / MySQL Databases (Docker)                           │
│ - postgres:15 on port 5432 (analytics DB)                       │
│ - mysql:8.0 on port 3306 (inventory DB)                         │
└─────────────────────────────────────────────────────────────────┘
```

---

## Quick Start

### Prerequisites
- Docker & Docker Compose
- Python 3.10+
- Node.js/npm
- Google Gemini API credentials

### Step 1: Set Up Environment

```powershell
# Copy template and add passwords
copy .env.example .env
# Edit .env and set your passwords
```

### Step 2: Start Databases

```powershell
docker-compose up -d
docker ps  # verify containers are running
```

Access Adminer at `http://localhost:8080`

### Step 3: Start FastMCP Server (Terminal A)

```powershell
python -m venv .venv
(Set-ExecutionPolicy -Scope Process -ExecutionPolicy RemoteSigned) ; (& .venv\Scripts\Activate.ps1)
pip install -r requirements.txt
python server.py
# Server runs at http://127.0.0.1:8000/sse
```

### Step 4: Start n8n (Terminal B)

```powershell
npx n8n
# Opens n8n at http://localhost:5678
```

### Step 5: Import & Activate Workflow

1. In n8n, import `MCP Database Agent.json`
2. Set up Google Gemini credentials
3. Click "Activate" to enable the workflow
4. Open the chat interface and start asking questions

---

## Usage Examples

### Create a Database
```
You: "Create a database called ecommerce"
→ Gemini calls: create_database(db_type='mysql', database_name='ecommerce')
→ Result: ✓ Database 'ecommerce' created
```

### Design a Table
```
You: "Create a products table with id, name, price, and stock"
→ Gemini calls: create_table(
    db_type='mysql', 
    table_name='products',
    columns={'id': 'INT AUTO_INCREMENT', 'name': 'VARCHAR(255)', 'price': 'DECIMAL(10,2)', 'stock': 'INT'},
    primary_key='id'
)
→ Result: ✓ Table 'products' created
```

### Insert Data
```
You: "Add a product: laptop, $999, 50 in stock"
→ Gemini calls: insert_data(
    db_type='mysql',
    table_name='products',
    row_data={'name': 'laptop', 'price': 999, 'stock': 50}
)
→ Result: ✓ Inserted row
```

### Query Data
```
You: "Show me the first 5 products"
→ Gemini calls: read_data(db_type='mysql', table_name='products', limit=5)
→ Result: [
    {'id': 1, 'name': 'laptop', 'price': 999, 'stock': 50},
    ...
]
```

### View Schema
```
You: "What tables exist in the database?"
→ Gemini calls: get_database_schema(db_type='mysql')
→ Result: [
    {'table_name': 'products', 'column_name': 'id', 'data_type': 'int'},
    {'table_name': 'products', 'column_name': 'name', 'data_type': 'varchar'},
    ...
]
```

---

## Environment Variables

### Database Configuration

| Variable | Default | Purpose |
|----------|---------|---------|
| `PG_HOST` | localhost | PostgreSQL host |
| `PG_PORT` | 5432 | PostgreSQL port |
| `PG_USER` | admin | PostgreSQL user |
| `PG_PASSWORD` | — | PostgreSQL password (required) |
| `PG_DATABASE` | analytics | Default PostgreSQL database |
| `MYSQL_HOST` | localhost | MySQL host |
| `MYSQL_PORT` | 3306 | MySQL port |
| `MYSQL_USER` | root | MySQL user |
| `MYSQL_PASSWORD` | — | MySQL password (required) |
| `MYSQL_DATABASE` | inventory | Default MySQL database |

Create databases with `create_database` tool. Specify which database to use by passing `db_type='mysql'` or `db_type='postgres'` to each tool.

---

## Project Structure

```
.
├── docker-compose.yaml          # Database containers
├── server.py                     # FastMCP server with tools
├── MCP Database Agent.json       # n8n workflow
├── requirements.txt              # Python dependencies
├── .env                          # Environment variables (gitignored)
├── .env.example                  # Template for .env
└── README.md                     # This file
```

---

## Troubleshooting

### "Access denied for user 'root' (using password: NO)"
- Ensure `.env` is populated with valid passwords
- Restart `server.py` to reload env vars

### FastMCP server not found at http://127.0.0.1:8000/sse
- Verify `python server.py` is running in a dedicated terminal
- Check that no firewall is blocking port 8000

### Gemini API errors
- Verify Google Gemini credentials are set in n8n
- Check API key validity and quotas

### Docker containers fail to start
- Run `docker-compose down && docker-compose up -d` to restart
- Check `docker logs <container_name>` for errors

---

## Extending the Project

### Add a New Tool
1. Create a function decorated with `@mcp.tool()`
2. Add validation and error handling
3. Use parameterized queries to prevent injection
4. Update the n8n agent system prompt

### Use a Different AI Model
Replace the Gemini node in n8n with OpenAI, Claude, or another provider. Update the system prompt accordingly.

### Deploy to Production
- Use environment-specific `.env` files
- Run databases on managed services (RDS, Cloud SQL)
- Deploy FastMCP server to a cloud platform (AWS ECS, Google Cloud Run, etc.)
- Use n8n Cloud or self-hosted n8n instance

---

## Security Considerations

- ✅ All SQL queries use parameterized statements
- ✅ Identifier validation prevents unauthorized table/column access
- ✅ `.env` file is gitignored and never committed
- ✅ Error messages sanitized to prevent information leakage
- ✅ Read-only enforcement for SELECT-only tool usage
- ⚠️ Always validate user requests before execution in production
- ⚠️ Restrict database user permissions to minimum required
- ⚠️ Use HTTPS/TLS for production deployments

---

## License & Attribution

This project integrates:
- [FastMCP](https://github.com/jlopp/fastmcp) — MCP server framework
- [n8n](https://n8n.io/) — Workflow automation
- [Google Gemini](https://ai.google.dev/) — AI capabilities
- [PostgreSQL](https://www.postgresql.org/) & [MySQL](https://www.mysql.com/) — Database engines
