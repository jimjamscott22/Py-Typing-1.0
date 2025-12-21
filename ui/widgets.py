import random
from typing import Dict, List, Tuple

from PyQt6.QtCore import Qt, QRectF, QTimer, QPropertyAnimation, QEasingCurve, pyqtProperty
from PyQt6.QtGui import (
    QColor,
    QFont,
    QPainter,
    QPainterPath,
    QPen,
    QBrush,
)
from PyQt6.QtWidgets import (
    QSizePolicy,
    QWidget,
)

from core.constants import KEY_FINGER_MAP, FINGER_COLORS
from core.audio import CelebrationSoundManager

class KeyboardWidget(QWidget):
    """Virtual keyboard display with next-key highlighting and finger color coding."""

    # Keyboard layout: each row is a list of (key_label, width_multiplier)
    KEYBOARD_LAYOUT = [
        [('`', 1), ('1', 1), ('2', 1), ('3', 1), ('4', 1), ('5', 1), ('6', 1), ('7', 1), ('8', 1), ('9', 1), ('0', 1), ('-', 1), ('=', 1), ('⌫', 2)],
        [('Tab', 1.5), ('Q', 1), ('W', 1), ('E', 1), ('R', 1), ('T', 1), ('Y', 1), ('U', 1), ('I', 1), ('O', 1), ('P', 1), ('[', 1), (']', 1), ('\\', 1.5)],
        [('Caps', 1.75), ('A', 1), ('S', 1), ('D', 1), ('F', 1), ('G', 1), ('H', 1), ('J', 1), ('K', 1), ('L', 1), (';', 1), ("'", 1), ('Enter', 2.25)],
        [('Shift', 2.25), ('Z', 1), ('X', 1), ('C', 1), ('V', 1), ('B', 1), ('N', 1), ('M', 1), (',', 1), ('.', 1), ('/', 1), ('Shift', 2.75)],
        [('Ctrl', 1.5), ('Win', 1.25), ('Alt', 1.25), ('Space', 6.25), ('Alt', 1.25), ('Win', 1.25), ('Menu', 1.25), ('Ctrl', 1.5)],
    ]

    # Map display labels to actual characters
    KEY_CHAR_MAP = {
        'Space': ' ',
        '⌫': 'backspace',
        'Tab': '\t',
        'Enter': '\n',
        'Caps': 'capslock',
        'Shift': 'shift',
        'Ctrl': 'ctrl',
        'Alt': 'alt',
        'Win': 'win',
        'Menu': 'menu',
    }

    def __init__(self, parent=None):
        super().__init__(parent)
        self.next_key: str = ""
        self.error_key: str = ""  # Key that should have been pressed on error
        self.dark_mode: bool = False
        self.setMinimumHeight(260)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Expanding)

    def set_next_key(self, key: str, error: bool = False) -> None:
        """Set the next key to highlight. If error=True, highlight as error."""
        if error:
            self.error_key = key
            self.next_key = ""
        else:
            self.next_key = key
            self.error_key = ""
        self.update()

    def clear_highlights(self) -> None:
        """Clear all key highlights."""
        self.next_key = ""
        self.error_key = ""
        self.update()

    def set_dark_mode(self, enabled: bool) -> None:
        """Toggle dark mode styling."""
        self.dark_mode = enabled
        self.update()

    def paintEvent(self, event) -> None:
        """Draw the keyboard with highlighting."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        # Calculate dimensions
        widget_width = self.width() - 20
        widget_height = self.height() - 20
        
        # Calculate key sizes based on available space
        total_units = 15  # Approximate total width units for longest row
        key_unit_width = widget_width / total_units
        key_height = min(widget_height / 5.5, 32)
        key_spacing = 3
        
        start_x = 10
        y = 10

        # Colors
        if self.dark_mode:
            bg_color = QColor("#2d2d2d")
            key_bg = QColor("#404040")
            key_border = QColor("#555555")
            text_color = QColor("#ffffff")
            highlight_color = QColor("#4CAF50")  # Green for next key
            error_color = QColor("#f44336")  # Red for error
        else:
            bg_color = QColor("#e8e8e8")
            key_bg = QColor("#ffffff")
            key_border = QColor("#cccccc")
            text_color = QColor("#333333")
            highlight_color = QColor("#4CAF50")
            error_color = QColor("#f44336")

        # Draw background
        painter.fillRect(self.rect(), bg_color)

        # Draw each row
        for row in self.KEYBOARD_LAYOUT:
            x = start_x
            for key_label, width_mult in row:
                key_width = key_unit_width * width_mult - key_spacing
                
                # Determine key character
                key_char = self.KEY_CHAR_MAP.get(key_label, key_label.lower())
                
                # Determine key color
                is_next = (self.next_key.lower() == key_char.lower() if self.next_key else False)
                is_error = (self.error_key.lower() == key_char.lower() if self.error_key else False)
                
                if is_next:
                    fill_color = highlight_color
                    current_text_color = QColor("#ffffff")
                elif is_error:
                    fill_color = error_color
                    current_text_color = QColor("#ffffff")
                else:
                    # Use finger color coding
                    finger = KEY_FINGER_MAP.get(key_char.lower(), None)
                    if finger:
                        finger_color = FINGER_COLORS.get(finger, "#ffffff")
                        fill_color = QColor(finger_color)
                        if self.dark_mode:
                            fill_color = fill_color.darker(130)
                        current_text_color = text_color
                    else:
                        fill_color = key_bg
                        current_text_color = text_color

                # Draw key background
                key_rect = QRectF(x, y, key_width, key_height)
                path = QPainterPath()
                path.addRoundedRect(key_rect, 5, 5)
                painter.fillPath(path, fill_color)
                
                # Draw border
                painter.setPen(QPen(key_border, 1))
                painter.drawPath(path)
                
                # Draw label
                painter.setPen(current_text_color)
                font_size = 10 if len(key_label) > 1 else 12
                painter.setFont(QFont("Segoe UI", font_size, QFont.Weight.Medium))
                painter.drawText(key_rect, Qt.AlignmentFlag.AlignCenter, key_label)
                
                x += key_width + key_spacing
            
            y += key_height + key_spacing

        painter.end()


class FingerLegendWidget(QWidget):
    """Small legend showing finger-color mapping."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = False
        self.setFixedHeight(30)

    def set_dark_mode(self, enabled: bool) -> None:
        self.dark_mode = enabled
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        legend_items = [
            ("L.Pinky", "left_pinky"),
            ("L.Ring", "left_ring"),
            ("L.Mid", "left_middle"),
            ("L.Index", "left_index"),
            ("R.Index", "right_index"),
            ("R.Mid", "right_middle"),
            ("R.Ring", "right_ring"),
            ("R.Pinky", "right_pinky"),
            ("Thumb", "thumbs"),
        ]

        x = 5
        item_width = (self.width() - 10) / len(legend_items)
        
        text_color = QColor("#ffffff") if self.dark_mode else QColor("#333333")
        painter.setFont(QFont("Segoe UI", 8))

        for label, finger in legend_items:
            color = QColor(FINGER_COLORS[finger])
            if self.dark_mode:
                color = color.darker(130)
            
            # Draw color swatch
            painter.setBrush(color)
            painter.setPen(Qt.PenStyle.NoPen)
            painter.drawRoundedRect(int(x), 5, 12, 12, 2, 2)
            
            # Draw label
            painter.setPen(text_color)
            painter.drawText(int(x + 15), 15, label)
            
            x += item_width

        painter.end()


class CelebrationOverlay(QWidget):
    """A transparent overlay that displays falling confetti particles and dancing animals."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.setAttribute(Qt.WidgetAttribute.WA_TransparentForMouseEvents)
        self.setAttribute(Qt.WidgetAttribute.WA_TranslucentBackground)
        self.hide()
        
        self.particles: List[Dict] = []
        self.animals = "🦁 🐯 🐻 🦊 🐼 🐨 🐵 🦄 🐸 🐷 🐮 🐔 🦆 🐧 🦉 🦅 🦋 🐝 🐛"
        self.animal_position = 0
        self.animal_speed = 4
        
        self.timer = QTimer(self)
        self.timer.timeout.connect(self._update_particles)
        self.duration_timer = QTimer(self)
        self.duration_timer.setSingleShot(True)
        self.duration_timer.timeout.connect(self.stop)
        
        # Initialize the celebration sound manager
        self._sound = CelebrationSoundManager.get_instance(self)

    def start(self, play_sound: bool = False) -> None:
        """Start the celebration animation.
        
        Args:
            play_sound: If True, also plays the celebration melody (for perfect rounds).
        """
        self.particles = []
        for _ in range(150):
            self.particles.append(self._create_particle())
        
        self.animal_position = 0
        self.raise_()
        self.show()
        self.timer.start(16)  # ~60 FPS
        self.duration_timer.start(3000)  # 3 seconds
        
        # Play celebration sound if requested (perfect round)
        if play_sound:
            self._sound.play()

    def stop(self) -> None:
        self.timer.stop()
        self.hide()
        self.particles = []
        self.animal_position = 0

    def _create_particle(self) -> Dict:
        colors = [
            "#FF5252", "#FF4081", "#E040FB", "#7C4DFF", "#536DFE", 
            "#448AFF", "#40C4FF", "#18FFFF", "#64FFDA", "#69F0AE", 
            "#B2FF59", "#EEFF41", "#FFFF00", "#FFD740", "#FFAB40", "#FF6E40"
        ]
        
        return {
            'x': random.randint(0, self.width()),
            'y': random.randint(-self.height(), 0),
            'vx': random.uniform(-2, 2),
            'vy': random.uniform(2, 5),
            'color': QColor(random.choice(colors)),
            'size': random.randint(5, 10),
            'type': random.choice(['circle', 'rect', 'triangle'])
        }

    def _update_particles(self) -> None:
        for p in self.particles:
            p['x'] += p['vx']
            p['y'] += p['vy']
            p['vy'] += 0.1  # Gravity
        
        # Update animal scroll position
        self.animal_position += self.animal_speed
        text_width = len(self.animals) * 30
        if self.animal_position > self.width() + text_width:
            self.animal_position = -text_width
        
        self.update()

    def paintEvent(self, event) -> None:
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)
        
        # Draw confetti particles
        for p in self.particles:
            painter.setBrush(QBrush(p['color']))
            painter.setPen(Qt.PenStyle.NoPen)
            
            if p['type'] == 'circle':
                painter.drawEllipse(int(p['x']), int(p['y']), p['size'], p['size'])
            elif p['type'] == 'rect':
                painter.drawRect(int(p['x']), int(p['y']), p['size'], p['size'])
            elif p['type'] == 'triangle':
                path = QPainterPath()
                path.moveTo(p['x'], p['y'])
                path.lineTo(p['x'] + p['size'], p['y'])
                path.lineTo(p['x'] + p['size']/2, p['y'] - p['size'])
                path.closeSubpath()
                painter.drawPath(path)
        
        # Draw dancing animals at the top
        animal_font = QFont("Segoe UI Emoji", 32)
        painter.setFont(animal_font)
        
        # Draw semi-transparent background bar for visibility
        painter.setPen(Qt.PenStyle.NoPen)
        painter.setBrush(QBrush(QColor(76, 175, 80, 200)))  # Green with alpha
        painter.drawRect(0, 0, self.width(), 50)
        
        # Draw animals
        painter.setPen(QColor("white"))
        text_width = len(self.animals) * 30
        
        # Draw multiple times for seamless scrolling
        for offset in [-text_width, 0, text_width]:
            painter.drawText(int(self.animal_position + offset), 38, self.animals)


class VirtualHandWidget(QWidget):
    """Virtual hand guide widget that shows animated finger positions for typing."""

    def __init__(self, parent=None):
        super().__init__(parent)
        self.dark_mode = False
        self.current_key = ""
        self.error_key = ""

        # Animation properties for finger highlighting
        self.left_pinky_scale = 1.0
        self.left_ring_scale = 1.0
        self.left_middle_scale = 1.0
        self.left_index_scale = 1.0
        self.right_index_scale = 1.0
        self.right_middle_scale = 1.0
        self.right_ring_scale = 1.0
        self.right_pinky_scale = 1.0
        self.thumb_scale = 1.0

        # Create animations
        self._setup_animations()

        self.setMinimumHeight(200)
        self.setSizePolicy(QSizePolicy.Policy.Expanding, QSizePolicy.Policy.Fixed)

    def _setup_animations(self):
        """Setup smooth scaling animations for finger highlighting."""
        self.animations = {}

        finger_scales = [
            ('left_pinky', 'left_pinky_scale'),
            ('left_ring', 'left_ring_scale'),
            ('left_middle', 'left_middle_scale'),
            ('left_index', 'left_index_scale'),
            ('right_index', 'right_index_scale'),
            ('right_middle', 'right_middle_scale'),
            ('right_ring', 'right_ring_scale'),
            ('right_pinky', 'right_pinky_scale'),
            ('thumbs', 'thumb_scale'),
        ]

        for finger_name, scale_attr in finger_scales:
            anim = QPropertyAnimation(self, scale_attr.encode(), self)
            anim.setDuration(150)  # 150ms animation
            anim.setEasingCurve(QEasingCurve.Type.InOutQuad)
            self.animations[finger_name] = anim

    def set_next_key(self, key: str, error: bool = False) -> None:
        """Set the next key to highlight and animate corresponding finger."""
        # Reset all scales to normal
        for anim in self.animations.values():
            anim.stop()

        # Set all fingers to normal scale
        self.left_pinky_scale = 1.0
        self.left_ring_scale = 1.0
        self.left_middle_scale = 1.0
        self.left_index_scale = 1.0
        self.right_index_scale = 1.0
        self.right_middle_scale = 1.0
        self.right_ring_scale = 1.0
        self.right_pinky_scale = 1.0
        self.thumb_scale = 1.0

        self.current_key = key if not error else ""
        self.error_key = key if error else ""

        # Find which finger should be highlighted
        key_lower = key.lower() if key else ""
        finger = KEY_FINGER_MAP.get(key_lower, None)

        if finger and finger in self.animations:
            # Animate the finger to highlight scale
            anim = self.animations[finger]
            anim.setStartValue(1.0)
            anim.setEndValue(1.3)  # Scale up to 1.3x for highlighting
            anim.start()

        self.update()

    def clear_highlights(self) -> None:
        """Clear all highlights and reset finger scales."""
        for anim in self.animations.values():
            anim.stop()

        self.current_key = ""
        self.error_key = ""

        # Reset all scales to normal
        self.left_pinky_scale = 1.0
        self.left_ring_scale = 1.0
        self.left_middle_scale = 1.0
        self.left_index_scale = 1.0
        self.right_index_scale = 1.0
        self.right_middle_scale = 1.0
        self.right_ring_scale = 1.0
        self.right_pinky_scale = 1.0
        self.thumb_scale = 1.0

        self.update()

    def set_dark_mode(self, enabled: bool) -> None:
        """Toggle dark mode styling."""
        self.dark_mode = enabled
        self.update()

    def _get_finger_scale(self, finger_name: str) -> float:
        """Get the current scale for a finger."""
        scale_map = {
            'left_pinky': self.left_pinky_scale,
            'left_ring': self.left_ring_scale,
            'left_middle': self.left_middle_scale,
            'left_index': self.left_index_scale,
            'right_index': self.right_index_scale,
            'right_middle': self.right_middle_scale,
            'right_ring': self.right_ring_scale,
            'right_pinky': self.right_pinky_scale,
            'thumbs': self.thumb_scale,
        }
        return scale_map.get(finger_name, 1.0)

    def _get_finger_color(self, finger_name: str) -> QColor:
        """Get the color for a finger, considering highlighting."""
        base_color = QColor(FINGER_COLORS.get(finger_name, "#ffffff"))

        if self.dark_mode:
            base_color = base_color.darker(130)

        # Check if this finger should be highlighted
        key_lower = (self.current_key or self.error_key or "").lower()
        highlighted_finger = KEY_FINGER_MAP.get(key_lower, None)

        if finger_name == highlighted_finger:
            if self.error_key:
                return QColor("#f44336")  # Red for errors
            else:
                return QColor("#4CAF50")  # Green for next key

        return base_color

    def paintEvent(self, event) -> None:
        """Draw the virtual hands with finger highlighting."""
        painter = QPainter(self)
        painter.setRenderHint(QPainter.RenderHint.Antialiasing)

        width = self.width()
        height = self.height()

        # Colors
        if self.dark_mode:
            bg_color = QColor("#2d2d2d")
            hand_outline = QColor("#555555")
            text_color = QColor("#ffffff")
        else:
            bg_color = QColor("#e8e8e8")
            hand_outline = QColor("#666666")
            text_color = QColor("#333333")

        # Draw background
        painter.fillRect(self.rect(), bg_color)

        # Calculate hand positions
        left_hand_x = width * 0.25
        right_hand_x = width * 0.75
        hand_y = height * 0.4
        hand_width = width * 0.15
        hand_height = height * 0.4

        # Draw left hand
        self._draw_hand(painter, left_hand_x, hand_y, hand_width, hand_height,
                       hand_outline, is_left=True)

        # Draw right hand
        self._draw_hand(painter, right_hand_x, hand_y, hand_width, hand_height,
                       hand_outline, is_left=False)

        painter.end()

    def _draw_hand(self, painter: QPainter, center_x: float, center_y: float,
                   width: float, height: float, outline_color: QColor, is_left: bool) -> None:
        """Draw a single hand with fingers."""
        # Draw palm (oval shape)
        palm_width = width * 0.8
        palm_height = height * 0.6

        palm_path = QPainterPath()
        palm_path.addEllipse(center_x - palm_width/2, center_y - palm_height/2,
                           palm_width, palm_height)

        # Draw palm outline
        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(QBrush(outline_color.lighter(120)))
        painter.drawPath(palm_path)

        # Draw fingers
        if is_left:
            self._draw_left_fingers(painter, center_x, center_y - height * 0.3,
                                  width, height * 0.7, outline_color)
        else:
            self._draw_right_fingers(painter, center_x, center_y - height * 0.3,
                                   width, height * 0.7, outline_color)

    def _draw_left_fingers(self, painter: QPainter, start_x: float, start_y: float,
                          width: float, height: float, outline_color: QColor) -> None:
        """Draw fingers for left hand."""
        finger_names = ['left_pinky', 'left_ring', 'left_middle', 'left_index']
        finger_width = width * 0.2
        finger_height = height * 0.8

        for i, finger_name in enumerate(finger_names):
            scale = self._get_finger_scale(finger_name)
            color = self._get_finger_color(finger_name)

            # Scale finger dimensions
            scaled_width = finger_width * scale
            scaled_height = finger_height * scale

            # Position finger (from pinky to index, left to right)
            finger_x = start_x + (i * finger_width * 0.9) - (scaled_width - finger_width) / 2
            finger_y = start_y - (scaled_height - finger_height) / 2

            self._draw_finger(painter, finger_x, finger_y, scaled_width, scaled_height, color, outline_color)

    def _draw_right_fingers(self, painter: QPainter, start_x: float, start_y: float,
                           width: float, height: float, outline_color: QColor) -> None:
        """Draw fingers for right hand."""
        finger_names = ['right_index', 'right_middle', 'right_ring', 'right_pinky']
        finger_width = width * 0.2
        finger_height = height * 0.8

        for i, finger_name in enumerate(finger_names):
            scale = self._get_finger_scale(finger_name)
            color = self._get_finger_color(finger_name)

            # Scale finger dimensions
            scaled_width = finger_width * scale
            scaled_height = finger_height * scale

            # Position finger (from index to pinky, left to right)
            finger_x = start_x + (i * finger_width * 0.9) - (scaled_width - finger_width) / 2
            finger_y = start_y - (scaled_height - finger_height) / 2

            self._draw_finger(painter, finger_x, finger_y, scaled_width, scaled_height, color, outline_color)

    def _draw_finger(self, painter: QPainter, x: float, y: float, width: float,
                    height: float, fill_color: QColor, outline_color: QColor) -> None:
        """Draw a single finger as a rounded rectangle."""
        finger_path = QPainterPath()
        finger_path.addRoundedRect(QRectF(x, y, width, height), width * 0.2, width * 0.2)

        painter.setPen(QPen(outline_color, 2))
        painter.setBrush(QBrush(fill_color))
        painter.drawPath(finger_path)

    # Property getters/setters for animations
    def get_left_pinky_scale(self):
        return self.left_pinky_scale

    def set_left_pinky_scale(self, scale):
        self.left_pinky_scale = scale
        self.update()

    def get_left_ring_scale(self):
        return self.left_ring_scale

    def set_left_ring_scale(self, scale):
        self.left_ring_scale = scale
        self.update()

    def get_left_middle_scale(self):
        return self.left_middle_scale

    def set_left_middle_scale(self, scale):
        self.left_middle_scale = scale
        self.update()

    def get_left_index_scale(self):
        return self.left_index_scale

    def set_left_index_scale(self, scale):
        self.left_index_scale = scale
        self.update()

    def get_right_index_scale(self):
        return self.right_index_scale

    def set_right_index_scale(self, scale):
        self.right_index_scale = scale
        self.update()

    def get_right_middle_scale(self):
        return self.right_middle_scale

    def set_right_middle_scale(self, scale):
        self.right_middle_scale = scale
        self.update()

    def get_right_ring_scale(self):
        return self.right_ring_scale

    def set_right_ring_scale(self, scale):
        self.right_ring_scale = scale
        self.update()

    def get_right_pinky_scale(self):
        return self.right_pinky_scale

    def set_right_pinky_scale(self, scale):
        self.right_pinky_scale = scale
        self.update()

    def get_thumb_scale(self):
        return self.thumb_scale

    def set_thumb_scale(self, scale):
        self.thumb_scale = scale
        self.update()

    # PyQt properties for animation
    leftPinkyScale = pyqtProperty(float, get_left_pinky_scale, set_left_pinky_scale)
    leftRingScale = pyqtProperty(float, get_left_ring_scale, set_left_ring_scale)
    leftMiddleScale = pyqtProperty(float, get_left_middle_scale, set_left_middle_scale)
    leftIndexScale = pyqtProperty(float, get_left_index_scale, set_left_index_scale)
    rightIndexScale = pyqtProperty(float, get_right_index_scale, set_right_index_scale)
    rightMiddleScale = pyqtProperty(float, get_right_middle_scale, set_right_middle_scale)
    rightRingScale = pyqtProperty(float, get_right_ring_scale, set_right_ring_scale)
    rightPinkyScale = pyqtProperty(float, get_right_pinky_scale, set_right_pinky_scale)
    thumbScale = pyqtProperty(float, get_thumb_scale, set_thumb_scale)
