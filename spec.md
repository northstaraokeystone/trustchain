# TrustChain v1.0 Specification

## Purpose
Transform cryptographic receipts into binary trust indicators (Green/Yellow/Red) that operators can understand in <5 seconds.

## Core Question
"Can I trust this AI decision?"
- ✅ Green (85-100): Trust it
- ⚠️ Yellow (60-84): Review it
- ❌ Red (0-59): Override it

## Inputs
- Receipt JSON from Flight Recorder (receipts.jsonl)
- Fields extracted: confidence, sources, approver, monte_carlo_validated, human_verified

## Outputs
- Trust score: 0-100 integer
- Traffic light: Green/Yellow/Red emoji + 2-sentence summary
- trust_receipt: Emitted for every computation

## Receipt Types

### trust_receipt
```json
{
  "receipt_type": "trustchain_trust_score",
  "ts": "ISO8601",
  "tenant_id": "string",
  "source_receipt_hash": "dual_hash",
  "trust_score": "0-100",
  "trust_level": "GREEN|YELLOW|RED",
  "source_count": "integer",
  "approver": "string|null",
  "confidence": "0.0-1.0",
  "monte_carlo_passed": "boolean",
  "human_verified": "boolean",
  "summary_line_1": "string",
  "summary_line_2": "string",
  "payload_hash": "dual_hash"
}
```

### error_receipt
Standard CLAUDEME error_receipt for malformed JSON, missing files.

### anomaly_receipt
Standard CLAUDEME anomaly_receipt for trust score outliers (>2σ).

### bias_receipt
Standard CLAUDEME bias_receipt for cross-domain disparity (≥0.005).

### watchdog_health_receipt
```json
{
  "receipt_type": "watchdog_health",
  "ts": "ISO8601",
  "tenant_id": "string",
  "status": "healthy|unhealthy",
  "checks_passed": "integer",
  "checks_failed": "integer",
  "payload_hash": "dual_hash"
}
```

## SLOs

| Metric | Threshold | Action |
|--------|-----------|--------|
| Ingestion latency | <1s per 1000 receipts | anomaly_receipt |
| Trust score computation | <10ms per receipt | anomaly_receipt |
| Rendering latency | <5ms per view | anomaly_receipt |
| Summary wordcount | ≤50 words | HALT (StopRule) |
| Crypto terms in summary | 0 | HALT (StopRule) |
| Trust score range | 0-100 | HALT (StopRule) |
| Receipt emission | 100% | HALT (StopRule) |
| Memory usage | <5.5GB | anomaly_receipt |
| Bias disparity | <0.005 | bias_receipt |

## Trust Score Algorithm

```
BASE_SCORE = 50

Add points:
- source_count ≥ 5: +20
- source_count ≥ 3: +10 (else)
- source_count ≥ 1: +5 (else)
- approver present: +15
- confidence ≥ 0.90: +20
- confidence ≥ 0.75: +10 (else)
- confidence ≥ 0.50: +5 (else)
- monte_carlo passed: +15
- human_verified: +20

TOTAL = min(100, sum(points))
```

## Stoprules

- `stoprule_trust_score_invalid`: Score not in [0, 100]
- `stoprule_summary_too_long`: Summary > 50 words
- `stoprule_crypto_in_summary`: Summary contains sha256, blake3, merkle, hash
- `stoprule_malformed_receipt`: JSON parse error (emit error, continue)

## Rollback
Not applicable - read-only consumption of Flight Recorder receipts.

## Gates

### T+2h (Skeleton)
- spec.md exists
- ledger_schema.json exists
- cli.py emits receipt
- core functions work (dual_hash, emit_receipt, merkle, StopRule)

### T+24h (MVP)
- All tests pass
- Receipt emission in all src/*.py
- BASELINE scenario passes
- No single hash usage
- No crypto in summaries

### T+48h (Hardened)
- Anomaly detection active
- Bias checking active
- Stoprules active
- Watchdog healthy
- All 3 scenarios pass
- Streamlit demo works
- Integration test passes

## Files (14 total)

```
trustchain/
├── spec.md
├── ledger_schema.json
├── cli.py
├── receipts.jsonl
├── watchdog.py
├── src/
│   ├── __init__.py
│   ├── core.py
│   ├── ingest.py
│   ├── trust_score.py
│   └── traffic_light.py
├── demo/
│   └── streamlit_app.py
├── sim/
│   ├── sim.py
│   └── scenarios.py
├── tests/
│   ├── test_trust_score.py
│   ├── test_traffic_light.py
│   └── test_ingest.py
├── gate_t2h.sh
├── gate_t24h.sh
└── gate_t48h.sh
```
