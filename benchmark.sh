#!/bin/bash

echo "=========================================="
echo "Log Analytics Pipeline Benchmark"
echo "=========================================="

DATA_DIR="./data"
BENCH_RESULTS="benchmark_results.txt"
NUM_LOGS=1000000
KEYWORD="database"

echo "Clearing existing data..."
rm -rf "$DATA_DIR/docs"/* "$DATA_DIR/index"/* 2>/dev/null || true
mkdir -p "$DATA_DIR/docs" "$DATA_DIR/index"

echo "Stopping existing containers..."
docker-compose down 2>/dev/null || true

echo "Starting services..."
docker-compose up -d --build

echo "Waiting for services to be healthy..."
sleep 15

echo "Checking service health..."
max_retries=30
retry_count=0
while [ $retry_count -lt $max_retries ]; do
    if curl -s http://localhost:8000/health > /dev/null 2>&1; then
        echo "Ingestor is healthy"
        break
    fi
    echo "Waiting for ingestor to be healthy..."
    sleep 2
    retry_count=$((retry_count + 1))
done

if [ $retry_count -eq $max_retries ]; then
    echo "Services failed to start"
    exit 1
fi

echo "Monitoring log ingestion (wait for indexing to complete)..."

total_logs=0
previous_logs=0
stable_count=0

while [ $total_logs -lt $NUM_LOGS ] && [ $stable_count -lt 30 ]; do
    total_logs=$(find "$DATA_DIR/docs" -name "*.json" 2>/dev/null | wc -l)
    
    if [ $total_logs -eq $previous_logs ]; then
        stable_count=$((stable_count + 1))
    else
        stable_count=0
    fi
    
    echo "Indexed: $total_logs logs"
    previous_logs=$total_logs
    sleep 2
    
    if [ $total_logs -ge $NUM_LOGS ]; then
        echo "Reached target number of logs"
        break
    fi
done

echo "Giving the system 10 seconds to stabilize..."
sleep 10

echo ""
echo "=========================================="
echo "Running Benchmark Queries"
echo "=========================================="

docker-compose run --rm -v "$(pwd)/data:/app/data" querier search "$KEYWORD" > /dev/null 2>&1 &
INDEX_SEARCH_PID=$!

time_index_start=$(date +%s.%N)
wait $INDEX_SEARCH_PID
time_index_end=$(date +%s.%N)

INDEX_TIME=$(echo "$time_index_end - $time_index_start" | bc)

echo ""
echo "Running linear grep scan (grep)..."
time_grep_start=$(date +%s.%N)
grep -r "$KEYWORD" "$DATA_DIR/docs" > /dev/null 2>&1
time_grep_end=$(date +%s.%N)

GREP_TIME=$(echo "$time_grep_end - $time_grep_start" | bc)

actual_logs=$(find "$DATA_DIR/docs" -name "*.json" 2>/dev/null | wc -l)

echo ""
echo "=========================================="
echo "Benchmark Results"
echo "=========================================="
echo "Total logs indexed: $actual_logs"
echo "Inverted Index Search Time: ${INDEX_TIME}s"
echo "Linear Scan (grep) Time: ${GREP_TIME}s"
echo ""

SPEEDUP=$(echo "scale=2; $GREP_TIME / $INDEX_TIME" | bc)
echo "Speedup: ${SPEEDUP}x"

TIMESTAMP=$(date '+%Y-%m-%d %H:%M:%S')
{
    echo "Benchmark Results ($TIMESTAMP)"
    echo "========================================"
    echo "Keyword: $KEYWORD"
    echo "Total logs: $actual_logs"
    echo "Inverted Index Search Time: ${INDEX_TIME}s"
    echo "Linear Scan (grep) Time: ${GREP_TIME}s"
    echo "Speedup: ${SPEEDUP}x"
    echo ""
} >> "$BENCH_RESULTS"

echo "Results appended to $BENCH_RESULTS"
cat "$BENCH_RESULTS"

docker-compose down

echo ""
echo "Benchmark completed!"
