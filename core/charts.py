"""Chart generation utilities using matplotlib for the typing practice app."""

import io
from typing import List, Dict, Optional
import matplotlib
matplotlib.use('Agg')  # Use non-interactive backend
import matplotlib.pyplot as plt
from matplotlib.figure import Figure
from matplotlib.patches import Rectangle, FancyBboxPatch
from PyQt6.QtGui import QPixmap
from PyQt6.QtCore import QBuffer, QIODevice

from core.themes import Theme
from core.constants import KEY_FINGER_MAP


def create_chart_pixmap(fig: Figure) -> QPixmap:
    """Convert a matplotlib figure to a QPixmap for display in PyQt."""
    buf = io.BytesIO()
    fig.savefig(buf, format='png', dpi=100, bbox_inches='tight')
    buf.seek(0)
    
    pixmap = QPixmap()
    pixmap.loadFromData(buf.read())
    buf.close()
    
    return pixmap


def create_wpm_progress_chart(session_history: List[Dict], theme: Theme, max_sessions: int = 20) -> QPixmap:
    """Create a WPM progress chart showing the last N sessions."""
    if not session_history:
        # Return empty pixmap if no data
        return QPixmap()
    
    last_sessions = session_history[-max_sessions:]
    session_nums = list(range(1, len(last_sessions) + 1))
    wpms = [s.get("wpm", 0) for s in last_sessions]
    
    # Create figure with theme colors
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(theme.chart_bg)
    ax.set_facecolor(theme.chart_bg)
    
    # Plot data
    ax.plot(session_nums, wpms, marker='o', linewidth=2, 
            color=theme.chart_primary, markersize=6)
    
    # Fill area under curve
    ax.fill_between(session_nums, wpms, alpha=0.3, color=theme.chart_primary)
    
    # Styling
    ax.set_xlabel('Session Number', color=theme.chart_text, fontsize=10)
    ax.set_ylabel('Words Per Minute', color=theme.chart_text, fontsize=10)
    ax.set_title(f'WPM Progress (Last {len(last_sessions)} Sessions)', 
                 color=theme.chart_text, fontsize=12, fontweight='bold')
    ax.grid(True, alpha=0.3, color=theme.chart_grid)
    ax.tick_params(colors=theme.chart_text)
    
    # Set spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap


def create_accuracy_progress_chart(session_history: List[Dict], theme: Theme, max_sessions: int = 20) -> QPixmap:
    """Create an accuracy progress chart showing the last N sessions."""
    if not session_history:
        return QPixmap()
    
    last_sessions = session_history[-max_sessions:]
    session_nums = list(range(1, len(last_sessions) + 1))
    accuracies = [s.get("accuracy", 0) for s in last_sessions]
    
    # Create figure with theme colors
    fig, ax = plt.subplots(figsize=(8, 4))
    fig.patch.set_facecolor(theme.chart_bg)
    ax.set_facecolor(theme.chart_bg)
    
    # Plot data
    ax.plot(session_nums, accuracies, marker='s', linewidth=2,
            color=theme.chart_secondary, markersize=6)
    
    # Fill area under curve
    ax.fill_between(session_nums, accuracies, alpha=0.3, color=theme.chart_secondary)
    
    # Styling
    ax.set_xlabel('Session Number', color=theme.chart_text, fontsize=10)
    ax.set_ylabel('Accuracy (%)', color=theme.chart_text, fontsize=10)
    ax.set_title(f'Accuracy Progress (Last {len(last_sessions)} Sessions)',
                 color=theme.chart_text, fontsize=12, fontweight='bold')
    ax.set_ylim(0, 105)  # Set y-axis from 0 to 105%
    ax.grid(True, alpha=0.3, color=theme.chart_grid)
    ax.tick_params(colors=theme.chart_text)
    
    # Set spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap


def create_combined_progress_chart(session_history: List[Dict], theme: Theme, max_sessions: int = 20) -> QPixmap:
    """Create a combined chart with both WPM and accuracy."""
    if not session_history:
        return QPixmap()
    
    last_sessions = session_history[-max_sessions:]
    session_nums = list(range(1, len(last_sessions) + 1))
    wpms = [s.get("wpm", 0) for s in last_sessions]
    accuracies = [s.get("accuracy", 0) for s in last_sessions]
    
    # Create figure with dual y-axes
    fig, ax1 = plt.subplots(figsize=(10, 5))
    fig.patch.set_facecolor(theme.chart_bg)
    ax1.set_facecolor(theme.chart_bg)
    
    # Plot WPM on left axis
    color1 = theme.chart_primary
    ax1.set_xlabel('Session Number', color=theme.chart_text, fontsize=10)
    ax1.set_ylabel('Words Per Minute', color=color1, fontsize=10)
    line1 = ax1.plot(session_nums, wpms, marker='o', linewidth=2,
                     color=color1, markersize=6, label='WPM')
    ax1.tick_params(axis='y', labelcolor=color1)
    ax1.tick_params(axis='x', colors=theme.chart_text)
    ax1.grid(True, alpha=0.2, color=theme.chart_grid)
    
    # Create second y-axis for accuracy
    ax2 = ax1.twinx()
    ax2.set_facecolor('none')
    color2 = theme.chart_secondary
    ax2.set_ylabel('Accuracy (%)', color=color2, fontsize=10)
    line2 = ax2.plot(session_nums, accuracies, marker='s', linewidth=2,
                     color=color2, markersize=6, label='Accuracy')
    ax2.tick_params(axis='y', labelcolor=color2)
    ax2.set_ylim(0, 105)
    
    # Title
    ax1.set_title(f'Performance Progress (Last {len(last_sessions)} Sessions)',
                  color=theme.chart_text, fontsize=12, fontweight='bold')
    
    # Combined legend
    lines = line1 + line2
    labels = [l.get_label() for l in lines]
    ax1.legend(lines, labels, loc='upper left', facecolor=theme.chart_bg,
               edgecolor=theme.chart_grid, labelcolor=theme.chart_text)
    
    # Set spine colors
    for spine in ax1.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    for spine in ax2.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap


def create_lesson_performance_chart(session_history: List[Dict], theme: Theme) -> QPixmap:
    """Create a bar chart showing average WPM by lesson."""
    if not session_history:
        return QPixmap()
    
    # Group by lesson and calculate averages
    lesson_wpms: Dict[str, List[int]] = {}
    for s in session_history:
        lesson = s.get("lesson_name", "Unknown")
        wpm = s.get("wpm", 0)
        if lesson not in lesson_wpms:
            lesson_wpms[lesson] = []
        lesson_wpms[lesson].append(wpm)
    
    # Calculate averages
    lessons = []
    avg_wpms = []
    for lesson, wpms in lesson_wpms.items():
        if wpms:  # Only include if we have data
            lessons.append(lesson[:20])  # Truncate long names
            avg_wpms.append(sum(wpms) / len(wpms))
    
    if not lessons:
        return QPixmap()
    
    # Sort by WPM
    sorted_data = sorted(zip(lessons, avg_wpms), key=lambda x: x[1], reverse=True)
    lessons, avg_wpms = zip(*sorted_data)
    
    # Limit to top 10 for readability
    lessons = list(lessons)[:10]
    avg_wpms = list(avg_wpms)[:10]
    
    # Create figure
    fig, ax = plt.subplots(figsize=(10, 6))
    fig.patch.set_facecolor(theme.chart_bg)
    ax.set_facecolor(theme.chart_bg)
    
    # Create bars
    bars = ax.barh(lessons, avg_wpms, color=theme.chart_primary, alpha=0.8)
    
    # Add value labels on bars
    for bar in bars:
        width = bar.get_width()
        ax.text(width, bar.get_y() + bar.get_height()/2,
                f'{width:.1f}',
                ha='left', va='center', color=theme.chart_text,
                fontsize=9, fontweight='bold')
    
    # Styling
    ax.set_xlabel('Average WPM', color=theme.chart_text, fontsize=10)
    ax.set_title('Average Performance by Lesson', color=theme.chart_text,
                 fontsize=12, fontweight='bold')
    ax.tick_params(colors=theme.chart_text)
    ax.grid(True, axis='x', alpha=0.3, color=theme.chart_grid)
    
    # Set spine colors
    for spine in ax.spines.values():
        spine.set_edgecolor(theme.chart_grid)
    
    plt.tight_layout()
    pixmap = create_chart_pixmap(fig)
    plt.close(fig)
    
    return pixmap
