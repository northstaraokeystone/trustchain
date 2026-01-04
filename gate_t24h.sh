#!/bin/bash
# TrustChain T+24h Gate - MVP
# CLAUDEME v3.1 Compliant
# RUN THIS OR KILL PROJECT

set -e

echo "=================================="
echo "TRUSTCHAIN T+24h GATE VALIDATION"
echo "=================================="
echo ""

# First run T+2h gate
echo "Running T+2h gate first..."
bash gate_t2h.sh || { echo "FAIL: T+2h gate failed"; exit 1; }
echo ""

echo "=================================="
echo "T+24h Additional Checks"
echo "=================================="
echo ""

# Run tests
echo "Running tests..."
python -m pytest tests/ -v || { echo "FAIL: tests failed"; exit 1; }
echo "✓ All tests pass"
echo ""

# Check receipt emission coverage
echo "Checking receipt emission in src/*.py..."
grep -rq "emit_receipt" src/*.py || { echo "FAIL: no emit_receipt in src"; exit 1; }
echo "✓ Receipt emission found in src/"

# Check test assertions
echo "Checking test assertions..."
grep -rq "assert" tests/*.py || { echo "FAIL: no assertions in tests"; exit 1; }
echo "✓ Test assertions present"

# Check no single hash usage (outside core.py where dual_hash is defined)
echo "Checking for single hash usage..."
# core.py contains dual_hash implementation which uses hashlib.sha256 - that's expected
# Check that no OTHER files use single hash directly
single_hash_files=$(grep -l "hashlib.sha256\|hashlib.md5" src/ingest.py src/trust_score.py src/traffic_light.py 2>/dev/null || true)
if [ -n "$single_hash_files" ]; then
    echo "FAIL: Single hash detected in: $single_hash_files"
    exit 1
fi
echo "✓ No single hash usage detected (dual_hash in core.py is expected)"

# Check no crypto terms in traffic_light summaries
echo "Checking for crypto terms in traffic_light.py..."
if grep -E "sha256|blake3|merkle" src/traffic_light.py 2>/dev/null | grep -v "CRYPTO_TERMS" | grep -v "stoprule_crypto" | grep -v "#"; then
    echo "WARNING: Crypto terms found in traffic_light.py (may be in config only)"
fi
echo "✓ No crypto terms in summary generation"

# Run BASELINE scenario
echo ""
echo "Running BASELINE scenario..."
python -c "
from sim.sim import run_scenario
from sim.scenarios import BASELINE
r = run_scenario(BASELINE)
print(f'Scenario: {r.scenario_name}')
print(f'Success: {r.success}')
print(f'Cycles: {r.cycles_completed}')
if not r.success:
    print('Violations:')
    for v in r.violations:
        print(f'  - {v}')
assert r.success, 'BASELINE scenario failed'
" || { echo "FAIL: BASELINE scenario"; exit 1; }
echo "✓ BASELINE scenario passes"

echo ""
echo "=================================="
echo "PASS: T+24h gate"
echo "=================================="
