"""Keyboard heatmap visualization for error tracking."""

from typing import Dict
import matplotlib
matplotlib.use('Agg')
import matplotlib.pyplot as plt
from matplotlib.patches import FancyBboxPatch
from PyQt6.QtGui import QPixmap

from core.themes import Theme
from core.constants import KEY_FINGER_MAP
from core.charts import create_chart_pixmap


def create_keyboard_heatmap(key_error_stats: Dict[str, int], theme: Theme) -> QPixmap:
    """Create a keyboard heatmap showing which keys have the most errors."""
    if not key_error_stats:
        return QPixmap()
    
    # Keyboard layout with positions (x, y, width) for each key
    keyboard_layout = {
        # Row 1 (numbers)
        '`': (0, 3, 1), '1': (1, 3, 1), '2': (2, 3, 1), '3': (3, 3, 1), '4': (4, 3, 1),
        '5': (5, 3, 1), '6': (6, 3, 1), '7': (7, 3, 1), '8': (8, 3, 1), '9': (9, 3, 1),
        '0': (10, 3, 1), '-': (11, 3, 1), '=': (12, 3, 1),
        # Row 2 (QWERTY)
        'q': (1.5, 2, 1), 'w': (2.5, 2, 1), 'e': (3.5, 2, 1), 'r': (4.5, 2, 1), 't': (5.5, 2, 1),
        'y': (6.5, 2, 1), 'u': (7.5, 2, 1), 'i': (8.5, 2, 1), 'o': (9.5, 2, 1), 'p': (10.5, 2, 1),
        '[': (11.5, 2, 1), ']': (12.5, 2, 1),
        # Row 3 (ASDF)
        'a': (1.75, 1, 1), 's': (2.75, 1, 1), 'd': (3.75, 1, 1), 'f': (4.75, 1, 1), 'g': (5.75, 1, 1),
        'h': (6.75, 1, 1), 'j': (7.75, 1, 1), 'k': (8.75, 1, 1), 'l': (9.75, 1, 1), ';': (10.75, 1, 1),
        "'": (11.75, 1, 1),
        # Row 4 (ZXCV)
        'z': (2.25, 0, 1), 'x': (3.25, 0, 1), 'c': (4.25, 0, 1), 'v': (5.25, 0, 1), 'b': (6.25, 0, 1),
        'n': (7.25, 0, 1), 'm': (8.25, 0, 1), ',': (9.25, 0, 1), '.': (10.25, 0, 1), '/': (11.25, 0, 1),
        # Space bar
        ' ': (4, -0.8, 6),
    }
    
    # Normalize error counts for coloring
    max_errors = max(key_error_stats.values()) if key_error_stats else 1
    
    # Create figure
    fig, ax = plt.subplots(figsize=(14, 6))
    fig.patch.set_facecolor(theme.chart_bg)
    ax.set_facecolor(theme.chart_bg)
    
    # Draw keys
    for key, (x, y, width) in keyboard_layout.items():
        key_lower = key.lower()
        error_count = key_error_stats.get(key_lower, 0)
        
        # Calculate color intensity based on errors
        if error_count == 0:
            # No errors - use theme background
            color = theme.keyboard_key_bg
            alpha = 0.3
        else:
            # Scale from light to dark red based on error count
            intensity = min(error_count / max(max_errors, 1), 1.0)
            # Use red gradient
            color = (1.0, 1.0 - intensity * 0.7, 1.0 - intensity * 0.7)
            alpha = 0.5 + intensity * 0.5
        
        # Draw key
        rect = FancyBboxPatch(
            (x, y), width * 0.95, 0.9,
            boxstyle="round,pad=0.05",
            facecolor=color,
            edgecolor=theme.chart_grid,
            linewidth=1.5,
            alpha=alpha
        )
        ax.add_patch(rect)
        
        # Add key label
        label = key.upper() if key != ' ' else 'SPACE'
        ax.text(x + width * 0.475, y + 0.6, label,
                ha='center', va='center',
                fontsize=10, fontweight='bold',
                color=theme.chart_text)
        
        # Add error count if > 0
        if error_count > 0:
            ax.text(x + width * 0.475, y + 0.2, str(error_count),
                    ha='center', va='center',
                    fontsize=8,
                    color=theme.chart_text,
                    bbox=dict(boxstyle='round,pad=0.3', 
                             facecolor=theme.chart_bg, 
                             edgecolor='none',
                             alpha=0.7))
    
    # Set limits and remove axes
    ax.set_xlim(-0.5, 14)
    ax.set_ylim(-1.5, 4.5)
    ax.set_aspect('equal')
    ax.axis('off')
    
    # Add title
    total_errors = sum(key_error_stats.values())
    ax.set_title(f'Keyboard Error Heatmap (Total Errors: {total_errors})',
                 color=theme.chart_text, fontsize=14, fontweight='bold', pad=20)
    
    # Add legend
    legend_y = -1.2
    legend_text = "Color intensity shows error frequency • Numbers show error count"
    ax.text(7, legend_y, legend_text,
            ha='center', va='center',
            fontsize=10,
            color=theme.text_secondary,
            style='italic')
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap


def create_finger_error_chart(key_error_stats: Dict[str, int], theme: Theme) -> QPixmap:
    """Create a bar chart showing errors grouped by finger."""
    if not key_error_stats:
        return QPixmap()
    
    # Group errors by finger
    finger_errors = {
        'Left Pinky': 0,
        'Left Ring': 0,
        'Left Middle': 0,
        'Left Index': 0,
        'Right Index': 0,
        'Right Middle': 0,
        'Right Ring': 0,
        'Right Pinky': 0,
        'Thumbs': 0,
    }
    
    finger_name_map = {
        'left_pinky': 'Left Pinky',
        'left_ring': 'Left Ring',
        'left_middle': 'Left Middle',
        'left_index': 'Left Index',
        'right_index': 'Right Index',
        'right_middle': 'Right Middle',
        'right_ring': 'Right Ring',
        'right_pinky': 'Right Pinky',
        'thumbs': 'Thumbs',
    }
    
    for key, count in key_error_stats.items():
        finger = KEY_FINGER_MAP.get(key.lower())
        if finger:
            finger_name = finger_name_map.get(finger, 'Unknown')
            finger_errors[finger_name] = finger_errors.get(finger_name, 0) + count
    
    # Filter out fingers with no errors
    fingers = [f for f in finger_errors.keys() if finger_errors[f] > 0]
    errors = [finger_errors[f] for f in fingers]
    
    if not fingers:
        return QPixmap()
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(theme.chart_bg)
    ax.set_facecolor(theme.chart_bg)
    
    # Create bars with gradient colors
    colors = [theme.chart_primary if 'Left' in f else theme.chart_secondary for f in fingers]
    bars = ax.bar(fingers, errors, color=colors, alpha=0.7, edgecolor=theme.chart_grid, linewidth=1.5)
    
    # Add value labels on bars
    for bar in bars:
        height = bar.get_height()
        ax.text(bar.get_x() + bar.get_width()/2, height,
                f'{int(height)}',
                ha='center', va='bottom',
                color=theme.chart_text, fontsize=10, fontweight='bold')
    
    # Styling
    ax.set_ylabel('Error Count', color=theme.chart_text, fontsize=11, fontweight='bold')
    ax.set_title('Errors by Finger', color=theme.chart_text, fontsize=13, fontweight='bold')
    ax.tick_params(colors=theme.chart_text)
    plt.xticks(rotation=45, ha='right')
    ax.grid(True, axis='y', alpha=0.3, color=theme.chart_grid)
    
    # Set spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap
