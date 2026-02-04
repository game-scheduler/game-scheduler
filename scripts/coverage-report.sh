#!/bin/bash
# Copyright 2026 Bret McKee
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.


# Run all tests with coverage and generate combined reports

set -e

cd "$(dirname "$0")/.."

# Parse options
RUN_E2E=true
if [[ "$1" == "--skip-e2e" ]]; then
    RUN_E2E=false
fi

# Ensure coverage files are writable by container user
echo "Setting permissions for coverage collection..."
mkdir -p .pytest_cache htmlcov coverage
chmod 777 .pytest_cache htmlcov coverage 2>/dev/null || true

# Clean up old coverage data
echo "Cleaning up old coverage data..."
rm -f .coverage .coverage.* coverage.xml
rm -f coverage/.coverage.*
rm -rf htmlcov/

# Run unit tests
echo ""
echo "Running unit tests with coverage..."
echo "===================================="
if ! COVERAGE_FILE=.coverage.unit pytest --cov=shared --cov=services --cov-report=; then
    echo "ERROR: Unit tests failed"
    exit 1
fi

# Capture unit test coverage immediately
UNIT_COV=$(coverage report --data-file=.coverage.unit 2>/dev/null | awk '/^TOTAL/ {print $NF}')
echo "Unit tests completed with $UNIT_COV coverage"

# Run integration tests
echo ""
echo "Running integration tests with coverage..."
echo "=========================================="
if ! ./scripts/run-integration-tests.sh; then
    echo "ERROR: Integration tests failed"
    exit 1
fi

# Capture integration coverage if file exists
INT_COV=""
if [[ -f "coverage/.coverage.integration" ]]; then
    INT_COV=$(coverage report --data-file=coverage/.coverage.integration 2>/dev/null | awk '/^TOTAL/ {print $NF}')
    echo "Integration tests completed with $INT_COV coverage"
fi

# Run e2e tests (optional)
E2E_RAN=false
E2E_COV=""
if $RUN_E2E; then
    echo ""
    echo "Running e2e tests with coverage..."
    echo "=================================="
    if [[ ! -f "config/env.e2e" ]]; then
        echo "WARNING: config/env.e2e not found - skipping e2e tests"
        echo "See docs/developer/TESTING.md for setup instructions"
    else
        if ! ./scripts/run-e2e-tests.sh; then
            echo "ERROR: E2E tests failed"
            exit 1
        fi
        E2E_RAN=true
        # Capture e2e coverage if file exists
        if [[ -f "coverage/.coverage.e2e" ]]; then
            E2E_COV=$(coverage report --data-file=coverage/.coverage.e2e 2>/dev/null | awk '/^TOTAL/ {print $NF}')
            echo "E2E tests completed with $E2E_COV coverage"
        fi
    fi
else
    echo ""
    echo "Skipping e2e tests (--skip-e2e specified)"
fi

# Combine all coverage data
echo ""
echo "Combining coverage data..."
echo "========================="
# Move coverage files from coverage/ directory to root for combining
if ls coverage/.coverage.* 1> /dev/null 2>&1; then
    cp coverage/.coverage.* .
fi

if ! ls .coverage* 1> /dev/null 2>&1; then
    echo "ERROR: No coverage data files found"
    exit 1
fi

# Now combine all files (keeping originals for individual reporting)
coverage combine --keep

# Capture final combined coverage
FINAL_COV=$(coverage report | awk '/^TOTAL/ {print $NF}')

# Generate reports
echo ""
echo "Coverage Report:"
echo "================"
coverage report

echo ""
echo "Generating XML report (coverage.xml)..."
coverage xml

echo "Generating HTML report (htmlcov/)..."
coverage html

echo ""
echo "════════════════════════════════════════════════"
echo "Coverage Summary:"
echo "════════════════════════════════════════════════"
echo "  Unit tests:         $UNIT_COV"
if [[ -n "$INT_COV" ]]; then
    echo "  Integration tests:  $INT_COV"
fi
if [[ -n "$E2E_COV" ]]; then
    echo "  E2E tests:          $E2E_COV"
fi
echo "  ────────────────────────────────────────────────"
echo "  Combined total:     $FINAL_COV"
echo "════════════════════════════════════════════════"

echo ""
echo "✓ Coverage reports generated:"
echo "  - Terminal report (above)"
echo "  - coverage.xml (for CI/CD)"
echo "  - htmlcov/index.html (detailed view)"
echo ""
echo "To view HTML report: open htmlcov/index.html in your browser"
