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

On every pull-request (and manually via `workflow_dispatch`, where the base ref
and the threshold can be chosen) the workflow

1. installs the pull-request head with its dependencies,
2. checks out the base commit of the pull-request into a separate directory,
   installs it into the same environment (`pip install --no-deps`) and runs the
   benchmarks of the pull-request head against it,
3. re-installs the head and runs the same benchmarks again,
4. compares the two runs with `compare.py`.

Both runs happen on the same runner in the same job, single-threaded
(`OMP_NUM_THREADS=1`, `NUMBA_NUM_THREADS=1`) to keep the comparison as fair as
possible. The full comparison table, the verdict and the raw per-benchmark
statistics of both runs are shown in the job's **Summary** tab of the workflow
run (and the table is also printed in the log of the compare step); no
artifacts are uploaded and no PR comment is posted.

The job fails if any benchmark's median on the head exceeds **1.5x** the base
median. GitHub-hosted runners are shared and noisy, so this threshold is
deliberately generous: the check is a coarse guard against accidentally making
a metric several times slower, not a precise measurement. A borderline result
on a change that is not expected to affect performance is most likely noise;
re-run the job before investigating.
