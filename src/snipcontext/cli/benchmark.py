"""Benchmark CLI helpers for SnipContext."""

from __future__ import annotations

import logging
import math
import time

import typer
from rich.box import ASCII as ASCII_BOX
from rich.console import Console
from rich.table import Table

from snipcontext.config.settings import Config, SearchConfig
from snipcontext.core.index_backends import _create_backend

logger = logging.getLogger(__name__)
benchmark_app = typer.Typer(name="benchmark", help="Benchmarks and profiling utilities")

console = Console()


def _safe_nlist(vectors: int) -> int:
    return max(2, min(int(math.sqrt(max(vectors, 2))), 256))


def _safe_pq(vectors: int, max_bits: int = 8) -> int:
    return max(2, min(8, vectors))


@benchmark_app.command("index")  # type: ignore[untyped-decorator]
def benchmark_index(
    vectors: int = typer.Option(10000, "--vectors", "-n", help="Synthetic vector count"),
    dimension: int = typer.Option(384, "--dim", "-d", help="Embedding dimension"),
    top_k: int = typer.Option(10, "--top-k", "-k", help="Top-k search depth"),
    index_type: str = typer.Option("flat", "--index-type", help="Flat, hnsw, ivf, or ivfpq"),
    no_auto_switch: bool = typer.Option(
        False, "--no-auto-switch", help="Disable auto-promotion from flat to IVFPQ"
    ),
) -> None:
    """Benchmark vector index build and search latency."""
    nlist = _safe_nlist(vectors)
    pq_m = _safe_pq(vectors)
    config = Config(
        search=SearchConfig(
            index_type=index_type,
            auto_index_threshold=max(vectors + 1, 100_000),
            auto_switch=not no_auto_switch,
            ivf_nlist=nlist,
            pq_M=pq_m,
            pq_nbits=8,
        ),
    )
    backend = _create_backend(
        config, dimension, snippet_count=vectors, auto_switch=config.search.auto_switch
    )
    rng = __import__("numpy").random.RandomState(0)
    data = rng.randn(vectors, dimension).astype("float32")
    data /= __import__("numpy").linalg.norm(data, axis=1, keepdims=True)
    ids = [f"doc-{i}" for i in range(vectors)]

    build_start = time.perf_counter()
    try:
        backend.train(data)
        backend.add(data, ids)
    except Exception as exc:
        logger.warning("Benchmark train/add failed: %s", exc)
    build_elapsed = time.perf_counter() - build_start

    query = rng.randn(1, dimension).astype("float32")
    query /= __import__("numpy").linalg.norm(query, axis=1, keepdims=True)

    search_elapsed = _bootstrap_search(backend, query, top_k)

    table = Table(title="Vector index benchmark", box=ASCII_BOX)
    table.add_column("Backend", style="magenta")
    table.add_column("count", justify="right")
    table.add_column("trained", justify="center")
    table.add_column("build_ms", justify="right")
    table.add_column("search_ms", justify="right")
    table.add_row(
        index_type,
        str(backend.count),
        str(backend.is_trained),
        f"{build_elapsed * 1000:.2f}",
        f"{search_elapsed * 1000:.2f}" if search_elapsed is not None else "n/a",
    )
    console.print(table)
    logger.info("Benchmark complete on %d vectors", vectors)


def _bootstrap_search(backend, query, top_k):
    start = time.perf_counter()
    try:
        backend.search(query, top_k)
        return time.perf_counter() - start
    except Exception as exc:
        logger.warning("Search benchmark failed: %s", exc)
        return None


def register_commands(app) -> None:
    app.add_typer(benchmark_app)
