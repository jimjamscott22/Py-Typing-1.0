"""Quick test to verify new enhancements work."""
import os
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

# Ensure Qt can create QPixmaps during headless test runs.
os.environ.setdefault("QT_QPA_PLATFORM", "offscreen")

_QT_APP = None


def _ensure_qapplication():
    global _QT_APP
    from PyQt6.QtWidgets import QApplication

    app = QApplication.instance()
    if app is None:
        app = QApplication(sys.argv)
    _QT_APP = app
    return app

def test_themes():
    """Test theme system."""
    from core.themes import get_theme, get_theme_names

    print("✓ Testing theme system...")
    names = get_theme_names()
    assert len(names) == 5, f"Expected 5 themes, got {len(names)}"
    assert "Light" in names
    assert "Dark" in names
    assert "Solarized Dark" in names
    assert "Nord" in names
    assert "Dracula" in names
    
    # Test getting themes
    light = get_theme("Light")
    assert light.name == "Light"
    assert light.bg_primary == "#ffffff"
    
    dark = get_theme("Dark")
    assert dark.name == "Dark"
    assert dark.bg_primary == "#1e1e1e"
    
    print("  ✓ All 5 themes loaded successfully")
    print(f"  ✓ Available themes: {', '.join(names)}")


def test_charts():
    """Test chart generation."""
    _ensure_qapplication()
    from core.charts import create_combined_progress_chart
    from core.themes import get_theme
    
    print("\n✓ Testing chart generation...")
    
    # Test with empty data
    theme = get_theme("Light")
    pixmap = create_combined_progress_chart([], theme)
    assert pixmap.isNull(), "Empty data should return null pixmap"
    
    # Test with sample data
    sample_history = [
        {"wpm": 30, "accuracy": 95.0},
        {"wpm": 35, "accuracy": 96.5},
        {"wpm": 40, "accuracy": 97.0},
    ]
    pixmap = create_combined_progress_chart(sample_history, theme)
    assert not pixmap.isNull(), "Valid data should return pixmap"
    
    print("  ✓ Chart generation works")
    print("  ✓ Matplotlib integration successful")


def test_lessons():
    """Test lesson list includes the new developer category."""
    from core.lessons import build_lessons

    print("\n✓ Testing lesson list...")

    lessons = build_lessons()
    titles = [lesson.title for lesson in lessons]

    assert titles[-1] == "Developer Keys", f"Expected Developer Keys to be the last lesson, got {titles[-1]!r}"
    assert "Developer Keys" in titles

    developer_lesson = lessons[-1]
    assert developer_lesson.texts == ["__DEVELOPER__"]

    print("  ✓ Developer Keys lesson is available")
    print(f"  ✓ Total lessons: {len(lessons)}")


def test_wordgen():
    """Test developer-key text generation."""
    from core.wordgen import (
        DEVELOPER_CODE_TOKENS,
        DEVELOPER_SYMBOL_TOKENS,
        generate_developer_text,
    )

    print("\n✓ Testing developer text generation...")

    symbol_text = generate_developer_text(12, "symbol-heavy")
    symbol_tokens = symbol_text.split()
    code_text = generate_developer_text(12, "code-snippet-heavy")
    code_tokens = code_text.split()

    assert len(symbol_tokens) == 12, f"Expected 12 tokens, got {len(symbol_tokens)}"
    assert len(code_tokens) == 12, f"Expected 12 tokens, got {len(code_tokens)}"
    assert set(symbol_tokens).issubset(set(DEVELOPER_SYMBOL_TOKENS)), "Symbol-heavy text contained unexpected tokens"
    assert set(code_tokens).issubset(set(DEVELOPER_SYMBOL_TOKENS + DEVELOPER_CODE_TOKENS)), "Code-heavy text contained unexpected tokens"
    assert generate_developer_text(0) == ""

    print("  ✓ Developer-key text generation works")
    print(f"  ✓ Symbol-heavy sample: {symbol_text}")
    print(f"  ✓ Code-heavy sample: {code_text}")


def test_developer_settings_persistence():
    """Test developer settings round-trip through the progress store."""
    from core.constants import DEFAULT_DEVELOPER_KEYS_LENGTH, DEFAULT_DEVELOPER_KEYS_MODE
    from core.persistence import ProgressStore
    from pathlib import Path
    import tempfile

    print("\n✓ Testing developer settings persistence...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)

    try:
        store = ProgressStore(temp_path)
        assert store.get_setting("developer_keys_length", -1) == DEFAULT_DEVELOPER_KEYS_LENGTH
        assert store.get_setting("developer_keys_mode", "") == DEFAULT_DEVELOPER_KEYS_MODE

        store.set_setting("developer_keys_length", 18)
        store.set_setting("developer_keys_mode", "code-snippet-heavy")
        store.set_developer_text(9, "def main return", token_count=18, mode="code-snippet-heavy")

        reloaded = ProgressStore(temp_path)
        assert reloaded.get_setting("developer_keys_length", -1) == 18
        assert reloaded.get_setting("developer_keys_mode", "") == "code-snippet-heavy"

        cached = reloaded.get_developer_text(9)
        assert cached is not None
        assert cached.get("text") == "def main return"
        assert cached.get("token_count") == 18
        assert cached.get("mode") == "code-snippet-heavy"

        print("  ✓ Developer settings persist correctly")
        print("  ✓ Cached developer drills persist with metadata")
    finally:
        if temp_path.exists():
            os.unlink(temp_path)


def test_settings_dialog_developer_controls():
    """Test that the settings dialog exposes Developer Keys controls."""
    _ensure_qapplication()
    from core.persistence import ProgressStore
    from ui.dialogs import SettingsDialog
    from pathlib import Path
    import tempfile

    print("\n✓ Testing settings dialog Developer Keys controls...")

    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)

    try:
        store = ProgressStore(temp_path)
        store.set_setting("developer_keys_length", 30)
        store.set_setting("developer_keys_mode", "code-snippet-heavy")

        dialog = SettingsDialog(store)
        assert dialog.developer_length_spin.value() == 30
        assert dialog.developer_mode_combo.currentText() == "code-snippet-heavy"

        print("  ✓ Settings dialog exposes Developer Keys controls")
        print("  ✓ Controls reflect saved values")
    finally:
        if temp_path.exists():
            os.unlink(temp_path)


def test_heatmap():
    """Test heatmap generation."""
    _ensure_qapplication()
    from core.heatmap import create_keyboard_heatmap, create_finger_error_chart
    from core.themes import get_theme
    
    print("\n✓ Testing heatmap visualization...")
    
    # Test with empty data
    theme = get_theme("Dark")
    pixmap = create_keyboard_heatmap({}, theme)
    assert pixmap.isNull(), "Empty data should return null pixmap"
    
    # Test with sample error data
    sample_errors = {
        'a': 5, 's': 3, 'd': 7, 'f': 2,
        'j': 4, 'k': 6, 'l': 1,
    }
    pixmap = create_keyboard_heatmap(sample_errors, theme)
    assert not pixmap.isNull(), "Valid data should return pixmap"
    
    finger_pixmap = create_finger_error_chart(sample_errors, theme)
    assert not finger_pixmap.isNull(), "Valid data should return finger chart"
    
    print("  ✓ Keyboard heatmap generation works")
    print("  ✓ Finger error chart works")


def test_persistence():
    """Test key error persistence."""
    from core.persistence import ProgressStore
    from pathlib import Path
    import tempfile
    import os
    
    print("\n✓ Testing error tracking persistence...")
    
    # Create temporary file for testing
    with tempfile.NamedTemporaryFile(mode='w', suffix='.json', delete=False) as f:
        temp_path = Path(f.name)
    
    try:
        store = ProgressStore(temp_path)
        
        # Test adding key errors
        sample_errors = {'a': 5, 's': 3, 'd': 7}
        store.update_key_error_stats(sample_errors)
        
        # Retrieve and verify
        stats = store.get_key_error_stats()
        assert stats['a'] == 5
        assert stats['s'] == 3
        assert stats['d'] == 7
        
        # Add more errors (should accumulate)
        store.update_key_error_stats({'a': 2, 'f': 4})
        stats = store.get_key_error_stats()
        assert stats['a'] == 7  # 5 + 2
        assert stats['f'] == 4
        
        print("  ✓ Key error tracking works")
        print("  ✓ Accumulation across sessions works")
        
    finally:
        # Cleanup
        if temp_path.exists():
            os.unlink(temp_path)


def test_models():
    """Test updated models."""
    from core.models import TypingSession
    
    print("\n✓ Testing session models...")
    
    session = TypingSession()
    assert session.key_errors == {}
    
    # Test recording errors
    session.record_key_error('a')
    session.record_key_error('a')
    session.record_key_error('s')
    
    assert session.key_errors['a'] == 2
    assert session.key_errors['s'] == 1
    
    # Test reset
    session.reset()
    assert session.key_errors == {}
    
    print("  ✓ Key error tracking in sessions works")


def main():
    """Run all tests."""
    print("=" * 60)
    print("Testing Py-Typing-1.0 Enhancements")
    print("=" * 60)

    _ensure_qapplication()

    try:
        test_themes()
        test_charts()
        test_lessons()
        test_wordgen()
        test_developer_settings_persistence()
        test_settings_dialog_developer_controls()
        test_heatmap()
        test_persistence()
        test_models()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nEnhancements successfully implemented:")
        print("  1. ✓ Theme System (5 themes)")
        print("  2. ✓ Matplotlib Charts")
        print("  3. ✓ Developer Keys lesson")
        print("  4. ✓ Developer text generation")
        print("  5. ✓ Developer settings persistence")
        print("  6. ✓ Settings dialog Developer Keys controls")
        print("  7. ✓ Keyboard Error Heatmap")
        print("\nYou can now run the application:")
        print("  python main.py")
        
    except Exception as e:
        print("\n" + "=" * 60)
        print(f"❌ TEST FAILED: {e}")
        print("=" * 60)
        import traceback
        traceback.print_exc()
        return 1
    
    return 0


if __name__ == "__main__":
    exit(main())
