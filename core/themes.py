"""Theme definitions for the typing practice application."""

from dataclasses import dataclass
from typing import Dict

@dataclass
class Theme:
    """Defines colors and styles for a UI theme."""
    name: str
    # Main window colors
    bg_primary: str          # Main background
    bg_secondary: str        # Sidebar/secondary background
    text_primary: str        # Main text color
    text_secondary: str      # Secondary text color
    
    # Lesson description backgrounds
    description_bg: str      # Normal lesson description
    description_success_bg: str  # Completion message background
    description_complete_bg: str # All lessons complete background
    
    # Input/Target text
    target_bg: str           # Target text background
    target_border: str       # Target text border
    input_bg: str            # Input text background
    input_border: str        # Input text border
    
    # Stats labels
    wpm_bg: str              # WPM label background
    accuracy_bg: str         # Accuracy label background
    progress_bg: str         # Progress label background
    error_bg: str            # Error label background
    backspace_bg: str        # Backspace label background
    best_bg: str             # Best WPM label background
    
    # Progress bar
    progress_bar_bg: str     # Progress bar background
    progress_bar_fill: str   # Progress bar fill color
    
    # Buttons
    button_bg: str           # Button background
    button_hover_bg: str     # Button hover background
    button_border: str       # Button border
    button_text: str         # Button text color
    
    # List widget
    list_bg: str             # List background
    list_selected: str       # List selected item
    
    # Keyboard
    keyboard_bg: str         # Keyboard background
    keyboard_key_bg: str     # Key background
    keyboard_key_border: str # Key border
    keyboard_text: str       # Key text
    keyboard_highlight: str  # Next key highlight
    keyboard_error: str      # Error key highlight
    
    # Chart colors
    chart_bg: str            # Chart background
    chart_grid: str          # Chart grid lines
    chart_text: str          # Chart text
    chart_primary: str       # Primary chart color
    chart_secondary: str     # Secondary chart color


# Default light theme
LIGHT_THEME = Theme(
    name="Light",
    bg_primary="#ffffff",
    bg_secondary="#f5f5f5",
    text_primary="#333333",
    text_secondary="#666666",
    
    description_bg="#e3f2fd",
    description_success_bg="#c8e6c9",
    description_complete_bg="#fff9c4",
    
    target_bg="#f5f5f5",
    target_border="#cccccc",
    input_bg="#ffffff",
    input_border="#2196F3",
    
    wpm_bg="#4CAF50",
    accuracy_bg="#2196F3",
    progress_bg="#FF9800",
    error_bg="#F06292",
    backspace_bg="#FF5722",
    best_bg="#7E57C2",
    
    progress_bar_bg="#e0e0e0",
    progress_bar_fill="#4CAF50",
    
    button_bg="#424242",
    button_hover_bg="#535353",
    button_border="#555555",
    button_text="#e0e0e0",
    
    list_bg="#ffffff",
    list_selected="#0d47a1",
    
    keyboard_bg="#e8e8e8",
    keyboard_key_bg="#ffffff",
    keyboard_key_border="#cccccc",
    keyboard_text="#333333",
    keyboard_highlight="#4CAF50",
    keyboard_error="#f44336",
    
    chart_bg="#ffffff",
    chart_grid="#e0e0e0",
    chart_text="#333333",
    chart_primary="#2196F3",
    chart_secondary="#4CAF50",
)

# Dark theme
DARK_THEME = Theme(
    name="Dark",
    bg_primary="#1e1e1e",
    bg_secondary="#2d2d2d",
    text_primary="#e0e0e0",
    text_secondary="#b0b0b0",
    
    description_bg="#1a237e",
    description_success_bg="#2e7d32",
    description_complete_bg="#f57f17",
    
    target_bg="#2d2d2d",
    target_border="#555555",
    input_bg="#2d2d2d",
    input_border="#2196F3",
    
    wpm_bg="#4CAF50",
    accuracy_bg="#2196F3",
    progress_bg="#FF9800",
    error_bg="#F06292",
    backspace_bg="#FF5722",
    best_bg="#7E57C2",
    
    progress_bar_bg="#2d2d2d",
    progress_bar_fill="#4CAF50",
    
    button_bg="#424242",
    button_hover_bg="#535353",
    button_border="#555555",
    button_text="#e0e0e0",
    
    list_bg="#2d2d2d",
    list_selected="#0d47a1",
    
    keyboard_bg="#2d2d2d",
    keyboard_key_bg="#404040",
    keyboard_key_border="#555555",
    keyboard_text="#ffffff",
    keyboard_highlight="#4CAF50",
    keyboard_error="#f44336",
    
    chart_bg="#2d2d2d",
    chart_grid="#404040",
    chart_text="#e0e0e0",
    chart_primary="#42a5f5",
    chart_secondary="#66bb6a",
)

# Solarized Dark theme
SOLARIZED_DARK_THEME = Theme(
    name="Solarized Dark",
    bg_primary="#002b36",
    bg_secondary="#073642",
    text_primary="#839496",
    text_secondary="#657b83",
    
    description_bg="#073642",
    description_success_bg="#2aa198",
    description_complete_bg="#b58900",
    
    target_bg="#073642",
    target_border="#586e75",
    input_bg="#073642",
    input_border="#268bd2",
    
    wpm_bg="#859900",
    accuracy_bg="#268bd2",
    progress_bg="#cb4b16",
    error_bg="#dc322f",
    backspace_bg="#d33682",
    best_bg="#6c71c4",
    
    progress_bar_bg="#073642",
    progress_bar_fill="#859900",
    
    button_bg="#073642",
    button_hover_bg="#586e75",
    button_border="#586e75",
    button_text="#839496",
    
    list_bg="#073642",
    list_selected="#268bd2",
    
    keyboard_bg="#073642",
    keyboard_key_bg="#002b36",
    keyboard_key_border="#586e75",
    keyboard_text="#839496",
    keyboard_highlight="#859900",
    keyboard_error="#dc322f",
    
    chart_bg="#002b36",
    chart_grid="#073642",
    chart_text="#839496",
    chart_primary="#268bd2",
    chart_secondary="#859900",
)

# Nord theme
NORD_THEME = Theme(
    name="Nord",
    bg_primary="#2e3440",
    bg_secondary="#3b4252",
    text_primary="#eceff4",
    text_secondary="#d8dee9",
    
    description_bg="#3b4252",
    description_success_bg="#a3be8c",
    description_complete_bg="#ebcb8b",
    
    target_bg="#3b4252",
    target_border="#4c566a",
    input_bg="#3b4252",
    input_border="#88c0d0",
    
    wpm_bg="#a3be8c",
    accuracy_bg="#88c0d0",
    progress_bg="#d08770",
    error_bg="#bf616a",
    backspace_bg="#b48ead",
    best_bg="#5e81ac",
    
    progress_bar_bg="#3b4252",
    progress_bar_fill="#a3be8c",
    
    button_bg="#434c5e",
    button_hover_bg="#4c566a",
    button_border="#4c566a",
    button_text="#eceff4",
    
    list_bg="#3b4252",
    list_selected="#5e81ac",
    
    keyboard_bg="#3b4252",
    keyboard_key_bg="#434c5e",
    keyboard_key_border="#4c566a",
    keyboard_text="#eceff4",
    keyboard_highlight="#a3be8c",
    keyboard_error="#bf616a",
    
    chart_bg="#2e3440",
    chart_grid="#3b4252",
    chart_text="#eceff4",
    chart_primary="#88c0d0",
    chart_secondary="#a3be8c",
)

# Dracula theme
DRACULA_THEME = Theme(
    name="Dracula",
    bg_primary="#282a36",
    bg_secondary="#44475a",
    text_primary="#f8f8f2",
    text_secondary="#6272a4",
    
    description_bg="#44475a",
    description_success_bg="#50fa7b",
    description_complete_bg="#f1fa8c",
    
    target_bg="#44475a",
    target_border="#6272a4",
    input_bg="#44475a",
    input_border="#8be9fd",
    
    wpm_bg="#50fa7b",
    accuracy_bg="#8be9fd",
    progress_bg="#ffb86c",
    error_bg="#ff5555",
    backspace_bg="#ff79c6",
    best_bg="#bd93f9",
    
    progress_bar_bg="#44475a",
    progress_bar_fill="#50fa7b",
    
    button_bg="#44475a",
    button_hover_bg="#6272a4",
    button_border="#6272a4",
    button_text="#f8f8f2",
    
    list_bg="#44475a",
    list_selected="#bd93f9",
    
    keyboard_bg="#44475a",
    keyboard_key_bg="#282a36",
    keyboard_key_border="#6272a4",
    keyboard_text="#f8f8f2",
    keyboard_highlight="#50fa7b",
    keyboard_error="#ff5555",
    
    chart_bg="#282a36",
    chart_grid="#44475a",
    chart_text="#f8f8f2",
    chart_primary="#8be9fd",
    chart_secondary="#50fa7b",
)

# Cyber Hacker theme
CYBER_HACKER_THEME = Theme(
    name="Cyber Hacker",
    bg_primary="#000000",
    bg_secondary="#0d1f10",
    text_primary="#00ff41",
    text_secondary="#00a82b",
    
    description_bg="#0d1f10",
    description_success_bg="#11451b",
    description_complete_bg="#1e7330",
    
    target_bg="#0d1f10",
    target_border="#008f11",
    input_bg="#000000",
    input_border="#00ff41",
    
    wpm_bg="#00a82b",
    accuracy_bg="#00ff41",
    progress_bg="#005e18",
    error_bg="#cc0000",
    backspace_bg="#800000",
    best_bg="#008f11",
    
    progress_bar_bg="#0d1f10",
    progress_bar_fill="#00ff41",
    
    button_bg="#0d1f10",
    button_hover_bg="#11451b",
    button_border="#008f11",
    button_text="#00ff41",
    
    list_bg="#000000",
    list_selected="#11451b",
    
    keyboard_bg="#000000",
    keyboard_key_bg="#0d1f10",
    keyboard_key_border="#008f11",
    keyboard_text="#00ff41",
    keyboard_highlight="#00ff41",
    keyboard_error="#cc0000",
    
    chart_bg="#000000",
    chart_grid="#0d1f10",
    chart_text="#00ff41",
    chart_primary="#00ff41",
    chart_secondary="#00a82b",
)

# CRT Amber theme
CRT_AMBER_THEME = Theme(
    name="CRT Amber",
    bg_primary="#0f0900",
    bg_secondary="#211400",
    text_primary="#ffb000",
    text_secondary="#cc8c00",
    
    description_bg="#211400",
    description_success_bg="#3a2300",
    description_complete_bg="#573400",
    
    target_bg="#211400",
    target_border="#8a5300",
    input_bg="#0f0900",
    input_border="#ffb000",
    
    wpm_bg="#cc8c00",
    accuracy_bg="#ffb000",
    progress_bg="#8a5300",
    error_bg="#cc3300",
    backspace_bg="#8c1a00",
    best_bg="#ff9900",
    
    progress_bar_bg="#211400",
    progress_bar_fill="#ffb000",
    
    button_bg="#211400",
    button_hover_bg="#3a2300",
    button_border="#8a5300",
    button_text="#ffb000",
    
    list_bg="#0f0900",
    list_selected="#3a2300",
    
    keyboard_bg="#0f0900",
    keyboard_key_bg="#211400",
    keyboard_key_border="#8a5300",
    keyboard_text="#ffb000",
    keyboard_highlight="#ffb000",
    keyboard_error="#cc3300",
    
    chart_bg="#0f0900",
    chart_grid="#211400",
    chart_text="#ffb000",
    chart_primary="#ffb000",
    chart_secondary="#cc8c00",
)

# Monokai theme
MONOKAI_THEME = Theme(
    name="Monokai",
    bg_primary="#272822",
    bg_secondary="#3e3d32",
    text_primary="#f8f8f2",
    text_secondary="#75715e",
    
    description_bg="#3e3d32",
    description_success_bg="#a6e22e",
    description_complete_bg="#fd971f",
    
    target_bg="#3e3d32",
    target_border="#75715e",
    input_bg="#272822",
    input_border="#66d9ef",
    
    wpm_bg="#a6e22e",
    accuracy_bg="#66d9ef",
    progress_bg="#fd971f",
    error_bg="#f92672",
    backspace_bg="#ae81ff",
    best_bg="#e6db74",
    
    progress_bar_bg="#3e3d32",
    progress_bar_fill="#a6e22e",
    
    button_bg="#3e3d32",
    button_hover_bg="#49483e",
    button_border="#75715e",
    button_text="#f8f8f2",
    
    list_bg="#272822",
    list_selected="#49483e",
    
    keyboard_bg="#272822",
    keyboard_key_bg="#3e3d32",
    keyboard_key_border="#75715e",
    keyboard_text="#f8f8f2",
    keyboard_highlight="#a6e22e",
    keyboard_error="#f92672",
    
    chart_bg="#272822",
    chart_grid="#3e3d32",
    chart_text="#f8f8f2",
    chart_primary="#66d9ef",
    chart_secondary="#a6e22e",
)

# Gruvbox theme
GRUVBOX_THEME = Theme(
    name="Gruvbox",
    bg_primary="#282828",
    bg_secondary="#3c3836",
    text_primary="#ebdbb2",
    text_secondary="#a89984",
    
    description_bg="#3c3836",
    description_success_bg="#98971a",
    description_complete_bg="#d79921",
    
    target_bg="#3c3836",
    target_border="#665c54",
    input_bg="#282828",
    input_border="#83a598",
    
    wpm_bg="#98971a",
    accuracy_bg="#83a598",
    progress_bg="#d79921",
    error_bg="#cc241d",
    backspace_bg="#b16286",
    best_bg="#d3869b",
    
    progress_bar_bg="#3c3836",
    progress_bar_fill="#98971a",
    
    button_bg="#3c3836",
    button_hover_bg="#504945",
    button_border="#665c54",
    button_text="#ebdbb2",
    
    list_bg="#282828",
    list_selected="#504945",
    
    keyboard_bg="#282828",
    keyboard_key_bg="#3c3836",
    keyboard_key_border="#665c54",
    keyboard_text="#ebdbb2",
    keyboard_highlight="#98971a",
    keyboard_error="#cc241d",
    
    chart_bg="#282828",
    chart_grid="#3c3836",
    chart_text="#ebdbb2",
    chart_primary="#83a598",
    chart_secondary="#98971a",
)

# Synthwave theme
SYNTHWAVE_THEME = Theme(
    name="Synthwave",
    bg_primary="#262335",
    bg_secondary="#34294f",
    text_primary="#ffffff",
    text_secondary="#a48ebf",
    
    description_bg="#34294f",
    description_success_bg="#72f1b8",
    description_complete_bg="#ff7edb",
    
    target_bg="#34294f",
    target_border="#49386d",
    input_bg="#262335",
    input_border="#36f9f6",
    
    wpm_bg="#72f1b8",
    accuracy_bg="#36f9f6",
    progress_bg="#fede5d",
    error_bg="#ff8b39",
    backspace_bg="#fe4450",
    best_bg="#ff7edb",
    
    progress_bar_bg="#34294f",
    progress_bar_fill="#36f9f6",
    
    button_bg="#34294f",
    button_hover_bg="#49386d",
    button_border="#a48ebf",
    button_text="#ffffff",
    
    list_bg="#262335",
    list_selected="#49386d",
    
    keyboard_bg="#262335",
    keyboard_key_bg="#34294f",
    keyboard_key_border="#49386d",
    keyboard_text="#ffffff",
    keyboard_highlight="#72f1b8",
    keyboard_error="#fe4450",
    
    chart_bg="#262335",
    chart_grid="#34294f",
    chart_text="#ffffff",
    chart_primary="#36f9f6",
    chart_secondary="#ff7edb",
)

# Theme registry
THEMES: Dict[str, Theme] = {
    "Light": LIGHT_THEME,
    "Dark": DARK_THEME,
    "Solarized Dark": SOLARIZED_DARK_THEME,
    "Nord": NORD_THEME,
    "Dracula": DRACULA_THEME,
    "Cyber Hacker": CYBER_HACKER_THEME,
    "CRT Amber": CRT_AMBER_THEME,
    "Monokai": MONOKAI_THEME,
    "Gruvbox": GRUVBOX_THEME,
    "Synthwave": SYNTHWAVE_THEME,
}

def get_theme(name: str) -> Theme:
    """Get a theme by name, defaulting to Light if not found."""
    return THEMES.get(name, LIGHT_THEME)

def get_theme_names() -> list:
    """Get list of all available theme names."""
    return list(THEMES.keys())
