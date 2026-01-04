"""
TrustChain Trust Score Module - CLAUDEME v3.1 Compliant

Compute 0-100 trust score from receipt metadata with:
- Anomaly detection
- Bias checking
- Stoprules
"""

import statistics
from typing import Dict, List, Optional, Tuple

from .core import (
    StopRule, dual_hash, emit_receipt, emit_anomaly, emit_bias
)


# Score thresholds
SCORE_GREEN_MIN = 85
SCORE_YELLOW_MIN = 60

# Bias threshold
BIAS_THRESHOLD = 0.005  # 0.5%

# Anomaly threshold (standard deviations)
ANOMALY_SIGMA = 2.0


def compute_trust_score(receipt: Dict) -> int:
    """
    Compute 0-100 trust score from receipt metadata.
    Triggers stoprule if score out of bounds.

    Args:
        receipt: Receipt dict with metadata

    Returns:
        Trust score (0-100)

    SLO: <10ms per receipt
    """
    score = 50  # BASE_SCORE

    # Extract and score source count
    source_count = extract_sources(receipt)
    if source_count >= 5:
        score += 20
    elif source_count >= 3:
        score += 10
    elif source_count >= 1:
        score += 5

    # Extract and score approver
    approver = extract_approver(receipt)
    if approver:
        score += 15
        # Check for RACI chain completeness (approver + accountable)
        if has_raci_chain(receipt):
            score += 10

    # Extract and score confidence
    confidence = extract_confidence(receipt)
    if confidence is not None:
        if confidence >= 0.90:
            score += 20
        elif confidence >= 0.75:
            score += 10
        elif confidence >= 0.50:
            score += 5

    # Check Monte Carlo validation
    if check_monte_carlo(receipt):
        score += 15

    # Check human verification
    if check_human_verified(receipt):
        score += 20

    # Cap at 100
    score = min(100, score)

    # Validate score range
    if score < 0 or score > 100:
        stoprule_trust_score_invalid(score)

    return score


def extract_sources(receipt: Dict) -> int:
    """
    Count data sources from receipt payload.

    Args:
        receipt: Receipt dict

    Returns:
        Number of sources (0 if not found)
    """
    # Check for explicit source_count field first
    source_count = receipt.get("source_count")
    if isinstance(source_count, int):
        return source_count

    # Check sources list
    sources = receipt.get("sources")
    if isinstance(sources, list):
        return len(sources)

    # Check payload for sources
    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        source_count = payload.get("source_count")
        if isinstance(source_count, int):
            return source_count
        sources = payload.get("sources")
        if isinstance(sources, list):
            return len(sources)

    return 0


def extract_approver(receipt: Dict) -> Optional[str]:
    """
    Extract RACI accountable person from receipt.

    Args:
        receipt: Receipt dict

    Returns:
        Approver name or None
    """
    # Check direct approver field
    approver = receipt.get("approver")
    if approver:
        return str(approver)

    # Check RACI structure
    raci = receipt.get("raci", {})
    if isinstance(raci, dict):
        accountable = raci.get("accountable")
        if accountable:
            return str(accountable)

    # Check payload for approver
    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        approver = payload.get("approver")
        if approver:
            return str(approver)
        raci = payload.get("raci", {})
        if isinstance(raci, dict):
            accountable = raci.get("accountable")
            if accountable:
                return str(accountable)

    return None


def extract_confidence(receipt: Dict) -> Optional[float]:
    """
    Extract confidence score (0.0-1.0) from receipt.

    Args:
        receipt: Receipt dict

    Returns:
        Confidence score or None
    """
    # Check direct confidence field
    confidence = receipt.get("confidence")
    if confidence is not None:
        try:
            conf = float(confidence)
            if 0.0 <= conf <= 1.0:
                return conf
            # Handle percentage format (0-100 -> 0-1)
            elif 0.0 <= conf <= 100.0:
                return conf / 100.0
        except (ValueError, TypeError):
            pass

    # Check payload for confidence
    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        confidence = payload.get("confidence")
        if confidence is not None:
            try:
                conf = float(confidence)
                if 0.0 <= conf <= 1.0:
                    return conf
            except (ValueError, TypeError):
                pass

    return None


def check_monte_carlo(receipt: Dict) -> bool:
    """
    Check if receipt references Monte Carlo validation.

    Args:
        receipt: Receipt dict

    Returns:
        True if Monte Carlo validated
    """
    # Check various field names
    if receipt.get("monte_carlo_validated"):
        return True
    if receipt.get("monte_carlo_passed"):
        return True
    if receipt.get("simulation_validated"):
        return True

    # Check payload
    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        if payload.get("monte_carlo_validated"):
            return True
        if payload.get("monte_carlo_passed"):
            return True

    return False


def check_human_verified(receipt: Dict) -> bool:
    """
    Check if human verified (intervention_receipt present).

    Args:
        receipt: Receipt dict

    Returns:
        True if human verified
    """
    # Check direct fields
    if receipt.get("human_verified"):
        return True
    if receipt.get("intervention_receipt"):
        return True
    if receipt.get("human_approved"):
        return True

    # Check payload
    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        if payload.get("human_verified"):
            return True
        if payload.get("intervention_receipt"):
            return True

    return False


def has_raci_chain(receipt: Dict) -> bool:
    """
    Check if RACI chain is complete (has accountable).

    Args:
        receipt: Receipt dict

    Returns:
        True if RACI chain is complete
    """
    raci = receipt.get("raci", {})
    if isinstance(raci, dict):
        return bool(raci.get("accountable"))

    payload = receipt.get("payload", {})
    if isinstance(payload, dict):
        raci = payload.get("raci", {})
        if isinstance(raci, dict):
            return bool(raci.get("accountable"))

    return False


def detect_trust_anomaly(score: int, historical_scores: List[int]) -> bool:
    """
    Detect if score is >2σ from mean.

    Args:
        score: Current trust score
        historical_scores: List of historical scores

    Returns:
        True if anomaly detected (>2σ deviation)
    """
    # Require at least 10 historical scores
    if len(historical_scores) < 10:
        return False

    mean = statistics.mean(historical_scores)
    stdev = statistics.stdev(historical_scores)

    if stdev == 0:
        return False

    z_score = abs(score - mean) / stdev
    is_anomaly = z_score > ANOMALY_SIGMA

    if is_anomaly:
        emit_anomaly(
            metric="trust_score",
            baseline=mean,
            actual=float(score),
            classification="deviation",
            action="alert"
        )

    return is_anomaly


def check_trust_bias(scores_by_domain: Dict[str, List[int]]) -> float:
    """
    Compute disparity across domains, emit bias_receipt if ≥0.005.

    Args:
        scores_by_domain: Dict mapping domain names to lists of scores

    Returns:
        Disparity value (0.0 if insufficient data)
    """
    # Require at least 2 domain groups
    if len(scores_by_domain) < 2:
        return 0.0

    # Compute mean score per domain
    domain_means = {}
    for domain, scores in scores_by_domain.items():
        if scores:
            domain_means[domain] = statistics.mean(scores)

    if len(domain_means) < 2:
        return 0.0

    # Compute disparity (max - min normalized to 0-1)
    max_mean = max(domain_means.values())
    min_mean = min(domain_means.values())

    # Normalize disparity to 0-1 range (assuming scores are 0-100)
    disparity = (max_mean - min_mean) / 100.0

    # Emit bias receipt if threshold exceeded
    if disparity >= BIAS_THRESHOLD:
        emit_bias(
            groups=list(domain_means.keys()),
            disparity=disparity,
            threshold=BIAS_THRESHOLD,
            mitigation_action="alert"
        )

    return disparity


def stoprule_trust_score_invalid(score: int) -> None:
    """
    Emit anomaly receipt and raise StopRule if score not in [0, 100].

    Args:
        score: Invalid trust score

    Raises:
        StopRule: Always raises
    """
    emit_anomaly(
        metric="trust_score_range",
        baseline=50.0,
        actual=float(score),
        classification="violation",
        action="halt"
    )
    raise StopRule(f"Trust score {score} out of valid range [0, 100]")


def get_trust_level(score: int) -> str:
    """
    Get trust level string from score.

    Args:
        score: Trust score (0-100)

    Returns:
        "GREEN", "YELLOW", or "RED"
    """
    if score >= SCORE_GREEN_MIN:
        return "GREEN"
    elif score >= SCORE_YELLOW_MIN:
        return "YELLOW"
    else:
        return "RED"


def emit_trust_receipt(receipt: Dict, score: int, summary_line_1: str,
                       summary_line_2: str) -> Dict:
    """
    Emit a trust_receipt for a computed score.

    Args:
        receipt: Source receipt that was scored
        score: Computed trust score
        summary_line_1: First summary line
        summary_line_2: Second summary line

    Returns:
        Trust receipt dict
    """
    trust_level = get_trust_level(score)

    return emit_receipt("trustchain_trust_score", {
        "source_receipt_hash": dual_hash(str(receipt)),
        "trust_score": score,
        "trust_level": trust_level,
        "source_count": extract_sources(receipt),
        "approver": extract_approver(receipt),
        "confidence": extract_confidence(receipt),
        "monte_carlo_passed": check_monte_carlo(receipt),
        "human_verified": check_human_verified(receipt),
        "summary_line_1": summary_line_1,
        "summary_line_2": summary_line_2
    })
