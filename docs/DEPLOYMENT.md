# Deployment Guide

## Docker Deployment (Recommended)

### Prerequisites

- Docker Engine 24+
- Docker Compose v2+
- At least 4 GB RAM and 10 GB disk space

### Step-by-step

1. **Clone the repository**

```bash
git clone <repository-url>
cd epstein_rag
```

2. **Configure environment**

```bash
cp .env.example .env
# Edit .env to set passwords and ports
```

Key variables to review:

| Variable | Default | Description |
|----------|---------|-------------|
| `POSTGRES_PASSWORD` | `epstein_rag` | Database password (change for production) |
| `DASHBOARD_FRONTEND_PORT` | `3000` | Dashboard UI port |
| `DASHBOARD_BACKEND_PORT` | `8001` | API port |
| `CHROMA_PORT` | `8000` | ChromaDB port |
| `MCP_SERVER_PORT` | `8080` | MCP server HTTP port |

3. **Start all services**

```bash
docker compose up -d
```

4. **Verify health**

```bash
# Check all containers are running
docker compose ps

# Test API health endpoint
curl http://localhost:8001/api/dashboard/health

# Test frontend
curl -s -o /dev/null -w "%{http_code}" http://localhost:3000
```

5. **View logs**

```bash
# All services
docker compose logs -f

# Specific service
docker compose logs -f mcp-server
docker compose logs -f dashboard-backend
```

### Stopping and restarting

```bash
# Stop all services (preserves data volumes)
docker compose down

# Stop and remove all data
docker compose down -v

# Rebuild after code changes
docker compose up -d --build
```

---

## Manual Deployment (Development)

### 1. PostgreSQL

Install and start PostgreSQL 15. Create the database:

```sql
CREATE USER epstein_rag WITH PASSWORD 'epstein_rag';
CREATE DATABASE epstein_rag OWNER epstein_rag;
```

### 2. ChromaDB

```bash
pip install chromadb
chroma run --host 0.0.0.0 --port 8000
```

### 3. MCP Server

```bash
cd mcp_server
pip install -r requirements.txt
export DATABASE_URL="postgresql+asyncpg://epstein_rag:epstein_rag@localhost:5432/epstein_rag"
export CHROMA_HOST=localhost
export CHROMA_PORT=8000
python -m mcp_server
```

### 4. Dashboard Backend

```bash
cd dashboard_backend
pip install -r requirements.txt
export DASHBOARD_DATABASE_URL="postgresql+asyncpg://epstein_rag:epstein_rag@localhost:5432/epstein_rag"
uvicorn dashboard_backend.main:app --host 0.0.0.0 --port 8001
```

### 5. Dashboard Frontend

```bash
cd dashboard_frontend
npm install
npm run dev
# Or for production build:
npm run build && npx serve -s dist -l 3000
```

---

## Production Deployment

### Security checklist

- [ ] Change all default passwords in `.env`
- [ ] Enable HTTPS/TLS on frontend (use a reverse proxy like Caddy or nginx)
- [ ] Restrict CORS origins to your domain
- [ ] Use a managed PostgreSQL instance with encrypted connections
- [ ] Set `DASHBOARD_DEBUG=false`
- [ ] Place all services behind a firewall; only expose ports 80/443

### Recommended architecture

```
Internet --> Reverse Proxy (Caddy/nginx with TLS)
                |
                +--> Dashboard Frontend (port 80 internal)
                |
                +--> Dashboard Backend (port 8001 internal)
                      |
                      +--> PostgreSQL (port 5432 internal)
                      +--> ChromaDB (port 8000 internal)
                      +--> MCP Server (port 8080 internal)
```

### Environment variables for production

```bash
POSTGRES_PASSWORD=<strong-random-password>
DASHBOARD_DEBUG=false
DASHBOARD_CORS_ORIGINS='["https://your-domain.com"]'
LOG_LEVEL=WARNING
```

### Monitoring

- Dashboard API health: `GET /api/dashboard/health`
- Docker health checks are configured for all services
- All query and indexing operations are logged to PostgreSQL

### Backup

```bash
# Backup PostgreSQL data
docker compose exec postgres pg_dump -U epstein_rag epstein_rag > backup.sql

# Restore
cat backup.sql | docker compose exec -T postgres psql -U epstein_rag epstein_rag
```

### Scaling considerations

- **ChromaDB**: For large document collections (100k+ chunks), consider a dedicated server
- **PostgreSQL**: Enable connection pooling (PgBouncer) for high query volumes
- **Frontend**: Serve via CDN for best performance
- **MCP Server**: Stateless; can run multiple instances behind a load balancer
