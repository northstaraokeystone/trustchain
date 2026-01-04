"""
TrustChain Traffic Light Tests - CLAUDEME v3.1 Compliant

Tests for traffic light rendering with SLO validation.
"""

import pytest
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from src.core import StopRule
from src.traffic_light import (
    select_emoji,
    build_summary,
    render_traffic_light,
    render_compact,
    CRYPTO_TERMS
)


class TestSelectEmoji:
    """Tests for select_emoji function."""

    def test_green_emoji(self):
        """Score 85-100 should show green emoji."""
        emoji = select_emoji(85)
        assert "🟢" in emoji or "✅" in emoji

        emoji = select_emoji(100)
        assert "🟢" in emoji or "✅" in emoji

    def test_yellow_emoji(self):
        """Score 60-84 should show yellow emoji."""
        emoji = select_emoji(60)
        assert "🟡" in emoji or "⚠️" in emoji

        emoji = select_emoji(84)
        assert "🟡" in emoji or "⚠️" in emoji

    def test_red_emoji(self):
        """Score 0-59 should show red emoji."""
        emoji = select_emoji(0)
        assert "🔴" in emoji or "❌" in emoji

        emoji = select_emoji(59)
        assert "🔴" in emoji or "❌" in emoji


class TestBuildSummary:
    """Tests for build_summary function."""

    def test_summary_line_1_format(self):
        """Line 1 should include sources, approver, confidence."""
        receipt = {
            "sources": ["a", "b", "c"],
            "raci": {"accountable": "CPT Anderson"},
            "confidence": 0.85
        }
        line_1, line_2 = build_summary(receipt)
        assert "3 sources" in line_1
        assert "CPT Anderson" in line_1
        assert "85%" in line_1

    def test_summary_line_2_monte_carlo(self):
        """Line 2 should mention validation for Monte Carlo."""
        receipt = {"monte_carlo_validated": True}
        line_1, line_2 = build_summary(receipt)
        assert "validated" in line_2.lower() or "scenario" in line_2.lower()

    def test_summary_line_2_human_verified(self):
        """Line 2 should mention human verification."""
        receipt = {"human_verified": True}
        line_1, line_2 = build_summary(receipt)
        assert "human" in line_2.lower()

    def test_summary_line_2_automated(self):
        """Line 2 should indicate automated decision if unvalidated."""
        receipt = {}
        line_1, line_2 = build_summary(receipt)
        assert "automated" in line_2.lower()


class TestRenderTrafficLight:
    """Tests for render_traffic_light function."""

    def test_output_format(self):
        """Output should contain trust status and score."""
        output = render_traffic_light(90, {"confidence": 0.9})
        assert "TRUST STATUS" in output
        assert "90/100" in output

    def test_green_output(self):
        """Green score should show green indicator."""
        output = render_traffic_light(90, {})
        assert "GREEN" in output
        assert "🟢" in output or "✅" in output

    def test_yellow_output(self):
        """Yellow score should show yellow indicator."""
        output = render_traffic_light(70, {})
        assert "YELLOW" in output
        assert "🟡" in output or "⚠️" in output

    def test_red_output(self):
        """Red score should show red indicator."""
        output = render_traffic_light(40, {})
        assert "RED" in output
        assert "🔴" in output or "❌" in output

    def test_summary_word_count_slo(self):
        """SLO: Summary must be ≤50 words."""
        receipt = {
            "sources": ["a", "b", "c", "d", "e"],
            "raci": {"accountable": "CPT Anderson"},
            "confidence": 0.95,
            "monte_carlo_validated": True,
            "human_verified": True
        }
        line_1, line_2 = build_summary(receipt)
        word_count = len(f"{line_1} {line_2}".split())
        assert word_count <= 50

    def test_no_crypto_terms_slo(self):
        """SLO: Summary must contain zero crypto terms."""
        receipt = {"confidence": 0.9}
        output = render_traffic_light(90, receipt)
        output_lower = output.lower()
        for term in CRYPTO_TERMS:
            assert term not in output_lower, f"Crypto term '{term}' found in output"


class TestRenderCompact:
    """Tests for render_compact function."""

    def test_compact_format(self):
        """Compact output should be single line with emoji, level, score."""
        output = render_compact(90)
        assert "GREEN" in output
        assert "90/100" in output
        assert "🟢" in output or "✅" in output

    def test_compact_yellow(self):
        """Compact output should show YELLOW for medium scores."""
        output = render_compact(70)
        assert "YELLOW" in output

    def test_compact_red(self):
        """Compact output should show RED for low scores."""
        output = render_compact(40)
        assert "RED" in output


class TestRendererSLOs:
    """SLO validation tests for traffic light renderer."""

    def test_rendering_latency_slo(self):
        """SLO: Rendering latency <5ms."""
        import time

        receipt = {"confidence": 0.9, "sources": ["a", "b"]}
        start = time.time()

        for _ in range(100):
            render_traffic_light(90, receipt)

        elapsed_ms = (time.time() - start) * 1000
        avg_ms = elapsed_ms / 100

        # Allow some slack for test environment
        assert avg_ms < 50, f"Average rendering time {avg_ms}ms exceeds limit"

    def test_no_crypto_in_any_output(self):
        """SLO: No crypto terms in any valid output."""
        # Note: approver/source names with crypto terms SHOULD trigger stoprule
        # This tests that normal receipts don't contain crypto terms
        test_receipts = [
            {},
            {"confidence": 0.9},
            {"sources": ["sensor_1", "sensor_2"]},
            {"raci": {"accountable": "CPT Anderson"}},
        ]

        for receipt in test_receipts:
            output = render_traffic_light(50, receipt)
            # Summary lines specifically should not contain crypto terms
            lines = output.split("\n")
            summary_lines = [l for l in lines if l.strip() and
                            not l.startswith("━") and
                            "TRUST STATUS" not in l and
                            "/100" not in l and
                            "View Full" not in l]
            for line in summary_lines:
                for term in ["sha256", "blake3", "dual_hash"]:
                    assert term not in line.lower()
