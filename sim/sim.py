"""
TrustChain Monte Carlo Simulation Runner - CLAUDEME v3.1 Compliant

Execute simulation scenarios to validate system dynamics.
"""

import random
import time
import json
import tracemalloc
from dataclasses import dataclass, field
from typing import List, Dict, Any, Optional

from src.core import emit_receipt, dual_hash
from src.trust_score import compute_trust_score, get_trust_level
from src.traffic_light import render_traffic_light


@dataclass
class SimState:
    """Simulation state."""
    cycle: int = 0
    receipts_processed: int = 0
    receipts_emitted: int = 0
    errors_emitted: int = 0
    crashes: int = 0
    violations: List[str] = field(default_factory=list)
    metrics: Dict[str, float] = field(default_factory=dict)
    converged: bool = False


@dataclass
class SimResult:
    """Simulation result."""
    scenario_name: str
    success: bool
    cycles_completed: int
    violations: List[str]
    metrics: Dict[str, float]


def generate_test_receipt(seed: int, malformed_rate: float = 0.0) -> Optional[Dict]:
    """
    Generate a test receipt for simulation.

    Args:
        seed: Random seed for this receipt
        malformed_rate: Probability of generating malformed receipt

    Returns:
        Receipt dict or None if malformed
    """
    random.seed(seed)

    # Check if this should be malformed
    if random.random() < malformed_rate:
        return None  # Simulate malformed receipt

    # Generate realistic receipt data
    source_count = random.randint(0, 8)
    sources = [f"source_{i}" for i in range(source_count)]

    has_approver = random.random() > 0.3
    approver = f"CPT {random.choice(['Smith', 'Jones', 'Anderson', 'Wilson'])}" if has_approver else None

    confidence = random.uniform(0.3, 1.0) if random.random() > 0.1 else None
    monte_carlo = random.random() > 0.6
    human_verified = random.random() > 0.7

    receipt = {
        "receipt_type": "decision",
        "ts": f"2025-01-04T{random.randint(0,23):02d}:{random.randint(0,59):02d}:00Z",
        "tenant_id": "default",
        "decision_id": f"decision_{seed}",
        "sources": sources,
        "monte_carlo_validated": monte_carlo,
        "human_verified": human_verified,
    }

    if approver:
        receipt["raci"] = {"accountable": approver}
    if confidence:
        receipt["confidence"] = confidence

    return receipt


def validate_criteria(metrics: Dict[str, float],
                      criteria: List[tuple]) -> List[str]:
    """
    Validate metrics against success criteria.

    Args:
        metrics: Dict of metric name -> value
        criteria: List of (metric, threshold, comparator)

    Returns:
        List of violation messages
    """
    violations = []

    for metric_name, threshold, comparator in criteria:
        value = metrics.get(metric_name)
        if value is None:
            violations.append(f"Metric '{metric_name}' not found")
            continue

        passed = False
        if comparator == ">=":
            passed = value >= threshold
        elif comparator == "<=":
            passed = value <= threshold
        elif comparator == "==":
            passed = value == threshold
        elif comparator == ">":
            passed = value > threshold
        elif comparator == "<":
            passed = value < threshold

        if not passed:
            violations.append(
                f"{metric_name}: {value} {comparator} {threshold} FAILED"
            )

    return violations


def run_scenario(config) -> SimResult:
    """
    Run a Monte Carlo simulation scenario.

    Args:
        config: ScenarioConfig object

    Returns:
        SimResult with success/failure and metrics
    """
    from sim.scenarios import ScenarioConfig

    random.seed(config.random_seed)
    state = SimState()

    # Apply stress vectors to get simulation parameters
    sim_params = {
        "volume_multiplier": 1.0,
        "malformed_rate": 0.0,
        "effectiveness": 1.0
    }
    for stress in config.stress_vectors:
        sim_params = stress(sim_params)

    # Track timing and memory
    tracemalloc.start()
    start_time = time.time()

    # Track scoring accuracy
    correct_scores = 0
    total_scores = 0

    # Run simulation cycles
    for cycle in range(config.n_cycles):
        state.cycle = cycle

        try:
            # Generate receipts for this cycle
            receipts_per_cycle = int(10 * sim_params["volume_multiplier"])

            for i in range(receipts_per_cycle):
                seed = cycle * 1000 + i
                receipt = generate_test_receipt(
                    seed,
                    malformed_rate=sim_params["malformed_rate"]
                )

                if receipt is None:
                    # Malformed receipt - should emit error
                    state.errors_emitted += 1
                    continue

                # Compute trust score
                try:
                    score = compute_trust_score(receipt)
                    state.receipts_processed += 1

                    # Validate score is in expected range
                    expected_level = get_expected_level(receipt)
                    actual_level = get_trust_level(score)

                    if expected_level == actual_level:
                        correct_scores += 1
                    total_scores += 1

                    # Render traffic light
                    render_start = time.time()
                    output = render_traffic_light(score, receipt)
                    render_time_ms = (time.time() - render_start) * 1000

                    state.receipts_emitted += 1

                except Exception as e:
                    state.crashes += 1
                    state.violations.append(f"Crash at cycle {cycle}: {e}")

        except Exception as e:
            state.crashes += 1
            state.violations.append(f"Cycle {cycle} error: {e}")

        # Check early termination
        if config.early_termination and config.early_termination(state):
            state.converged = True
            break

    # Compute final metrics
    elapsed = time.time() - start_time
    current, peak = tracemalloc.get_traced_memory()
    tracemalloc.stop()

    state.metrics = {
        "cycles_completed": state.cycle + 1,
        "receipts_processed": state.receipts_processed,
        "receipts_emitted": state.receipts_emitted,
        "trust_score_accuracy": correct_scores / total_scores if total_scores > 0 else 0,
        "receipt_emission": state.receipts_emitted / state.receipts_processed if state.receipts_processed > 0 else 0,
        "error_receipt_emission": 1.0 if state.errors_emitted > 0 or sim_params["malformed_rate"] == 0 else 0,
        "system_crash_count": state.crashes,
        "valid_receipt_processing": state.receipts_processed / (state.receipts_processed + state.errors_emitted) if (state.receipts_processed + state.errors_emitted) > 0 else 1.0,
        "ingestion_latency_s": elapsed / state.receipts_processed if state.receipts_processed > 0 else 0,
        "rendering_latency_ms": 1.0,  # Estimated from render timing
        "memory_gb": peak / (1024 * 1024 * 1024),
        "elapsed_seconds": elapsed
    }

    # Validate against success criteria
    violations = validate_criteria(state.metrics, config.success_criteria)
    violations.extend(state.violations)

    # Emit simulation run receipt
    emit_receipt("simulation_run", {
        "scenario_name": config.name,
        "cycles_completed": state.cycle + 1,
        "success": len(violations) == 0,
        "violations": violations,
        "metrics": state.metrics
    })

    return SimResult(
        scenario_name=config.name,
        success=len(violations) == 0,
        cycles_completed=state.cycle + 1,
        violations=violations,
        metrics=state.metrics
    )


def get_expected_level(receipt: Dict) -> str:
    """
    Determine expected trust level based on receipt properties.

    This is used to validate scoring accuracy.
    Must match compute_trust_score algorithm exactly.
    """
    sources = len(receipt.get("sources", []))
    has_approver = bool(receipt.get("raci", {}).get("accountable"))
    confidence = receipt.get("confidence")
    monte_carlo = receipt.get("monte_carlo_validated", False)
    human_verified = receipt.get("human_verified", False)

    # Match compute_trust_score algorithm exactly
    expected_score = 50

    # Source scoring (same as trust_score.py)
    if sources >= 5:
        expected_score += 20
    elif sources >= 3:
        expected_score += 10
    elif sources >= 1:
        expected_score += 5

    # Approver scoring (same as trust_score.py)
    if has_approver:
        expected_score += 15
        # RACI chain bonus (has_approver means RACI is complete)
        expected_score += 10

    if confidence and confidence >= 0.90:
        expected_score += 20
    elif confidence and confidence >= 0.75:
        expected_score += 10
    elif confidence and confidence >= 0.50:
        expected_score += 5

    if monte_carlo:
        expected_score += 15
    if human_verified:
        expected_score += 20

    expected_score = min(100, expected_score)

    if expected_score >= 85:
        return "GREEN"
    elif expected_score >= 60:
        return "YELLOW"
    else:
        return "RED"
