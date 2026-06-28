"""Tests for the analytics module (Issue #18)."""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from snipcontext.core.analytics import compute_basic_stats, compute_detailed_stats, format_ascii_bar
from snipcontext.core.models import Language, Snippet, SnippetMetadata


def _make_snippet(
    title: str = "Test",
    language: str = "python",
    tags: list[str] | None = None,
    content: str = "print('hello')",
    access_count: int = 0,
    confidence: str = "draft",
    days_ago: int = 0,
) -> Snippet:
    """Helper to create a snippet for testing."""
    created = datetime.now(timezone.utc) - timedelta(days=days_ago)
    try:
        lang_enum = Language(language)
    except ValueError:
        lang_enum = Language.UNKNOWN
    snippet = Snippet(
        content=content,
        metadata=SnippetMetadata(
            title=title,
            language=lang_enum,
            confidence=confidence,
        ),
        tags=tags or [],
        created_at=created,
        updated_at=created,
        access_count=access_count,
    )
    return snippet


class TestBasicStats:
    """Tests for compute_basic_stats."""

    def test_empty_collection(self):
        result = compute_basic_stats([])
        assert result["total_snippets"] == 0
        assert result["total_tags"] == 0
        assert result["languages"] == {}
        assert result["oldest"] is None

    def test_single_snippet(self):
        snippets = [_make_snippet(title="A", tags=["python", "cli"])]
        result = compute_basic_stats(snippets)
        assert result["total_snippets"] == 1
        assert result["total_tags"] == 2
        assert result["languages"] == {"python": 1}
        assert result["oldest"] is not None
        assert result["newest"] is not None

    def test_language_distribution(self):
        snippets = [
            _make_snippet(title="Py1", language="python"),
            _make_snippet(title="Py2", language="python"),
            _make_snippet(title="Go1", language="go"),
        ]
        result = compute_basic_stats(snippets)
        assert result["languages"] == {"python": 2, "go": 1}

    def test_tag_distribution(self):
        snippets = [
            _make_snippet(title="A", tags=["web", "api"]),
            _make_snippet(title="B", tags=["web", "test"]),
        ]
        result = compute_basic_stats(snippets)
        assert result["tags"]["web"] == 2
        assert result["tags"]["api"] == 1

    def test_size_metrics(self):
        snippets = [
            _make_snippet(content="x" * 100),
            _make_snippet(content="y" * 200),
        ]
        result = compute_basic_stats(snippets)
        assert result["total_size_bytes"] == 300


class TestDetailedStats:
    """Tests for compute_detailed_stats."""

    def test_empty_collection(self):
        result = compute_detailed_stats([])
        assert result["total_snippets"] == 0
        assert result["access_counts"]["average"] == 0.0

    def test_access_counts(self):
        snippets = [
            _make_snippet(title="Popular", access_count=10),
            _make_snippet(title="Unpopular", access_count=1),
            _make_snippet(title="Medium", access_count=5),
        ]
        result = compute_detailed_stats(snippets)
        assert result["access_counts"]["average"] == round(16 / 3, 2)
        assert result["access_counts"]["most_accessed"][0]["count"] == 10

    def test_size_metrics(self):
        snippets = [
            _make_snippet(content="line1\nline2\nline3"),  # 3 lines
            _make_snippet(content="single"),  # 1 line
        ]
        result = compute_detailed_stats(snippets)
        assert result["size_metrics"]["average_lines"] == 2.0
        assert result["size_metrics"]["largest"][0]["lines"] == 3

    def test_confidence_breakdown(self):
        snippets = [
            _make_snippet(confidence="production"),
            _make_snippet(confidence="production"),
            _make_snippet(confidence="draft"),
        ]
        result = compute_detailed_stats(snippets)
        assert result["confidence"]["production"] == 2
        assert result["confidence"]["draft"] == 1

    def test_avg_tags_per_snippet(self):
        snippets = [
            _make_snippet(tags=["a", "b", "c"]),
            _make_snippet(tags=["x"]),
        ]
        result = compute_detailed_stats(snippets)
        assert result["avg_tags_per_snippet"] == 2.0

    def test_language_distribution_with_percentages(self):
        snippets = [
            _make_snippet(language="python"),
            _make_snippet(language="python"),
            _make_snippet(language="go"),
            _make_snippet(language="go"),
        ]
        result = compute_detailed_stats(snippets)
        dist = result["language_distribution"]
        assert dist["python"]["count"] == 2
        assert dist["python"]["percent"] == 50.0
        assert dist["go"]["percent"] == 50.0

    def test_recent_counts(self):
        today = 0
        yesterday = 1
        snippets = [
            _make_snippet(title="Today", days_ago=today),
            _make_snippet(title="Yesterday", days_ago=yesterday),
            _make_snippet(title="Old", days_ago=120),
        ]
        result = compute_detailed_stats(snippets)
        # "this_week" should include snippets from last 7 days
        assert result["recent"]["this_week"] == 2
        assert result["recent"]["this_month"] == 2
        assert result["recent"]["last_3_months"] == 2
        assert result["recent"]["last_6_months"] == 3

    def test_includes_basic_fields(self):
        snippets = [_make_snippet(title="T", tags=["x"])]
        result = compute_detailed_stats(snippets)
        assert result["total_snippets"] == 1
        assert result["total_tags"] == 1


class TestFormatAsciiBar:
    """Tests for format_ascii_bar."""

    def test_empty_data(self):
        lines = format_ascii_bar({})
        assert lines == ["  (no data)"]

    def test_single_entry(self):
        lines = format_ascii_bar({"python": 5})
        assert len(lines) == 1
        assert "python" in lines[0]
        assert "\u2588" in lines[0]

    def test_multiple_entries_sorted_by_value(self):
        data = {"go": 1, "python": 5, "rust": 3}
        lines = format_ascii_bar(data, max_width=10)
        assert len(lines) == 3
        # Python should have the longest bar
        python_line = next(line for line in lines if "python" in line)
        go_line = next(line for line in lines if "go" in line)
        assert python_line.count("\u2588") > go_line.count("\u2588")

    def test_max_width_respected(self):
        lines = format_ascii_bar({"x": 100}, max_width=5)
        bar_part = lines[0].split("\u2588")[1] if "\u2588" in lines[0] else ""
        block_count = len(bar_part.split("\u2588")) - 1
        assert block_count <= 5
