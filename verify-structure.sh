#!/bin/bash

echo "==========================================="
echo "Log Analytics Pipeline Quick Start"
echo "==========================================="

set -e

REPO_ROOT="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

echo ""
echo "1. Verifying project structure..."

required_files=(
    "docker-compose.yml"
    ".env.example"
    ".env"
    "README.md"
    "ARCHITECTURE.md"
    "VERIFICATION.md"
    "benchmark.sh"
    "log-generator/main.py"
    "log-generator/Dockerfile"
    "ingestor/main.py"
    "ingestor/Dockerfile"
    "indexer/main.py"
    "indexer/Dockerfile"
    "querier/cli.py"
    "querier/Dockerfile"
    "scheduler/main.py"
    "scheduler/Dockerfile"
)

missing_files=()
for file in "${required_files[@]}"; do
    if [ ! -f "$REPO_ROOT/$file" ]; then
        missing_files+=("$file")
    fi
done

if [ ${#missing_files[@]} -gt 0 ]; then
    echo "❌ Missing files:"
    printf '   - %s\n' "${missing_files[@]}"
    exit 1
fi

echo "✓ All required files present"

echo ""
echo "2. Verifying project directories..."

required_dirs=(
    "data"
    "data/docs"
    "data/index"
    "reports"
    "log-generator"
    "ingestor"
    "indexer"
    "querier"
    "scheduler"
)

missing_dirs=()
for dir in "${required_dirs[@]}"; do
    if [ ! -d "$REPO_ROOT/$dir" ]; then
        missing_dirs+=("$dir")
    fi
done

if [ ${#missing_dirs[@]} -gt 0 ]; then
    echo "❌ Missing directories:"
    printf '   - %s\n' "${missing_dirs[@]}"
    exit 1
fi

echo "✓ All required directories present"

echo ""
echo "3. Checking Python code for required patterns..."

indexer_check=$(grep -c "parser_registry\|def parse_nginx\|def parse_json\|def parse_syslog\|def tokenize\|inverted_index\|update_index" "$REPO_ROOT/indexer/main.py" || echo "0")
if [ "$indexer_check" -lt 6 ]; then
    echo "❌ Indexer missing required functions"
    exit 1
fi
echo "✓ Indexer has required parser registry and functions"

querier_check=$(grep -c "def search_inverted_index\|def filter_documents\|def aggregate_command" "$REPO_ROOT/querier/cli.py" || echo "0")
if [ "$querier_check" -lt 3 ]; then
    echo "❌ Querier missing required functions"
    exit 1
fi
echo "✓ Querier has required search/filter/aggregate functions"

ingestor_check=$(grep -c "/logs\|/logs/batch\|X-Request-ID\|buffer" "$REPO_ROOT/ingestor/main.py" || echo "0")
if [ "$ingestor_check" -lt 3 ]; then
    echo "❌ Ingestor missing required endpoints"
    exit 1
fi
echo "✓ Ingestor has required endpoints and buffering"

echo ""
echo "4. Checking docker-compose.yml..."

services_needed=("log-generator" "ingestor" "indexer" "querier" "scheduler")
for service in "${services_needed[@]}"; do
    if ! grep -q "^  $service:" "$REPO_ROOT/docker-compose.yml"; then
        echo "❌ Service '$service' not defined in docker-compose.yml"
        exit 1
    fi
done
echo "✓ All required services defined"

echo ""
echo "5. Checking .env.example..."

env_vars=("INGESTOR_PORT" "BUFFER_WINDOW_SECONDS" "BATCH_SIZE" "LOG_GENERATION_INTERVAL" "TIME_JITTER_SECONDS")
for var in "${env_vars[@]}"; do
    if ! grep -q "$var" "$REPO_ROOT/.env.example"; then
        echo "❌ Environment variable '$var' not in .env.example"
        exit 1
    fi
done
echo "✓ All environment variables documented"

echo ""
echo "==========================================="
echo "✓ Project Structure Verification Complete!"
echo "==========================================="
echo ""
echo "Next steps:"
echo "  1. Review ARCHITECTURE.md for system design"
echo "  2. Review README.md for usage instructions"
echo "  3. Run: docker-compose up --build -d"
echo "  4. Monitor: docker-compose logs -f"
echo "  5. Query: docker-compose run --rm querier search 'error'"
echo ""
