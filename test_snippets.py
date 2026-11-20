"""Tests for snippet lessons: infrastructure, index stability and snippet quality."""

import ast
import re

import pytest

import core.lessons as lessons_module
from core.lessons import build_lessons, completion_message, curriculum_text_counts
from core.models import Lesson, Snippet
from core.snippets import (
    DIFFICULTIES, LANGUAGES, MAX_COLUMNS, MAX_LINES, SNIPPETS, build_snippet_lessons,
)

CORE_LESSON_COUNT = 18
CORE_TEXT_COUNT = 62

# Languages whose snippet content is complete; each content task extends this.
COMPLETED_LANGUAGES: list[str] = [
    "TypeScript", "JavaScript", "Python", "Rust", "Go", "SQL", "HTML/CSS", "C++",
    "PowerShell", "Active Directory",
]

# Every Verb-Noun cmdlet used by the PowerShell and Active Directory snippets
# must be listed here. Names were checked against Microsoft Learn; Test-NetConnection,
# Get-CimInstance, Where-Object, Export-Csv (-Path/-NoTypeInformation/-Encoding),
# Get-ChildItem, Sort-Object and Invoke-Command (-ComputerName/-ScriptBlock) had their
# parameters read from the docs; so did Search-ADAccount (-LockedOut, -UsersOnly),
# Unlock-ADAccount (-Identity), Get-ADReplicationFailure (-Target and the Server,
# FirstFailureTime, FailureCount, LastError properties) and Get-GPO (-All, GpoStatus).
# The rest are core or well-known ActiveDirectory cmdlets.
KNOWN_CMDLETS = {
    "Get-ADUser", "Get-ADGroupMember", "Get-ADComputer", "Search-ADAccount",
    "Unlock-ADAccount", "New-ADUser", "Enable-ADAccount", "Get-ADDomainController",
    "Get-ADReplicationFailure", "Get-ADDefaultDomainPasswordPolicy", "Get-GPO",
    "Get-Date", "Import-Csv",
    "Get-ChildItem", "Where-Object", "Sort-Object", "Select-Object", "Get-Process",
    "Write-Host", "Get-Service", "Start-Service", "Write-Output", "Get-CimInstance",
    "Export-Csv", "Get-Content", "Write-Warning", "Test-NetConnection",
    "Invoke-Command", "Format-Table", "ForEach-Object",
}
CMDLET_TOKEN = re.compile(r"\b[A-Z][a-z]+-[A-Z][A-Za-z]+\b")
DEFINED_FUNCTION = re.compile(r"function\s+([A-Za-z]+-[A-Za-z]+)")


def test_core_lessons_unchanged_and_first():
    core = lessons_module._build_core_lessons()
    assert len(core) == CORE_LESSON_COUNT
    assert build_lessons()[:CORE_LESSON_COUNT] == core
    assert core[CORE_LESSON_COUNT - 1].texts == ["__WEAK_KEYS__"]


def test_build_snippet_lessons_groups_by_language_then_tier():
    snippets = [
        Snippet("Python", "Mid", "b", "x = 1"),
        Snippet("Python", "Junior", "a", "y = 2"),
        Snippet("Python", "Junior", "c", "z = 3"),
        Snippet("Rust", "Junior", "d", "let a = 1;"),
    ]
    lessons = build_snippet_lessons(snippets)
    assert [l.title for l in lessons] == ["Python - Junior", "Python - Mid", "Rust - Junior"]
    assert [l.category for l in lessons] == ["Python", "Python", "Rust"]
    assert lessons[0].texts == ["y = 2", "z = 3"]
    assert all(l.curriculum is False for l in lessons)


def test_sidebar_label_strips_language_prefix():
    lesson = build_snippet_lessons([Snippet("Python", "Junior", "a", "x = 1")])[0]
    assert lesson.title[len(f"{lesson.category} - "):] == "Junior"


def test_go_lessons_mention_spaces():
    lesson = build_snippet_lessons([Snippet("Go", "Junior", "a", "x := 1")])[0]
    assert "spaces" in lesson.description


@pytest.mark.parametrize(
    "snippet",
    [Snippet("Cobol", "Junior", "t", "x"), Snippet("Python", "Expert", "t", "x")],
    ids=["unknown-language", "unknown-tier"],
)
def test_unknown_language_or_tier_rejected(snippet):
    with pytest.raises(ValueError):
        build_snippet_lessons([snippet])


def test_curriculum_text_counts_ignore_snippets():
    counts = curriculum_text_counts(build_lessons())
    assert sum(counts) == CORE_TEXT_COUNT
    assert all(count == 0 for count in counts[CORE_LESSON_COUNT:])


def test_completion_message_differs_for_snippets():
    core = Lesson(title="t", description="d", texts=["x"])
    optional = Lesson(title="t", description="d", texts=["x"], curriculum=False)
    assert "completed all lessons" in completion_message(core)
    assert "code snippets" in completion_message(optional)


def snippet_id(snippet):
    return f"{snippet.language}-{snippet.difficulty}-{snippet.title}"


@pytest.mark.parametrize("snippet", SNIPPETS, ids=snippet_id)
def test_snippet_well_formed(snippet):
    text = snippet.text
    lines = text.split("\n")
    assert snippet.language in LANGUAGES
    assert snippet.difficulty in DIFFICULTIES
    assert text.isascii()
    assert "\t" not in text and "\r" not in text
    assert all(line == line.rstrip() for line in lines), "trailing whitespace"
    assert not text.endswith("\n")
    assert 3 <= len(lines) <= MAX_LINES
    assert len(text) <= 450
    assert max(len(line) for line in lines) <= MAX_COLUMNS


def test_no_duplicate_titles_or_texts():
    titles = [(s.language, s.difficulty, s.title) for s in SNIPPETS]
    assert len(titles) == len(set(titles))
    texts = [s.text for s in SNIPPETS]
    assert len(texts) == len(set(texts))


@pytest.mark.parametrize(
    "snippet", [s for s in SNIPPETS if s.language == "Python"], ids=snippet_id,
)
def test_python_snippets_parse(snippet):
    ast.parse(snippet.text)


@pytest.mark.parametrize("language", COMPLETED_LANGUAGES)
def test_language_covers_all_tiers_with_three_snippets(language):
    for tier in DIFFICULTIES:
        count = sum(1 for s in SNIPPETS if s.language == language and s.difficulty == tier)
        assert count >= 3, f"{language} {tier} has {count} snippets"


@pytest.mark.parametrize(
    "snippet",
    [s for s in SNIPPETS if s.language in ("PowerShell", "Active Directory")],
    ids=snippet_id,
)
def test_powershell_and_ad_cmdlets_are_known(snippet):
    defined = set(DEFINED_FUNCTION.findall(snippet.text))
    used = set(CMDLET_TOKEN.findall(snippet.text)) - defined
    assert used <= KNOWN_CMDLETS, f"unverified cmdlets: {sorted(used - KNOWN_CMDLETS)}"
