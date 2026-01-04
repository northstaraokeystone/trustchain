#!/usr/bin/env python3
"""
TrustChain CLI - CLAUDEME v3.1 Compliant

Commands:
- --test: Emit test receipt (T+2h gate requirement)
- trust --receipt: Process single receipt
- batch --receipts: Process batch from JSONL file
- simulate: Run Monte Carlo scenarios
- health: Run watchdog health check
"""

import argparse
import json
import sys
from pathlib import Path

# Add project root to path for imports
sys.path.insert(0, str(Path(__file__).parent))

from src.core import emit_receipt, dual_hash


def cmd_test() -> int:
    """
    Test mode - emit a test receipt.
    Required for T+2h gate.

    Returns:
        Exit code (0 = success)
    """
    emit_receipt("test", {
        "status": "pass",
        "message": "TrustChain CLI test receipt"
    })
    return 0


def cmd_trust(receipt_path: str) -> int:
    """
    Process a single receipt and display traffic light.

    Args:
        receipt_path: Path to receipt JSON file

    Returns:
        Exit code (0 = success)
    """
    from src.ingest import parse_receipt_json
    from src.trust_score import compute_trust_score
    from src.traffic_light import render_traffic_light_with_receipt

    path = Path(receipt_path)
    if not path.exists():
        print(f"Error: Receipt file not found: {receipt_path}", file=sys.stderr)
        return 1

    try:
        with open(path, 'r') as f:
            receipt = json.load(f)
    except json.JSONDecodeError as e:
        print(f"Error: Invalid JSON in receipt file: {e}", file=sys.stderr)
        return 1

    score = compute_trust_score(receipt)
    output = render_traffic_light_with_receipt(score, receipt)
    print(output)
    return 0


def cmd_batch(receipts_path: str) -> int:
    """
    Process batch of receipts from JSONL file.

    Args:
        receipts_path: Path to receipts.jsonl file

    Returns:
        Exit code (0 = success)
    """
    from src.ingest import read_receipts
    from src.trust_score import compute_trust_score
    from src.traffic_light import render_compact

    receipts = read_receipts(receipts_path)

    if not receipts:
        print("No receipts found in file.", file=sys.stderr)
        return 1

    # Process and display each receipt
    green_count = 0
    yellow_count = 0
    red_count = 0

    for i, receipt in enumerate(receipts, 1):
        score = compute_trust_score(receipt)
        compact = render_compact(score)
        print(f"[{i}] {compact}")

        if score >= 85:
            green_count += 1
        elif score >= 60:
            yellow_count += 1
        else:
            red_count += 1

    # Print summary
    total = len(receipts)
    print(f"\n━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━")
    print(f"Summary: {total} receipts processed")
    print(f"  ✅ Green:  {green_count} ({green_count*100//total}%)")
    print(f"  ⚠️ Yellow: {yellow_count} ({yellow_count*100//total}%)")
    print(f"  ❌ Red:    {red_count} ({red_count*100//total}%)")

    return 0


def cmd_simulate(scenario_name: str = None, run_all: bool = False) -> int:
    """
    Run Monte Carlo simulation scenarios.

    Args:
        scenario_name: Name of scenario to run (BASELINE, STRESS_VOLUME, MALFORMED_RECEIPTS)
        run_all: Run all scenarios

    Returns:
        Exit code (0 = all passed)
    """
    from sim.sim import run_scenario
    from sim import scenarios

    available = ["BASELINE", "STRESS_VOLUME", "MALFORMED_RECEIPTS"]

    if run_all:
        scenario_names = available
    elif scenario_name:
        if scenario_name.upper() not in available:
            print(f"Error: Unknown scenario '{scenario_name}'", file=sys.stderr)
            print(f"Available: {', '.join(available)}", file=sys.stderr)
            return 1
        scenario_names = [scenario_name.upper()]
    else:
        print("Error: Specify a scenario name or --all", file=sys.stderr)
        return 1

    all_passed = True

    for name in scenario_names:
        config = getattr(scenarios, name)
        print(f"\n{'='*40}")
        print(f"Running scenario: {name}")
        print(f"{'='*40}")

        result = run_scenario(config)

        if result.success:
            print(f"✅ {name}: PASSED")
        else:
            print(f"❌ {name}: FAILED")
            for v in result.violations:
                print(f"   - {v}")
            all_passed = False

    return 0 if all_passed else 1


def cmd_health() -> int:
    """
    Run watchdog health check.

    Returns:
        Exit code from watchdog
    """
    import subprocess
    result = subprocess.run(
        [sys.executable, "watchdog.py", "--check"],
        cwd=Path(__file__).parent
    )
    return result.returncode


def main():
    parser = argparse.ArgumentParser(
        description="TrustChain CLI - Receipts to Trust Traffic Light"
    )

    parser.add_argument(
        "--test",
        action="store_true",
        help="Emit test receipt (T+2h gate requirement)"
    )

    subparsers = parser.add_subparsers(dest="command")

    # trust command
    trust_parser = subparsers.add_parser("trust", help="Process single receipt")
    trust_parser.add_argument(
        "--receipt",
        required=True,
        help="Path to receipt JSON file"
    )

    # batch command
    batch_parser = subparsers.add_parser("batch", help="Process batch of receipts")
    batch_parser.add_argument(
        "--receipts",
        required=True,
        help="Path to receipts.jsonl file"
    )

    # simulate command
    sim_parser = subparsers.add_parser("simulate", help="Run Monte Carlo scenarios")
    sim_parser.add_argument(
        "scenario",
        nargs="?",
        help="Scenario name (BASELINE, STRESS_VOLUME, MALFORMED_RECEIPTS)"
    )
    sim_parser.add_argument(
        "--all",
        action="store_true",
        help="Run all scenarios"
    )

    # health command
    subparsers.add_parser("health", help="Run watchdog health check")

    args = parser.parse_args()

    # Handle --test flag
    if args.test:
        return cmd_test()

    # Handle subcommands
    if args.command == "trust":
        return cmd_trust(args.receipt)
    elif args.command == "batch":
        return cmd_batch(args.receipts)
    elif args.command == "simulate":
        return cmd_simulate(args.scenario, args.all)
    elif args.command == "health":
        return cmd_health()
    else:
        parser.print_help()
        return 0


if __name__ == "__main__":
    sys.exit(main())
