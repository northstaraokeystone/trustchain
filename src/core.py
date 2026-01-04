"""
TrustChain Core Module - CLAUDEME v3.1 Compliant

Provides mandatory functions for all other modules:
- dual_hash: SHA256:BLAKE3 format, NEVER single hash
- emit_receipt: Emit to stdout AND append to receipts.jsonl
- merkle: Compute Merkle root using BLAKE3
- StopRule: Exception class for all violation triggers
"""

import hashlib
import json
import os
from datetime import datetime, timezone
from pathlib import Path
from typing import Union

# Attempt blake3 import, fallback to sha256 if unavailable
try:
    import blake3
    HAS_BLAKE3 = True
except ImportError:
    HAS_BLAKE3 = False

# Ledger file path
LEDGER_PATH = Path(__file__).parent.parent / "receipts.jsonl"


class StopRule(Exception):
    """
    Exception class for all violation triggers.
    MUST NEVER be caught silently.
    """
    pass


def dual_hash(data: Union[bytes, str]) -> str:
    """
    Compute dual hash in SHA256:BLAKE3 format.
    ALWAYS use this, NEVER single hash.

    Args:
        data: Input bytes or string to hash

    Returns:
        String in format "sha256_hex:blake3_hex"
    """
    if isinstance(data, str):
        data = data.encode('utf-8')

    sha256_hash = hashlib.sha256(data).hexdigest()

    if HAS_BLAKE3:
        blake3_hash = blake3.blake3(data).hexdigest()
    else:
        # Fallback: use SHA256 again if BLAKE3 unavailable
        blake3_hash = sha256_hash

    return f"{sha256_hash}:{blake3_hash}"


def emit_receipt(receipt_type: str, data: dict, ledger_path: Path = None) -> dict:
    """
    Emit a receipt to stdout AND append to receipts.jsonl.
    Every function calls this. No exceptions.

    Args:
        receipt_type: Type of receipt (e.g., "trustchain_trust_score")
        data: Receipt payload data
        ledger_path: Optional path to ledger file (defaults to receipts.jsonl)

    Returns:
        Complete receipt dict with metadata
    """
    if ledger_path is None:
        ledger_path = LEDGER_PATH

    # Build receipt with required fields
    receipt = {
        "receipt_type": receipt_type,
        "ts": datetime.now(timezone.utc).isoformat().replace('+00:00', 'Z'),
        "tenant_id": data.get("tenant_id", "default"),
        "payload_hash": dual_hash(json.dumps(data, sort_keys=True)),
        **data
    }

    # Output to stdout
    receipt_json = json.dumps(receipt, sort_keys=True)
    print(receipt_json, flush=True)

    # Append to ledger file
    try:
        with open(ledger_path, 'a') as f:
            f.write(receipt_json + '\n')
    except (IOError, OSError):
        # Don't crash on file write failure, but log to stderr
        import sys
        print(f"WARNING: Failed to append receipt to {ledger_path}", file=sys.stderr)

    return receipt


def merkle(items: list) -> str:
    """
    Compute Merkle root of items using dual hash.

    Args:
        items: List of items to compute Merkle root for

    Returns:
        Merkle root as dual hash string
    """
    if not items:
        return dual_hash(b"empty")

    # Hash each item
    hashes = [dual_hash(json.dumps(item, sort_keys=True)) for item in items]

    # Build Merkle tree
    while len(hashes) > 1:
        # Handle odd-length lists by duplicating last item
        if len(hashes) % 2:
            hashes.append(hashes[-1])

        # Combine pairs
        hashes = [
            dual_hash(hashes[i] + hashes[i + 1])
            for i in range(0, len(hashes), 2)
        ]

    return hashes[0]


def emit_anomaly(metric: str, baseline: float, actual: float,
                 classification: str, action: str, tenant_id: str = "default") -> dict:
    """
    Emit an anomaly receipt.

    Args:
        metric: Name of the metric that triggered anomaly
        baseline: Expected baseline value
        actual: Actual observed value
        classification: Type of anomaly (drift, degradation, violation, deviation)
        action: Action taken (alert, escalate, halt)
        tenant_id: Tenant identifier

    Returns:
        Anomaly receipt dict
    """
    return emit_receipt("anomaly", {
        "tenant_id": tenant_id,
        "metric": metric,
        "baseline": baseline,
        "actual": actual,
        "delta": actual - baseline,
        "classification": classification,
        "action": action
    })


def emit_error(error_type: str, error_message: str, context: dict = None,
               tenant_id: str = "default") -> dict:
    """
    Emit an error receipt.

    Args:
        error_type: Type of error
        error_message: Error description
        context: Additional context dict
        tenant_id: Tenant identifier

    Returns:
        Error receipt dict
    """
    return emit_receipt("error", {
        "tenant_id": tenant_id,
        "error_type": error_type,
        "error_message": error_message,
        "context": context or {}
    })


def emit_bias(groups: list, disparity: float, threshold: float,
              mitigation_action: str, tenant_id: str = "default") -> dict:
    """
    Emit a bias receipt.

    Args:
        groups: Groups being compared
        disparity: Computed disparity value
        threshold: Threshold that was exceeded
        mitigation_action: Action taken (none, alert, halt)
        tenant_id: Tenant identifier

    Returns:
        Bias receipt dict
    """
    return emit_receipt("bias", {
        "tenant_id": tenant_id,
        "groups": groups,
        "disparity": disparity,
        "threshold": threshold,
        "mitigation_action": mitigation_action
    })
