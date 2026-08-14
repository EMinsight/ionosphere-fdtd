from benchmarks.analytic_solutions import benchmark_cases


def test_analytic_benchmark_registry_covers_each_case_once() -> None:
    assert tuple(benchmark_cases()) == ("A0", "A1", "A2", "A3", "A4")
    assert "auxiliary-reference" in benchmark_cases()["A3"][0]
    assert all("workflow" in workload for workload, _, _ in benchmark_cases().values())
