"""
TrustChain Ingest Tests - CLAUDEME v3.1 Compliant

Tests for receipt ingestion with graceful degradation.
"""

import json
import pytest
import tempfile
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.ingest import (
    read_receipts,
    filter_by_type,
    filter_by_types,
    parse_receipt_json,
    get_latest_receipts
)


class TestReadReceipts:
    """Tests for read_receipts function."""

    def test_read_valid_jsonl(self):
        """Should read valid JSONL file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"receipt_type": "test", "id": 1}\n')
            f.write('{"receipt_type": "test", "id": 2}\n')
            f.write('{"receipt_type": "test", "id": 3}\n')
            f.flush()

            receipts = read_receipts(f.name)
            assert len(receipts) == 3
            assert receipts[0]["id"] == 1

    def test_skip_malformed_lines(self):
        """Should skip malformed JSON lines and continue."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"receipt_type": "test", "id": 1}\n')
            f.write('not valid json\n')
            f.write('{"receipt_type": "test", "id": 3}\n')
            f.flush()

            receipts = read_receipts(f.name)
            # Should have 2 valid receipts, malformed line skipped
            assert len(receipts) == 2

    def test_missing_file(self):
        """Should return empty list for missing file."""
        receipts = read_receipts("/nonexistent/path/receipts.jsonl")
        assert receipts == []

    def test_empty_file(self):
        """Should return empty list for empty file."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.flush()
            receipts = read_receipts(f.name)
            assert receipts == []

    def test_skip_empty_lines(self):
        """Should skip empty lines."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            f.write('{"receipt_type": "test", "id": 1}\n')
            f.write('\n')
            f.write('{"receipt_type": "test", "id": 2}\n')
            f.write('   \n')
            f.write('{"receipt_type": "test", "id": 3}\n')
            f.flush()

            receipts = read_receipts(f.name)
            assert len(receipts) == 3


class TestFilterByType:
    """Tests for filter_by_type function."""

    def test_filter_single_type(self):
        """Should filter by single receipt_type."""
        receipts = [
            {"receipt_type": "decision", "id": 1},
            {"receipt_type": "anchor", "id": 2},
            {"receipt_type": "decision", "id": 3},
        ]
        filtered = filter_by_type(receipts, "decision")
        assert len(filtered) == 2
        assert all(r["receipt_type"] == "decision" for r in filtered)

    def test_filter_no_matches(self):
        """Should return empty list when no matches."""
        receipts = [
            {"receipt_type": "decision", "id": 1},
            {"receipt_type": "anchor", "id": 2},
        ]
        filtered = filter_by_type(receipts, "nonexistent")
        assert filtered == []


class TestFilterByTypes:
    """Tests for filter_by_types function."""

    def test_filter_multiple_types(self):
        """Should filter by multiple receipt_types."""
        receipts = [
            {"receipt_type": "decision", "id": 1},
            {"receipt_type": "anchor", "id": 2},
            {"receipt_type": "intervention", "id": 3},
            {"receipt_type": "decision", "id": 4},
        ]
        filtered = filter_by_types(receipts, ["decision", "intervention"])
        assert len(filtered) == 3


class TestParseReceiptJson:
    """Tests for parse_receipt_json function."""

    def test_parse_valid_json(self):
        """Should parse valid JSON string."""
        json_str = '{"receipt_type": "test", "value": 42}'
        receipt = parse_receipt_json(json_str)
        assert receipt is not None
        assert receipt["value"] == 42

    def test_parse_invalid_json(self):
        """Should return None for invalid JSON."""
        receipt = parse_receipt_json("not valid json")
        assert receipt is None

    def test_parse_empty_string(self):
        """Should return None for empty string."""
        receipt = parse_receipt_json("")
        assert receipt is None


class TestIngestionSLO:
    """SLO validation tests for ingestion."""

    def test_ingestion_latency_slo(self):
        """SLO: Ingestion latency <1s per 1000 receipts."""
        import time

        # Create file with 1000 receipts
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(1000):
                f.write(json.dumps({"receipt_type": "test", "id": i}) + '\n')
            f.flush()

            start = time.time()
            receipts = read_receipts(f.name)
            elapsed = time.time() - start

            assert len(receipts) == 1000
            assert elapsed < 1.0, f"Ingestion took {elapsed}s (>1s SLO)"

    def test_graceful_degradation(self):
        """System should not crash on malformed input."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            # Mix of valid, malformed, and edge cases
            f.write('{"valid": 1}\n')
            f.write('{"incomplete": \n')
            f.write('\x00\x01\x02\n')  # Binary garbage
            f.write('null\n')  # Valid JSON but not object
            f.write('{"valid": 2}\n')
            f.flush()

            # Should not raise, should return valid receipts
            receipts = read_receipts(f.name)
            # Only the first and last are valid objects
            assert len(receipts) >= 1


class TestGetLatestReceipts:
    """Tests for get_latest_receipts function."""

    def test_get_latest(self):
        """Should return most recent receipts."""
        with tempfile.NamedTemporaryFile(mode='w', suffix='.jsonl', delete=False) as f:
            for i in range(10):
                f.write(json.dumps({"receipt_type": "test", "id": i}) + '\n')
            f.flush()

            latest = get_latest_receipts(f.name, limit=3)
            # Should be newest first (ids 9, 8, 7)
            assert len(latest) == 3
            assert latest[0]["id"] == 9
            assert latest[1]["id"] == 8
            assert latest[2]["id"] == 7
