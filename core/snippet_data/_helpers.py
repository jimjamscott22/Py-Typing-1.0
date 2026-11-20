"""Helpers shared by the per-language snippet modules."""


def code(text: str) -> str:
    """Strip the leading/trailing newlines that triple-quoted literals add.

    Indentation is untouched, so the snippet's first line keeps any it has.
    """
    return text.strip("\n")
