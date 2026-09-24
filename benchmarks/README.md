# Performance benchmarks

This directory contains [pytest-benchmark](https://pytest-benchmark.readthedocs.io/)
based timings of the metrics in `cloudmetrics.mask`, computed on deterministic
synthetic cloud masks (thresholded, gaussian-smoothed noise; see
`conftest.py`):

| mask     | size       | objects | cloud fraction |
|----------|------------|---------|----------------|
| `small`  | 256x256 px | 199     | 0.3            |
| `medium` | 512x512 px | 686     | 0.3            |

The benchmarks are not part of the regular test-suite (`pytest` only collects
`tests/`, see `testpaths` in `pyproject.toml`), they are used by the
`performance benchmarks` GitHub workflow (`.github/workflows/ci-performance.yml`)
to check that a pull-request does not make any metric substantially slower.

## Running locally

```bash
pip install pytest-benchmark
OMP_NUM_THREADS=1 NUMBA_NUM_THREADS=1 pytest benchmarks --benchmark-only \
    --benchmark-min-rounds=5 --benchmark-warmup=on --benchmark-disable-gc \
    --benchmark-json=head.json
```

Do the same with the code you want to compare against (e.g. `master` checked
out in a second directory and installed into the same environment with
`pip install --no-deps <path>`, or by pointing `PYTHONPATH` at it) to produce
`base.json`, and compare the two runs with

```bash
python benchmarks/compare.py --base base.json --head head.json \
    --max-slowdown 1.5 --summary summary.md
```

`compare.py` only needs the python standard library. It prints a table with
the median run-time of every benchmark on both sides, the ratio `head / base`
and a status (`faster`, `same`, `slower`, `REGRESSION`), writes the same table
together with the raw statistics of both runs to `summary.md` and exits with
status `1` if any ratio is larger than `--max-slowdown` or a benchmark that ran
on the base is missing (i.e. errored or was removed) on the head. Benchmarks
that only exist on the head are reported for information.

## What the CI check does

On every pull-request the workflow

1. resolves the base commit of the pull-request and checks whether anything
   under `cloudmetrics/` or in `pyproject.toml` differs between the base and
   the head (the merge commit that is tested). If nothing differs, base and
   head would run identical metric code, so the benchmark runs are **skipped**,
   the job succeeds and the Summary tab states that (and why) the benchmarks
   were skipped. This is the case for pull-requests that only touch e.g. the
   documentation, the CI configuration or the benchmarks themselves.
2. installs the pull-request head with its dependencies
   (`pip install ".[test]" pytest-benchmark`),
3. checks out the base commit into a separate directory, installs it into the
   same environment (`pip install --no-deps`) and runs the benchmarks of the
   pull-request head against it,
4. re-installs the head and runs the same benchmarks again,
5. compares the two runs with `compare.py`.

Both runs happen on the same runner in the same job, single-threaded
(`OMP_NUM_THREADS=1`, `NUMBA_NUM_THREADS=1`) to keep the comparison as fair as
possible. The full comparison table, the verdict, the numpy version used and
the raw per-benchmark statistics of both runs are shown in the job's
**Summary** tab of the workflow run (and the table is also printed in the log
of the compare step); no artifacts are uploaded and no PR comment is posted.

The job fails if any benchmark's median on the head exceeds **1.5x** the base
median. GitHub-hosted runners are shared and noisy, so this threshold is
deliberately generous: the check is a coarse guard against accidentally making
a metric several times slower, not a precise measurement. A borderline result
on a change that is not expected to affect performance is most likely noise;
re-run the job before investigating.

### numpy version

Both sides are always measured against the same numpy version, normally the
one resolved by the head install. `np.trapz` was removed in numpy 2.4 (it is
now `np.trapezoid`); if the installed numpy has no `trapz` but the code of
either side (e.g. a base commit that predates the switch to `np.trapezoid`)
still calls it, the workflow installs `numpy<2.4` **before both** benchmark
runs and says so in the summary header and as a warning in the job log. No
numpy version is pinned otherwise.

## Manual runs and A/B comparison of two refs

The workflow can be started manually (`Actions` -> `performance benchmarks` ->
`Run workflow`; this requires the workflow file to be on the default branch).
A manual run always benchmarks, even if the package code is unchanged (the
summary then notes this). The inputs are

| input          | default            | meaning                                          |
|----------------|--------------------|--------------------------------------------------|
| `base_ref`     | `master`           | branch, tag or sha to compare against            |
| `head_ref`     | empty              | branch, tag or sha to benchmark as "head"; empty = the ref the workflow is run from |
| `max_slowdown` | `1.5`              | maximum allowed head/base ratio of the medians   |

With `head_ref` set, that ref is checked out into a second directory and
installed (`pip install --no-deps`) as the head, while the benchmark files and
the dependencies are always taken from the ref the workflow is run from. This
allows e.g. comparing a feature branch `perf/xyz` against `master` (or against
any other ref) without opening a pull-request, and is the way to demonstrate
the check itself for a pull-request that does not change the package code.
