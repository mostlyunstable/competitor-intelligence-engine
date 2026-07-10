"""APM endpoint for performance monitoring.

Provides API endpoints for accessing APM data.
"""

from __future__ import annotations

from typing import Any

from fastapi import APIRouter

from app.observability.apm import apm_collector
from app.observability.performance_budgets import performance_budget_manager

router = APIRouter(tags=["APM"])


@router.get(
    "/apm/transactions",
    summary="APM Transactions",
    description="Get recent APM transactions with performance data.",
    responses={
        200: {
            "description": "List of APM transactions",
            "content": {
                "application/json": {
                    "example": {
                        "transactions": [
                            {
                                "transaction_id": "txn_123",
                                "name": "collection",
                                "start_time": 1689000000.0,
                                "duration_ms": 25000,
                                "status": "ok",
                                "span_count": 15,
                                "attributes": {"competitor_id": 1},
                            }
                        ],
                        "stats": {
                            "total_transactions": 150,
                            "avg_transaction_duration": 25000,
                            "p95_transaction_duration": 45000,
                            "error_rate": 0.02,
                        },
                    }
                }
            },
        }
    },
)
async def get_apm_transactions(limit: int = 100) -> dict[str, Any]:
    """Get recent APM transactions."""
    transactions = apm_collector.get_transactions(limit)
    stats = apm_collector.get_stats()
    return {"transactions": transactions, "stats": stats}


@router.get(
    "/apm/performance-budgets",
    summary="Performance Budgets",
    description="Get performance budget status and compliance.",
    responses={
        200: {
            "description": "Performance budget status",
            "content": {
                "application/json": {
                    "example": {
                        "budgets": [
                            {
                                "budget": "parse_time",
                                "target": 1000,
                                "unit": "ms",
                                "status": "within_budget",
                                "measurements": {
                                    "count": 500,
                                    "avg": 250,
                                    "min": 100,
                                    "max": 500,
                                    "p95": 400,
                                    "p99": 480,
                                },
                                "compliance": {
                                    "within_budget": 450,
                                    "warnings": 30,
                                    "exceeded": 20,
                                },
                            }
                        ],
                        "summary": {
                            "total_budgets": 10,
                            "total_violations": 50,
                            "recent_violations": 5,
                        },
                    }
                }
            },
        }
    },
)
async def get_performance_budgets() -> dict[str, Any]:
    """Get performance budget status."""
    budgets = performance_budget_manager.get_all_budgets_status()
    summary = performance_budget_manager.get_summary()
    return {"budgets": budgets, "summary": summary}


@router.get(
    "/apm/performance-budgets/{budget_name}",
    summary="Performance Budget Detail",
    description="Get detailed status for a specific performance budget.",
    responses={
        200: {
            "description": "Performance budget detail",
            "content": {
                "application/json": {
                    "example": {
                        "budget": "parse_time",
                        "target": 1000,
                        "warning_threshold": 0.8,
                        "unit": "ms",
                        "description": "HTML parsing time",
                        "measurements": {
                            "count": 500,
                            "avg": 250,
                            "min": 100,
                            "max": 500,
                            "p95": 400,
                            "p99": 480,
                        },
                        "compliance": {
                            "within_budget": 450,
                            "warnings": 30,
                            "exceeded": 20,
                        },
                        "recent_violations": 5,
                    }
                }
            },
        }
    },
)
async def get_performance_budget_detail(budget_name: str) -> dict[str, Any]:
    """Get detailed status for a specific performance budget."""
    return performance_budget_manager.get_budget_status(budget_name)


@router.get(
    "/apm/violations",
    summary="Performance Violations",
    description="Get recent performance budget violations.",
    responses={
        200: {
            "description": "List of violations",
            "content": {
                "application/json": {
                    "example": {
                        "violations": [
                            {
                                "budget": "parse_time",
                                "actual_value": 1200,
                                "target_value": 1000,
                                "unit": "ms",
                                "status": "exceeded",
                                "timestamp": 1689000000.0,
                            }
                        ],
                        "total": 50,
                        "recent": 5,
                    }
                }
            },
        }
    },
)
async def get_performance_violations(limit: int = 50) -> dict[str, Any]:
    """Get recent performance violations."""
    violations = performance_budget_manager.get_violations(limit)
    return {
        "violations": violations,
        "total": len(violations),
        "recent": len([v for v in violations if v.get("timestamp", 0) > 1689000000]),
    }
