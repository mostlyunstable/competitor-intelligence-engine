from app.services.analytics.benchmark_matrix import benchmark_matrix_service


def test_benchmark_matrix_computation():
    rows = benchmark_matrix_service.compute_matrix()
    assert len(rows) > 0

    first = rows[0]
    assert first.market_min <= first.market_median <= first.market_max
    assert first.price_index > 0
    assert first.market_position in {"overpriced", "discount", "par_with_market", "competitive"}
