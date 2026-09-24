"""
Shared fixtures for the cloudmetrics performance benchmarks.

The benchmarks operate on deterministic synthetic cloud masks (thresholded,
gaussian-smoothed white noise), so that the same input is used for every run
and the timings of two different code versions can be compared.
"""

import numpy as np
import pytest
from scipy import ndimage

import cloudmetrics

# Mask specifications. `n_objects` is the number of 4-connected objects in the
# mask and is asserted when the mask is created, so that a change in the mask
# generation (e.g. a new numpy/scipy version) is noticed rather than silently
# changing the benchmark workload.
MASK_SPECS = {
    "small": dict(shape=(256, 256), sigma=2.5, seed=0, n_objects=199),
    "medium": dict(shape=(512, 512), sigma=2.5, seed=1, n_objects=686),
}
CLOUD_FRACTION = 0.3


def make_cloud_mask(shape, sigma, seed, cloud_fraction=CLOUD_FRACTION):
    """
    Create a deterministic synthetic cloud mask by gaussian-smoothing white
    noise and thresholding it so that `cloud_fraction` of the pixels are
    cloudy.
    """
    rng = np.random.default_rng(seed)
    field = ndimage.gaussian_filter(rng.standard_normal(shape), sigma)
    return field > np.quantile(field, 1.0 - cloud_fraction)


def count_objects(mask):
    # 4-connectivity, independent of cloudmetrics' own labelling
    _, n_objects = ndimage.label(mask)
    return n_objects


def mask_id(name):
    spec = MASK_SPECS[name]
    ny, nx = spec["shape"]
    return f"{name}-{ny}x{nx}px-{spec['n_objects']}obj"


@pytest.fixture(
    scope="session", params=list(MASK_SPECS), ids=[mask_id(n) for n in MASK_SPECS]
)
def cloud_mask(request):
    """
    Synthetic cloud mask, parametrised over all entries in `MASK_SPECS`.
    """
    spec = MASK_SPECS[request.param]
    mask = make_cloud_mask(shape=spec["shape"], sigma=spec["sigma"], seed=spec["seed"])
    n_objects = count_objects(mask)
    assert n_objects == spec["n_objects"], (
        f"mask '{request.param}' has {n_objects} objects, expected "
        f"{spec['n_objects']} -- the synthetic mask generation changed"
    )
    return mask


@pytest.fixture(scope="session", params=["small"], ids=[mask_id("small")])
def small_cloud_mask(request):
    """
    Only the small synthetic mask, for benchmarks that are expensive to run
    (e.g. O(N^2) in the number of objects).
    """
    spec = MASK_SPECS[request.param]
    mask = make_cloud_mask(shape=spec["shape"], sigma=spec["sigma"], seed=spec["seed"])
    assert count_objects(mask) == spec["n_objects"]
    return mask


@pytest.fixture
def bench(benchmark, request):
    """
    Thin wrapper around the pytest-benchmark `benchmark` fixture that records
    which cloudmetrics version was benchmarked and on which mask, and checks
    that the metric returned a finite value.
    """
    params = getattr(getattr(request.node, "callspec", None), "params", {})
    mask_name = params.get("cloud_mask", params.get("small_cloud_mask"))
    if mask_name is not None:
        spec = MASK_SPECS[mask_name]
        benchmark.extra_info["mask"] = mask_name
        benchmark.extra_info["mask_shape"] = list(spec["shape"])
        benchmark.extra_info["mask_n_objects"] = spec["n_objects"]
    benchmark.extra_info["cloudmetrics_version"] = getattr(
        cloudmetrics, "__version__", "unknown"
    )
    benchmark.extra_info["cloudmetrics_path"] = cloudmetrics.__file__

    def run(fn, *args, **kwargs):
        result = benchmark(fn, *args, **kwargs)
        assert np.all(np.isfinite(result)), f"{fn.__name__} returned {result!r}"
        return result

    return run


def pytest_report_header(config):
    lines = [
        f"cloudmetrics: {getattr(cloudmetrics, '__version__', 'unknown')} "
        f"({cloudmetrics.__file__})",
    ]
    for name, spec in MASK_SPECS.items():
        ny, nx = spec["shape"]
        lines.append(
            f"benchmark mask '{name}': {ny}x{nx} px, {spec['n_objects']} objects, "
            f"cloud fraction {CLOUD_FRACTION}"
        )
    return lines
