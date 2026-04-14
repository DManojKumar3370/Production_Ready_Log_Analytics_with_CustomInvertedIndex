# Operational Guide

## Deployment

### Local Development Deployment

1. **Clone and Setup**
   ```bash
   cd Production_Ready_Log_Analytics_with_CustomInvertedIndex
   ```

2. **Copy environment configuration**
   ```bash
   cp .env.example .env
   ```

3. **Build and start services**
   ```bash
   docker-compose up --build -d
   ```

4. **Wait for services to become healthy**
   ```bash
   docker-compose ps
   ```
   All services should show "Up" status within 30 seconds.

5. **Verify data directories are created**
   ```bash
   ls -la data/
   ls -la reports/
   ```

### Production Deployment Checklist

- [ ] Increase `BATCH_SIZE` to 5000
- [ ] Increase `BUFFER_WINDOW_SECONDS` to 120
- [ ] Configure `LOG_GENERATION_INTERVAL` based on expected volume
- [ ] Set `REPORT_TIME` to off-peak hours
- [ ] Mount shared storage for `data/` and `reports/` volumes
- [ ] Configure log rotation for container logs
- [ ] Set up monitoring for service health
- [ ] Configure backup for persisted indices
- [ ] Enable authentication for querier API (if deployed)

## Monitoring

### Service Health

Check all services:
```bash
docker-compose ps
```

Check individual service health:
```bash
docker-compose exec ingestor curl http://localhost:8000/health
docker-compose exec indexer curl http://localhost:8001/health
```

### View Logs

All services:
```bash
docker-compose logs -f
```

Specific service:
```bash
docker-compose logs -f [service-name]
```

Last 100 lines:
```bash
docker-compose logs --tail=100
```

### Monitor Indexing Progress

Watch documents being indexed:
```bash
watch 'ls data/docs/ | wc -l'
```

Watch index file size:
```bash
watch 'ls -lh data/index/inverted_index.json'
```

Monitor ingestor buffer:
```bash
docker-compose logs ingestor | tail -20
```

### Performance Metrics

Count indexed documents:
```bash
find data/docs -name "*.json" | wc -l
```

Index file size:
```bash
du -h data/index/inverted_index.json
```

Number of unique tokens:
```bash
cat data/index/inverted_index.json | python3 -c "import sys, json; print(len(json.load(sys.stdin)))"
```

Query performance:
```bash
time docker-compose run --rm querier search "error"
```

## Maintenance

### Clearing Data

**Warning**: This deletes all indexed logs and index.

```bash
docker-compose down
rm -rf data/docs/* data/index/*
docker-compose up -d
```

### Backing Up

```bash
tar -czf backup-$(date +%Y%m%d).tar.gz data/ reports/
```

### Restoring from Backup

```bash
docker-compose down
tar -xzf backup-20240101.tar.gz
docker-compose up -d
```

### Archiving Old Reports

```bash
find reports -type d -mtime +30 -exec tar -czf archive-{}.tar.gz {} \; -delete
```

### Database Optimization

Rebuild index (compact):
```bash
docker-compose exec indexer python3 -c "
import json
with open('/app/data/index/inverted_index.json', 'r') as f:
    index = json.load(f)
with open('/app/data/index/inverted_index.json', 'w') as f:
    json.dump(index, f)
print('Index compacted')
"
```

## Troubleshooting

### Services won't start

Check Docker status:
```bash
docker ps
docker-compose ps
```

View startup logs:
```bash
docker-compose logs --no-pager
```

Rebuild containers:
```bash
docker-compose down
docker-compose build --no-cache
docker-compose up -d
```

### Health check failures

Ingestor not responding:
```bash
docker-compose exec ingestor curl -v http://localhost:8000/health
```

Indexer not responding:
```bash
docker-compose exec indexer curl -v http://localhost:8001/health
```

Restart service:
```bash
docker-compose restart [service-name]
```

### No logs being indexed

Check ingestor is receiving logs:
```bash
docker-compose logs ingestor | grep "Accepted\|POST"
```

Check indexer is fetching batches:
```bash
docker-compose logs indexer | grep "Fetched batch"
```

Check parser errors:
```bash
docker-compose logs indexer | grep "Error"
```

### Slow search performance

Check index size:
```bash
du -h data/index/inverted_index.json
```

If too large (>1GB), consider:
- Archiving old documents
- Increasing `INDEX_CHECK_INTERVAL`
- Implementing index sharding

Monitor index loading time:
```bash
time docker-compose run --rm querier search "test"
```

### High memory usage

Check container memory:
```bash
docker stats
```

Reduce `BATCH_SIZE` in `.env`:
```bash
BATCH_SIZE=500  # reduced from 1000
```

Consider archiving old logs:
```bash
find data/docs -newermt '30 days ago' -delete
```

### Duplicate logs in index

This shouldn't happen, but if deduplication fails:

1. Stop the system
   ```bash
   docker-compose down
   ```

2. Clear index and reingest
   ```bash
   rm -rf data/index/*
   docker-compose up -d
   ```

3. Monitor for duplicates:
   ```bash
   docker-compose logs ingestor | grep "duplicate\|duplicate ID"
   ```

## Scaling Considerations

### Single Machine Optimization

**For 10M+ logs:**

1. Increase buffer window (handle spikes):
   ```
   BUFFER_WINDOW_SECONDS=120
   ```

2. Increase batch size:
   ```
   BATCH_SIZE=5000
   ```

3. Adjust indexing interval:
   ```
   INDEX_CHECK_INTERVAL=10
   ```

4. Use faster storage (SSD):
   ```
   data/ and reports/ on SSD mount
   ```

### Multi-Machine Deployment

For production scale:

1. **Use message queue** (instead of HTTP):
   - Replace ingestor with Kafka consumer
   - Producer in log-generator
   - Benefits: Durability, replay, partitioning

2. **Shard index by token prefix**:
   - Token "a*" → server-1
   - Token "b*" → server-2
   - Requires query fan-out

3. **Time-based document sharding**:
   - Documents from day-1 → storage-1
   - Documents from day-2 → storage-2
   - Enables archival and deletion

4. **Distributed query with caching**:
   - Cache layer (Redis) for frequent queries
   - Query coordinator broadcasts to shards
   - Aggregate results

## Disaster Recovery

### Backup Strategy

Daily backup:
```bash
mkdir -p /backup/logs-analytics
cp -r data/ /backup/logs-analytics/data-$(date +%Y%m%d)/
cp -r reports/ /backup/logs-analytics/reports-$(date +%Y%m%d)/
```

Automated backup:
```bash
0 2 * * * cd /path/to/project && tar -czf /backup/logs-$(date +\%Y\%m\%d).tar.gz data/ reports/
```

### Recovery Procedure

1. Stop services
   ```bash
   docker-compose down
   ```

2. Restore backup
   ```bash
   tar -xzf /backup/logs-20240101.tar.gz
   ```

3. Start services
   ```bash
   docker-compose up -d
   ```

4. Verify data integrity
   ```bash
   find data/docs -name "*.json" | wc -l
   cat data/index/inverted_index.json | python3 -m json.tool | head
   ```

## Performance Tuning

### Low-Latency Configuration

```bash
BATCH_SIZE=100           # smaller batches, more frequent indexing
INDEX_CHECK_INTERVAL=1   # check every second
LOG_GENERATION_INTERVAL=0.01  # generate logs faster
BUFFER_WINDOW_SECONDS=30      # shorter buffering
```

### High-Throughput Configuration

```bash
BATCH_SIZE=10000        # larger batches
INDEX_CHECK_INTERVAL=30  # less frequent indexing
LOG_GENERATION_INTERVAL=0.001  # fast generation
BUFFER_WINDOW_SECONDS=120     # longer buffering
```

### Balanced Configuration (Default)

```bash
BATCH_SIZE=1000
INDEX_CHECK_INTERVAL=5
LOG_GENERATION_INTERVAL=0.1
BUFFER_WINDOW_SECONDS=60
```

## Alerting

### Monitor Index Growth

```bash
watch -n 60 'du -h data/index/inverted_index.json; echo "---"; ls data/docs | wc -l'
```

Alert if:
- Index file > 2GB (may not fit in memory)
- Documents > 50M (performance degradation)
- Indexing rate drops (ingestor issues)

### Monitor Error Rate

```bash
docker-compose run --rm querier aggregate count --by level --last 1h
```

Alert if:
- Error rate > 5% (application issues)
- Missing logs (ingestor issues)
- Query timeouts (performance issues)

## Capacity Planning

For N logs per day:

- **Disk space**: N * 2KB (documents) + N / 1000KB (index) = 2.001 * N KB
- **Memory for index**: N / 1000000 * 500MB (1M logs = 500MB)
- **Processing time**: N / 1000 seconds (1000 logs/sec typical)

Example: 100M logs/day
- Disk: 200GB
- Memory: 50GB (need to shard!)
- CPU: 100k seconds (need parallelization)

## Support

### Check logs for errors

```bash
docker-compose logs | grep -i error
```

### Export logs for analysis

```bash
docker-compose logs > container-logs.txt
```

### Memory/CPU usage

```bash
docker stats --no-stream
```

### Network connectivity

```bash
docker-compose exec indexer ping ingestor
docker-compose exec querier ping -c 1 localhost:8000
```
