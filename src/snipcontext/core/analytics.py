"""Analytics and insights for snippet collections.

Pure functions that compute detailed statistics from Snippet data.
No I/O, no CLI dependencies. Accepts a list of Snippet objects and
returns structured analytics data.
"""

from __future__ import annotations

from collections import Counter
from datetime import datetime, timedelta
from typing import Any


def compute_basic_stats(snippets: list[Any]) -> dict[str, Any]:
    """Compute basic collection statistics.

    Args:
        snippets: List of Snippet model instances.

    Returns:
        Dictionary with total counts, language distribution, tag counts,
        oldest/newest dates, and storage size metrics.
    """
    if not snippets:
        return {
            "total_snippets": 0,
            "total_tags": 0,
            "languages": {},
            "tags": {},
            "oldest": None,
            "newest": None,
            "deleted_count": 0,
            "total_size_bytes": 0,
        }

    languages: Counter[str] = Counter()
    tags: Counter[str] = Counter()
    total_size = 0
    deleted_count = 0
    oldest = None
    newest = None

    for s in snippets:
        languages[s.metadata.language.value] += 1
        for tag in s.tags:
            tags[tag] += 1
        total_size += len(s.content.encode("utf-8"))
        if s.deleted:
            deleted_count += 1

        created = s.created_at
        updated = s.updated_at
        if oldest is None or created < oldest:
            oldest = created
        if newest is None or updated > newest:
            newest = updated

    return {
        "total_snippets": len(snippets),
        "total_tags": len(tags),
        "languages": dict(languages.most_common()),
        "tags": dict(tags.most_common()),
        "oldest": oldest.isoformat() if oldest else None,
        "newest": newest.isoformat() if newest else None,
        "deleted_count": deleted_count,
        "total_size_bytes": total_size,
    }


def compute_detailed_stats(snippets: list[Any]) -> dict[str, Any]:
    """Compute detailed collection statistics for power users.

    Includes everything from basic_stats plus:
    - Tag distribution (top N)
    - Access count metrics (most/least accessed, average)
    - Size metrics (lines, characters per snippet)
    - Temporal metrics (creation timeline by month/week)
    - Confidence breakdown
    - Version statistics
    - Average tags per snippet

    Args:
        snippets: List of Snippet model instances.

    Returns:
        Dictionary with all analytics data.
    """
    basic = compute_basic_stats(snippets)
    if not snippets:
        return {
            **basic,
            "access_counts": {"most_accessed": [], "least_accessed": [], "average": 0.0},
            "size_metrics": {"average_lines": 0.0, "average_chars": 0.0, "largest": []},
            "confidence": {},
            "versions": {"average": 0.0, "max": 0},
            "avg_tags_per_snippet": 0.0,
            "timeline_weekly": {},
            "timeline_monthly": {},
            "authors": {},
            "language_distribution": {},
        }

    # Access counts
    access_list = [(s.id[:8], s.metadata.title, s.access_count) for s in snippets]
    access_list.sort(key=lambda item: item[2], reverse=True)
    most_accessed = access_list[:5]
    least_accessed = (
        [item for item in access_list if item[2] > 0][-5:]
        if any(item[2] > 0 for item in access_list)
        else []
    )
    avg_access = sum(item[2] for item in access_list) / len(access_list)

    # Size metrics
    size_list = [
        (s.id[:8], s.metadata.title, len(s.content.splitlines()), len(s.content)) for s in snippets
    ]
    size_list.sort(key=lambda item: item[3], reverse=True)
    largest = size_list[:5]
    avg_lines = sum(item[2] for item in size_list) / len(size_list)
    avg_chars = sum(item[3] for item in size_list) / len(size_list)

    # Confidence breakdown
    confidence: Counter[str] = Counter()
    for s in snippets:
        confidence[s.metadata.confidence] += 1

    # Version statistics
    version_counts = [len(s.versions) for s in snippets]
    avg_versions = sum(version_counts) / len(version_counts) if version_counts else 0.0
    max_versions = max(version_counts) if version_counts else 0

    # Average tags per snippet
    avg_tags = sum(len(s.tags) for s in snippets) / len(snippets)

    # Timeline — weekly and monthly counts based on created_at
    from datetime import timezone

    now = datetime.now(timezone.utc)
    if snippets:
        # Use the same timezone as the snippets
        sample_dt = snippets[0].created_at
        if sample_dt.tzinfo is None:
            now = now.replace(tzinfo=None)
    one_week_ago = now - timedelta(weeks=1)
    one_month_ago = now - timedelta(days=30)
    three_months_ago = now - timedelta(days=90)
    six_months_ago = now - timedelta(days=180)

    weekly: Counter[str] = Counter()
    monthly: Counter[str] = Counter()
    for s in snippets:
        # Weekly buckets (last 8 weeks)
        age_weeks = (now - s.created_at).days // 7
        if age_weeks < 8:
            bucket = f"W{-age_weeks}" if age_weeks > 0 else "this week"
            weekly[bucket] += 1

        # Monthly buckets (last 6 months)
        age_months = (now - s.created_at).days // 30
        if age_months < 6:
            bucket = f"M{-age_months}" if age_months > 0 else "this month"
            monthly[bucket] += 1

    # Recent counts
    added_this_week = sum(1 for s in snippets if s.created_at >= one_week_ago)
    added_this_month = sum(1 for s in snippets if s.created_at >= one_month_ago)
    added_last_3_months = sum(1 for s in snippets if s.created_at >= three_months_ago)
    added_last_6_months = sum(1 for s in snippets if s.created_at >= six_months_ago)

    # Author breakdown
    authors: Counter[str] = Counter()
    for s in snippets:
        author = s.metadata.author or "unknown"
        authors[author] += 1

    # Language distribution with percentages
    lang_total = sum(basic["languages"].values())
    language_distribution = {
        lang: {
            "count": count,
            "percent": round(count / lang_total * 100, 1) if lang_total else 0,
        }
        for lang, count in sorted(
            basic["languages"].items(), key=lambda item: item[1], reverse=True
        )
    }

    return {
        **basic,
        "access_counts": {
            "most_accessed": [
                {"id": item[0], "title": item[1], "count": item[2]} for item in most_accessed
            ],
            "least_accessed": [
                {"id": item[0], "title": item[1], "count": item[2]} for item in least_accessed
            ],
            "average": round(avg_access, 2),
        },
        "size_metrics": {
            "average_lines": round(avg_lines, 1),
            "average_chars": round(avg_chars, 1),
            "largest": [
                {"id": item[0], "title": item[1], "lines": item[2], "chars": item[3]}
                for item in largest
            ],
        },
        "confidence": dict(confidence.most_common()),
        "versions": {"average": round(avg_versions, 2), "max": max_versions},
        "avg_tags_per_snippet": round(avg_tags, 2),
        "timeline_weekly": dict(sorted(weekly.items(), key=lambda item: item[0], reverse=True)),
        "timeline_monthly": dict(sorted(monthly.items(), key=lambda item: item[0], reverse=True)),
        "recent": {
            "this_week": added_this_week,
            "this_month": added_this_month,
            "last_3_months": added_last_3_months,
            "last_6_months": added_last_6_months,
        },
        "authors": dict(authors.most_common()),
        "language_distribution": language_distribution,
    }


def format_ascii_bar(data: dict[str, int], max_width: int = 30) -> list[str]:
    """Format a dict of label->count as ASCII bar chart lines.

    Args:
        data: Dictionary of label to count.
        max_width: Maximum width of the bar in characters.

    Returns:
        List of formatted strings, one per entry.
    """
    if not data:
        return ["  (no data)"]

    max_val = max(data.values()) if data else 1
    lines: list[str] = []
    for label, count in data.items():
        bar_len = int(count / max_val * max_width) if max_val else 0
        bar = "\u2588" * bar_len
        lines.append(f"  {label:<16} {bar} {count}")
    return lines
