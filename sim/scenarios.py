"""
TrustChain Monte Carlo Scenarios - CLAUDEME v3.1 Compliant

3 validation scenarios that prove system dynamics:
1. BASELINE - Core trust scoring accuracy
2. STRESS_VOLUME - Performance under 5x load
3. MALFORMED_RECEIPTS - Graceful degradation
"""

from dataclasses import dataclass, field
from typing import Callable, List, Tuple, Any


@dataclass
class ScenarioConfig:
    """Monte Carlo scenario configuration."""
    name: str
    n_cycles: int
    stress_vectors: List[Callable] = field(default_factory=list)
    success_criteria: List[Tuple[str, Any, str]] = field(default_factory=list)
    random_seed: int = 42
    early_termination: Callable = None


# Stress vector functions

def multiply_volume(factor: float) -> Callable:
    """Create stress vector that multiplies receipt volume."""
    def stress(state):
        state["volume_multiplier"] = factor
        return state
    return stress


def inject_malformed(rate: float) -> Callable:
    """Create stress vector that injects malformed receipts."""
    def stress(state):
        state["malformed_rate"] = rate
        return state
    return stress


def vary_effectiveness(low: float, high: float) -> Callable:
    """Create stress vector that varies effectiveness randomly."""
    def stress(state):
        import random
        state["effectiveness"] = random.uniform(low, high)
        return state
    return stress


# Scenario 1: BASELINE
BASELINE = ScenarioConfig(
    name="BASELINE",
    n_cycles=1000,
    stress_vectors=[],
    success_criteria=[
        ("trust_score_accuracy", 0.95, ">="),  # 95% match expected Green/Yellow/Red
        ("rendering_latency_ms", 10, "<="),
        ("receipt_emission", 1.0, "=="),  # 100% receipts emitted
    ],
    random_seed=42
)


# Scenario 2: STRESS_VOLUME
STRESS_VOLUME = ScenarioConfig(
    name="STRESS_VOLUME",
    n_cycles=500,
    stress_vectors=[multiply_volume(5.0)],
    success_criteria=[
        ("ingestion_latency_s", 5.0, "<="),
        ("trust_score_accuracy", 0.90, ">="),
        ("memory_gb", 5.5, "<="),
    ],
    random_seed=42
)


# Scenario 3: MALFORMED_RECEIPTS
MALFORMED_RECEIPTS = ScenarioConfig(
    name="MALFORMED_RECEIPTS",
    n_cycles=200,
    stress_vectors=[inject_malformed(rate=0.20)],
    success_criteria=[
        ("error_receipt_emission", 1.0, "=="),  # 100% errors logged
        ("system_crash_count", 0, "=="),  # Zero crashes
        ("valid_receipt_processing", 0.80, ">="),  # 80% valid receipts processed
    ],
    random_seed=42
)


# All scenarios for --all flag
ALL_SCENARIOS = [BASELINE, STRESS_VOLUME, MALFORMED_RECEIPTS]
