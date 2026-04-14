# Quick Reference

## Most Important Commands

### Setup & Start
```bash
cp .env.example .env
docker-compose up --build -d
```

### Monitor System
```bash
docker-compose ps
docker-compose logs -f
docker-compose logs -f [service-name]
```

### Query Data
```bash
# Search (fast, uses index)
docker-compose run --rm querier search "error database"

# Filter (scans docs)
docker-compose run --rm querier filter --level ERROR

# Aggregate
docker-compose run --rm querier aggregate count --by service --last 1h
```

### Check Data
```bash
ls data/docs/*.json | wc -l          # Document count
du -h data/index/inverted_index.json  # Index size
cat data/index/inverted_index.json | python3 -m json.tool | head  # View index
```

### Cleanup
```bash
docker-compose down
rm -rf data/docs/* data/index/*
```

## Services Overview

| Service | Port | Purpose | Health Check |
|---------|------|---------|--------------|
| `log-generator` | - | Generates synthetic logs | Logs to stdout |
| `ingestor` | 8000 | HTTP endpoint for logs | GET /health |
| `indexer` | 8001 | Parses & indexes | GET /health |
| `querier` | - | CLI for querying | N/A (CLI) |
| `scheduler` | - | Daily reporting | None |

## Configuration

Edit `.env` to change:
```bash
INGESTOR_PORT=8000              # API port
BUFFER_WINDOW_SECONDS=60        # Reorder buffer
BATCH_SIZE=1000                 # Logs per batch
INDEX_CHECK_INTERVAL=5          # Update frequency
LOG_GENERATION_INTERVAL=0.1     # Log rate
TIME_JITTER_SECONDS=30          # Out-of-order simulation
REPORT_TIME=00:00               # Daily report time
```

## Data Locations

```
data/
├── docs/                 # Parsed log documents (JSON files)
│   ├── uuid-1.json
│   ├── uuid-2.json
│   └── ...
└── index/               # Inverted index
    └── inverted_index.json

reports/
└── YYYY-MM-DD/         # Daily reports
    ├── service1.json
    ├── service2.json
    └── ...
```

## Log Formats Generated

**Nginx**:
```
127.0.0.1 - - [10/Oct/2023:13:55:36 +0000] "GET /api/users HTTP/1.1" 200 512 "-" "Mozilla/5.0"
```

**JSON**:
```json
{"timestamp": "2023-10-10T13:55:36.123Z", "level": "ERROR", "service": "payment-service", "trace_id": "xyz-123", "message": "Database timeout"}
```

**Syslog**:
```
<34>1 2023-10-10T13:55:36.123Z hostname app-name - - - Error message
```

## Parsed Document Format

```json
{
  "id": "unique-uuid",
  "timestamp": "2023-10-10T13:55:36.000Z",
  "log_type": "nginx|json|syslog",
  "level": "INFO|WARNING|ERROR|DEBUG",
  "service": "service-name",
  "message": "parsed message",
  "raw": "original log line"
}
```

## Inverted Index Format

```json
{
  "database": ["doc-id-1", "doc-id-3", "doc-id-5"],
  "error": ["doc-id-3", "doc-id-5"],
  "connection": ["doc-id-1", "doc-id-2"]
}
```

## Query Syntax

### Search
```bash
docker-compose run --rm querier search "<keywords>" [OPTIONS]

Options:
  --level LEVEL        Filter by ERROR|WARNING|INFO|DEBUG
  --service SERVICE    Filter by service name
  --from TIMESTAMP     ISO 8601 timestamp
  --to TIMESTAMP       ISO 8601 timestamp
  --limit N            Max results (default: 100)
```

### Filter
```bash
docker-compose run --rm querier filter [OPTIONS]

Options: Same as search (no keywords)
```

### Aggregate
```bash
docker-compose run --rm querier aggregate count --by field1,field2 --last duration

Durations: 1h, 30m, 7d, 24h, 1w, etc
Fields: service, level, log_type
```

## Performance Expectations

| Operation | Time | Notes |
|-----------|------|-------|
| Index 1K logs | 1s | Depends on CPU |
| Search 1M logs | <100ms | Using index |
| Filter 1M logs | 1-5s | Linear scan |
| Aggregate 1M logs | 2-10s | Depends on groups |
| grep 1M logs | 15s+ | Baseline |

## Workflow Example

### 1. Start System
```bash
docker-compose up --build -d
```

### 2. Wait for Data
```bash
sleep 30
```

### 3. Search for Errors
```bash
docker-compose run --rm querier search "error" --level ERROR --limit 5
```

### 4. Aggregate by Service
```bash
docker-compose run --rm querier aggregate count --by service,level --last 1h
```

### 5. Generate Reports
```bash
docker-compose exec scheduler python3 -c "from main import generate_daily_report; generate_daily_report()"
```

### 6. View Report
```bash
cat reports/$(date +%Y-%m-%d)/payment-service.json | python3 -m json.tool
```

## Troubleshooting Quick Fixes

**Services not starting?**
```bash
docker-compose logs
docker-compose down
docker-compose up --build -d
```

**No logs indexed?**
```bash
docker-compose logs indexer | tail -20
curl http://localhost:8000/logs/batch
```

**Search returns nothing?**
```bash
ls data/docs/ | wc -l  # Check docs exist
docker-compose logs indexer | grep -i error
```

**Slow search?**
```bash
du -h data/index/inverted_index.json  # Check size
docker-compose logs indexer | tail -5
```

## Files at a Glance

| File | Purpose | Key Content |
|------|---------|------------|
| `docker-compose.yml` | Service orchestration | 5 services, health checks |
| `.env.example` | Config template | All env variables |
| `README.md` | User guide | Usage & API |
| `ARCHITECTURE.md` | Design details | System design |
| `OPERATIONS.md` | Maintenance | Deployment guide |
| `VERIFICATION.md` | Testing | Requirement checks |
| `benchmark.sh` | Performance test | Speed comparison |

## Key Algorithms

**Search (O(k))**: 
1. Tokenize query
2. Look up tokens in index
3. Intersect document IDs
4. Return matching docs

**Filter (O(n))**:
1. Scan all documents
2. Check field conditions
3. Check time range
4. Return matching docs

**Aggregate (O(n))**:
1. Scan documents in time range
2. Group by field values
3. Count occurrences
4. Sort and display

## Debug Commands

```bash
# Check specific service logs
docker-compose logs ingestor | grep -i "error\|warning"

# Follow real-time logs
docker-compose logs -f indexer

# Check service status in detail
docker-compose exec indexer curl -v http://localhost:8001/health

# Count total indexed documents
find data/docs -type f -name "*.json" | wc -l

# See what tokens are in index
python3 -c "import json; idx = json.load(open('data/index/inverted_index.json')); print('Tokens:', len(idx))"

# Test query directly
python3 querier/cli.py search "test"

# Check report generation
ls reports/$(date +%Y-%m-%d)/

# Benchmark runtime
time docker-compose run --rm querier search "error"
```

## Environment Variables Reference

```bash
# Ingestor buffering window
BUFFER_WINDOW_SECONDS=60

# Indexer batch processing
BATCH_SIZE=1000
INDEX_CHECK_INTERVAL=5

# Log generation
LOG_GENERATION_INTERVAL=0.1
TIME_JITTER_SECONDS=30

# Networking
INGESTOR_PORT=8000
INGESTOR_HOST=ingestor

# Storage
DATA_DIR=/app/data
REPORTS_DIR=/app/reports

# Scheduling
REPORT_TIME=00:00
```

## Common Queries

**Last hour errors:**
```bash
docker-compose run --rm querier filter --level ERROR --last 1h
```

**Payment service logs:**
```bash
docker-compose run --rm querier filter --service payment-service --limit 50
```

**Database failures:**
```bash
docker-compose run --rm querier search "database failure" --level ERROR
```

**Service statistics:**
```bash
docker-compose run --rm querier aggregate count --by service --last 24h
```

**Error rate by service:**
```bash
docker-compose run --rm querier aggregate count --by service,level --last 1h
```

## Performance Tuning

**For throughput (1M+ logs/day)**:
```bash
BATCH_SIZE=5000
INDEX_CHECK_INTERVAL=10
LOG_GENERATION_INTERVAL=0.01
```

**For low-latency**:
```bash
BATCH_SIZE=100
INDEX_CHECK_INTERVAL=1
BUFFER_WINDOW_SECONDS=30
```

**Default (balanced)**:
```bash
BATCH_SIZE=1000
INDEX_CHECK_INTERVAL=5
BUFFER_WINDOW_SECONDS=60
```

## Verification Checklist

```bash
docker-compose up --build -d
sleep 20
docker-compose ps  # All Up?
ls data/docs/*.json | wc -l  # > 0?
cat data/index/inverted_index.json | python3 -m json.tool | head  # Index exists?
docker-compose run --rm querier search "error" | head  # Search works?
docker-compose down
```

## Submission Checklist

- [ ] All services build: `docker-compose build`
- [ ] All services start: `docker-compose up -d`
- [ ] Data directory created: `ls data/docs data/index`
- [ ] Logs are generated: `docker-compose logs log-generator`
- [ ] Ingestor receives logs: `docker-compose logs ingestor`
- [ ] Indexer processes logs: `docker-compose logs indexer`
- [ ] Search works: `docker-compose run --rm querier search "error"`
- [ ] Reports generated: `ls reports/$(date +%Y-%m-%d)/`
- [ ] Benchmark data exists: `ls data/docs | wc -l` > 100

---

**For complete documentation, see: README.md, ARCHITECTURE.md, OPERATIONS.md**
