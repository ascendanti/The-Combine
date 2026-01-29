#!/bin/bash
# HookBus Smoke Test - PHASE 3
#
# Usage: ./scripts/smoke_hooks.sh
#
# Tests:
# 1. HookBus CLI commands work
# 2. Database is created/accessible
# 3. Metrics collection works
# 4. Cleanup runs without error

set -e

DAEMON_DIR="$(dirname "$0")/../daemon"
cd "$DAEMON_DIR/.."

echo "=== HookBus Smoke Test ==="
echo ""

# Test 1: Status command
echo "[1/5] Testing status command..."
HOOKBUS_ENABLED=0 python daemon/hook_bus.py status
echo "  ✓ Status OK"
echo ""

# Test 2: Self-test
echo "[2/5] Running self-test..."
python daemon/hook_bus.py test
echo "  ✓ Self-test OK"
echo ""

# Test 3: Metrics command
echo "[3/5] Testing metrics retrieval..."
HOOKBUS_ENABLED=1 python daemon/hook_bus.py metrics
echo "  ✓ Metrics OK"
echo ""

# Test 4: Cleanup command
echo "[4/5] Testing cleanup..."
python daemon/hook_bus.py cleanup
echo "  ✓ Cleanup OK"
echo ""

# Test 5: Database exists and is readable
echo "[5/5] Checking database..."
if [ -f "daemon/hook_bus.db" ]; then
    sqlite3 daemon/hook_bus.db "SELECT COUNT(*) FROM hook_logs;" > /dev/null 2>&1
    echo "  ✓ Database OK"
else
    echo "  ⚠ Database not created yet (normal if never enabled)"
fi
echo ""

# Test 6: Unit tests (if pytest available)
echo "[BONUS] Running unit tests..."
if command -v pytest &> /dev/null; then
    python -m pytest daemon/tests/test_hook_bus.py -v --tb=line -q
    echo "  ✓ Unit tests OK"
else
    echo "  ⚠ pytest not available, skipping"
fi
echo ""

echo "=== Smoke Test Complete ==="
echo ""
echo "HookBus is ready for integration."
echo "Enable with: HOOKBUS_ENABLED=1"
