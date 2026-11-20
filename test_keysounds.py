"""Tests for core/keysounds.py: synthesis, edit classification and the player."""

import io
import struct
import time
import wave

import pytest

from core.keysounds import (
    KINDS,
    PROFILES,
    SAMPLE_RATE,
    VARIANTS_PER_KIND,
    classify_edit,
    synthesize,
    synthesize_error,
)
from core.transitions import TextChange

FULL_SCALE = 32767


def decode(data: bytes) -> list[int]:
    with wave.open(io.BytesIO(data)) as wav:
        assert (wav.getnchannels(), wav.getsampwidth(), wav.getframerate()) == (1, 2, SAMPLE_RATE)
        count = wav.getnframes()
        return list(struct.unpack(f"<{count}h", wav.readframes(count)))


def duration_ms(data: bytes) -> float:
    return len(decode(data)) / SAMPLE_RATE * 1000


@pytest.mark.parametrize("variant", range(VARIANTS_PER_KIND))
@pytest.mark.parametrize("kind", KINDS)
@pytest.mark.parametrize("profile", PROFILES)
def test_every_voice_is_valid_audible_and_unclipped(profile, kind, variant):
    samples = decode(synthesize(profile, kind, variant))
    assert 30 <= len(samples) / SAMPLE_RATE * 1000 <= 150
    peak = max(abs(s) for s in samples)
    assert 0.2 * FULL_SCALE <= peak <= 0.95 * FULL_SCALE


def test_synthesis_is_deterministic():
    assert synthesize("clicky", "letter", 2) == synthesize("clicky", "letter", 2)


def test_variants_differ():
    assert len({synthesize("clicky", "letter", v) for v in range(VARIANTS_PER_KIND)}) == 4


def test_profiles_differ():
    assert len({synthesize(profile, "letter", 0) for profile in PROFILES}) == 3


def test_space_longer_than_letter_for_clicky():
    assert duration_ms(synthesize("clicky", "space", 0)) > duration_ms(synthesize("clicky", "letter", 0))


def test_error_sound_valid():
    samples = decode(synthesize_error())
    assert 30 <= len(samples) / SAMPLE_RATE * 1000 <= 150
    assert 0.2 * FULL_SCALE <= max(abs(s) for s in samples) <= 0.95 * FULL_SCALE


@pytest.mark.parametrize(
    ("profile", "kind", "variant"),
    [("nope", "letter", 0), ("clicky", "nope", 0), ("clicky", "letter", -1),
     ("clicky", "letter", VARIANTS_PER_KIND)],
)
def test_unknown_profile_kind_or_variant_raises(profile, kind, variant):
    with pytest.raises(ValueError):
        synthesize(profile, kind, variant)


def test_profile_synthesis_budget():
    start = time.perf_counter()
    for kind in KINDS:
        for variant in range(VARIANTS_PER_KIND):
            synthesize("clicky", kind, variant)
    assert time.perf_counter() - start < 1.0


@pytest.mark.parametrize(
    ("changes", "target", "expected"),
    [
        ([TextChange(0, 0, "a")], "ab", ["letter"]),
        ([TextChange(1, 0, " ")], "a b", ["space"]),
        ([TextChange(1, 0, "\n")], "a\nb", ["enter"]),
        ([TextChange(0, 0, "x")], "ab", ["error"]),
        ([TextChange(0, 1, "")], "ab", ["letter"]),  # backspace
        ([TextChange(2, 0, "z")], "ab", []),  # past the end of the target
        ([TextChange(0, 0, "ab")], "ab", []),  # multi-character (paste / IME)
        ([], "ab", []),
        ([TextChange(0, 1, "a")], "ab", ["letter"]),  # typing over a selection
    ],
    ids=["letter", "space", "enter", "error", "backspace", "past-end", "multichar",
         "no-changes", "replace-selection"],
)
def test_classify_edit(changes, target, expected):
    assert classify_edit(changes, target) == expected
