# Technology Stack and Version Requirements

## Container Runtime
- Docker 20.10+
- Docker Compose 2.0+

## Languages
- Python 3.11

## Python Dependencies

### log-generator
- requests>=2.28.0

### ingestor
- requests>=2.28.0

### indexer
- requests>=2.28.0

### scheduler
- schedule>=1.1.0

### querier
- (No external dependencies, uses Python stdlib)

## Base Images
- python:3.11-slim (all services)

## System Requirements
- RAM: 2GB minimum
- Disk: 5GB minimum for typical usage
- CPU: 2 cores minimum

## Port Mappings
- Ingestor API: 8000
- Indexer Health Check: 8001

## Shared Volumes
- /app/data (Document Store and Inverted Index)
- /app/reports (Generated Reports)
