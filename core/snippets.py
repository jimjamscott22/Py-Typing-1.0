"""Developer code snippets, turned into sidebar lessons."""

from __future__ import annotations

from typing import List, Sequence

from core.models import Lesson, Snippet
from core.snippet_data import ALL

# Sidebar section order.
LANGUAGES = (
    "TypeScript",
    "JavaScript",
    "Python",
    "Rust",
    "Go",
    "SQL",
    "HTML/CSS",
    "C++",
    "PowerShell",
    "Active Directory",
)
DIFFICULTIES = ("Junior", "Mid", "Senior")

# Layout budget, measured at the default 1100x850 window and 16 pt font:
# - 7 lines needs a ~1003 px window, which still fits a 1080p screen (8 would not);
# - with the shell prompt hidden for multi-line targets, both the typing box and
#   the target label hold 61 columns, so 60 keeps every line from wrapping.
MAX_LINES = 7
MAX_COLUMNS = 60

TIER_BLURBS = {
    "Junior": "clean, everyday constructs",
    "Mid": "operators, destructuring, pipelines and error handling",
    "Senior": "generics, nested delimiters, concurrency and bulk operations",
}

SNIPPETS: tuple[Snippet, ...] = ALL


def build_snippet_lessons(snippets: Sequence[Snippet] = SNIPPETS) -> List[Lesson]:
    """Group snippets into one lesson per (language, tier), in sidebar order.

    Raises ValueError for an unknown language or tier. The lessons are marked
    `curriculum=False` so they never count toward the curriculum achievement.
    """
    for snippet in snippets:
        if snippet.language not in LANGUAGES:
            raise ValueError(f"Unknown snippet language: {snippet.language!r}")
        if snippet.difficulty not in DIFFICULTIES:
            raise ValueError(f"Unknown snippet difficulty: {snippet.difficulty!r}")

    lessons: List[Lesson] = []
    for language in LANGUAGES:
        for difficulty in DIFFICULTIES:
            texts = [
                s.text for s in snippets
                if s.language == language and s.difficulty == difficulty
            ]
            if not texts:
                continue
            description = f"{difficulty} {language} snippets: {TIER_BLURBS[difficulty]}"
            if language == "Go":
                description += " (indented with spaces instead of tabs)"
            lessons.append(
                Lesson(
                    title=f"{language} - {difficulty}",
                    description=description,
                    texts=texts,
                    category=language,
                    curriculum=False,
                )
            )
    return lessons
