#!/bin/bash
# Test script for DocOrchestrator with normal mode (Qwen 2.5 32B)

echo "=========================================="
echo "Testing DocOrchestrator - Normal Mode"
echo "Model: Qwen 2.5 32B (local, ~11 tok/s)"
echo "=========================================="
echo ""

cd "$(dirname "$0")"

echo "Running orchestrator with normal mode config..."
python3 orchestrator.py --config test_config_normal.yaml --yes

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
