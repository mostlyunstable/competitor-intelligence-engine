from typing import Any

from app.observability.entity_profiler import EntityProfiler


class ProfilerRegistry:
    def __init__(self) -> None:
        self.strategy_stats: dict[str, Any] = {}
        self.page_metrics: list[dict[str, Any]] = []
        self.entity_metrics: list[Any] = []
        self.global_stats = {
            "total_pages": 0,
            "total_html_size": 0,
            "total_dom_nodes": 0,
            "total_entities_found": 0,
            "total_entities_accepted": 0,
            "parser_errors": 0,
            "skipped_pages": 0,
            "skipped_due_to_low_confidence": 0,
            "total_runtime_ms": 0.0,
        }

    def clear(self) -> None:
        self.strategy_stats.clear()
        self.page_metrics.clear()
        self.entity_metrics.clear()
        for key in self.global_stats:
            self.global_stats[key] = 0 if isinstance(self.global_stats[key], int) else 0.0


registry = ProfilerRegistry()
entity_profiler = EntityProfiler()


class ParserObserver:
    def __init__(self) -> None:
        self.current_page: dict[str, Any] = {}

    def on_page_start(self, url: str, competitor_id: int, html_size: int, dom_nodes: int) -> None:
        self.current_page = {
            "URL": url,
            "Competitor": competitor_id,
            "Page Type": "Unknown",
            "HTML Size": html_size,
            "DOM Nodes": dom_nodes,
            "Strategies Executed": 0,
            "Execution Order": [],
            "Execution Time": 0.0,
            "Winning Strategy": None,
            "Confidence": 0.0,
            "Entities Produced": 0,
            "Entities Stored": 0,
            "Entities Rejected": 0,
            "Duplicates Removed": 0,
            "Database Writes": 0,
        }
        registry.global_stats["total_pages"] += 1
        registry.global_stats["total_html_size"] += html_size
        registry.global_stats["total_dom_nodes"] += dom_nodes

    def on_strategy_start(self, strategy_name: str) -> None:
        if strategy_name not in registry.strategy_stats:
            registry.strategy_stats[strategy_name] = {
                "execution_count": 0,
                "total_execution_time_ms": 0.0,
                "average_execution_time_ms": 0.0,
                "minimum_execution_time_ms": float("inf"),
                "maximum_execution_time_ms": 0.0,
                "entities_found": 0,
                "entities_accepted": 0,
                "entities_rejected": 0,
                "duplicate_entities_generated": 0,
                "duplicate_entities_removed": 0,
                "average_confidence": 0.0,
                "highest_confidence": 0.0,
                "lowest_confidence": 1.0,
                "merge_contribution": 0.0,
                "contribution_percentage": 0.0,
                "parser_errors": 0,
                "exceptions": 0,
                "confidence_sum": 0.0,
            }

        self.current_page["Execution Order"].append(strategy_name)
        self.current_page["Strategies Executed"] += 1

    def on_strategy_success(
        self, strategy_name: str, partial_result: Any, execution_time_ms: float
    ) -> None:
        stats = registry.strategy_stats[strategy_name]
        stats["execution_count"] += 1
        stats["total_execution_time_ms"] += execution_time_ms
        stats["minimum_execution_time_ms"] = min(
            stats["minimum_execution_time_ms"], execution_time_ms
        )
        stats["maximum_execution_time_ms"] = max(
            stats["maximum_execution_time_ms"], execution_time_ms
        )
        stats["average_execution_time_ms"] = (
            stats["total_execution_time_ms"] / stats["execution_count"]
        )
        self.current_page["Execution Time"] += execution_time_ms

    def on_strategy_error(
        self, strategy_name: str, exception: Exception, execution_time_ms: float
    ) -> None:
        stats = registry.strategy_stats[strategy_name]
        stats["execution_count"] += 1
        stats["total_execution_time_ms"] += execution_time_ms
        stats["parser_errors"] += 1
        stats["exceptions"] += 1
        registry.global_stats["parser_errors"] += 1

    def on_merge_complete(
        self,
        strategy_name: str,
        partial_result: Any,
        pre_merge_result: Any,
        post_merge_result: Any,
        url: str,
    ) -> None:
        stats = registry.strategy_stats[strategy_name]

        # Deep profile the exact entities
        profile_res = entity_profiler.profile_merge(
            strategy_name, partial_result, pre_merge_result, post_merge_result, url
        )

        accepted_ents = profile_res["accepted"]
        rejected_ents = profile_res["rejected"]

        accepted = len(accepted_ents)
        rejected = len(rejected_ents)
        partial_entities = accepted + rejected

        stats["entities_found"] += partial_entities
        stats["entities_accepted"] += accepted
        stats["entities_rejected"] += rejected
        stats["duplicate_entities_generated"] += rejected
        stats["duplicate_entities_removed"] += rejected

        partial_conf = partial_result.confidence
        stats["confidence_sum"] += partial_conf
        stats["average_confidence"] = (
            stats["confidence_sum"] / stats["execution_count"] if stats["execution_count"] else 0
        )
        stats["highest_confidence"] = max(stats["highest_confidence"], partial_conf)
        stats["lowest_confidence"] = min(stats["lowest_confidence"], partial_conf)
        stats["merge_contribution"] += post_merge_result.confidence - pre_merge_result.confidence

        registry.global_stats["total_entities_found"] += partial_entities
        registry.global_stats["total_entities_accepted"] += accepted

        self.current_page["Entities Produced"] += partial_entities
        self.current_page["Entities Stored"] += accepted
        self.current_page["Entities Rejected"] += rejected
        self.current_page["Duplicates Removed"] += rejected

        # Save exact entities to registry
        registry.entity_metrics.extend(accepted_ents)
        registry.entity_metrics.extend(rejected_ents)

    def on_page_end(self, final_result: Any) -> None:
        self.current_page["Confidence"] = final_result.confidence

        winning = None
        highest = 0
        for strat in self.current_page["Execution Order"]:
            s = registry.strategy_stats.get(strat, {})
            if s.get("highest_confidence", 0) > highest:
                highest = s["highest_confidence"]
                winning = strat
        self.current_page["Winning Strategy"] = winning

        registry.global_stats["total_runtime_ms"] += self.current_page["Execution Time"]
        registry.page_metrics.append(self.current_page)
