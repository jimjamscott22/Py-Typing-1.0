"""Audio module for generating and playing celebratory sounds."""

import io
import struct
import wave
import math
import tempfile
import platform
import random
from pathlib import Path
from typing import Optional

from PyQt6.QtCore import QUrl, QObject
from PyQt6.QtMultimedia import QMediaPlayer, QAudioOutput

# Try to import platform-specific audio module
if platform.system() == "Windows":
    try:
        import winsound
        HAS_WINSOUND = True
    except ImportError:
        HAS_WINSOUND = False
else:
    HAS_WINSOUND = False


class CelebrationSound(QObject):
    """Generates and randomly plays celebratory perfect-round melodies."""

    MELODIES = (
        (
            (523.25, 0.10), (659.25, 0.10), (783.99, 0.10),
            (1046.50, 0.15), (0, 0.05), (783.99, 0.10),
            (1046.50, 0.25), (1318.51, 0.08), (1567.98, 0.08),
            (2093.00, 0.20),
        ),
        (
            (659.25, 0.09), (783.99, 0.09), (987.77, 0.09),
            (1318.51, 0.18), (0, 0.04), (987.77, 0.08),
            (1174.66, 0.08), (1318.51, 0.24),
        ),
        (
            (392.00, 0.11), (523.25, 0.11), (659.25, 0.11),
            (783.99, 0.16), (659.25, 0.08), (783.99, 0.08),
            (1046.50, 0.28),
        ),
        (
            (1046.50, 0.08), (1318.51, 0.08), (1567.98, 0.08),
            (2093.00, 0.12), (1567.98, 0.08), (2093.00, 0.12),
            (2637.02, 0.22),
        ),
    )

    def __init__(self, parent=None):
        super().__init__(parent)
        self._player: Optional[QMediaPlayer] = None
        self._audio_output: Optional[QAudioOutput] = None
        self._temp_files: dict[int, Path] = {}
        self._last_melody_index: Optional[int] = None
        self._initialized = False

    def _ensure_initialized(self) -> bool:
        """Lazily initialize the audio player."""
        if self._initialized:
            return self._player is not None

        try:
            # Set up the media player
            self._player = QMediaPlayer(self)
            self._audio_output = QAudioOutput(self)
            self._audio_output.setVolume(0.5)  # 50% volume
            self._player.setAudioOutput(self._audio_output)

            self._initialized = True
            return True
        except Exception:
            self._initialized = True
            return False

    def play(self) -> None:
        """Play a random celebration sound without immediately repeating one."""
        melody_index = self._choose_melody_index()
        try:
            sound_file = self._sound_file(melody_index)
        except Exception:
            return

        # Try using winsound first on Windows
        if HAS_WINSOUND:
            try:
                # Use SND_ASYNC to play asynchronously without blocking
                winsound.PlaySound(str(sound_file), winsound.SND_FILENAME | winsound.SND_ASYNC)
                return
            except Exception:
                pass
        
        # Fall back to QMediaPlayer
        if not self._ensure_initialized():
            return
        
        if self._player:
            self._player.stop()
            self._player.setSource(QUrl.fromLocalFile(str(sound_file)))
            self._player.play()

    def _choose_melody_index(self) -> int:
        """Choose a melody, excluding the previously played one when possible."""
        choices = [
            index
            for index in range(len(self.MELODIES))
            if index != self._last_melody_index
        ]
        selected = random.choice(choices)
        self._last_melody_index = selected
        return selected

    def _sound_file(self, melody_index: int) -> Path:
        """Return a cached WAV path, generating it on first use."""
        if melody_index not in self._temp_files:
            self._temp_files[melody_index] = self._generate_celebration_melody(
                melody_index
            )
        return self._temp_files[melody_index]

    def set_volume(self, volume: float) -> None:
        """Set the volume (0.0 to 1.0)."""
        if self._audio_output:
            self._audio_output.setVolume(max(0.0, min(1.0, volume)))

    def _generate_celebration_melody(self, melody_index: int = 0) -> Path:
        """Generate a short celebratory victory jingle as a WAV file."""
        sample_rate = 44100
        melody = self.MELODIES[melody_index]
        
        # Generate audio samples
        samples = []
        for freq, duration in melody:
            num_samples = int(sample_rate * duration)
            for i in range(num_samples):
                t = i / sample_rate
                
                if freq == 0:
                    # Silence
                    sample = 0
                else:
                    # Generate a rich tone with harmonics for a fuller sound
                    # Fundamental + overtones
                    sample = (
                        0.5 * math.sin(2 * math.pi * freq * t) +         # Fundamental
                        0.25 * math.sin(2 * math.pi * freq * 2 * t) +    # 2nd harmonic
                        0.125 * math.sin(2 * math.pi * freq * 3 * t) +   # 3rd harmonic
                        0.0625 * math.sin(2 * math.pi * freq * 4 * t)    # 4th harmonic
                    )
                    
                    # Apply envelope (attack/decay) to avoid clicks
                    attack_samples = int(0.01 * sample_rate)
                    decay_samples = int(0.05 * sample_rate)
                    
                    if i < attack_samples:
                        # Attack phase
                        envelope = i / attack_samples
                    elif i > num_samples - decay_samples:
                        # Decay phase
                        envelope = (num_samples - i) / decay_samples
                    else:
                        envelope = 1.0
                    
                    sample *= envelope
                
                # Scale to 16-bit range
                samples.append(int(sample * 32767 * 0.7))  # 0.7 to prevent clipping
        
        # Create WAV file in temp directory
        temp_dir = Path(tempfile.gettempdir())
        wav_path = temp_dir / f"typing_celebration_{melody_index}.wav"
        
        with wave.open(str(wav_path), 'w') as wav_file:
            wav_file.setnchannels(1)  # Mono
            wav_file.setsampwidth(2)  # 2 bytes = 16 bit
            wav_file.setframerate(sample_rate)
            
            # Pack samples as signed 16-bit integers
            packed_samples = struct.pack('<' + 'h' * len(samples), *samples)
            wav_file.writeframes(packed_samples)
        
        return wav_path


class CelebrationSoundManager:
    """Singleton manager for the celebration sound."""
    
    _instance: Optional[CelebrationSound] = None
    _parent: Optional[QObject] = None
    
    @classmethod
    def initialize(cls, parent: QObject) -> None:
        """Initialize the singleton with a parent QObject."""
        if cls._instance is None:
            cls._parent = parent
            cls._instance = CelebrationSound(parent)
    
    @classmethod
    def get_instance(cls, parent=None) -> CelebrationSound:
        """Get or create the singleton CelebrationSound instance."""
        if cls._instance is None:
            cls._instance = CelebrationSound(parent)
        return cls._instance
    
    @classmethod
    def play(cls) -> None:
        """Play the celebration sound using the singleton instance."""
        if cls._instance is None and cls._parent is not None:
            cls._instance = CelebrationSound(cls._parent)
        if cls._instance:
            cls._instance.play()
