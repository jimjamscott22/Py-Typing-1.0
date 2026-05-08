import json
from pathlib import Path
from typing import Dict, List, Optional

from core.models import SessionRecord
from core.constants import (
    DEFAULT_BACKSPACE_PENALTY,
    DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
    DEFAULT_STRICT_MODE,
    DEFAULT_DARK_MODE,
    DEFAULT_SHOW_KEYBOARD,
    DEFAULT_SHOW_CELEBRATION,
    DEFAULT_FONT_SIZE,
    DEFAULT_RANDOM_WORD_COUNT,
    DEFAULT_DEVELOPER_KEYS_LENGTH,
    DEFAULT_DEVELOPER_KEYS_MODE,
)

class ProgressStore:
    """Handles persistence of user progress and settings to JSON."""
    
    MAX_HISTORY_SIZE = 100  # Limit session history to prevent file bloat

    def __init__(self, path: Path):
        self.path = path
        self.data: Dict[str, object] = {
            "current_lesson_index": 0,
            "current_text_index": 0,
            "best_wpm": {},
            "session_history": [],
            "random_texts": {},  # Store generated random texts by lesson index
            "developer_texts": {},  # Store generated developer drills by lesson index
            "key_error_stats": {},  # Global statistics for key errors
            "settings": {
                "backspace_penalty": DEFAULT_BACKSPACE_PENALTY,
                "backspace_accuracy_weight": DEFAULT_BACKSPACE_ACCURACY_WEIGHT,
                "strict_mode": DEFAULT_STRICT_MODE,
                "dark_mode": DEFAULT_DARK_MODE,
                "show_keyboard": DEFAULT_SHOW_KEYBOARD,
                "show_celebration": DEFAULT_SHOW_CELEBRATION,
                "font_size": DEFAULT_FONT_SIZE,
                "random_word_count": DEFAULT_RANDOM_WORD_COUNT,
                "developer_keys_length": DEFAULT_DEVELOPER_KEYS_LENGTH,
                "developer_keys_mode": DEFAULT_DEVELOPER_KEYS_MODE,
            },
        }
        self.load()

    def load(self) -> Dict[str, object]:
        if self.path.exists():
            try:
                content = json.loads(self.path.read_text(encoding="utf-8"))
                if isinstance(content, dict):
                    # Merge loaded data with defaults to ensure all fields exist
                    for key, value in content.items():
                        if key == "settings" and isinstance(value, dict):
                            settings = self.data.get("settings")
                            if isinstance(settings, dict):
                                settings.update(value)
                            else:
                                self.data["settings"] = dict(value)
                        else:
                            self.data[key] = value
            except (OSError, json.JSONDecodeError):
                pass
        return self.data

    def save(self) -> None:
        try:
            self.path.write_text(json.dumps(self.data, indent=2), encoding="utf-8")
        except OSError:
            pass

    def add_session_record(self, record: SessionRecord) -> None:
        """Add a completed session to history, maintaining size limit."""
        history = self.data.get("session_history", [])
        if not isinstance(history, list):
            history = []
        
        history.append({
            "timestamp": record.timestamp,
            "lesson_index": record.lesson_index,
            "text_index": record.text_index,
            "lesson_name": record.lesson_name,
            "wpm": record.wpm,
            "accuracy": record.accuracy,
            "errors": record.errors,
            "backspaces": record.backspaces,
            "duration_seconds": record.duration_seconds,
            "text_length": record.text_length,
        })
        
        # Trim to max size
        if len(history) > self.MAX_HISTORY_SIZE:
            history = history[-self.MAX_HISTORY_SIZE:]
        
        self.data["session_history"] = history
        self.save()

    def get_session_history(self) -> List[Dict]:
        """Return the session history list."""
        history = self.data.get("session_history", [])
        return history if isinstance(history, list) else []

    def get_setting(self, key: str, default=None):
        """Get a setting value with fallback to default."""
        settings = self.data.get("settings", {})
        if isinstance(settings, dict):
            return settings.get(key, default)
        return default

    def set_setting(self, key: str, value) -> None:
        """Set a setting value and save."""
        settings = self.data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
            self.data["settings"] = settings
        settings[key] = value
        self.save()

    def get_random_text(self, lesson_index: int) -> Optional[str]:
        """Get the stored random text for a lesson, if any."""
        random_texts = self.data.get("random_texts", {})
        if isinstance(random_texts, dict):
            return random_texts.get(str(lesson_index))
        return None

    def set_random_text(self, lesson_index: int, text: str) -> None:
        """Store a generated random text for a lesson."""
        random_texts = self.data.get("random_texts")
        if not isinstance(random_texts, dict):
            random_texts = {}
            self.data["random_texts"] = random_texts
        random_texts[str(lesson_index)] = text
        self.save()

    def clear_random_text(self, lesson_index: int) -> None:
        """Clear the stored random text for a lesson to force regeneration."""
        random_texts = self.data.get("random_texts", {})
        if isinstance(random_texts, dict) and str(lesson_index) in random_texts:
            del random_texts[str(lesson_index)]
            self.data["random_texts"] = random_texts
            self.save()

    def get_developer_text(self, lesson_index: int) -> Optional[Dict[str, object]]:
        """Get the stored developer drill and its generation settings, if any."""
        developer_texts = self.data.get("developer_texts", {})
        if isinstance(developer_texts, dict):
            value = developer_texts.get(str(lesson_index))
            return value if isinstance(value, dict) else None
        return None

    def set_developer_text(self, lesson_index: int, text: str, *, token_count: int, mode: str) -> None:
        """Store a generated developer drill for a lesson."""
        developer_texts = self.data.get("developer_texts")
        if not isinstance(developer_texts, dict):
            developer_texts = {}
            self.data["developer_texts"] = developer_texts
        developer_texts[str(lesson_index)] = {
            "text": text,
            "token_count": token_count,
            "mode": mode,
        }
        self.save()

    def clear_developer_text(self, lesson_index: int) -> None:
        """Clear the stored developer drill for a lesson to force regeneration."""
        developer_texts = self.data.get("developer_texts", {})
        if isinstance(developer_texts, dict) and str(lesson_index) in developer_texts:
            del developer_texts[str(lesson_index)]
            self.data["developer_texts"] = developer_texts
            self.save()

    def update_key_error_stats(self, key_errors: Dict[str, int]) -> None:
        """Update global key error statistics with session data."""
        stats = self.data.get("key_error_stats")
        if not isinstance(stats, dict):
            stats = {}
            self.data["key_error_stats"] = stats

        for key, count in key_errors.items():
            stats[key] = stats.get(key, 0) + count
        
        self.save()
    
    def get_key_error_stats(self) -> Dict[str, int]:
        """Get global key error statistics."""
        stats = self.data.get("key_error_stats", {})
        return stats if isinstance(stats, dict) else {}