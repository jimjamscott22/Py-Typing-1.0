"""Synthesized mechanical-keyboard key sounds.

The recipe is a port of TypeForge-R's Web Audio synth: a pitch-swept oscillator
(or two) plus a short band-passed noise burst, each with an exponential decay.
Randomness is replaced by a per-variant offset so output is deterministic.
Pure Python (stdlib only); the Qt playback layer lives further down.
"""

from __future__ import annotations

import io
import math
import random
import struct
import wave
from dataclasses import dataclass
from typing import List, Sequence, Tuple

from core.transitions import TextChange

SAMPLE_RATE = 44100
PROFILES = ("clicky", "tactile", "linear")
KINDS = ("letter", "space", "enter")
ERROR_KIND = "error"
VARIANTS_PER_KIND = 4

_PEAK = 0.9  # results are scaled down to this fraction of full scale if louder
_FLOOR = 0.001  # level an envelope decays to, like Web Audio's exponential ramp


@dataclass(frozen=True)
class _Voice:
    """An oscillator whose frequency falls exponentially from f0 to f1."""

    shape: str  # "sine", "triangle" or "sawtooth"
    f0: float
    f1: float
    sweep: float  # seconds over which the frequency falls
    decay: float  # seconds over which the amplitude decays
    gain: float


@dataclass(frozen=True)
class _Noise:
    """A band-passed white-noise burst."""

    center: float  # Hz
    duration: float  # seconds
    gain: float


def _check(profile: str, kind: str, variant: int) -> None:
    if profile not in PROFILES:
        raise ValueError(f"Unknown key sound profile: {profile!r}")
    if kind not in KINDS:
        raise ValueError(f"Unknown key sound kind: {kind!r}")
    if not 0 <= variant < VARIANTS_PER_KIND:
        raise ValueError(f"Variant must be 0..{VARIANTS_PER_KIND - 1}, got {variant}")


def _recipe(profile: str, kind: str, variant: int) -> Tuple[List[_Voice], _Noise]:
    j = variant / (VARIANTS_PER_KIND - 1) * 2 - 1  # -1.0 .. 1.0, replaces random jitter
    wide = kind != "letter"  # space and enter are longer and lower

    if profile == "clicky":
        body_base = 875 + 125 * j if not wide else (320 if kind == "space" else 420)
        return (
            [
                _Voice("triangle", 2200 if wide else 3800 + 200 * j, 800, 0.015, 0.018, 0.45),
                _Voice("sine", body_base, 120, 0.06 if wide else 0.04,
                       0.07 if wide else 0.05, 0.5),
            ],
            _Noise(1400, 0.04 if wide else 0.02, 0.25),
        )
    if profile == "tactile":
        base = 260 if wide else 480 + 40 * j
        return (
            [_Voice("triangle", base * 1.8, base * 0.6, 0.035, 0.045, 0.45)],
            _Noise(900, 0.025, 0.2),
        )
    base = 180 if wide else 280 + 25 * j  # linear
    return (
        [_Voice("sine", base * 1.4, base * 0.5, 0.04, 0.06 if wide else 0.045, 0.5)],
        _Noise(600, 0.03, 0.15),
    )


def _oscillator(shape: str, phase: float) -> float:
    if shape == "sine":
        return math.sin(phase)
    if shape == "triangle":
        return 2 / math.pi * math.asin(math.sin(phase))
    return 2 * ((phase / (2 * math.pi)) % 1.0) - 1  # sawtooth


def _envelope(gain: float, t: float, decay: float) -> float:
    return gain * (_FLOOR / gain) ** (t / decay) if t < decay else 0.0


def _render_voice(voice: _Voice) -> List[float]:
    samples: List[float] = []
    phase = 0.0
    ratio = voice.f1 / voice.f0
    for i in range(int(voice.decay * SAMPLE_RATE)):
        t = i / SAMPLE_RATE
        phase += 2 * math.pi * voice.f0 * ratio ** min(t / voice.sweep, 1.0) / SAMPLE_RATE
        samples.append(_oscillator(voice.shape, phase) * _envelope(voice.gain, t, voice.decay))
    return samples


def _render_noise(noise: _Noise, rng: random.Random) -> List[float]:
    """White noise through a band-pass biquad (Q = 2), shaped by a decay envelope."""
    w0 = 2 * math.pi * noise.center / SAMPLE_RATE
    alpha = math.sin(w0) / (2 * 2.0)
    b0 = alpha / (1 + alpha)
    a1 = -2 * math.cos(w0) / (1 + alpha)
    a2 = (1 - alpha) / (1 + alpha)
    x1 = x2 = y1 = y2 = 0.0
    samples: List[float] = []
    for i in range(int(noise.duration * SAMPLE_RATE)):
        x = rng.uniform(-1.0, 1.0)
        y = b0 * x - b0 * x2 - a1 * y1 - a2 * y2
        x2, x1, y2, y1 = x1, x, y1, y
        samples.append(y * _envelope(noise.gain, i / SAMPLE_RATE, noise.duration))
    return samples


def _to_wav(layers: List[List[float]]) -> bytes:
    length = max(len(layer) for layer in layers)
    mixed = [0.0] * length
    for layer in layers:
        for i, value in enumerate(layer):
            mixed[i] += value
    peak = max(abs(value) for value in mixed)
    scale = _PEAK / peak if peak > _PEAK else 1.0
    frames = struct.pack(
        f"<{length}h", *(max(-32767, min(32767, round(v * scale * 32767))) for v in mixed)
    )
    buffer = io.BytesIO()
    with wave.open(buffer, "wb") as wav:
        wav.setnchannels(1)
        wav.setsampwidth(2)
        wav.setframerate(SAMPLE_RATE)
        wav.writeframes(frames)
    return buffer.getvalue()


def synthesize(profile: str, kind: str, variant: int) -> bytes:
    """Return a complete WAV file (16-bit mono) for one key sound."""
    _check(profile, kind, variant)
    voices, noise = _recipe(profile, kind, variant)
    rng = random.Random(f"{profile}:{kind}:{variant}")
    layers = [_render_voice(voice) for voice in voices] + [_render_noise(noise, rng)]
    return _to_wav(layers)


def synthesize_error() -> bytes:
    """Return the low "thunk" played on a wrong key (shared by every profile)."""
    voice = _render_voice(_Voice("sawtooth", 140, 90, 0.08, 0.09, 0.35))
    alpha = 1 - math.exp(-2 * math.pi * 450 / SAMPLE_RATE)  # one-pole low-pass at 450 Hz
    filtered: List[float] = []
    state = 0.0
    for value in voice:
        state += alpha * (value - state)
        filtered.append(state)
    return _to_wav([filtered])


def classify_edit(changes: Sequence[TextChange], target_text: str) -> List[str]:
    """Map one input edit to the key sounds it should trigger (at most one per change).

    A correct character gives its kind (letter, space or enter), a wrong one
    gives the error sound, and a backspace gives a letter click. Nothing plays
    for multi-character changes (paste/IME) or characters past the end of the
    target.
    """
    kinds: List[str] = []
    for change in changes:
        if len(change.inserted) > 1:
            continue
        if not change.inserted:
            if change.removed > 0:
                kinds.append("letter")
            continue
        if change.position >= len(target_text):
            continue
        expected = target_text[change.position]
        if change.inserted != expected:
            kinds.append(ERROR_KIND)
        elif expected == " ":
            kinds.append("space")
        elif expected == "\n":
            kinds.append("enter")
        else:
            kinds.append("letter")
    return kinds
