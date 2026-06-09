from __future__ import annotations

import argparse
import csv
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GradeRow:
    category: str
    weight: float
    earned_pct: float | None


def parse_args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(
        description="Plan required averages on remaining course components."
    )
    parser.add_argument("--input", type=Path, required=True, help="CSV with category,weight,earned_pct columns.")
    parser.add_argument(
        "--targets",
        type=str,
        default="90,80,70",
        help="Comma-separated target course percentages to evaluate.",
    )
    parser.add_argument(
        "--pending-average",
        type=float,
        help="Optional projected average to apply across all remaining weight.",
    )
    parser.add_argument("--output", type=Path, help="Optional CSV path for the scenario table.")
    return parser.parse_args()


def parse_float(value: str, row_number: int, field_name: str) -> float:
    try:
        return float(value)
    except ValueError as exc:
        raise ValueError(f"Invalid {field_name} at row {row_number}.") from exc


def load_grade_rows(path: Path) -> list[GradeRow]:
    if not path.exists():
        raise FileNotFoundError(f"Input file not found: {path}")

    rows: list[GradeRow] = []
    with path.open("r", encoding="utf-8-sig", newline="") as handle:
        reader = csv.DictReader(handle)
        expected = {"category", "weight", "earned_pct"}
        if set(reader.fieldnames or []) != expected:
            raise ValueError("CSV columns must be exactly: category,weight,earned_pct")

        for row_number, row in enumerate(reader, start=2):
            category = str(row["category"]).strip()
            if not category:
                raise ValueError(f"Empty category at row {row_number}.")

            weight = parse_float(str(row["weight"]).strip(), row_number, "weight")
            if weight <= 0:
                raise ValueError(f"Weight must be positive at row {row_number}.")

            earned_raw = str(row["earned_pct"]).strip()
            earned_pct = None if earned_raw == "" else parse_float(earned_raw, row_number, "earned_pct")
            if earned_pct is not None and not 0 <= earned_pct <= 100:
                raise ValueError(f"earned_pct must be between 0 and 100 at row {row_number}.")

            rows.append(GradeRow(category=category, weight=weight, earned_pct=earned_pct))

    if not rows:
        raise ValueError("Input CSV is empty.")

    total_weight = sum(row.weight for row in rows)
    if abs(total_weight - 100.0) > 0.01:
        raise ValueError(f"Category weights must sum to 100. Found {total_weight:.2f}.")

    return rows


def parse_targets(raw: str) -> list[float]:
    targets: list[float] = []
    for token in raw.split(","):
        stripped = token.strip()
        if not stripped:
            continue
        try:
            target = float(stripped)
        except ValueError as exc:
            raise ValueError(f"Invalid target percentage: {stripped}") from exc
        if not 0 <= target <= 100:
            raise ValueError(f"Target percentage must be between 0 and 100: {stripped}")
        targets.append(target)
    if not targets:
        raise ValueError("Provide at least one target percentage.")
    return sorted(set(targets), reverse=True)


def build_summary(rows: list[GradeRow]) -> dict[str, float]:
    completed_weight = sum(row.weight for row in rows if row.earned_pct is not None)
    remaining_weight = sum(row.weight for row in rows if row.earned_pct is None)
    locked_points = sum((row.earned_pct or 0.0) * row.weight / 100.0 for row in rows)
    current_average_on_graded = (locked_points / completed_weight * 100.0) if completed_weight else 0.0

    return {
        "completed_weight": completed_weight,
        "remaining_weight": remaining_weight,
        "locked_points": locked_points,
        "current_average_on_graded": current_average_on_graded,
    }


def build_target_rows(rows: list[GradeRow], targets: list[float]) -> list[dict[str, float | str]]:
    summary = build_summary(rows)
    target_rows: list[dict[str, float | str]] = []

    for target in targets:
        remaining_weight = summary["remaining_weight"]
        needed_points = target - summary["locked_points"]

        if remaining_weight <= 0:
            required_average = 0.0
            verdict = "already closed" if summary["locked_points"] >= target else "missed"
        else:
            required_average = (needed_points / remaining_weight) * 100.0
            if required_average <= 0:
                verdict = "already secured"
            elif required_average <= 100:
                verdict = "reachable"
            else:
                verdict = "not reachable"

        target_rows.append(
            {
                "target_pct": round(target, 2),
                "required_avg_on_remaining": round(required_average, 2),
                "remaining_weight": round(remaining_weight, 2),
                "verdict": verdict,
            }
        )

    return target_rows


def project_final_grade(rows: list[GradeRow], pending_average: float) -> float:
    if not 0 <= pending_average <= 100:
        raise ValueError("pending-average must be between 0 and 100.")

    total = 0.0
    for row in rows:
        earned_pct = pending_average if row.earned_pct is None else row.earned_pct
        total += earned_pct * row.weight / 100.0
    return total


def project_remaining_bounds(rows: list[GradeRow]) -> tuple[float, float]:
    floor = 0.0
    ceiling = 0.0
    for row in rows:
        earned_floor = 0.0 if row.earned_pct is None else row.earned_pct
        earned_ceiling = 100.0 if row.earned_pct is None else row.earned_pct
        floor += earned_floor * row.weight / 100.0
        ceiling += earned_ceiling * row.weight / 100.0
    return floor, ceiling


def print_report(rows: list[GradeRow], targets: list[float], pending_average: float | None) -> list[dict[str, float | str]]:
    summary = build_summary(rows)
    scenarios = build_target_rows(rows, targets)

    print("Course Grade Allocator")
    print("======================")
    print(f"Completed weight:          {summary['completed_weight']:.2f}%")
    print(f"Remaining weight:          {summary['remaining_weight']:.2f}%")
    print(f"Locked course points:      {summary['locked_points']:.2f}")
    print(f"Average on graded work:    {summary['current_average_on_graded']:.2f}%")
    floor, ceiling = project_remaining_bounds(rows)
    print(f"Floor if remaining work goes badly: {floor:.2f}%")
    print(f"Ceiling if remaining work is perfect: {ceiling:.2f}%")
    print()

    print("Remaining components:")
    remaining = [row for row in rows if row.earned_pct is None]
    if not remaining:
        print("  None")
    else:
        for row in remaining:
            print(f"  {row.category:<20} {row.weight:>6.2f}%")

    print()
    print(f"{'Target':<10} {'Need On Remaining':>20} {'Remaining Wt':>14} {'Verdict':>16}")
    print("-" * 66)
    for row in scenarios:
        print(
            f"{float(row['target_pct']):<10.2f} "
            f"{float(row['required_avg_on_remaining']):>20.2f}% "
            f"{float(row['remaining_weight']):>13.2f}% "
            f"{str(row['verdict']):>16}"
        )

    if pending_average is not None:
        projected = project_final_grade(rows, pending_average)
        print()
        print(f"Projected final grade at {pending_average:.2f}% on remaining work: {projected:.2f}%")

    return scenarios


def write_output(path: Path, rows: list[dict[str, float | str]]) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    with path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=["target_pct", "required_avg_on_remaining", "remaining_weight", "verdict"],
        )
        writer.writeheader()
        writer.writerows(rows)


def main() -> None:
    args = parse_args()
    rows = load_grade_rows(args.input)
    targets = parse_targets(args.targets)
    scenarios = print_report(rows, targets, args.pending_average)

    if args.output:
        write_output(args.output, scenarios)
        print(f"\nWrote scenario table: {args.output}")


if __name__ == "__main__":
    main()
