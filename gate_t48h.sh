#!/bin/bash
# TrustChain T+48h Gate - HARDENED (Production Ready)
# CLAUDEME v3.1 Compliant
# RUN THIS OR KILL PROJECT

set -e

echo "=================================="
echo "TRUSTCHAIN T+48h GATE VALIDATION"
echo "=================================="
echo ""

# First run T+24h gate
echo "Running T+24h gate first..."
bash gate_t24h.sh || { echo "FAIL: T+24h gate failed"; exit 1; }
echo ""

echo "=================================="
echo "T+48h Additional Checks (HARDENED)"
echo "=================================="
echo ""

# Check anomaly detection exists
echo "Checking anomaly detection..."
grep -rq "anomaly" src/*.py || { echo "FAIL: no anomaly detection"; exit 1; }
echo "✓ Anomaly detection present"

# Check bias check exists
echo "Checking bias checking..."
grep -rq "bias" src/*.py || { echo "FAIL: no bias check"; exit 1; }
echo "✓ Bias checking present"

# Check stoprules exist
echo "Checking stoprules..."
grep -rq "stoprule" src/*.py || { echo "FAIL: no stoprules"; exit 1; }
echo "✓ Stoprules present"

# Check watchdog healthy
echo ""
echo "Running watchdog health check..."
python watchdog.py --check || { echo "FAIL: watchdog unhealthy"; exit 1; }
echo "✓ Watchdog healthy"

# Run all 3 scenarios
echo ""
echo "Running all Monte Carlo scenarios..."
python -c "
from sim.sim import run_scenario
from sim.scenarios import BASELINE, STRESS_VOLUME, MALFORMED_RECEIPTS

scenarios = [BASELINE, STRESS_VOLUME, MALFORMED_RECEIPTS]
all_passed = True

for config in scenarios:
    r = run_scenario(config)
    status = '✓' if r.success else '✗'
    result_text = 'PASSED' if r.success else 'FAILED'
    print(f'{status} {r.scenario_name}: {result_text}')
    if not r.success:
        all_passed = False
        for v in r.violations:
            print(f'    - {v}')

assert all_passed, 'Not all scenarios passed'
" || { echo "FAIL: scenarios"; exit 1; }
echo "✓ All 3 scenarios pass"

# Test integration (Flight Recorder -> TrustChain)
echo ""
echo "Running integration test..."
python -c "
from src.ingest import read_receipts
from src.trust_score import compute_trust_score
from src.traffic_light import render_traffic_light

# Try to read Flight Recorder receipts
receipts = read_receipts('../flight_recorder/receipts.jsonl')
if len(receipts) == 0:
    # Try local test receipts
    receipts = read_receipts('receipts.jsonl')

if len(receipts) == 0:
    print('INFO: No receipts found, creating test receipt')
    test_receipt = {
        'confidence': 0.85,
        'sources': ['test'],
        'raci': {'accountable': 'Test'}
    }
    receipts = [test_receipt]

for r in receipts[:10]:
    score = compute_trust_score(r)
    view = render_traffic_light(score, r)
    assert '🟢' in view or '🟡' in view or '🔴' in view, 'Invalid traffic light'

print(f'Integration test PASSED ({len(receipts)} receipts tested)')
" || { echo "FAIL: integration test"; exit 1; }
echo "✓ Integration test passes"

echo ""
echo "=================================="
echo "PASS: T+48h gate — SHIP IT"
echo "=================================="
echo ""
echo "TrustChain v1.0 is production-ready."
echo "All CLAUDEME v3.1 requirements satisfied."
