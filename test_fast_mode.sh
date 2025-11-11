#!/bin/bash
# Test script for DocOrchestrator with fast mode (Gemini 2.5 Flash)

echo "=========================================="
echo "Testing DocOrchestrator - Fast Mode"
echo "Model: Gemini 2.5 Flash (cloud, 300+ tok/s)"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

echo "Running orchestrator with fast mode config..."
python3 orchestrator.py --config test_config_fast.yaml --yes

EXIT_CODE=$?

echo ""
echo "=========================================="
if [ $EXIT_CODE -eq 0 ]; then
    echo "✓ Test completed successfully"
else
    echo "✗ Test failed with exit code: $EXIT_CODE"
fi
echo "=========================================="

exit $EXIT_CODE
