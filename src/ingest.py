"""
TrustChain Ingestion Module - CLAUDEME v3.1 Compliant

Read receipts from Flight Recorder's receipts.jsonl with graceful degradation.
"""

import json
from pathlib import Path
from typing import List, Dict, Optional

from .core import emit_error


def read_receipts(filepath: str) -> List[Dict]:
    """
    Read JSONL file, skip malformed lines.

    Args:
        filepath: Path to receipts.jsonl file

    Returns:
        List of receipt dicts (malformed lines skipped with error receipt)

    SLO: <1s per 1000 receipts
    """
    receipts = []
    path = Path(filepath)

    # Handle missing file gracefully
    if not path.exists():
        emit_error(
            error_type="file_not_found",
            error_message=f"Receipts file not found: {filepath}",
            context={"filepath": filepath}
        )
        return []

    try:
        with open(path, 'r') as f:
            for line_num, line in enumerate(f, start=1):
                line = line.strip()
                if not line:
                    continue

                try:
                    receipt = json.loads(line)
                    receipts.append(receipt)
                except json.JSONDecodeError as e:
                    # Emit error receipt on malformed JSON, skip line, continue
                    stoprule_malformed_receipt(line_num, str(e))

    except (IOError, OSError) as e:
        emit_error(
            error_type="file_read_error",
            error_message=f"Failed to read receipts file: {e}",
            context={"filepath": filepath}
        )
        return []

    return receipts


def filter_by_type(receipts: List[Dict], receipt_type: str) -> List[Dict]:
    """
    Filter receipts by receipt_type field.

    Args:
        receipts: List of receipt dicts
        receipt_type: Type to filter for

    Returns:
        Filtered list of receipts matching the type
    """
    return [r for r in receipts if r.get("receipt_type") == receipt_type]


def filter_by_types(receipts: List[Dict], receipt_types: List[str]) -> List[Dict]:
    """
    Filter receipts by multiple receipt_type values.

    Args:
        receipts: List of receipt dicts
        receipt_types: Types to filter for

    Returns:
        Filtered list of receipts matching any of the types
    """
    return [r for r in receipts if r.get("receipt_type") in receipt_types]


def stoprule_malformed_receipt(line_num: int, error: str) -> None:
    """
    Emit error receipt on malformed JSON (don't crash).

    Args:
        line_num: Line number with malformed JSON
        error: Error message from JSON parser
    """
    emit_error(
        error_type="malformed_receipt",
        error_message=f"Malformed JSON at line {line_num}: {error}",
        context={"line_number": line_num, "parse_error": error}
    )


def get_latest_receipts(filepath: str, limit: int = 100) -> List[Dict]:
    """
    Get the most recent receipts from the ledger.

    Args:
        filepath: Path to receipts.jsonl file
        limit: Maximum number of receipts to return

    Returns:
        List of most recent receipts (newest first)
    """
    receipts = read_receipts(filepath)
    return receipts[-limit:][::-1] if receipts else []


def parse_receipt_json(receipt_json: str) -> Optional[Dict]:
    """
    Parse a single receipt JSON string.

    Args:
        receipt_json: JSON string of a receipt

    Returns:
        Receipt dict or None if parsing fails
    """
    try:
        return json.loads(receipt_json)
    except json.JSONDecodeError as e:
        emit_error(
            error_type="malformed_receipt",
            error_message=f"Failed to parse receipt JSON: {e}",
            context={"json_preview": receipt_json[:100] if receipt_json else ""}
        )
        return None
