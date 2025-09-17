# Database Persistence in Docker Production

## Problem
Previously, the database was getting wiped on every Docker rebuild because:
1. The application was hardcoded to use `trading.db` in the working directory
2. Docker containers are ephemeral - data is lost when container is rebuilt
3. Multiple services were using different database paths

## Solution Implemented

### 1. Environment Variable Configuration
The application now uses `SQLITE_DB_PATH` environment variable:

```python
# database.py
DATABASE_PATH = os.getenv("SQLITE_DB_PATH", "trading.db")
```

### 2. Docker Configuration
**docker-compose.prod.yml:**
```yaml
environment:
  - SQLITE_DB_PATH=/app/data/trading.db
volumes:
  - ./data:/app/data  # Persistent storage
```

### 3. Directory Structure in Production
```
/app/
├── data/
│   └── trading.db    # Persistent database
├── src/
├── logs/
└── reports/
```

### 4. Volume Mounting
The `./data` directory on the host is mounted to `/app/data` in the container, ensuring:
- Database persists across container rebuilds
- Data survives Docker updates
- Backups can be made from host system

## Files Updated

1. **src/api/database/database.py**: Uses environment variable for database path
2. **src/api/services/excel_reports_service.py**: Uses centralized DATABASE_PATH
3. **src/api/routers/portfolio.py**: Uses centralized DATABASE_PATH
4. **docs/deployment/Dockerfile**: Creates `/app/data` directory with proper permissions
5. **docs/deployment/docker-compose.prod.yml**: Already configured correctly

## Verification

After rebuilding, check the startup logs for:
```
Database path: /app/data/trading.db
✅ Database directory ready
Database location: /app/data/trading.db
✅ Database ready
```

## Backup Strategy

### Manual Backup
```bash
# From host system
cp ./data/trading.db ./data/trading.db.backup.$(date +%Y%m%d_%H%M%S)
```

### Automated Backup (recommended)
Add to crontab:
```bash
# Daily backup at 2 AM
0 2 * * * cd /path/to/stock-analyzer && cp ./data/trading.db ./data/backups/trading.db.$(date +\%Y\%m\%d)
```

## Recovery

If database is corrupted:
1. Stop the container: `docker-compose -f docs/deployment/docker-compose.prod.yml down`
2. Restore from backup: `cp ./data/trading.db.backup.YYYYMMDD ./data/trading.db`
3. Start the container: `docker-compose -f docs/deployment/docker-compose.prod.yml up -d`

## Development vs Production

- **Development**: Uses `trading.db` in project root
- **Production**: Uses `/app/data/trading.db` via environment variable
- **Local Docker**: Can use either depending on environment setup