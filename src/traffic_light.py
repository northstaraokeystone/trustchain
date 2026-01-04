"""
TrustChain Traffic Light Module - CLAUDEME v3.1 Compliant

Render Green/Yellow/Red visual indicator with 2-sentence summary.
ZERO crypto terms allowed in output.
"""

import re
from typing import Dict, Tuple

from .core import StopRule, emit_receipt
from .trust_score import (
    extract_sources, extract_approver, extract_confidence,
    check_monte_carlo, check_human_verified, get_trust_level
)


# Forbidden crypto terms (must not appear in summary)
CRYPTO_TERMS = ["sha256", "blake3", "merkle", "hash", "dual_hash", "payload_hash"]

# Score thresholds
SCORE_GREEN_MIN = 85
SCORE_YELLOW_MIN = 60


def select_emoji(score: int) -> str:
    """
    Select emoji based on trust score.

    Args:
        score: Trust score (0-100)

    Returns:
        Emoji string: "✅ 🟢" (85-100), "⚠️ 🟡" (60-84), or "❌ 🔴" (0-59)
    """
    if score >= SCORE_GREEN_MIN:
        return "✅ 🟢"
    elif score >= SCORE_YELLOW_MIN:
        return "⚠️ 🟡"
    else:
        return "❌ 🔴"


def build_summary(receipt: Dict) -> Tuple[str, str]:
    """
    Build 2-sentence summary from receipt.
    MUST be ≤50 words total.
    MUST contain zero crypto terms.

    Args:
        receipt: Receipt dict with metadata

    Returns:
        Tuple of (summary_line_1, summary_line_2)
    """
    # Extract data for summary
    source_count = extract_sources(receipt)
    approver = extract_approver(receipt)
    confidence = extract_confidence(receipt)
    monte_carlo = check_monte_carlo(receipt)
    human_verified = check_human_verified(receipt)

    # Build line 1: "AI checked {n} sources, {approver} approved, {confidence}% confidence."
    source_text = f"{source_count} source" + ("s" if source_count != 1 else "")

    if approver:
        approver_text = f"{approver} approved"
    else:
        approver_text = "no approver assigned"

    if confidence is not None:
        confidence_pct = int(confidence * 100)
        confidence_text = f"{confidence_pct}% confidence"
    else:
        confidence_text = "confidence unknown"

    line_1 = f"AI checked {source_text}, {approver_text}, {confidence_text}."

    # Build line 2 (conditional)
    if monte_carlo and human_verified:
        line_2 = "Validated across scenarios and human-verified."
    elif monte_carlo:
        line_2 = "Validated across simulation scenarios."
    elif human_verified:
        line_2 = "Human-verified decision."
    else:
        line_2 = "Automated decision (unvalidated)."

    return line_1, line_2


def render_traffic_light(score: int, receipt: Dict) -> str:
    """
    Render traffic light display with emoji + summary + score.

    Args:
        score: Trust score (0-100)
        receipt: Receipt dict with metadata

    Returns:
        Formatted string with traffic light display

    SLO: <5ms latency, ≤50 words, 0 crypto terms
    """
    emoji = select_emoji(score)
    trust_level = get_trust_level(score)
    line_1, line_2 = build_summary(receipt)

    # Build display
    output = f"""━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
{emoji} TRUST STATUS: {trust_level}

{line_1}
{line_2}

Trust Score: {score}/100
[View Full Receipt] ← Auditor drill-down
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━"""

    # Validate summary word count
    summary_text = f"{line_1} {line_2}"
    word_count = len(summary_text.split())
    if word_count > 50:
        stoprule_summary_too_long(word_count)

    # Validate no crypto terms
    summary_lower = summary_text.lower()
    for term in CRYPTO_TERMS:
        if term in summary_lower:
            stoprule_crypto_in_summary(term)

    return output


def render_traffic_light_with_receipt(score: int, receipt: Dict,
                                      show_receipt: bool = False) -> str:
    """
    Render traffic light with optional full receipt display.

    Args:
        score: Trust score (0-100)
        receipt: Receipt dict with metadata
        show_receipt: Whether to show full receipt JSON

    Returns:
        Formatted string with traffic light (and optional receipt)
    """
    import json

    output = render_traffic_light(score, receipt)

    if show_receipt:
        # Filter out sensitive/internal fields for display
        display_receipt = {k: v for k, v in receipt.items()
                          if not k.startswith("_")}
        receipt_json = json.dumps(display_receipt, indent=2, default=str)
        output += f"\n\n📋 Full Receipt:\n{receipt_json}"

    return output


def stoprule_summary_too_long(word_count: int) -> None:
    """
    HALT on summary exceeding 50 words.

    Args:
        word_count: Actual word count

    Raises:
        StopRule: Always raises
    """
    from .core import emit_anomaly
    emit_anomaly(
        metric="summary_word_count",
        baseline=50.0,
        actual=float(word_count),
        classification="violation",
        action="halt"
    )
    raise StopRule(f"Summary word count {word_count} exceeds limit of 50 words")


def stoprule_crypto_in_summary(term: str) -> None:
    """
    HALT on crypto term appearing in summary.

    Args:
        term: Crypto term found

    Raises:
        StopRule: Always raises
    """
    from .core import emit_anomaly
    emit_anomaly(
        metric="crypto_in_summary",
        baseline=0.0,
        actual=1.0,
        classification="violation",
        action="halt"
    )
    raise StopRule(f"Crypto term '{term}' found in summary - forbidden for operator display")


def get_trust_color_code(score: int) -> str:
    """
    Get ANSI color code for terminal display.

    Args:
        score: Trust score (0-100)

    Returns:
        ANSI color code string
    """
    if score >= SCORE_GREEN_MIN:
        return "\033[92m"  # Green
    elif score >= SCORE_YELLOW_MIN:
        return "\033[93m"  # Yellow
    else:
        return "\033[91m"  # Red


def render_compact(score: int) -> str:
    """
    Render compact single-line traffic light.

    Args:
        score: Trust score (0-100)

    Returns:
        Compact display string
    """
    emoji = select_emoji(score)
    trust_level = get_trust_level(score)
    return f"{emoji} {trust_level} ({score}/100)"
