"""Reproduce the five-company v2.1 scores using Python standard library."""
import json
import math
from pathlib import Path


def score(row, market_factor=1.0, target=None):
    target = row["target"] if target is None else target
    market = row["market_cap"] * market_factor
    assert market > 0 and target > 0
    assert 0 <= row["direction"] <= 40
    assert 0 <= row["trend"] <= 35
    assert 0 <= row["intensity"] <= 25
    assert -10 <= row["intuition"] <= 10
    confidence = min(90, row["direction"] + row["trend"] + row["intensity"])
    space = min(100, max(0, 100 * math.log(target / market) / math.log(6)))
    base = (confidence + space) / 2
    return {
        "C": confidence, "space": space, "upside_pct": (target / market - 1) * 100,
        "base": base, "final": min(100, max(0, base + row["intuition"])),
    }


if __name__ == "__main__":
    root = Path(__file__).resolve().parents[1]
    data = json.loads((root / "research/2026-10-09-v2.1-scores.json").read_text())
    results = []
    for row in data["companies"]:
        n = row["broker_count"]
        assert row["direction"] == (10 if n == 1 else 20 if n <= 3 else 30 if n <= 5 else 40)
        result = {"name": row["name"], **score(row)}
        result["alternative"] = score(row, target=row["alternative_target"])["final"]
        result["market_sensitivity"] = {
            f"{factor:+.0%}": score(row, market_factor=1 + factor)["final"]
            for factor in (-.2, -.1, 0, .1, .2)
        }
        results.append(result)
    print(json.dumps(sorted(results, key=lambda x: x["final"], reverse=True), ensure_ascii=False, indent=2))
