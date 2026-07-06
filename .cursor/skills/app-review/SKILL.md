---
name: app-review
description: Reviews this PyQt6 typing-practice app and suggests prioritized improvements or new features. Use when the user asks for an app review, codebase audit, improvement ideas, or feature suggestions.
disable-model-invocation: true
---

# App Review

## Process

1. **Explore.** Use a code-explorer subagent to map the codebase (architecture: `main.py`, `ui/`, `core/`; persistence in `core/persistence.py`; tests in `test_enhancements.py`).
2. **Review.** Use a code-reviewer subagent against the checklist below.
3. **Verify where cheap.** Run `uv run pytest test_enhancements.py -v`; smoke-test the UI headlessly with `QT_QPA_PLATFORM=offscreen`. If tests fail or the app won't start, report that as the top finding.

## Review checklist

- **Correctness:** logic bugs, edge cases, error handling
- **Performance:** keystroke hot path (`on_text_changed`), UI refreshes, SQLite writes
- **Security:** input handling, unsafe file/DB operations, dependency risk
- **Testing:** coverage gaps beyond `test_enhancements.py`, missing edge/failure cases
- **Maintainability:** duplication, oversized functions, unclear naming
- **UX / accessibility:** typing flow, feedback, theming, keyboard navigation

## Suggestion quality bar

Each suggestion must include:

- **What & where:** specific file/function, not generic advice
- **Why:** the concrete impact (bug risk, perf, user pain)
- **Effort:** rough size (S / M / L)
- **Severity:** Critical / Recommended / Nice-to-have

Prefer changes that fit the existing architecture over rewrites. This is a review: flag issues and propose fixes; do not implement them unless asked.

## Output

Markdown, grouped by category (Performance, Testing, UX, Features, Code Quality):

- 3-5 suggestions, each following the quality bar above
- End with a prioritized "start here" list, ordered by impact vs. effort
