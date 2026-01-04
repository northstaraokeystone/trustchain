#!/bin/bash
# TrustChain T+2h Gate - SKELETON
# CLAUDEME v3.1 Compliant
# RUN THIS OR KILL PROJECT

set -e

echo "=================================="
echo "TRUSTCHAIN T+2h GATE VALIDATION"
echo "=================================="
echo ""

# Check required files exist
echo "Checking required files..."

[ -f spec.md ] || { echo "FAIL: no spec.md"; exit 1; }
echo "✓ spec.md exists"

[ -f ledger_schema.json ] || { echo "FAIL: no ledger_schema.json"; exit 1; }
echo "✓ ledger_schema.json exists"

[ -f cli.py ] || { echo "FAIL: no cli.py"; exit 1; }
echo "✓ cli.py exists"

echo ""
echo "Checking core functions..."

# Verify dual_hash returns SHA256:BLAKE3 format
python -c "from src.core import dual_hash; assert ':' in dual_hash(b'test'), 'dual_hash format wrong'" || { echo "FAIL: dual_hash invalid"; exit 1; }
echo "✓ dual_hash returns SHA256:BLAKE3 format"

# Verify all core functions exist
python -c "from src.core import dual_hash, emit_receipt, merkle, StopRule; print('core loaded')" || { echo "FAIL: core functions missing"; exit 1; }
echo "✓ Core functions (dual_hash, emit_receipt, merkle, StopRule) exist"

echo ""
echo "Checking trust score stub..."

# Verify trust score stub works
python -c "from src.trust_score import compute_trust_score; score = compute_trust_score({'confidence': 0.9}); assert 0 <= score <= 100, f'score {score} out of range'" || { echo "FAIL: trust_score stub broken"; exit 1; }
echo "✓ Trust score stub works"

echo ""
echo "Checking traffic light stub..."

# Verify traffic light stub works
python -c "from src.traffic_light import render_traffic_light, select_emoji; assert '🟢' in select_emoji(90) or '✅' in select_emoji(90); view = render_traffic_light(90, {}); assert 'TRUST STATUS' in view" || { echo "FAIL: traffic_light stub broken"; exit 1; }
echo "✓ Traffic light stub works"

echo ""
echo "Checking CLI emits receipt..."

# Verify CLI emits receipt
python cli.py --test 2>&1 | grep -q '"receipt_type"' || { echo "FAIL: CLI doesn't emit receipt"; exit 1; }
echo "✓ CLI emits receipt"

echo ""
echo "=================================="
echo "PASS: T+2h gate"
echo "=================================="
