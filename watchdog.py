#!/usr/bin/env python3
"""
TrustChain Watchdog Daemon - CLAUDEME v3.1 Compliant

Health monitoring for T+48h gate requirement.
Checks:
- receipts.jsonl exists and is writable
- Core modules are importable
"""

import argparse
import sys
from pathlib import Path
from typing import Tuple, List

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent))


def check_receipts_ledger() -> Tuple[bool, str]:
    """
    Verify receipts.jsonl exists and is writable.

    Returns:
        Tuple of (success, message)
    """
    ledger_path = Path(__file__).parent / "receipts.jsonl"

    # Check exists
    if not ledger_path.exists():
        # Try to create it
        try:
            ledger_path.touch()
            return True, f"Created {ledger_path}"
        except Exception as e:
            return False, f"Cannot create {ledger_path}: {e}"

    # Check is file
    if not ledger_path.is_file():
        return False, f"{ledger_path} is not a file"

    # Check writable
    try:
        with open(ledger_path, 'a') as f:
            pass
        return True, f"{ledger_path} exists and is writable"
    except Exception as e:
        return False, f"{ledger_path} is not writable: {e}"


def check_core_modules() -> Tuple[bool, str]:
    """
    Verify core modules are importable.

    Returns:
        Tuple of (success, message)
    """
    modules = [
        "src.core",
        "src.ingest",
        "src.trust_score",
        "src.traffic_light"
    ]

    failed = []
    for module in modules:
        try:
            __import__(module)
        except ImportError as e:
            failed.append(f"{module}: {e}")

    if failed:
        return False, f"Import failures: {', '.join(failed)}"

    return True, f"All {len(modules)} core modules importable"


def check_core_functions() -> Tuple[bool, str]:
    """
    Verify core functions work correctly.

    Returns:
        Tuple of (success, message)
    """
    try:
        from src.core import dual_hash, emit_receipt, merkle, StopRule

        # Test dual_hash
        result = dual_hash(b"test")
        if ":" not in result:
            return False, "dual_hash does not return SHA256:BLAKE3 format"

        # Test merkle
        root = merkle([{"a": 1}, {"b": 2}])
        if ":" not in root:
            return False, "merkle does not return dual hash format"

        # Test StopRule exists
        if not issubclass(StopRule, Exception):
            return False, "StopRule is not an Exception subclass"

        return True, "Core functions (dual_hash, merkle, StopRule) working"

    except Exception as e:
        return False, f"Core function error: {e}"


def check_trust_score() -> Tuple[bool, str]:
    """
    Verify trust score computation works.

    Returns:
        Tuple of (success, message)
    """
    try:
        from src.trust_score import compute_trust_score

        # Test with sample receipt
        receipt = {
            "confidence": 0.95,
            "sources": ["a", "b", "c", "d", "e"],
            "raci": {"accountable": "CPT Test"}
        }
        score = compute_trust_score(receipt)

        if not (0 <= score <= 100):
            return False, f"Trust score {score} out of range [0, 100]"

        return True, f"Trust score computation working (sample score: {score})"

    except Exception as e:
        return False, f"Trust score error: {e}"


def check_traffic_light() -> Tuple[bool, str]:
    """
    Verify traffic light rendering works.

    Returns:
        Tuple of (success, message)
    """
    try:
        from src.traffic_light import render_traffic_light, select_emoji

        # Test emoji selection
        emoji = select_emoji(90)
        if "🟢" not in emoji and "✅" not in emoji:
            return False, f"Wrong emoji for score 90: {emoji}"

        # Test rendering
        output = render_traffic_light(90, {"confidence": 0.9})
        if "TRUST STATUS" not in output:
            return False, "Rendered output missing TRUST STATUS"

        # Check no crypto terms
        crypto_terms = ["sha256", "blake3", "merkle", "hash"]
        for term in crypto_terms:
            if term in output.lower():
                return False, f"Crypto term '{term}' found in output"

        return True, "Traffic light rendering working"

    except Exception as e:
        return False, f"Traffic light error: {e}"


def run_all_checks() -> Tuple[int, int, List[Tuple[str, bool, str]]]:
    """
    Run all health checks.

    Returns:
        Tuple of (passed_count, failed_count, check_results)
    """
    checks = [
        ("receipts_ledger", check_receipts_ledger),
        ("core_modules", check_core_modules),
        ("core_functions", check_core_functions),
        ("trust_score", check_trust_score),
        ("traffic_light", check_traffic_light),
    ]

    results = []
    passed = 0
    failed = 0

    for name, check_func in checks:
        try:
            success, message = check_func()
            results.append((name, success, message))
            if success:
                passed += 1
            else:
                failed += 1
        except Exception as e:
            results.append((name, False, f"Check crashed: {e}"))
            failed += 1

    return passed, failed, results


def emit_health_receipt(status: str, passed: int, failed: int,
                        check_details: List[dict]) -> None:
    """
    Emit watchdog_health_receipt.
    """
    try:
        from src.core import emit_receipt
        emit_receipt("watchdog_health", {
            "status": status,
            "checks_passed": passed,
            "checks_failed": failed,
            "check_details": check_details
        })
    except Exception:
        # Don't fail if we can't emit - just print
        pass


def main() -> int:
    parser = argparse.ArgumentParser(description="TrustChain Watchdog")
    parser.add_argument(
        "--check",
        action="store_true",
        help="Run health checks and exit with status"
    )
    args = parser.parse_args()

    if not args.check:
        parser.print_help()
        return 0

    # Run all checks
    passed, failed, results = run_all_checks()

    # Print results
    print("\n" + "=" * 40)
    print("TRUSTCHAIN WATCHDOG HEALTH CHECK")
    print("=" * 40 + "\n")

    check_details = []
    for name, success, message in results:
        symbol = "✓" if success else "✗"
        print(f"{symbol} {name}: {message}")
        check_details.append({
            "name": name,
            "success": success,
            "message": message
        })

    print()
    status = "healthy" if failed == 0 else "unhealthy"
    print(f"Status: {status.upper()}")
    print(f"Passed: {passed}/{passed + failed}")

    # Emit health receipt
    emit_health_receipt(status, passed, failed, check_details)

    # Return exit code
    return 0 if failed == 0 else 1


if __name__ == "__main__":
    sys.exit(main())
