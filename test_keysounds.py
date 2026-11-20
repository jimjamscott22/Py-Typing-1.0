"""Tests for core/keysounds.py: synthesis, edit classification and the player."""

import io
import struct
import time
import wave
from pathlib import Path

import pytest

import core.keysounds as keysounds
from core.keysounds import (
    KINDS,
    PROFILES,
    SAMPLE_RATE,
    VARIANTS_PER_KIND,
    KeySoundPlayer,
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


# --- KeySoundPlayer (QSoundEffect replaced by a recording fake) -------------------


class FakeEffect:
    instances: list = []

    def __init__(self, parent=None):
        self.source = None
        self.volume = None
        self.plays = 0
        self.stopped = False
        FakeEffect.instances.append(self)

    def setSource(self, url):
        self.source = url

    def setVolume(self, volume):
        self.volume = volume

    def play(self):
        self.plays += 1

    def stop(self):
        self.stopped = True


@pytest.fixture
def fake_effects(monkeypatch):
    FakeEffect.instances = []
    monkeypatch.setattr(keysounds, "QSoundEffect", FakeEffect)
    return FakeEffect


def test_player_is_off_by_default():
    player = KeySoundPlayer()
    assert player.enabled is False
    player.play("letter")  # must not raise


def test_configure_builds_effects_and_rotates_variants(fake_effects):
    player = KeySoundPlayer()
    player.configure("clicky", 50)
    assert player.enabled is True
    assert len(fake_effects.instances) == 13  # 3 kinds x 4 variants + error
    assert all(effect.volume == 0.5 for effect in fake_effects.instances)

    for _ in range(4):
        player.play("letter")
    plays = [effect.plays for effect in fake_effects.instances]
    assert sum(plays) == 4 and max(plays) == 1  # four distinct effects
    player.play("letter")
    plays = [effect.plays for effect in fake_effects.instances]
    assert sum(plays) == 5 and max(plays) == 2  # the fifth replays the first


def test_error_kind_plays_the_error_effect(fake_effects):
    player = KeySoundPlayer()
    player.configure("tactile", 60)
    player.play("error")
    assert fake_effects.instances[-1].plays == 1


def test_volume_change_does_not_resynthesize(fake_effects, monkeypatch):
    calls = []
    real = keysounds.synthesize
    monkeypatch.setattr(keysounds, "synthesize", lambda *a: calls.append(a) or real(*a))
    player = KeySoundPlayer()
    player.configure("clicky", 50)
    built = len(calls)
    player.configure("clicky", 80)
    assert len(calls) == built
    assert all(effect.volume == 0.8 for effect in fake_effects.instances)


def test_configure_off_disables(fake_effects):
    player = KeySoundPlayer()
    player.configure("clicky", 50)
    player.configure("off", 50)
    assert player.enabled is False
    assert all(effect.stopped for effect in fake_effects.instances)
    player.play("letter")
    assert sum(effect.plays for effect in fake_effects.instances) == 0


def test_setup_failure_disables_silently(fake_effects, monkeypatch):
    class Broken(FakeEffect):
        def setSource(self, url):
            raise RuntimeError("no audio device")

    monkeypatch.setattr(keysounds, "QSoundEffect", Broken)
    player = KeySoundPlayer()
    player.configure("clicky", 50)  # must not raise
    assert player.enabled is False
    player.play("letter")  # must not raise


def test_shutdown_removes_temp_dir(fake_effects):
    player = KeySoundPlayer()
    player.configure("linear", 50)
    folder = Path(fake_effects.instances[0].source.toLocalFile()).parent
    assert folder.exists()
    player.shutdown()
    assert not folder.exists()
    assert player.enabled is False
