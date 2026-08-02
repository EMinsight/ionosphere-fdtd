import numpy as np
import pytest

from ionosphere.backends import BackendUnavailableError
from ionosphere.backends.numpy_backend import NumPyBackend
from ionosphere.mesh import build_geodesic_mesh
from ionosphere.solver import GeodesicFDTD, SimulationConfig
from ionosphere.sources import GaussianCurrent


def config() -> SimulationConfig:
    return SimulationConfig(subdivision=1, radial_cells=6, courant_factor=0.2)


def source() -> GaussianCurrent:
    return GaussianCurrent(peak_current_a=1.0e6)


def test_numpy_backend_defaults_to_cpu_float64() -> None:
    simulation = GeodesicFDTD(config=config())
    assert simulation.backend.name == "numpy"
    assert simulation.backend.device == "cpu"
    assert simulation.backend.dtype_name == "float64"
    assert simulation.er.dtype == np.float64


def test_numpy_backend_rejects_accelerator_device() -> None:
    with pytest.raises(BackendUnavailableError, match="only supports"):
        GeodesicFDTD(config=config(), backend="numpy", device="mps")


def test_numpy_backend_rejects_compiled_step() -> None:
    with pytest.raises(BackendUnavailableError, match="compiled field steps"):
        GeodesicFDTD(config=config(), backend="numpy", compile_step=True)


def test_numpy_backend_rejects_torch_threads() -> None:
    with pytest.raises(BackendUnavailableError, match="PyTorch CPU"):
        GeodesicFDTD(config=config(), backend="numpy", torch_threads=1)


@pytest.mark.parametrize("trailing_shape", [(), (7,), (3, 4)])
def test_numpy_incidence_circulation_matches_scatter(
    trailing_shape: tuple[int, ...],
) -> None:
    mesh = build_geodesic_mesh(1)
    backend = NumPyBackend(mesh)
    values = np.random.default_rng(42).standard_normal(
        (mesh.n_edges,) + trailing_shape
    )

    expected = mesh.dual_cell_circulation(values)
    actual = backend.dual_cell_circulation(values)

    np.testing.assert_allclose(actual, expected, rtol=1.0e-13, atol=1.0e-13)
    assert np.count_nonzero(backend.vertex_edge_signs, axis=1).min() == 5
    assert np.count_nonzero(backend.vertex_edge_signs, axis=1).max() == 6


def test_torch_cpu_matches_numpy() -> None:
    torch = pytest.importorskip("torch")
    numpy_simulation = GeodesicFDTD(
        config=config(), source=source(), backend="numpy", dtype="float64"
    )
    torch_simulation = GeodesicFDTD(
        config=config(),
        source=source(),
        backend="torch",
        device="cpu",
        dtype="float64",
    )

    numpy_simulation.step(40)
    torch_simulation.step(40)

    assert torch_simulation.er.device.type == "cpu"
    assert torch_simulation.er.dtype == torch.float64
    for field in ("er", "et", "hr", "ht"):
        expected = getattr(numpy_simulation, field)
        actual = torch_simulation.to_numpy(getattr(torch_simulation, field))
        np.testing.assert_allclose(actual, expected, rtol=1.0e-11, atol=1.0e-12)


def test_torch_auto_float32_tracks_float64_reference() -> None:
    torch = pytest.importorskip("torch")
    reference = GeodesicFDTD(
        config=config(), source=source(), backend="numpy", dtype="float64"
    )
    optimized = GeodesicFDTD(
        config=config(), source=source(), backend="torch", device="cpu"
    )

    reference.step(80)
    optimized.step(80)

    assert optimized.er.dtype == torch.float32
    assert optimized.memory_bytes * 2 == reference.memory_bytes
    for fields in (("er", "et"), ("hr", "ht")):
        expected = np.concatenate(
            tuple(getattr(reference, field).ravel() for field in fields)
        )
        actual = np.concatenate(
            tuple(
                optimized.to_numpy(getattr(optimized, field)).ravel()
                for field in fields
            )
        )
        relative_l2_error = np.linalg.norm(actual - expected) / np.linalg.norm(
            expected
        )
        assert relative_l2_error < 2.0e-5
    radial_magnetic_noise = np.max(
        np.abs(optimized.to_numpy(optimized.hr) - reference.hr)
    )
    assert radial_magnetic_noise < 1.0e-6 * np.max(np.abs(reference.ht))


def test_torch_compiled_cpu_matches_eager_with_source() -> None:
    pytest.importorskip("torch")
    eager = GeodesicFDTD(
        config=config(),
        source=source(),
        backend="torch",
        device="cpu",
        dtype="float64",
    )
    compiled = GeodesicFDTD(
        config=config(),
        source=source(),
        backend="torch",
        device="cpu",
        dtype="float64",
        compile_step=True,
    )

    eager.step(12)
    compiled.step(12)

    assert compiled.compiled
    assert compiled.steps == eager.steps
    assert compiled.time_s == pytest.approx(eager.time_s)
    for field in ("er", "et", "hr", "ht"):
        np.testing.assert_allclose(
            compiled.to_numpy(getattr(compiled, field)),
            eager.to_numpy(getattr(eager, field)),
            rtol=1.0e-11,
            atol=1.0e-12,
        )


def test_torch_cpu_thread_count_is_configurable() -> None:
    torch = pytest.importorskip("torch")
    previous_threads = torch.get_num_threads()
    try:
        simulation = GeodesicFDTD(
            config=config(),
            backend="torch",
            device="cpu",
            torch_threads=1,
        )
        assert simulation.backend.threads == 1
        assert torch.get_num_threads() == 1
    finally:
        torch.set_num_threads(previous_threads)


def test_torch_auto_selects_an_available_device() -> None:
    torch = pytest.importorskip("torch")
    expected = (
        "cuda"
        if torch.cuda.is_available()
        else "mps"
        if torch.backends.mps.is_available()
        else "cpu"
    )
    simulation = GeodesicFDTD(config=config(), backend="torch", device="auto")
    assert simulation.er.device.type == expected
    assert simulation.er.dtype == torch.float32


def test_torch_fields_cross_the_visualization_boundary_as_numpy() -> None:
    pytest.importorskip("torch")
    from ionosphere.visualization import _surface_values

    simulation = GeodesicFDTD(
        config=config(), source=source(), backend="torch", device="cpu"
    )
    simulation.step(2)
    values, _, association = _surface_values(simulation, "er", 0.0)
    assert isinstance(values, np.ndarray)
    assert association == "point"
    assert np.isfinite(values).all()


def test_torch_mps_runs_when_available() -> None:
    torch = pytest.importorskip("torch")
    if not torch.backends.mps.is_available():
        with pytest.raises(BackendUnavailableError, match="MPS"):
            GeodesicFDTD(config=config(), backend="torch", device="mps")
        return

    simulation = GeodesicFDTD(
        config=config(), source=source(), backend="torch", device="mps"
    )
    simulation.step(5)
    assert simulation.er.device.type == "mps"
    assert simulation.er.dtype == torch.float32
    assert np.isfinite(simulation.to_numpy(simulation.er)).all()


def test_torch_gpu_alias_uses_cuda_or_reports_unavailable() -> None:
    torch = pytest.importorskip("torch")
    if not torch.cuda.is_available():
        with pytest.raises(BackendUnavailableError, match="CUDA"):
            GeodesicFDTD(config=config(), backend="torch", device="gpu")
        return

    simulation = GeodesicFDTD(config=config(), backend="torch", device="gpu")
    assert simulation.er.device.type == "cuda"


def test_torch_mps_rejects_float64_when_available() -> None:
    torch = pytest.importorskip("torch")
    if not torch.backends.mps.is_available():
        pytest.skip("MPS is unavailable")
    with pytest.raises(BackendUnavailableError, match="does not support float64"):
        GeodesicFDTD(
            config=config(), backend="torch", device="mps", dtype="float64"
        )
