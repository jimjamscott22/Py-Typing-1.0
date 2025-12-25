# Default settings values
DEFAULT_BACKSPACE_PENALTY = 3  # WPM penalty per backspace
DEFAULT_BACKSPACE_ACCURACY_WEIGHT = 0.5  # Each backspace counts as 0.5 errors
DEFAULT_STRICT_MODE = False
DEFAULT_DARK_MODE = False
DEFAULT_SHOW_KEYBOARD = True
DEFAULT_SHOW_CELEBRATION = True
DEFAULT_FONT_SIZE = 16
DEFAULT_RANDOM_WORD_COUNT = 25  # Number of random words to generate

FREE_PRACTICE_DESCRIPTION = (
    "Free practice mode: paste or import any text, click <b>Use Custom Text</b>, and start typing."
)
FREE_PRACTICE_PLACEHOLDER = "Provide custom text or import a file to begin."

# Finger color mapping for keyboard visualization
FINGER_COLORS = {
    "left_pinky": "#e57373",    # Red
    "left_ring": "#f06292",     # Pink
    "left_middle": "#ba68c8",   # Purple
    "left_index": "#64b5f6",    # Light blue
    "right_index": "#4fc3f7",   # Cyan
    "right_middle": "#4db6ac",  # Teal
    "right_ring": "#81c784",    # Green
    "right_pinky": "#aed581",   # Light green
    "thumbs": "#ffb74d",        # Orange (space bar)
}

# Key to finger mapping
KEY_FINGER_MAP = {
    # Left pinky
    '`': 'left_pinky', '1': 'left_pinky', 'q': 'left_pinky', 'a': 'left_pinky', 'z': 'left_pinky',
    '~': 'left_pinky', '!': 'left_pinky',
    # Left ring
    '2': 'left_ring', 'w': 'left_ring', 's': 'left_ring', 'x': 'left_ring',
    '@': 'left_ring',
    # Left middle
    '3': 'left_middle', 'e': 'left_middle', 'd': 'left_middle', 'c': 'left_middle',
    '#': 'left_middle',
    # Left index (two columns)
    '4': 'left_index', '5': 'left_index', 'r': 'left_index', 't': 'left_index',
    'f': 'left_index', 'g': 'left_index', 'v': 'left_index', 'b': 'left_index',
    '$': 'left_index', '%': 'left_index',
    # Right index (two columns)
    '6': 'right_index', '7': 'right_index', 'y': 'right_index', 'u': 'right_index',
    'h': 'right_index', 'j': 'right_index', 'n': 'right_index', 'm': 'right_index',
    '^': 'right_index', '&': 'right_index',
    # Right middle
    '8': 'right_middle', 'i': 'right_middle', 'k': 'right_middle', ',': 'right_middle',
    '*': 'right_middle', '<': 'right_middle',
    # Right ring
    '9': 'right_ring', 'o': 'right_ring', 'l': 'right_ring', '.': 'right_ring',
    '(': 'right_ring', '>': 'right_ring',
    # Right pinky
    '0': 'right_pinky', '-': 'right_pinky', '=': 'right_pinky', 'p': 'right_pinky',
    '[': 'right_pinky', ']': 'right_pinky', '\\': 'right_pinky', ';': 'right_pinky',
    "'": 'right_pinky', '/': 'right_pinky',
    ')': 'right_pinky', '_': 'right_pinky', '+': 'right_pinky', '{': 'right_pinky',
    '}': 'right_pinky', '|': 'right_pinky', ':': 'right_pinky', '"': 'right_pinky',
    '?': 'right_pinky',
    # Space bar
    ' ': 'thumbs',
}
