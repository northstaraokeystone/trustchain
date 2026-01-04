"""
TrustChain Trust Score Tests - CLAUDEME v3.1 Compliant

Tests for trust score computation, anomaly detection, and bias checking.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import StopRule
from src.trust_score import (
    compute_trust_score,
    extract_sources,
    extract_approver,
    extract_confidence,
    check_monte_carlo,
    check_human_verified,
    detect_trust_anomaly,
    check_trust_bias,
    get_trust_level
)


class TestComputeTrustScore:
    """Tests for compute_trust_score function."""

    def test_base_score(self):
        """Empty receipt should return base score of 50."""
        receipt = {}
        score = compute_trust_score(receipt)
        assert score == 50

    def test_high_trust_receipt(self):
        """High trust receipt should score 85+."""
        receipt = {
            "confidence": 0.95,
            "sources": ["a", "b", "c", "d", "e"],
            "raci": {"accountable": "CPT Anderson"},
            "monte_carlo_validated": True,
            "human_verified": True
        }
        score = compute_trust_score(receipt)
        assert 85 <= score <= 100

    def test_medium_trust_receipt(self):
        """Medium trust receipt should score 60-84."""
        receipt = {
            "confidence": 0.55,
            "sources": ["a"],
        }
        score = compute_trust_score(receipt)
        assert 60 <= score <= 84

    def test_low_trust_receipt(self):
        """Low trust receipt should score <60."""
        receipt = {
            "confidence": 0.45,
            "sources": []
        }
        score = compute_trust_score(receipt)
        assert score < 60

    def test_score_capped_at_100(self):
        """Score should never exceed 100."""
        receipt = {
            "confidence": 0.99,
            "sources": ["a", "b", "c", "d", "e", "f", "g", "h"],
            "raci": {"accountable": "CPT Anderson"},
            "approver": "COL Smith",
            "monte_carlo_validated": True,
            "human_verified": True
        }
        score = compute_trust_score(receipt)
        assert score <= 100

    def test_score_range_slo(self):
        """SLO: Score must be in range [0, 100]."""
        receipt = {"confidence": 0.5}
        score = compute_trust_score(receipt)
        assert 0 <= score <= 100


class TestExtractSources:
    """Tests for extract_sources function."""

    def test_sources_list(self):
        """Should extract source count from sources list."""
        receipt = {"sources": ["a", "b", "c"]}
        assert extract_sources(receipt) == 3

    def test_source_count_field(self):
        """Should use source_count if provided."""
        receipt = {"source_count": 5}
        assert extract_sources(receipt) == 5

    def test_sources_in_payload(self):
        """Should extract sources from payload."""
        # Only checks payload if no top-level sources field
        receipt = {"payload": {"sources": ["a", "b"]}}
        assert extract_sources(receipt) == 2

    def test_empty_sources(self):
        """Should return 0 for empty sources."""
        receipt = {"sources": []}
        assert extract_sources(receipt) == 0

    def test_missing_sources(self):
        """Should return 0 for missing sources."""
        receipt = {}
        assert extract_sources(receipt) == 0


class TestExtractApprover:
    """Tests for extract_approver function."""

    def test_direct_approver(self):
        """Should extract direct approver field."""
        receipt = {"approver": "CPT Anderson"}
        assert extract_approver(receipt) == "CPT Anderson"

    def test_raci_accountable(self):
        """Should extract accountable from RACI."""
        receipt = {"raci": {"accountable": "SGT Williams"}}
        assert extract_approver(receipt) == "SGT Williams"

    def test_approver_in_payload(self):
        """Should extract approver from payload."""
        receipt = {"payload": {"approver": "LT Jones"}}
        assert extract_approver(receipt) == "LT Jones"

    def test_missing_approver(self):
        """Should return None for missing approver."""
        receipt = {}
        assert extract_approver(receipt) is None


class TestExtractConfidence:
    """Tests for extract_confidence function."""

    def test_direct_confidence(self):
        """Should extract direct confidence field."""
        receipt = {"confidence": 0.85}
        assert extract_confidence(receipt) == 0.85

    def test_percentage_format(self):
        """Should convert percentage to 0-1 range."""
        receipt = {"confidence": 85}
        assert extract_confidence(receipt) == 0.85

    def test_confidence_in_payload(self):
        """Should extract confidence from payload."""
        receipt = {"payload": {"confidence": 0.72}}
        assert extract_confidence(receipt) == 0.72

    def test_missing_confidence(self):
        """Should return None for missing confidence."""
        receipt = {}
        assert extract_confidence(receipt) is None


class TestCheckMonteCarlo:
    """Tests for check_monte_carlo function."""

    def test_monte_carlo_validated(self):
        """Should detect monte_carlo_validated."""
        receipt = {"monte_carlo_validated": True}
        assert check_monte_carlo(receipt) is True

    def test_monte_carlo_passed(self):
        """Should detect monte_carlo_passed."""
        receipt = {"monte_carlo_passed": True}
        assert check_monte_carlo(receipt) is True

    def test_no_monte_carlo(self):
        """Should return False if not validated."""
        receipt = {}
        assert check_monte_carlo(receipt) is False


class TestCheckHumanVerified:
    """Tests for check_human_verified function."""

    def test_human_verified(self):
        """Should detect human_verified."""
        receipt = {"human_verified": True}
        assert check_human_verified(receipt) is True

    def test_human_approved(self):
        """Should detect human_approved."""
        receipt = {"human_approved": True}
        assert check_human_verified(receipt) is True

    def test_not_human_verified(self):
        """Should return False if not verified."""
        receipt = {}
        assert check_human_verified(receipt) is False


class TestDetectTrustAnomaly:
    """Tests for detect_trust_anomaly function."""

    def test_insufficient_data(self):
        """Should return False with <10 historical scores."""
        historical = [80, 82, 85]
        assert detect_trust_anomaly(90, historical) is False

    def test_normal_score(self):
        """Should return False for normal score."""
        historical = [80, 82, 78, 81, 79, 83, 80, 82, 81, 79]
        assert detect_trust_anomaly(80, historical) is False

    def test_anomaly_detected(self):
        """Should detect score >2σ from mean."""
        historical = [80, 82, 78, 81, 79, 83, 80, 82, 81, 79]  # mean ~80, std ~1.5
        # Score of 40 is way outside normal range
        assert detect_trust_anomaly(40, historical) is True


class TestCheckTrustBias:
    """Tests for check_trust_bias function."""

    def test_insufficient_groups(self):
        """Should return 0.0 with <2 domain groups."""
        scores = {"autonomy": [90, 85, 92]}
        assert check_trust_bias(scores) == 0.0

    def test_no_disparity(self):
        """Should return low disparity for similar scores."""
        scores = {
            "autonomy": [80, 82, 78],
            "compliance": [79, 81, 80]
        }
        disparity = check_trust_bias(scores)
        assert disparity < 0.005

    def test_high_disparity(self):
        """Should detect high disparity (≥0.005)."""
        scores = {
            "autonomy": [90, 85, 92],
            "compliance": [60, 65, 58]
        }
        disparity = check_trust_bias(scores)
        assert disparity >= 0.005


class TestGetTrustLevel:
    """Tests for get_trust_level function."""

    def test_green_level(self):
        """Score ≥85 should be GREEN."""
        assert get_trust_level(85) == "GREEN"
        assert get_trust_level(100) == "GREEN"

    def test_yellow_level(self):
        """Score 60-84 should be YELLOW."""
        assert get_trust_level(60) == "YELLOW"
        assert get_trust_level(84) == "YELLOW"

    def test_red_level(self):
        """Score <60 should be RED."""
        assert get_trust_level(59) == "RED"
        assert get_trust_level(0) == "RED"
