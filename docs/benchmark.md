# Benchmarking Vector Indexes

SnipContext ships with `sc benchmark index` to profile build and search latency
for the available vector index backends.

## Usage

```bash
sc benchmark index --help
```

### Options

| Flag | Description | Default |
|------|-------------|---------|
| `-n, --vectors` | Synthetic vector count | `10000` |
| `-d, --dim` | Embedding dimension | `384` |
| `-k, --top-k` | Top-k search depth | `10` |
| `--index-type` | `flat`, `hnsw`, `ivf`, or `ivfpq` | `flat` |
| `--no-auto-switch` | Disable auto-promotion to IVFPQ | auto | 

### Example

```bash
sc benchmark index --vectors 50000 --dim 384 --index-type ivfpq
```

Output table:

```
Vector index benchmark
┏━━━━━━━━━┳━━━━━━━┳━━━━━━━━━┳━━━━━━━━━┳━━━━━━━━┓
┃ Backend ┃ count ┃ trained ┃ build_ms ┃ search_ms ┃
┡━━━━━━━━━╇━━━━━━━╇━━━━━━━━━╇━━━━━━━━━╇━━━━━━━━┩
│ ivfpq   │ 50000 │ True    │ 423.17  │ 12.04   │
└─────────┴───────┴─────────┴─────────┴─────────┘
```

## Running in CI

Synthetic tests are marked `@pytest.mark.slow` and run on a schedule.

```bash
pytest -q -m "slow"
```

## Tuning tips

- Use `--no-auto-switch` to force a specific backend for comparison.
- Keep `--vectors` close to your real collection size for meaningful latency numbers.
- For IVF / IVFPQ, `nlist` scales as `sqrt(n)` and is clamped automatically.
