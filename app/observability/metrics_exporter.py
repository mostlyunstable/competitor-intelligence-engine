import json
import os
from typing import Any

from app.observability.parser_metrics import registry


class MetricsExporter:
    def __init__(self, output_dir: str = "reports"):
        self.output_dir = output_dir
        os.makedirs(self.output_dir, exist_ok=True)

    def _write_json(self, filename: str, data: Any) -> None:
        path = os.path.join(self.output_dir, filename)
        with open(path, "w") as f:
            json.dump(data, f, indent=2)

    def export_all(self) -> None:
        # Calculate contribution percentage
        total_accepted = registry.global_stats["total_entities_accepted"]
        for _strat, stats in registry.strategy_stats.items():
            if total_accepted > 0:
                stats["contribution_percentage"] = (
                    stats["entities_accepted"] / total_accepted
                ) * 100
            else:
                stats["contribution_percentage"] = 0.0

        # 1. parser_metrics.json (per page metrics)
        self._write_json("parser_metrics.json", registry.page_metrics)

        # 2. strategy_metrics.json
        self._write_json("strategy_metrics.json", registry.strategy_stats)

        # 3. entity_metrics.json (all tracked entities)
        self._write_json("entity_metrics.json", registry.entity_metrics)

        # 4. duplicate_analysis.json
        dupes = {}
        for s, st in registry.strategy_stats.items():
            dupes[s] = {
                "duplicate_entities_generated": st["duplicate_entities_generated"],
                "duplicate_entities_removed": st["duplicate_entities_removed"],
            }
        self._write_json("duplicate_analysis.json", dupes)

        # 5. confidence_distribution.json
        conf = {}
        for s, st in registry.strategy_stats.items():
            conf[s] = {
                "average_confidence": st["average_confidence"],
                "highest_confidence": st["highest_confidence"],
                "lowest_confidence": (
                    st["lowest_confidence"] if st["lowest_confidence"] <= 1.0 else 0.0
                ),
            }
        self._write_json("confidence_distribution.json", conf)

        # 6. strategy_execution_order.json
        order = []
        for page in registry.page_metrics:
            order.append(
                {
                    "URL": page["URL"],
                    "Execution Order": page["Execution Order"],
                    "Winning Strategy": page["Winning Strategy"],
                }
            )
        self._write_json("strategy_execution_order.json", order)

        # 7. entity_contribution.json
        contrib = {}
        for s, st in registry.strategy_stats.items():
            contrib[s] = {
                "entities_contributed": st["entities_accepted"],
                "contribution_percentage": st["contribution_percentage"],
            }
        self._write_json("entity_contribution.json", contrib)

        # 8. benchmark_summary.json
        ent_per_strat = {s: st["entities_accepted"] for s, st in registry.strategy_stats.items()}

        total_dupes = sum(
            st["duplicate_entities_generated"] for st in registry.strategy_stats.values()
        )
        duplicate_rate = total_dupes / (registry.global_stats["total_entities_found"] or 1)

        # Best/Worst
        sorted_strats = sorted(
            registry.strategy_stats.items(), key=lambda x: x[1]["entities_accepted"], reverse=True
        )
        top = [s[0] for s in sorted_strats[:3]]
        worst = [s[0] for s in sorted_strats[-3:]] if len(sorted_strats) >= 3 else []

        avg_runtime = registry.global_stats["total_runtime_ms"] / (
            registry.global_stats["total_pages"] or 1
        )
        avg_conf = sum(st["confidence_sum"] for st in registry.strategy_stats.values()) / (
            sum(st["execution_count"] for st in registry.strategy_stats.values()) or 1
        )

        summary = {
            "Total Pages": registry.global_stats["total_pages"],
            "Total HTML": registry.global_stats["total_html_size"],
            "Total DOM Nodes": registry.global_stats["total_dom_nodes"],
            "Total Entities": registry.global_stats["total_entities_accepted"],
            "Entities Per Strategy": ent_per_strat,
            "Entities Per Competitor": "Not Measured",  # Hard to map competitor names cleanly without DB join here
            "Average Confidence": avg_conf,
            "Average Runtime": avg_runtime,
            "Average Merge Rate": "Not Measured",
            "Duplicate Rate": duplicate_rate,
            "Parser Success Rate": "Not Measured",  # Requires manual validation
            "Top Performing Strategies": top,
            "Worst Performing Strategies": worst,
        }
        self._write_json("benchmark_summary.json", summary)

        # 9. performance_report.json
        perf = {}
        for s, st in registry.strategy_stats.items():
            perf[s] = {
                "execution_count": st["execution_count"],
                "total_execution_time_ms": st["total_execution_time_ms"],
                "average_execution_time_ms": st["average_execution_time_ms"],
                "minimum_execution_time_ms": (
                    st["minimum_execution_time_ms"]
                    if st["minimum_execution_time_ms"] != float("inf")
                    else 0.0
                ),
                "maximum_execution_time_ms": st["maximum_execution_time_ms"],
            }
        self._write_json("performance_report.json", perf)

        print("Observability Framework: Successfully exported 9 JSON reports to reports/")
