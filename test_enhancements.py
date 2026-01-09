"""Quick test to verify new enhancements work."""
import sys
import io

# Fix encoding for Windows console
if sys.platform == 'win32':
    sys.stdout = io.TextIOWrapper(sys.stdout.buffer, encoding='utf-8')

def test_themes():
    """Test theme system."""
    from core.themes import get_theme, get_theme_names, THEMES
    
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
    from core.charts import (
        create_combined_progress_chart,
        create_lesson_performance_chart,
    )
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


def test_heatmap():
    """Test heatmap generation."""
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
    
    try:
        test_themes()
        test_charts()
        test_heatmap()
        test_persistence()
        test_models()
        
        print("\n" + "=" * 60)
        print("✅ ALL TESTS PASSED!")
        print("=" * 60)
        print("\nEnhancements successfully implemented:")
        print("  1. ✓ Theme System (5 themes)")
        print("  2. ✓ Matplotlib Charts")
        print("  3. ✓ Keyboard Error Heatmap")
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
