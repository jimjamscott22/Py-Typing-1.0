import json
import sqlite3
from pathlib import Path
from typing import Dict, List, Optional, Set, Tuple

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
    DEFAULT_TIMED_MODE_SECONDS,
    DEFAULT_ADAPTIVE_DRILLS,
)


_DEFAULT_SETTINGS: Dict[str, object] = {
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
    "timed_mode_seconds": DEFAULT_TIMED_MODE_SECONDS,
    "adaptive_drills": DEFAULT_ADAPTIVE_DRILLS,
}


class ProgressStore:
    """SQLite-backed persistence for user progress and settings.

    Granular writes (one row per setting / session / key) replace the previous
    full-file JSON rewrite on every save. The `data` attribute mirrors the
    persisted state in memory so existing read-paths that touch `.data`
    directly continue to work.
    """

    MAX_HISTORY_SIZE = 100

    def __init__(self, path: Path):
        # Keep `path` pointing at the legacy JSON file for one-shot migration,
        # and derive the SQLite filename from it.
        self.path = path
        self.db_path = path.with_suffix(".sqlite3")
        self.data: Dict[str, object] = self._empty_state()
        self._conn = sqlite3.connect(str(self.db_path))
        self._conn.execute("PRAGMA journal_mode=WAL")
        self._conn.execute("PRAGMA synchronous=NORMAL")
        self._create_schema()
        self._migrate_from_json_if_needed()
        self._backfill_completed_lesson_texts()
        self._refresh_cache()

    @staticmethod
    def _empty_state() -> Dict[str, object]:
        return {
            "current_lesson_index": 0,
            "current_text_index": 0,
            "best_wpm": {},
            "session_history": [],
            "random_texts": {},
            "developer_texts": {},
            "key_error_stats": {},
            "key_attempt_stats": {},
            "achievements": {},
            "completed_lesson_texts": [],
            "settings": dict(_DEFAULT_SETTINGS),
        }

    def _create_schema(self) -> None:
        c = self._conn
        c.executescript(
            """
            CREATE TABLE IF NOT EXISTS kv (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS settings (
                key TEXT PRIMARY KEY,
                value TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS best_wpm (
                lesson_key TEXT PRIMARY KEY,
                wpm INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_history (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                timestamp TEXT NOT NULL,
                lesson_index INTEGER NOT NULL,
                text_index INTEGER NOT NULL,
                lesson_name TEXT NOT NULL,
                wpm INTEGER NOT NULL,
                accuracy REAL NOT NULL,
                errors INTEGER NOT NULL,
                backspaces INTEGER NOT NULL,
                duration_seconds REAL NOT NULL,
                text_length INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS random_texts (
                lesson_key TEXT PRIMARY KEY,
                text TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS developer_texts (
                lesson_key TEXT PRIMARY KEY,
                text TEXT NOT NULL,
                token_count INTEGER NOT NULL,
                mode TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS key_error_stats (
                key TEXT PRIMARY KEY,
                count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS key_attempt_stats (
                key TEXT PRIMARY KEY,
                count INTEGER NOT NULL
            );
            CREATE TABLE IF NOT EXISTS session_key_errors (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                session_timestamp TEXT NOT NULL,
                lesson_index INTEGER NOT NULL,
                lesson_name TEXT NOT NULL,
                key TEXT NOT NULL,
                error_count INTEGER NOT NULL,
                attempt_count INTEGER NOT NULL
            );
            CREATE INDEX IF NOT EXISTS idx_session_key_errors_lesson
                ON session_key_errors (lesson_index);
            CREATE INDEX IF NOT EXISTS idx_session_key_errors_timestamp
                ON session_key_errors (session_timestamp);
            CREATE TABLE IF NOT EXISTS achievements (
                achievement_id TEXT PRIMARY KEY,
                unlocked_at TEXT NOT NULL
            );
            CREATE TABLE IF NOT EXISTS completed_lesson_texts (
                lesson_index INTEGER NOT NULL,
                text_index INTEGER NOT NULL,
                completed_at TEXT NOT NULL,
                PRIMARY KEY (lesson_index, text_index)
            );
            """
        )
        c.commit()

    def _migrate_from_json_if_needed(self) -> None:
        """One-shot import of the legacy JSON file, then rename it aside."""
        if not self.path.exists():
            return
        cur = self._conn.execute("SELECT 1 FROM kv LIMIT 1")
        if cur.fetchone() is not None:
            return
        cur = self._conn.execute("SELECT 1 FROM settings LIMIT 1")
        if cur.fetchone() is not None:
            return

        try:
            content = json.loads(self.path.read_text(encoding="utf-8"))
        except (OSError, json.JSONDecodeError):
            return
        if not isinstance(content, dict):
            return

        with self._conn:
            for key in ("current_lesson_index", "current_text_index"):
                if key in content:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                        (key, json.dumps(content[key])),
                    )
            settings = content.get("settings")
            if isinstance(settings, dict):
                for key, value in settings.items():
                    self._conn.execute(
                        "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                        (key, json.dumps(value)),
                    )
            best_wpm = content.get("best_wpm")
            if isinstance(best_wpm, dict):
                for lesson_key, wpm in best_wpm.items():
                    if isinstance(wpm, (int, float)):
                        self._conn.execute(
                            "INSERT OR REPLACE INTO best_wpm (lesson_key, wpm) VALUES (?, ?)",
                            (str(lesson_key), int(wpm)),
                        )
            history = content.get("session_history")
            if isinstance(history, list):
                for entry in history[-self.MAX_HISTORY_SIZE:]:
                    if not isinstance(entry, dict):
                        continue
                    self._conn.execute(
                        """INSERT INTO session_history
                           (timestamp, lesson_index, text_index, lesson_name,
                            wpm, accuracy, errors, backspaces, duration_seconds, text_length)
                           VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                        (
                            str(entry.get("timestamp", "")),
                            int(entry.get("lesson_index", 0) or 0),
                            int(entry.get("text_index", 0) or 0),
                            str(entry.get("lesson_name", "")),
                            int(entry.get("wpm", 0) or 0),
                            float(entry.get("accuracy", 0.0) or 0.0),
                            int(entry.get("errors", 0) or 0),
                            int(entry.get("backspaces", 0) or 0),
                            float(entry.get("duration_seconds", 0.0) or 0.0),
                            int(entry.get("text_length", 0) or 0),
                        ),
                    )
            random_texts = content.get("random_texts")
            if isinstance(random_texts, dict):
                for lesson_key, text in random_texts.items():
                    if isinstance(text, str):
                        self._conn.execute(
                            "INSERT OR REPLACE INTO random_texts (lesson_key, text) VALUES (?, ?)",
                            (str(lesson_key), text),
                        )
            developer_texts = content.get("developer_texts")
            if isinstance(developer_texts, dict):
                for lesson_key, entry in developer_texts.items():
                    if not isinstance(entry, dict):
                        continue
                    text = entry.get("text")
                    if not isinstance(text, str):
                        continue
                    self._conn.execute(
                        """INSERT OR REPLACE INTO developer_texts
                           (lesson_key, text, token_count, mode) VALUES (?, ?, ?, ?)""",
                        (
                            str(lesson_key),
                            text,
                            int(entry.get("token_count", 0) or 0),
                            str(entry.get("mode", "")),
                        ),
                    )
            for table, source_key in (
                ("key_error_stats", "key_error_stats"),
                ("key_attempt_stats", "key_attempt_stats"),
            ):
                stats = content.get(source_key)
                if isinstance(stats, dict):
                    for key, count in stats.items():
                        if isinstance(count, (int, float)):
                            self._conn.execute(
                                f"INSERT OR REPLACE INTO {table} (key, count) VALUES (?, ?)",
                                (str(key), int(count)),
                            )

        try:
            self.path.rename(self.path.with_suffix(".json.migrated"))
        except OSError:
            pass

    def _backfill_completed_lesson_texts(self) -> None:
        """Seed curriculum progress from history once when badges are introduced."""
        marker = self._conn.execute(
            "SELECT value FROM kv WHERE key = ?",
            ("achievement_completion_backfill_v1",),
        ).fetchone()
        if marker is not None:
            return

        with self._conn:
            self._conn.execute(
                """INSERT OR IGNORE INTO completed_lesson_texts
                   (lesson_index, text_index, completed_at)
                   SELECT lesson_index, text_index, MIN(timestamp)
                   FROM session_history
                   WHERE lesson_index >= 0
                   GROUP BY lesson_index, text_index"""
            )
            self._conn.execute(
                "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                ("achievement_completion_backfill_v1", json.dumps(True)),
            )

    def _refresh_cache(self) -> None:
        """Repopulate the `data` mirror from SQLite."""
        state = self._empty_state()

        for row in self._conn.execute("SELECT key, value FROM kv"):
            try:
                state[row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                continue

        for row in self._conn.execute("SELECT key, value FROM settings"):
            try:
                state["settings"][row[0]] = json.loads(row[1])
            except (json.JSONDecodeError, TypeError):
                continue

        state["best_wpm"] = {
            row[0]: row[1]
            for row in self._conn.execute("SELECT lesson_key, wpm FROM best_wpm")
        }

        state["session_history"] = [
            {
                "timestamp": row[0],
                "lesson_index": row[1],
                "text_index": row[2],
                "lesson_name": row[3],
                "wpm": row[4],
                "accuracy": row[5],
                "errors": row[6],
                "backspaces": row[7],
                "duration_seconds": row[8],
                "text_length": row[9],
            }
            for row in self._conn.execute(
                """SELECT timestamp, lesson_index, text_index, lesson_name,
                          wpm, accuracy, errors, backspaces, duration_seconds, text_length
                   FROM session_history ORDER BY id ASC"""
            )
        ]

        state["random_texts"] = {
            row[0]: row[1]
            for row in self._conn.execute("SELECT lesson_key, text FROM random_texts")
        }

        state["developer_texts"] = {
            row[0]: {"text": row[1], "token_count": row[2], "mode": row[3]}
            for row in self._conn.execute(
                "SELECT lesson_key, text, token_count, mode FROM developer_texts"
            )
        }

        state["key_error_stats"] = {
            row[0]: row[1]
            for row in self._conn.execute("SELECT key, count FROM key_error_stats")
        }

        state["key_attempt_stats"] = {
            row[0]: row[1]
            for row in self._conn.execute("SELECT key, count FROM key_attempt_stats")
        }

        state["achievements"] = {
            row[0]: row[1]
            for row in self._conn.execute(
                "SELECT achievement_id, unlocked_at FROM achievements"
            )
        }

        state["completed_lesson_texts"] = [
            (row[0], row[1])
            for row in self._conn.execute(
                "SELECT lesson_index, text_index FROM completed_lesson_texts"
            )
        ]

        self.data = state

    def load(self) -> Dict[str, object]:
        """Reload the in-memory cache from disk and return it."""
        self._refresh_cache()
        return self.data

    def save(self) -> None:
        """Flush the in-memory mirror back to SQLite.

        Granular setters already persist each change directly, so this only
        needs to sync the two top-level position keys plus the best-WPM map
        that callers may have mutated through `.data`.
        """
        with self._conn:
            for key in ("current_lesson_index", "current_text_index"):
                if key in self.data:
                    self._conn.execute(
                        "INSERT OR REPLACE INTO kv (key, value) VALUES (?, ?)",
                        (key, json.dumps(self.data[key])),
                    )
            best_wpm = self.data.get("best_wpm")
            if isinstance(best_wpm, dict):
                self._conn.execute("DELETE FROM best_wpm")
                for lesson_key, wpm in best_wpm.items():
                    if isinstance(wpm, (int, float)):
                        self._conn.execute(
                            "INSERT OR REPLACE INTO best_wpm (lesson_key, wpm) VALUES (?, ?)",
                            (str(lesson_key), int(wpm)),
                        )

    def add_session_record(self, record: SessionRecord) -> None:
        """Append a completed session, trimming history to the size limit."""
        with self._conn:
            self._conn.execute(
                """INSERT INTO session_history
                   (timestamp, lesson_index, text_index, lesson_name,
                    wpm, accuracy, errors, backspaces, duration_seconds, text_length)
                   VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                (
                    record.timestamp,
                    record.lesson_index,
                    record.text_index,
                    record.lesson_name,
                    record.wpm,
                    record.accuracy,
                    record.errors,
                    record.backspaces,
                    record.duration_seconds,
                    record.text_length,
                ),
            )
            self._conn.execute(
                """DELETE FROM session_history
                   WHERE id IN (
                     SELECT id FROM session_history
                     ORDER BY id DESC LIMIT -1 OFFSET ?
                   )""",
                (self.MAX_HISTORY_SIZE,),
            )

        history = self.data.get("session_history")
        if not isinstance(history, list):
            history = []
        history.append(
            {
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
            }
        )
        if len(history) > self.MAX_HISTORY_SIZE:
            history = history[-self.MAX_HISTORY_SIZE:]
        self.data["session_history"] = history

    def get_session_history(self) -> List[Dict]:
        history = self.data.get("session_history", [])
        return history if isinstance(history, list) else []

    def get_unlocked_achievements(self) -> Dict[str, str]:
        achievements = self.data.get("achievements", {})
        return achievements if isinstance(achievements, dict) else {}

    def unlock_achievements(self, achievement_ids: List[str], unlocked_at: str) -> List[str]:
        """Persist newly earned achievement IDs and return the IDs actually inserted."""
        achievements = self.data.get("achievements")
        if not isinstance(achievements, dict):
            achievements = {}
            self.data["achievements"] = achievements

        newly_unlocked: List[str] = []
        with self._conn:
            for achievement_id in achievement_ids:
                cursor = self._conn.execute(
                    """INSERT OR IGNORE INTO achievements
                       (achievement_id, unlocked_at) VALUES (?, ?)""",
                    (achievement_id, unlocked_at),
                )
                if cursor.rowcount:
                    achievements[achievement_id] = unlocked_at
                    newly_unlocked.append(achievement_id)
        return newly_unlocked

    def mark_lesson_text_completed(
        self,
        lesson_index: int,
        text_index: int,
        completed_at: str,
    ) -> None:
        """Remember an exact lesson-text completion without trimming old progress."""
        pair = (int(lesson_index), int(text_index))
        completed = self.data.get("completed_lesson_texts")
        if not isinstance(completed, list):
            completed = []
            self.data["completed_lesson_texts"] = completed

        with self._conn:
            cursor = self._conn.execute(
                """INSERT OR IGNORE INTO completed_lesson_texts
                   (lesson_index, text_index, completed_at) VALUES (?, ?, ?)""",
                (pair[0], pair[1], completed_at),
            )
        if cursor.rowcount:
            completed.append(pair)

    def get_completed_lesson_texts(self) -> Set[Tuple[int, int]]:
        completed = self.data.get("completed_lesson_texts", [])
        if not isinstance(completed, list):
            return set()
        return {
            (int(pair[0]), int(pair[1]))
            for pair in completed
            if isinstance(pair, (list, tuple)) and len(pair) == 2
        }

    def get_setting(self, key: str, default=None):
        settings = self.data.get("settings", {})
        if isinstance(settings, dict):
            return settings.get(key, default)
        return default

    def set_setting(self, key: str, value) -> None:
        settings = self.data.get("settings")
        if not isinstance(settings, dict):
            settings = {}
            self.data["settings"] = settings
        settings[key] = value
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO settings (key, value) VALUES (?, ?)",
                (key, json.dumps(value)),
            )

    def get_random_text(self, lesson_index: int) -> Optional[str]:
        random_texts = self.data.get("random_texts", {})
        if isinstance(random_texts, dict):
            return random_texts.get(str(lesson_index))
        return None

    def set_random_text(self, lesson_index: int, text: str) -> None:
        random_texts = self.data.get("random_texts")
        if not isinstance(random_texts, dict):
            random_texts = {}
            self.data["random_texts"] = random_texts
        random_texts[str(lesson_index)] = text
        with self._conn:
            self._conn.execute(
                "INSERT OR REPLACE INTO random_texts (lesson_key, text) VALUES (?, ?)",
                (str(lesson_index), text),
            )

    def clear_random_text(self, lesson_index: int) -> None:
        random_texts = self.data.get("random_texts", {})
        if isinstance(random_texts, dict) and str(lesson_index) in random_texts:
            del random_texts[str(lesson_index)]
            self.data["random_texts"] = random_texts
        with self._conn:
            self._conn.execute(
                "DELETE FROM random_texts WHERE lesson_key = ?",
                (str(lesson_index),),
            )

    def get_developer_text(self, lesson_index: int) -> Optional[Dict[str, object]]:
        developer_texts = self.data.get("developer_texts", {})
        if isinstance(developer_texts, dict):
            value = developer_texts.get(str(lesson_index))
            return value if isinstance(value, dict) else None
        return None

    def set_developer_text(self, lesson_index: int, text: str, *, token_count: int, mode: str) -> None:
        developer_texts = self.data.get("developer_texts")
        if not isinstance(developer_texts, dict):
            developer_texts = {}
            self.data["developer_texts"] = developer_texts
        developer_texts[str(lesson_index)] = {
            "text": text,
            "token_count": token_count,
            "mode": mode,
        }
        with self._conn:
            self._conn.execute(
                """INSERT OR REPLACE INTO developer_texts
                   (lesson_key, text, token_count, mode) VALUES (?, ?, ?, ?)""",
                (str(lesson_index), text, token_count, mode),
            )

    def clear_developer_text(self, lesson_index: int) -> None:
        developer_texts = self.data.get("developer_texts", {})
        if isinstance(developer_texts, dict) and str(lesson_index) in developer_texts:
            del developer_texts[str(lesson_index)]
            self.data["developer_texts"] = developer_texts
        with self._conn:
            self._conn.execute(
                "DELETE FROM developer_texts WHERE lesson_key = ?",
                (str(lesson_index),),
            )

    def update_key_error_stats(self, key_errors: Dict[str, int]) -> None:
        self._upsert_key_counts("key_error_stats", key_errors)

    def get_key_error_stats(self) -> Dict[str, int]:
        stats = self.data.get("key_error_stats", {})
        return stats if isinstance(stats, dict) else {}

    def update_key_attempt_stats(self, key_attempts: Dict[str, int]) -> None:
        self._upsert_key_counts("key_attempt_stats", key_attempts)

    def get_key_attempt_stats(self) -> Dict[str, int]:
        stats = self.data.get("key_attempt_stats", {})
        return stats if isinstance(stats, dict) else {}

    def _upsert_key_counts(self, table: str, counts: Dict[str, int]) -> None:
        stats = self.data.get(table)
        if not isinstance(stats, dict):
            stats = {}
            self.data[table] = stats
        with self._conn:
            for key, count in counts.items():
                new_total = stats.get(key, 0) + count
                stats[key] = new_total
                self._conn.execute(
                    f"INSERT OR REPLACE INTO {table} (key, count) VALUES (?, ?)",
                    (str(key), int(new_total)),
                )

    def add_session_key_stats(
        self,
        timestamp: str,
        lesson_index: int,
        lesson_name: str,
        key_errors: Dict[str, int],
        key_attempts: Dict[str, int],
    ) -> None:
        """Log per-session, per-key error counts for one completed session.

        Only keys that produced at least one error are stored (with their
        attempt count for the same session), keeping the table compact. After
        inserting, the table is trimmed to the same retention window as
        `session_history` so it cannot grow unbounded.
        """
        if not key_errors:
            return
        with self._conn:
            for key, error_count in key_errors.items():
                if error_count <= 0:
                    continue
                self._conn.execute(
                    """INSERT INTO session_key_errors
                       (session_timestamp, lesson_index, lesson_name,
                        key, error_count, attempt_count)
                       VALUES (?, ?, ?, ?, ?, ?)""",
                    (
                        str(timestamp),
                        int(lesson_index),
                        str(lesson_name),
                        str(key),
                        int(error_count),
                        int(key_attempts.get(key, 0)),
                    ),
                )
            self._conn.execute(
                """DELETE FROM session_key_errors
                   WHERE session_timestamp NOT IN (
                     SELECT session_timestamp FROM (
                       SELECT DISTINCT session_timestamp FROM session_key_errors
                       ORDER BY session_timestamp DESC LIMIT ?
                     )
                   )""",
                (self.MAX_HISTORY_SIZE,),
            )

    def get_lesson_key_errors(self, lesson_index: int) -> Dict[str, int]:
        """Aggregate per-key error counts for a single lesson."""
        return {
            row[0]: row[1]
            for row in self._conn.execute(
                """SELECT key, SUM(error_count) FROM session_key_errors
                   WHERE lesson_index = ? GROUP BY key""",
                (int(lesson_index),),
            )
        }

    def get_lesson_key_attempts(self, lesson_index: int) -> Dict[str, int]:
        """Aggregate per-key attempt counts for a single lesson."""
        return {
            row[0]: row[1]
            for row in self._conn.execute(
                """SELECT key, SUM(attempt_count) FROM session_key_errors
                   WHERE lesson_index = ? GROUP BY key""",
                (int(lesson_index),),
            )
        }

    def get_lessons_with_error_data(self) -> List[Dict[str, object]]:
        """Return lessons that have logged per-session error data, newest first."""
        return [
            {"lesson_index": row[0], "lesson_name": row[1]}
            for row in self._conn.execute(
                """SELECT lesson_index, lesson_name, MAX(session_timestamp) AS last_seen
                   FROM session_key_errors
                   GROUP BY lesson_index, lesson_name
                   ORDER BY last_seen DESC"""
            )
        ]

    def get_error_timeseries(self) -> List[Dict[str, object]]:
        """Return total errors per session over time, oldest first."""
        return [
            {"timestamp": row[0], "errors": row[1]}
            for row in self._conn.execute(
                """SELECT session_timestamp, SUM(error_count) FROM session_key_errors
                   GROUP BY session_timestamp
                   ORDER BY session_timestamp ASC"""
            )
        ]

    def close(self) -> None:
        try:
            self._conn.close()
        except sqlite3.Error:
            pass

    def __del__(self) -> None:
        self.close()
