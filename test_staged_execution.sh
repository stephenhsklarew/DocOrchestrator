#!/bin/bash
# Comprehensive test script for staged execution mode
# Tests all stages of the workflow independently

# Don't exit on error - we want to count failures
# set -e

# Colors for output
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
BLUE='\033[0;34m'
NC='\033[0m' # No Color

# Test counters
TESTS_PASSED=0
TESTS_FAILED=0

# Cleanup function
cleanup() {
    echo ""
    echo -e "${BLUE}=== Cleaning up test artifacts ===${NC}"
    # Remove test sessions
    rm -rf sessions/test_*
    # Remove test output
    rm -rf test_output/
    # Remove mock topic files from root
    rm -f topic_*.md
    echo -e "${GREEN}✓ Cleanup complete${NC}"
}

# Trap cleanup on exit
trap cleanup EXIT

# Helper function to print test results
print_result() {
    local test_name=$1
    local exit_code=$2

    if [ $exit_code -eq 0 ]; then
        echo -e "${GREEN}✓ PASS${NC}: $test_name"
        ((TESTS_PASSED++))
    else
        echo -e "${RED}✗ FAIL${NC}: $test_name"
        ((TESTS_FAILED++))
    fi
}

# Change to DocOrchestrator directory
cd ~/Development/Scripts/DocOrchestrator

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   DocOrchestrator Staged Execution Test Suite${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""

# Test 1: List utility commands (should work with no sessions)
echo -e "${YELLOW}[Test 1]${NC} Testing utility commands with no sessions..."
python3 orchestrator.py --list-pending > /dev/null 2>&1
print_result "List pending sessions (empty)" $?

python3 orchestrator.py --list-sessions > /dev/null 2>&1
print_result "List all sessions (empty)" $?

echo ""

# Test 2: Generate ideas (Stage 1)
echo -e "${YELLOW}[Test 2]${NC} Testing Stage 1: Generate Ideas..."
python3 orchestrator.py --config test_staged_config.yaml --generate-ideas --yes > /tmp/test_stage1.log 2>&1
exit_code=$?
print_result "Generate ideas stage" $exit_code

if [ $exit_code -eq 0 ]; then
    # Extract session ID from output (last occurrence, trimmed)
    SESSION_ID=$(grep "Session ID:" /tmp/test_stage1.log | tail -1 | awk '{print $NF}' | tr -d '\n\r')
    echo -e "${BLUE}   Created session: ${SESSION_ID}${NC}"
else
    echo -e "${RED}   Failed to generate ideas. Check /tmp/test_stage1.log${NC}"
    exit 1
fi

echo ""

# Test 3: Verify session state was created
echo -e "${YELLOW}[Test 3]${NC} Verifying session state file..."
if [ -f "sessions/${SESSION_ID}/session_state.json" ]; then
    print_result "Session state file exists" 0

    # Check stage is correct
    STAGE=$(jq -r '.stage' "sessions/${SESSION_ID}/session_state.json")
    if [ "$STAGE" == "ideas_generated" ]; then
        print_result "Session stage is 'ideas_generated'" 0
    else
        print_result "Session stage is 'ideas_generated'" 1
    fi

    # Check topics were saved
    TOPIC_COUNT=$(jq '.topics | length' "sessions/${SESSION_ID}/session_state.json")
    if [ "$TOPIC_COUNT" -gt 0 ]; then
        echo -e "${BLUE}   Found ${TOPIC_COUNT} topics${NC}"
        print_result "Topics were saved in state" 0
    else
        print_result "Topics were saved in state" 1
    fi
else
    print_result "Session state file exists" 1
fi

echo ""

# Test 4: Verify pending reviews index
echo -e "${YELLOW}[Test 4]${NC} Verifying pending reviews index..."
if [ -f "sessions/pending_reviews.json" ]; then
    print_result "Pending reviews index exists" 0

    # Check session is in pending reviews
    PENDING_COUNT=$(jq '.pending_reviews | length' sessions/pending_reviews.json)
    if [ "$PENDING_COUNT" -gt 0 ]; then
        echo -e "${BLUE}   Found ${PENDING_COUNT} pending session(s)${NC}"
        print_result "Session added to pending reviews" 0
    else
        print_result "Session added to pending reviews" 1
    fi
else
    print_result "Pending reviews index exists" 1
fi

echo ""

# Test 5: List pending sessions (should show our session)
echo -e "${YELLOW}[Test 5]${NC} Testing list-pending with active session..."
python3 orchestrator.py --list-pending > /tmp/test_list_pending.log 2>&1
if grep -q "$SESSION_ID" /tmp/test_list_pending.log; then
    print_result "Session appears in pending list" 0
else
    print_result "Session appears in pending list" 1
fi

echo ""

# Test 6: Review session (Stage 2)
echo -e "${YELLOW}[Test 6]${NC} Testing Stage 2: Review Session..."
# Auto-confirm will select all topics
python3 orchestrator.py --review --session "$SESSION_ID" --yes > /tmp/test_stage2.log 2>&1
exit_code=$?
print_result "Review session stage" $exit_code

if [ $exit_code -eq 0 ]; then
    # Verify stage changed to 'reviewed'
    STAGE=$(jq -r '.stage' "sessions/${SESSION_ID}/session_state.json")
    if [ "$STAGE" == "reviewed" ]; then
        print_result "Session stage is 'reviewed'" 0
    else
        print_result "Session stage is 'reviewed'" 1
    fi

    # Verify selected topics were saved
    SELECTED_COUNT=$(jq '.selected_topics | length' "sessions/${SESSION_ID}/session_state.json")
    if [ "$SELECTED_COUNT" -gt 0 ]; then
        echo -e "${BLUE}   Selected ${SELECTED_COUNT} topic(s)${NC}"
        print_result "Selected topics saved in state" 0
    else
        print_result "Selected topics saved in state" 1
    fi
else
    echo -e "${RED}   Failed to review session. Check /tmp/test_stage2.log${NC}"
fi

echo ""

# Test 7: Verify moved to awaiting generation
echo -e "${YELLOW}[Test 7]${NC} Verifying session moved to awaiting generation..."
if [ -f "sessions/pending_reviews.json" ]; then
    AWAITING_COUNT=$(jq '.reviewed_awaiting_generation | length' sessions/pending_reviews.json)
    if [ "$AWAITING_COUNT" -gt 0 ]; then
        echo -e "${BLUE}   Found ${AWAITING_COUNT} session(s) awaiting generation${NC}"
        print_result "Session in awaiting generation list" 0
    else
        print_result "Session in awaiting generation list" 1
    fi
fi

echo ""

# Test 8: Generate documents (Stage 3)
echo -e "${YELLOW}[Test 8]${NC} Testing Stage 3: Generate Documents..."
python3 orchestrator.py --generate-docs --session "$SESSION_ID" --yes > /tmp/test_stage3.log 2>&1
exit_code=$?
print_result "Generate documents stage" $exit_code

if [ $exit_code -eq 0 ]; then
    # Verify stage changed to 'completed'
    STAGE=$(jq -r '.stage' "sessions/${SESSION_ID}/session_state.json")
    if [ "$STAGE" == "completed" ]; then
        print_result "Session stage is 'completed'" 0
    else
        print_result "Session stage is 'completed'" 1
    fi

    # Verify documents were generated
    DOC_COUNT=$(jq '.generated_documents | length' "sessions/${SESSION_ID}/session_state.json")
    if [ "$DOC_COUNT" -gt 0 ]; then
        echo -e "${BLUE}   Generated ${DOC_COUNT} document(s)${NC}"
        print_result "Documents tracked in state" 0
    else
        print_result "Documents tracked in state" 1
    fi

    # Check if output files exist
    if [ -d "test_output" ] && [ "$(ls -A test_output/*.md 2>/dev/null | wc -l)" -gt 0 ]; then
        OUTPUT_FILES=$(ls test_output/*.md 2>/dev/null | wc -l)
        echo -e "${BLUE}   Found ${OUTPUT_FILES} output file(s)${NC}"
        print_result "Output files created" 0
    else
        print_result "Output files created" 1
    fi
else
    echo -e "${RED}   Failed to generate documents. Check /tmp/test_stage3.log${NC}"
fi

echo ""

# Test 9: List all sessions (should show completed session)
echo -e "${YELLOW}[Test 9]${NC} Testing list-sessions with completed session..."
python3 orchestrator.py --list-sessions > /tmp/test_list_all.log 2>&1
if grep -q "$SESSION_ID" /tmp/test_list_all.log; then
    print_result "Completed session appears in list" 0
else
    print_result "Completed session appears in list" 1
fi

echo ""

# Test 10: Error handling - try to review completed session
echo -e "${YELLOW}[Test 10]${NC} Testing error handling: Review completed session..."
python3 orchestrator.py --review --session "$SESSION_ID" --yes > /tmp/test_error1.log 2>&1
# Should exit with 0 but show warning message
if grep -q "already completed" /tmp/test_error1.log || grep -q "already reviewed" /tmp/test_error1.log; then
    print_result "Handles review of completed session" 0
else
    print_result "Handles review of completed session" 1
fi

echo ""

# Test 11: Error handling - try to generate docs for completed session
echo -e "${YELLOW}[Test 11]${NC} Testing error handling: Generate docs for completed session..."
python3 orchestrator.py --generate-docs --session "$SESSION_ID" --yes > /tmp/test_error2.log 2>&1
exit_code=$?
# Should fail with error
if [ $exit_code -ne 0 ] && grep -q "already completed" /tmp/test_error2.log; then
    print_result "Handles duplicate doc generation" 0
else
    print_result "Handles duplicate doc generation" 1
fi

echo ""

# Test 12: Backward compatibility - full sequential mode still works
echo -e "${YELLOW}[Test 12]${NC} Testing backward compatibility: Full sequential mode..."
python3 orchestrator.py --config test_staged_config.yaml --yes > /tmp/test_full.log 2>&1
exit_code=$?
print_result "Full sequential mode still works" $exit_code

echo ""
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo -e "${BLUE}   Test Results Summary${NC}"
echo -e "${BLUE}═══════════════════════════════════════════════════${NC}"
echo ""
echo -e "${GREEN}Tests Passed: ${TESTS_PASSED}${NC}"
echo -e "${RED}Tests Failed: ${TESTS_FAILED}${NC}"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
    echo -e "${GREEN}✓ All tests passed!${NC}"
    exit 0
else
    echo -e "${RED}✗ Some tests failed. Check log files in /tmp/test_*.log${NC}"
    exit 1
fi
