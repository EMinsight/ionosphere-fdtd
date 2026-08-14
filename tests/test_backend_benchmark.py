from benchmarks.backend_matrix import run_backend_matrix


def test_backend_matrix_always_reports_numpy_cpu() -> None:
    payload = run_backend_matrix(
        subdivision=0,
        radial_cells=2,
        steps=1,
        warmup_steps=0,
        repeats=1,
    )
    numpy_result = payload["results"][0]
    assert numpy_result["backend"] == "numpy"
    assert numpy_result["device"] == "cpu"
    assert numpy_result["status"] == "ok"
    assert numpy_result["steps_per_second"] > 0.0
    assert payload["configuration"]["torch_compile_chunk_size"] == 8
    assert numpy_result["compile_chunk_size"] == 8
