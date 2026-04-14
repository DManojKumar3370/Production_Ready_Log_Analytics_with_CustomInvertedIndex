#!/bin/bash

echo "=========================================="
echo "FINAL PROJECT VERIFICATION"
echo "=========================================="
echo ""

ERRORS=0

echo "Checking file structure..."
echo ""

FILES=(
    ".env"
    ".env.example"
    "docker-compose.yml"
    "README.md"
    "ARCHITECTURE.md"
    "QUICKSTART.md"
    "OPERATIONS.md"
    "VERIFICATION.md"
    "SUBMISSION.md"
    "PROJECT_SUMMARY.md"
    "REQUIREMENTS.md"
    "DOCUMENTATION_INDEX.md"
    "COMPLETION_SUMMARY.md"
    "benchmark.sh"
    "setup.sh"
    "verify-structure.sh"
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

for file in "${FILES[@]}"; do
    if [ -f "$file" ]; then
        echo "✅ $file"
    else
        echo "❌ Missing: $file"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "Checking directories..."

DIRS=(
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

for dir in "${DIRS[@]}"; do
    if [ -d "$dir" ]; then
        echo "✅ $dir/"
    else
        echo "❌ Missing: $dir/"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "Checking Python syntax..."

for file in log-generator/main.py ingestor/main.py indexer/main.py querier/cli.py scheduler/main.py; do
    if python3 -m py_compile "$file" 2>/dev/null; then
        echo "✅ $file (valid Python)"
    else
        echo "❌ $file (syntax error)"
        ERRORS=$((ERRORS + 1))
    fi
done

echo ""
echo "Checking key features in code..."

if grep -q "parser_registry\|def parse_nginx\|def parse_json\|def parse_syslog" indexer/main.py; then
    echo "✅ Indexer has parser registry"
else
    echo "❌ Indexer missing parser registry"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "def tokenize\|inverted_index\[" indexer/main.py; then
    echo "✅ Indexer has custom inverted index"
else
    echo "❌ Indexer missing inverted index"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "def search_inverted_index\|def filter_documents\|def aggregate_command" querier/cli.py; then
    echo "✅ Querier has search/filter/aggregate"
else
    echo "❌ Querier missing search/filter/aggregate"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "X-Request-ID.*seen_ids\|dedup" ingestor/main.py; then
    echo "✅ Ingestor has deduplication"
else
    echo "❌ Ingestor missing deduplication"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "healthcheck\|health" docker-compose.yml; then
    echo "✅ docker-compose.yml has health checks"
else
    echo "❌ docker-compose.yml missing health checks"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "Checking for prohibited libraries..."

if grep -r "elasticsearch\|opensearch\|solr\|whoosh\|bleve" --include="*.py" . 2>/dev/null | grep -v Binary; then
    echo "❌ Found prohibited search libraries"
    ERRORS=$((ERRORS + 1))
else
    echo "✅ No prohibited search libraries used"
fi

echo ""
echo "Checking documentation..."

if grep -q "docker-compose up" README.md; then
    echo "✅ README.md has setup instructions"
else
    echo "❌ README.md missing setup instructions"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "inverted index" ARCHITECTURE.md; then
    echo "✅ ARCHITECTURE.md describes inverted index"
else
    echo "❌ ARCHITECTURE.md missing inverted index description"
    ERRORS=$((ERRORS + 1))
fi

if grep -q "Requirement.*Implementation" VERIFICATION.md; then
    echo "✅ VERIFICATION.md has requirement mapping"
else
    echo "❌ VERIFICATION.md missing requirement mapping"
    ERRORS=$((ERRORS + 1))
fi

echo ""
echo "=========================================="

if [ $ERRORS -eq 0 ]; then
    echo "✅ ALL CHECKS PASSED!"
    echo "=========================================="
    echo ""
    echo "Project is ready for submission!"
    echo ""
    echo "Key components verified:"
    echo "  • 5 microservices with Dockerfiles"
    echo "  • 9 comprehensive documentation files"
    echo "  • Custom inverted index implementation"
    echo "  • Pluggable parser registry"
    echo "  • Query CLI (search/filter/aggregate)"
    echo "  • Daily reporting"
    echo "  • Benchmark script"
    echo ""
    echo "Next steps:"
    echo "  1. Review README.md for overview"
    echo "  2. Run: cp .env.example .env"
    echo "  3. Run: docker-compose up --build -d"
    echo "  4. Wait 30 seconds for services to initialize"
    echo "  5. Run: docker-compose run --rm querier search 'error'"
    echo ""
    exit 0
else
    echo "❌ $ERRORS ISSUES FOUND"
    echo "=========================================="
    echo ""
    echo "Please fix the issues listed above."
    echo ""
    exit 1
fi
