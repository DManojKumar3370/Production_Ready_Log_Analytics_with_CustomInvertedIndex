# Production-Ready Log Analytics Pipeline with Custom Inverted Index

A containerized log analytics engine with a custom-built inverted index for efficient text search, designed to handle heterogeneous log data from multiple sources.

## Architecture

The system consists of five main services:

- **log-generator**: Generates synthetic logs in three formats (Nginx, JSON, Syslog) with out-of-order simulation
- **ingestor**: Receives raw log lines, buffers them to handle out-of-order events, and deduplicates
- **indexer**: Parses logs using a pluggable registry and builds the custom inverted index
- **querier**: Command-line interface for searching, filtering, and aggregating logs
- **scheduler**: Generates daily summary reports

## Quick Start

### Prerequisites
- Docker and Docker Compose
- Python 3.7+
- At least 2GB of available disk space

### Installation

1. Clone the repository:
```bash
git clone <repository-url>
cd Production_Ready_Log_Analytics_with_CustomInvertedIndex
```

2. Configure environment variables:
```bash
cp .env.example .env
```

3. Start the pipeline:
```bash
docker-compose up --build -d
```

4. Verify all services are running:
```bash
docker-compose ps
```

## Usage

### Search Logs by Keywords
```bash
docker-compose run --rm querier search "error database"
```

### Filter Logs by Level and Service
```bash
docker-compose run --rm querier filter --level ERROR --service payment-service
```

### Time-range Filtering
```bash
docker-compose run --rm querier search "timeout" --from "2024-01-01T00:00:00Z" --to "2024-01-02T00:00:00Z"
```

### Aggregate Logs
```bash
docker-compose run --rm querier aggregate count --by service,level --last 1h
```

### View Logs in Interactive Mode
```bash
docker-compose run --rm -it querier
```

## Service Details

### Log Generator
- Generates 3 types of logs: Nginx, JSON, Syslog
- Applies ±30 seconds jitter to simulate out-of-order delivery
- Sends logs via HTTP to the ingestor service

### Ingestor Service
- Exposes `POST /logs` endpoint
- Buffers logs for 60 seconds to handle reordering
- Deduplicates logs using `X-Request-ID` header
- Provides `GET /logs/batch` for indexer to fetch ordered logs
- Health check: `GET /health`

### Indexer Service
- Fetches batches from ingestor every 5 seconds
- Parses logs using pluggable parser registry:
  - Nginx parser (regex-based)
  - JSON parser
  - Syslog parser (RFC 5424)
- Builds custom inverted index (token → document IDs)
- Stores parsed documents as JSON files
- Persists index to `data/index/inverted_index.json`

### Query CLI
Commands support:
- **search**: Uses inverted index for fast keyword search
- **filter**: Scans documents for field/time filtering
- **aggregate**: Groups logs by fields with counting

### Scheduler
- Runs daily at configured time (default: 00:00)
- Generates JSON reports in `reports/YYYY-MM-DD/`
- Reports include:
  - Total events count
  - Error rate
  - Top 10 error messages
  - P95 ingestion latency

## Project Structure

```
├── log-generator/
│   ├── main.py
│   └── Dockerfile
├── ingestor/
│   ├── main.py
│   └── Dockerfile
├── indexer/
│   ├── main.py
│   └── Dockerfile
├── querier/
│   ├── cli.py
│   └── Dockerfile
├── scheduler/
│   ├── main.py
│   └── Dockerfile
├── data/
│   ├── docs/          # Parsed log documents
│   └── index/         # Inverted index
├── reports/           # Generated daily reports
├── docker-compose.yml
├── .env.example
├── benchmark.sh
└── README.md
```

## Inverted Index Implementation

The inverted index is a custom-built data structure mapping tokens to document IDs:

```json
{
  "database": ["doc1", "doc3", "doc5"],
  "connection": ["doc1", "doc2"],
  "error": ["doc3", "doc5"]
}
```

### Tokenization
- Converts text to lowercase
- Removes punctuation
- Splits into words

### Search Example
Query: "database AND error"
1. Get document IDs for "database": [1, 3, 5]
2. Get document IDs for "error": [3, 5]
3. Intersect: [3, 5]
4. Return matching documents

## Benchmarking

Run the benchmark script to compare inverted index search vs linear grep:

```bash
chmod +x benchmark.sh
./benchmark.sh
```

This will:
1. Clear existing data
2. Populate system with 1 million logs
3. Time inverted index search
4. Time linear grep scan
5. Append results to `benchmark_results.txt`

Expected results: Inverted index search is typically 100-1000x faster for large datasets.

## Configuration

Edit `.env` file to configure:
- `INGESTOR_PORT`: Port for ingestor service (default: 8000)
- `BUFFER_WINDOW_SECONDS`: Reordering buffer window (default: 60)
- `BATCH_SIZE`: Logs fetched per batch (default: 1000)
- `INDEX_CHECK_INTERVAL`: Frequency of index updates in seconds (default: 5)
- `LOG_GENERATION_INTERVAL`: Interval between log generation (default: 0.1)
- `TIME_JITTER_SECONDS`: Time jitter for out-of-order simulation (default: 30)
- `REPORT_TIME`: Time for daily reports in HH:MM format (default: 00:00)

## Log Formats

### Nginx
```
127.0.0.1 - - [DD/Mon/YYYY:HH:MM:SS +0000] "VERB /path HTTP/1.1" STATUS BYTES "-" "USER_AGENT"
```

### JSON
```json
{"timestamp": "2023-10-10T13:55:36.123Z", "level": "ERROR", "service": "payment-service", "trace_id": "xyz-123-abc", "message": "Database connection timed out"}
```

### Syslog (RFC 5424)
```
<PRI>VERSION TIMESTAMP HOSTNAME APP-NAME - - - MESSAGE
```

## Parsed Document Format

All logs are standardized to:
```json
{
  "id": "unique-doc-id",
  "timestamp": "2023-10-10T13:55:36.000Z",
  "log_type": "nginx|json|syslog",
  "level": "INFO|ERROR|WARNING|DEBUG",
  "service": "service-name",
  "message": "log message",
  "raw": "original log line"
}
```

## Troubleshooting

### Services not starting
```bash
docker-compose logs -f
```

### Check indexer health
```bash
curl http://localhost:8001/health
```

### View ingested logs count
```bash
ls data/docs/ | wc -l
```

### Manual indexer trigger (for testing)
Logs will be automatically indexed every 5 seconds. To monitor:
```bash
docker-compose logs -f indexer
```

## Performance Characteristics

- **Index Size**: ~1KB per 100 unique tokens
- **Search Latency**: < 100ms for keyword search on 1M logs
- **Indexing Throughput**: 1000-5000 logs/second
- **Memory Usage**: ~500MB for 1M log entries with inverted index

## Advanced Usage

### Combine search and filter
```bash
docker-compose run --rm querier search "error" --level ERROR --service payment-service
```

### Query with time range
```bash
docker-compose run --rm querier filter \
  --from "2024-01-01T00:00:00Z" \
  --to "2024-01-31T23:59:59Z" \
  --level ERROR
```

### Aggregate over custom duration
```bash
docker-compose run --rm querier aggregate count --by service --last 24h
```

## Best Practices

1. **Monitor disk space**: Log documents consume disk proportional to volume
2. **Regular reporting**: Daily reports help identify patterns
3. **Index tuning**: Adjust `BATCH_SIZE` based on memory available
4. **Buffer window**: Increase `BUFFER_WINDOW_SECONDS` for unstable networks
5. **Cleanup**: Periodically archive old reports

## Limitations

- Index must fit in memory (for production, consider sharding)
- No distributed querying across nodes
- Single-node deployment only
- Time-windowed deduplication (not exact duplicates)

## Future Enhancements

- Distributed index sharding
- Compressed index format
- Query optimization with histogram statistics
- Real-time alerting on log patterns
- Integration with message queues (Kafka, RabbitMQ)
- Elasticsearch/OSS compatibility layer

## License

This project is provided as-is for educational purposes.
