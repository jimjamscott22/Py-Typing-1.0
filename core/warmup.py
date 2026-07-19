import random

WARMUP_PHRASES = [
    "the quick brown fox jumps over the lazy dog",
    "pack my box with five dozen liquor jugs",
    "sphinx of black quartz judge my vow",
    "how vexingly quick daft zebras jump",
    "the five boxing wizards jump quickly",
    "waltz nymph for quick jigs vex bud",
]


def get_warmup_text(exclude: str | None = None) -> str:
    """Return a random warmup drill phrase, avoiding an immediate repeat of `exclude`."""
    choices = WARMUP_PHRASES
    if exclude is not None and len(WARMUP_PHRASES) > 1:
        choices = [phrase for phrase in WARMUP_PHRASES if phrase != exclude]
    return random.choice(choices)
