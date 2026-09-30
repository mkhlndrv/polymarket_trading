"""python -m weather_edge <stage> [args]

    inventory prices trades checks truth forecasts labels pilot model backtest timing report
    collector paper

Each stage is a module with its own command line; arguments after the stage name go to it. The
research stages read and write data/ and reports/; `report` needs only the committed reports.
"""

from __future__ import annotations

import importlib
import sys

STAGES = {
    "inventory": "markets",
    "prices": "prices",
    "trades": "trades",
    "checks": "market_checks",
    "truth": "observations",
    "forecasts": "forecasts",
    "labels": "labels",
    "pilot": "pilot_nyc",
    "model": "model",
    "backtest": "backtest",
    "timing": "timing",
    "report": "plots",
    "collector": "collector",
    "paper": "paper_trader",
}


def main(argv: list[str] | None = None) -> int:
    argv = sys.argv[1:] if argv is None else argv
    if not argv or argv[0] not in STAGES:
        print(__doc__)
        print("stages:", " ".join(STAGES))
        return 2
    module = importlib.import_module(f"weather_edge.{STAGES[argv[0]]}")
    sys.argv = [f"weather_edge {argv[0]}", *argv[1:]]
    return int(module.main() or 0)


if __name__ == "__main__":
    sys.exit(main())
